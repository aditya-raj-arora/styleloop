"""Garment API schemas.

`GarmentOut` is the FROZEN CONTRACT between frontend and backend — both build
against this shape in parallel. Change it deliberately and in lockstep with the
frontend types (frontend/src/api/client.ts). `processed_url` is null until the
async worker finishes bg-removal + tagging; the frontend shows a placeholder
until it is populated.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GarmentOut(BaseModel):
    """Serialized garment returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    image_url: str
    processed_url: str | None = None

    category: str | None = None
    colors: list[str] | None = None
    pattern: str | None = None
    fabric: str | None = None
    fabric_confidence: float | None = None
    season: str | None = None
    formality: str | None = None

    state: str
    wear_count: int
    last_worn_at: datetime | None = None
    created_at: datetime


class TagUpdate(BaseModel):
    """User-supplied corrections to auto-tags. All fields optional (partial update)."""

    category: str | None = None
    colors: list[str] | None = None
    pattern: str | None = None
    fabric: str | None = None
    season: str | None = None
    formality: str | None = None


class StateUpdate(BaseModel):
    """Laundry state transition. `state` is one of "clean" | "worn" | "laundry"."""

    state: str


class WardrobeAnalyticsOut(BaseModel):
    """`GET /garments/analytics` — a snapshot of how the wardrobe is actually
    being used, not the frozen contract (safe to extend/change freely)."""

    total_garments: int
    clean_count: int
    worn_count: int
    laundry_count: int

    # Highest wear_count first, capped — see routers/garments.py.
    most_worn: list[GarmentOut]
    # wear_count == 0, oldest upload first (longest sitting unused), capped.
    never_worn: list[GarmentOut]
    # Subset of {"top", "bottom", "dress", "outerwear", "shoes"} with zero
    # clean, tagged garments — mirrors services/rotation.py's categories.
    category_gaps: list[str]
