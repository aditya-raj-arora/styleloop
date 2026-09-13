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
