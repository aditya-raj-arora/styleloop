"""Outfit API schemas.

`OutfitOut` mirrors the `Outfit` model exactly — it's the contract Sprint 2's
`GET /outfits/daily` will return, and what Sprint 1's Dashboard/Swipe mock
skeletons are built against ahead of the real endpoint (see docs/TASKS.md).
Same "frozen contract" discipline as `GarmentOut`: change it deliberately and
in lockstep with `frontend/src/api/client.ts`.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class OutfitOut(BaseModel):
    """Serialized outfit returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    garment_ids: list[int]
    score: float | None = None
    generated_for: date
    created_at: datetime


class FeedbackIn(BaseModel):
    """A swipe action on an outfit. `action` is one of "like" | "dislike" | "skip"."""

    action: str


class ShareOut(BaseModel):
    """`POST/GET .../share` — the owner-facing view of a share link.
    `share_url` is the frontend's public route, not an API path."""

    share_token: str
    share_url: str


class SharedGarmentOut(BaseModel):
    """A garment as shown on a public share page — deliberately a subset of
    `GarmentOut`: no `user_id`, `state`, `wear_count`, or `last_worn_at`.
    Those describe the owner's habits, not the outfit itself, and this page
    needs no auth to view."""

    model_config = ConfigDict(from_attributes=True)

    image_url: str
    processed_url: str | None = None
    category: str | None = None
    colors: list[str] | None = None
    pattern: str | None = None
    season: str | None = None
    formality: str | None = None


class SharedOutfitOut(BaseModel):
    """`GET /outfits/shared/{token}` — the public, unauthenticated view."""

    generated_for: date
    score: float | None = None
    garments: list[SharedGarmentOut]
