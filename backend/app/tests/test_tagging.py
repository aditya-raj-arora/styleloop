"""Deterministic color extraction + graceful degradation without an API key.

No DB or network needed — these exercise pure functions and the
ANTHROPIC_API_KEY-unset short-circuit in tag_garment.
"""

import io

from PIL import Image

from app.services import tagging


def _solid_rgba(size: tuple[int, int], rgb: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    w, h = size
    for x in range(w // 4, 3 * w // 4):
        for y in range(h // 4, 3 * h // 4):
            img.putpixel((x, y), (*rgb, 255))
    return img


def test_extract_colors_identifies_dominant_named_color() -> None:
    img = _solid_rgba((80, 80), (200, 30, 30))  # red
    assert tagging._extract_colors(img) == ["red"]


def test_extract_colors_is_deterministic() -> None:
    img = _solid_rgba((80, 80), (33, 80, 180))  # blue
    assert tagging._extract_colors(img) == tagging._extract_colors(img)


def test_extract_colors_orders_by_cluster_size() -> None:
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    for x in range(100):
        for y in range(100):
            if x < 70:
                img.putpixel((x, y), (33, 80, 180, 255))  # blue, 70%
            else:
                img.putpixel((x, y), (245, 245, 245, 255))  # white, 30%
    assert tagging._extract_colors(img) == ["blue", "white"]


def test_extract_colors_ignores_transparent_background() -> None:
    # Fully transparent canvas with a small opaque green patch.
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    for x in range(45, 55):
        for y in range(45, 55):
            img.putpixel((x, y), (46, 125, 50, 255))
    assert tagging._extract_colors(img) == ["green"]


def test_tag_garment_degrades_gracefully_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(tagging.settings, "ANTHROPIC_API_KEY", "")

    img = _solid_rgba((80, 80), (245, 245, 245))  # white
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    result = tagging.tag_garment(buf.getvalue())

    assert result["colors"] == ["white"]
    assert result["category"] is None
    assert result["pattern"] is None
    assert result["fabric"] is None
    assert result["fabric_confidence"] is None
    assert result["season"] is None
    assert result["formality"] is None
