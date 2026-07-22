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
