"""Background removal service.

Algorithm:
    1. Try local rembg (U2Net) to produce a transparent PNG cutout of the garment.
    2. If rembg is unavailable (not installed — it's an optional, heavy
       dependency; see requirements.txt) or the local run fails, fall back to
       the remove.bg HTTP API.
    3. The caller (the worker) uploads the cutout and generates signed URLs;
       this module never logs image bytes.

Runs inside the RQ worker only — never in a request path.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_REMOVE_BG_URL = "https://api.remove.bg/v1.0/removebg"


def remove_background(image_bytes: bytes) -> bytes:
    """Return a transparent PNG cutout of the garment in `image_bytes`."""
    try:
        return _remove_background_local(image_bytes)
    except Exception:
        logger.warning(
            "Local bg-removal (rembg) unavailable or failed; falling back to remove.bg",
            exc_info=True,
        )

    return _remove_background_via_api(image_bytes)


def _remove_background_local(image_bytes: bytes) -> bytes:
    # Imported lazily: rembg (+ onnxruntime) is a heavy, optional dependency —
    # only a worker that has it installed should pay that cost, and its
    # absence should fall back gracefully rather than break the whole service.
    from rembg import remove  # type: ignore[import-not-found]

    result = remove(image_bytes)
    if not isinstance(result, (bytes, bytearray)) or not result:
        raise RuntimeError("rembg returned an empty or unexpected result")
    return bytes(result)


def _remove_background_via_api(image_bytes: bytes) -> bytes:
    if not settings.REMOVE_BG_API_KEY:
        raise RuntimeError(
            "Background removal unavailable: local rembg failed or isn't "
            "installed, and REMOVE_BG_API_KEY is not set."
        )

    response = httpx.post(
        _REMOVE_BG_URL,
        files={"image_file": ("garment", image_bytes)},
        data={"size": "auto"},
        headers={"X-Api-Key": settings.REMOVE_BG_API_KEY},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.content
