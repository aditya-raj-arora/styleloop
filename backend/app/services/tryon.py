"""Virtual try-on service.

Algorithm:
    - Render an outfit onto the user's base photo via FASHN's virtual
      try-on model, called through fal.ai's queue API
      (https://fal.ai/models/fal-ai/fashn/tryon/v1.6).
    - FASHN takes exactly one `garment_image` per call — it cannot composite
      a top and a bottom in one request. So a multi-garment outfit is
      rendered as a *sequence*: render the first garment onto the base
      photo, then render the second garment onto *that* output, and so on —
      each call's result becomes the next call's "model" image.
    - FASHN's `category` only covers `tops` / `bottoms` / `one-pieces` (no
      outerwear or shoes) — see docs/rotation-scoring-design-note.md's
      Sprint 4 notes. Garments outside that set are silently skipped rather
      than failing the whole render: a coat still shows the shirt+pants
      underneath, it just isn't drawn on top.
    - On-demand only, and cached by `(user_id, outfit_id, photo_version)` —
      see models/tryon.py — so repeat views are free and instant. Caching
      and the per-user daily cap are the caller's (routers/outfits.py,
      workers/tasks.generate_tryon) responsibility; this module only talks
      to FASHN.

Runs in the RQ worker only (see workers/tasks.generate_tryon). Never blocks
a request.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.config import settings

_FAL_QUEUE_BASE = "https://queue.fal.run"
_FAL_MODEL_ID = "fal-ai/fashn/tryon/v1.6"

_POLL_INTERVAL_SECONDS = 2.0
_POLL_TIMEOUT_SECONDS = 60.0  # per garment; FASHN's own docs quote 5-8s typical

# FASHN's `category` enum is tops/bottoms/one-pieces/auto — no outerwear or
# shoes. Map our garment categories to it; anything absent from this dict is
# skipped by render_tryon rather than sent to FASHN.
_CATEGORY_MAP: dict[str, str] = {"top": "tops", "bottom": "bottoms", "dress": "one-pieces"}


class TryonError(Exception):
    """Raised when a render can't be produced (no renderable garments, a
    FASHN call fails, or polling times out). Caller (the worker task) treats
    this as "no cached render" and logs — never crashes the worker."""


@dataclass(frozen=True)
class TryonGarment:
    """A garment as seen by the renderer — just what FASHN needs, so this
    module never touches the Garment ORM model directly."""

    image_url: str  # presigned URL to the garment's processed cutout
    category: str  # e.g. 'top' | 'bottom' | 'dress' | 'outerwear' | 'shoes'


def _headers() -> dict[str, str]:
    return {"Authorization": f"Key {settings.FASHN_API_KEY}", "Content-Type": "application/json"}


def _submit(model_image_url: str, garment_image_url: str, category: str) -> str:
    response = httpx.post(
        f"{_FAL_QUEUE_BASE}/{_FAL_MODEL_ID}",
        headers=_headers(),
        json={
            "model_image": model_image_url,
            "garment_image": garment_image_url,
            "category": category,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["request_id"]


def _poll_until_complete(request_id: str) -> None:
    deadline = time.monotonic() + _POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        response = httpx.get(
            f"{_FAL_QUEUE_BASE}/{_FAL_MODEL_ID}/requests/{request_id}/status",
            headers=_headers(),
            timeout=15.0,
        )
        response.raise_for_status()
        state = response.json()["status"]
        if state == "COMPLETED":
            return
        if state not in ("IN_QUEUE", "IN_PROGRESS"):
            raise TryonError(f"Unexpected FASHN status {state!r} for request {request_id}")
        time.sleep(_POLL_INTERVAL_SECONDS)
    raise TryonError(f"Timed out waiting for FASHN render (request {request_id})")


def _fetch_result_url(request_id: str) -> str:
    response = httpx.get(
        f"{_FAL_QUEUE_BASE}/{_FAL_MODEL_ID}/requests/{request_id}",
        headers=_headers(),
        timeout=15.0,
    )
    response.raise_for_status()
    images = response.json().get("images") or []
    if not images:
        raise TryonError(f"FASHN returned no images for request {request_id}")
    return images[0]["url"]


def render_tryon(base_photo_url: str, garments: list[TryonGarment]) -> bytes:
    """Sequentially composite `garments` onto `base_photo_url` via FASHN.
    Returns the final rendered image's bytes.

    Raises `TryonError` if nothing in `garments` was renderable (see
    `_CATEGORY_MAP`), a FASHN call fails, or polling times out.
    """
    if not settings.FASHN_API_KEY:
        raise TryonError("FASHN_API_KEY is not configured")

    current_image_url = base_photo_url
    rendered_any = False

    for garment in garments:
        fashn_category = _CATEGORY_MAP.get(garment.category)
        if fashn_category is None:
            continue  # unsupported category (e.g. outerwear/shoes) - skip, don't fail

        try:
            request_id = _submit(current_image_url, garment.image_url, fashn_category)
            _poll_until_complete(request_id)
            current_image_url = _fetch_result_url(request_id)
        except httpx.HTTPError as exc:
            raise TryonError(f"FASHN request failed: {exc}") from exc
        rendered_any = True

    if not rendered_any:
        raise TryonError(
            "No renderable garments in this outfit (need a top/bottom or a dress)"
        )

    response = httpx.get(current_image_url, timeout=30.0)
    response.raise_for_status()
    return response.content
