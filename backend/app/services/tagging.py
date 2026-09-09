"""Auto-tagging service.

Algorithm:
    - colors:   deterministic — quantize the cutout's opaque pixels via k-means
                in LAB space (fixed seed) and map each cluster center to the
                nearest entry in a fixed named palette. Fully reproducible,
                no model, no API call.
    - category / pattern / season / formality:
                zero-shot classification via a single Claude vision call over
                fixed label sets (see `_LABELS`). Disabled (all None) when
                ANTHROPIC_API_KEY is unset — colors still work without it.
    - fabric:   returned by the same vision call with a confidence score;
                stored as None when confidence is below
                FABRIC_CONFIDENCE_THRESHOLD, so the UI can prompt the user
                instead of showing a low-confidence guess.

Input is expected to be the *processed* (background-removed) cutout — a PNG
with a transparent background — so color extraction and classification both
ignore background pixels. Returns a dict matching the Garment tag columns.
Runs in the RQ worker only.
"""

from __future__ import annotations

import io
import logging
from typing import Literal

import numpy as np
from PIL import Image
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

# --- Fixed label sets for zero-shot classification ---------------------------

_CATEGORIES = ["top", "bottom", "dress", "outerwear", "shoes", "accessory"]
_PATTERNS = ["solid", "striped", "plaid", "floral", "polka_dot", "graphic", "animal_print", "other"]
_FABRICS = ["cotton", "denim", "wool", "leather", "silk", "polyester", "linen", "knit", "other"]
_SEASONS = ["spring", "summer", "fall", "winter", "all_season"]
_FORMALITIES = ["casual", "smart_casual", "formal"]

# --- Fixed named color palette (approximate sRGB references) -----------------

_PALETTE_RGB: dict[str, tuple[int, int, int]] = {
    "black": (20, 20, 20),
    "white": (245, 245, 245),
    "gray": (128, 128, 128),
    "beige": (222, 202, 168),
    "brown": (101, 67, 33),
    "red": (200, 30, 30),
    "orange": (230, 126, 34),
    "yellow": (240, 200, 30),
    "green": (46, 125, 50),
    "teal": (0, 121, 121),
    "blue": (33, 80, 180),
    "navy": (20, 30, 80),
    "purple": (110, 60, 160),
    "pink": (230, 150, 180),
}


def _srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """Vectorized sRGB (0-255, shape [..., 3]) -> CIE LAB conversion (D65)."""
    c = rgb.astype(np.float64) / 255.0
    linear = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

    r, g, b = linear[..., 0], linear[..., 1], linear[..., 2]
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    xn, yn, zn = 0.95047, 1.0, 1.08883
    xr, yr, zr = x / xn, y / yn, z / zn

    delta = 6 / 29

    def f(t: np.ndarray) -> np.ndarray:
        return np.where(t > delta**3, np.cbrt(t), t / (3 * delta**2) + 4 / 29)

    fx, fy, fz = f(xr), f(yr), f(zr)
    lightness = 116 * fy - 16
    a = 500 * (fx - fy)
    bb = 200 * (fy - fz)
    return np.stack([lightness, a, bb], axis=-1)


_PALETTE_LAB = {
    name: _srgb_to_lab(np.array(rgb, dtype=np.float64)) for name, rgb in _PALETTE_RGB.items()
}


def _kmeans_lab(points: np.ndarray, k: int, seed: int = 42, iterations: int = 15) -> np.ndarray:
    """Minimal, deterministic Lloyd's-algorithm k-means. Returns (k, 3) centers.

    `points` is downsampled before this is called, so a handful of iterations
    over a fixed seed converges quickly and reproducibly — no external ML
    dependency needed for this.
    """
    rng = np.random.default_rng(seed)
    k = min(k, len(points))
    centers = points[rng.choice(len(points), size=k, replace=False)]

    for _ in range(iterations):
        distances = np.linalg.norm(points[:, None, :] - centers[None, :, :], axis=2)
        assignments = np.argmin(distances, axis=1)
        new_centers = np.array(
            [
                points[assignments == i].mean(axis=0) if np.any(assignments == i) else centers[i]
                for i in range(k)
            ]
        )
        if np.allclose(new_centers, centers):
            break
        centers = new_centers

    counts = np.bincount(assignments, minlength=k)
    order = np.argsort(-counts)
    return centers[order]


def _extract_colors(image: Image.Image, max_colors: int = 3) -> list[str]:
    """Dominant colors of the opaque region, as names from the fixed palette."""
    rgba = image.convert("RGBA")
    rgba.thumbnail((150, 150))
    arr = np.array(rgba)

    alpha = arr[..., 3]
    opaque = arr[alpha > 16][:, :3]
    if len(opaque) == 0:
        return []

    lab_points = _srgb_to_lab(opaque.astype(np.float64))
    centers = _kmeans_lab(lab_points, k=max_colors)

    names: list[str] = []
    for center in centers:
        best_name = min(
            _PALETTE_LAB, key=lambda name: float(np.linalg.norm(_PALETTE_LAB[name] - center))
        )
        if best_name not in names:
            names.append(best_name)
    return names


# --- Vision classification (Claude API) ---------------------------------------


class _GarmentClassification(BaseModel):
    category: Literal["top", "bottom", "dress", "outerwear", "shoes", "accessory"]
    pattern: Literal[
        "solid", "striped", "plaid", "floral", "polka_dot", "graphic", "animal_print", "other"
    ]
    season: Literal["spring", "summer", "fall", "winter", "all_season"]
    formality: Literal["casual", "smart_casual", "formal"]
    fabric: Literal[
        "cotton", "denim", "wool", "leather", "silk", "polyester", "linen", "knit", "other"
    ]
    fabric_confidence: float


def _classify(image_bytes: bytes, media_type: str) -> _GarmentClassification | None:
    """Zero-shot classify category/pattern/fabric/season/formality via Claude.

    Returns None (caller degrades gracefully) if ANTHROPIC_API_KEY is unset or
    the call fails — tagging should never take down the whole worker task.
    """
    if not settings.ANTHROPIC_API_KEY:
        return None

    import anthropic  # lazy: keeps this module importable without the SDK installed

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    try:
        response = client.messages.parse(
            model=settings.VISION_MODEL,
            max_tokens=1024,
            output_config={"effort": "low"},  # simple classification, not deep reasoning
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": _b64(image_bytes),
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Classify this single clothing item cutout. Pick exactly one "
                                "value per field from the schema's allowed labels. "
                                "fabric_confidence is your confidence (0.0-1.0) in the "
                                "fabric guess."
                            ),
                        },
                    ],
                }
            ],
            output_format=_GarmentClassification,
        )
    except Exception:
        logger.warning(
            "Vision classification failed; category/pattern/fabric left unset", exc_info=True
        )
        return None

    return response.parsed_output


def _b64(data: bytes) -> str:
    import base64

    return base64.standard_b64encode(data).decode("utf-8")


def tag_garment(image_bytes: bytes) -> dict:
    """Tag a garment cutout. See module docstring for the algorithm per field."""
    image = Image.open(io.BytesIO(image_bytes))
    media_type = Image.MIME.get(image.format or "PNG", "image/png")

    colors = _extract_colors(image)
    classification = _classify(image_bytes, media_type)

    if classification is None:
        return {
            "colors": colors,
            "category": None,
            "pattern": None,
            "fabric": None,
            "fabric_confidence": None,
            "season": None,
            "formality": None,
        }

    fabric = classification.fabric
    fabric_confidence = classification.fabric_confidence
    if fabric_confidence < settings.FABRIC_CONFIDENCE_THRESHOLD:
        fabric = None

    return {
        "colors": colors,
        "category": classification.category,
        "pattern": classification.pattern,
        "fabric": fabric,
        "fabric_confidence": fabric_confidence,
        "season": classification.season,
        "formality": classification.formality,
    }
