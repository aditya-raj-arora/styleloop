"""Background removal service.

Algorithm:
    1. Try local rembg (pinned to the lightweight u2netp model — see
       `_get_rembg_session`) to produce a transparent PNG cutout of the garment.
    2. If rembg is unavailable (not installed — it's an optional, heavy
       dependency; see requirements.txt) or the local run fails, fall back to
       the DeepAI background-remover HTTP API.
    3. The caller (the worker) uploads the cutout and generates signed URLs;
       this module never logs image bytes.

Runs inside the RQ worker only — never in a request path.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_DEEPAI_URL = "https://api.deepai.org/api/background-remover"


def remove_background(image_bytes: bytes) -> bytes:
    """Return a transparent PNG cutout of the garment in `image_bytes`."""
    try:
        return _remove_background_local(image_bytes)
    except Exception:
        logger.warning(
            "Local bg-removal (rembg) unavailable or failed; falling back to DeepAI",
            exc_info=True,
        )

    return _remove_background_via_api(image_bytes)


_rembg_session = None  # cached across calls — loaded once per worker process


def _get_rembg_session():
    global _rembg_session
    if _rembg_session is None:
        from rembg import new_session  # type: ignore[import-not-found]

        # Explicitly pin the lightweight "u2netp" model (~4.5MB). rembg's
        # own default has grown heavier over versions (e.g. bria-rmbg-2.0 in
        # 2.0.x) — that default OOM-killed a 1GB worker even with 2GB of
        # swap. u2netp trades a little quality for a much smaller memory
        # footprint, which matters more on a small always-on instance.
        _rembg_session = new_session("u2netp")
    return _rembg_session


def _remove_background_local(image_bytes: bytes) -> bytes:
    # Imported lazily: rembg (+ onnxruntime) is a heavy, optional dependency —
    # only a worker that has it installed should pay that cost, and its
    # absence should fall back gracefully rather than break the whole service.
    from rembg import remove  # type: ignore[import-not-found]

    result = remove(image_bytes, session=_get_rembg_session())
    if not isinstance(result, (bytes, bytearray)) or not result:
        raise RuntimeError("rembg returned an empty or unexpected result")
    return bytes(result)


def _remove_background_via_api(image_bytes: bytes) -> bytes:
    if not settings.DEEPAI_API_KEY:
        raise RuntimeError(
            "Background removal unavailable: local rembg failed or isn't "
            "installed, and DEEPAI_API_KEY is not set."
        )

    response = httpx.post(
        _DEEPAI_URL,
        files={"image": ("garment", image_bytes)},
        headers={"api-key": settings.DEEPAI_API_KEY},
        timeout=30.0,
    )
    response.raise_for_status()

    output_url = response.json().get("output_url")
    if not output_url:
        raise RuntimeError("DeepAI background-remover response missing output_url")

    # DeepAI returns a URL to the result rather than the image bytes directly.
    output = httpx.get(output_url, timeout=30.0)
    output.raise_for_status()
    return output.content
