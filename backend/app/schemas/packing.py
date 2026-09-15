"""Packing-list API schemas — GET /packing-list. Not the frozen contract
(GarmentOut is reused as-is for the chosen garments; nothing here is load-bearing
for any other endpoint), so this can evolve freely.
"""

from datetime import date

from pydantic import BaseModel

from app.schemas.garment import GarmentOut


class TripWeatherOut(BaseModel):
    temp_min_c: float | None
    temp_max_c: float | None
    rain: bool
    # How many of the trip's days actually had forecast data — OpenWeatherMap's
    # free tier only covers ~5 days out, so a longer or further-out trip may
    # show 0 without the forecast having "failed".
    days_with_forecast: int


class PackingCategoryOut(BaseModel):
    category: str
    garments: list[GarmentOut]
    # > 0 means the algorithm wanted more of this category than the clean,
    # tagged wardrobe actually had.
    short_by: int


class PackingListOut(BaseModel):
    start_date: date
    end_date: date
    num_days: int
    weather: TripWeatherOut
    needs_outerwear: bool
    needs_rain_gear: bool
    categories: list[PackingCategoryOut]
