"""Packing-list generator — weather + duration aware.

Given a trip's length and its forecast (services/weather.get_forecast), picks
which clean, tagged garments to bring: how many tops/bottoms scale with trip
length, whether to flag outerwear/rain gear, and which specific garments to
suggest (favoring the least-recently-worn, so packing doubles as another way
the wardrobe rotates rather than always grabbing the same favorites).

Stays pure — no DB, no HTTP — same discipline as rotation.py's
`generate_outfits`: the router owns fetching garments and calling
`weather.get_forecast`, this module just decides what goes in the bag.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

# Below this trip low, recommend packing outerwear. Matches the general
# "chilly" cutoff rotation.py's own validity scoring uses for outerwear.
_COLD_THRESHOLD_C = 15.0

# How many of each category a trip of `num_days` calls for, before capping to
# what's actually in the clean, tagged wardrobe. Bottoms/shoes are assumed
# reusable across a couple of days each; tops are not.
_MAX_SHOES = 2


@dataclass(frozen=True)
class PackableGarment:
    """The subset of a Garment the packing algorithm needs — mirrors
    rotation.ScoringGarment's shape/spirit, kept separate since packing
    doesn't care about season/formality the way daily rotation scoring does."""

    id: int
    category: str
    wear_count: int


@dataclass(frozen=True)
class TripWeather:
    temp_min_c: float | None
    temp_max_c: float | None
    rain: bool
    days_with_forecast: int


@dataclass(frozen=True)
class PackingCategory:
    category: str
    garment_ids: list[int]
    # The algorithm would have liked to pack more of this category than the
    # wardrobe actually has clean and tagged — a real "you're short N shirts
    # for this trip" signal, not just a cosmetic detail.
    short_by: int


@dataclass(frozen=True)
class PackingList:
    num_days: int
    weather: TripWeather
    needs_outerwear: bool
    needs_rain_gear: bool
    categories: list[PackingCategory]


def summarize_trip_weather(
    forecast: list[dict], start: date, end: date
) -> TripWeather:
    """Collapse whatever forecast days fall within [start, end] into one
    trip-level summary. A day outside the forecast's window (most trips
    booked more than ~5 days out) simply isn't counted — `days_with_forecast`
    tells the caller how much of the trip that summary actually covers."""
    relevant = [f for f in forecast if start <= f["date"] <= end]
    if not relevant:
        return TripWeather(temp_min_c=None, temp_max_c=None, rain=False, days_with_forecast=0)

    mins = [f["temp_min_c"] for f in relevant if f["temp_min_c"] is not None]
    maxs = [f["temp_max_c"] for f in relevant if f["temp_max_c"] is not None]
    return TripWeather(
        temp_min_c=min(mins) if mins else None,
        temp_max_c=max(maxs) if maxs else None,
        rain=any(f["rain"] for f in relevant),
        days_with_forecast=len(relevant),
    )


def _pick(garments: list[PackableGarment], category: str, target: int) -> PackingCategory:
    """Choose up to `target` garments of `category`, freshest (least worn)
    first — wear_count ascending, then id for a deterministic tie-break —
    so a packing list doesn't just keep reaching for the same top."""
    available = sorted(
        (g for g in garments if g.category == category), key=lambda g: (g.wear_count, g.id)
    )
    chosen = available[:target]
    return PackingCategory(
        category=category,
        garment_ids=[g.id for g in chosen],
        short_by=max(0, target - len(available)),
    )


def generate_packing_list(
    garments: list[PackableGarment], num_days: int, forecast: list[dict], start: date, end: date
) -> PackingList:
    """`garments` should already be filtered to the user's clean, tagged
    wardrobe (same eligibility rotation.py uses for daily outfits) —
    packing something dirty or untagged isn't useful, and this function
    doesn't know how to check either."""
    weather = summarize_trip_weather(forecast, start, end)
    # No forecast signal at all is treated as "could be cold" (pack a layer
    # just in case) rather than "definitely not cold" — the safer default
    # for something you can't check again once you've left. Rain gets no
    # such benefit of the doubt: flagging it without evidence would just be
    # noise on every long-range trip, where a forecast never covers more
    # than the first few days anyway.
    needs_outerwear = weather.temp_min_c is None or weather.temp_min_c < _COLD_THRESHOLD_C
    needs_rain_gear = weather.rain

    bottoms_target = max(1, math.ceil(num_days / 2))
    categories = [
        _pick(garments, "top", num_days),
        _pick(garments, "bottom", bottoms_target),
        _pick(garments, "shoes", _MAX_SHOES),
    ]
    if any(g.category == "dress" for g in garments):
        # Dresses stand in for a top+bottom day — offered as extras, not
        # counted against the tops/bottoms targets above.
        categories.append(_pick(garments, "dress", num_days))
    if needs_outerwear:
        # Unlike dresses, always attempted (not gated on already owning any)
        # — "you need a jacket for this trip and have none" is exactly the
        # kind of gap worth surfacing, not silently skipping.
        categories.append(_pick(garments, "outerwear", 1))

    return PackingList(
        num_days=num_days,
        weather=weather,
        needs_outerwear=needs_outerwear,
        needs_rain_gear=needs_rain_gear,
        categories=[c for c in categories if c.garment_ids or c.short_by > 0],
    )
