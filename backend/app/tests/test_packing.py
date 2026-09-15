"""services/packing.py — pure function, synthetic garments, no DB. See
test_packing_router.py for the GET /packing-list endpoint's own tests."""

from datetime import date

from app.services.packing import (
    PackableGarment,
    generate_packing_list,
    summarize_trip_weather,
)

_START = date(2026, 6, 1)
_END = date(2026, 6, 5)  # 5-day trip


def _garment(id: int, category: str, wear_count: int = 0) -> PackableGarment:
    return PackableGarment(id=id, category=category, wear_count=wear_count)


def _wardrobe(**counts: int) -> list[PackableGarment]:
    """counts like top=3, bottom=2 -> that many synthetic garments per category."""
    garments = []
    next_id = 1
    for category, n in counts.items():
        for _ in range(n):
            garments.append(_garment(next_id, category))
            next_id += 1
    return garments


# --- summarize_trip_weather ---


def test_summarize_trip_weather_with_no_forecast_data() -> None:
    summary = summarize_trip_weather([], _START, _END)
    assert summary.temp_min_c is None
    assert summary.temp_max_c is None
    assert summary.rain is False
    assert summary.days_with_forecast == 0


def test_summarize_trip_weather_only_counts_days_within_the_trip() -> None:
    forecast = [
        {"date": date(2026, 5, 31), "temp_min_c": -5.0, "temp_max_c": -5.0, "rain": True},
        {"date": date(2026, 6, 1), "temp_min_c": 10.0, "temp_max_c": 20.0, "rain": False},
        {"date": date(2026, 6, 2), "temp_min_c": 12.0, "temp_max_c": 22.0, "rain": True},
        {"date": date(2026, 6, 10), "temp_min_c": 99.0, "temp_max_c": 99.0, "rain": False},
    ]
    summary = summarize_trip_weather(forecast, _START, _END)
    assert summary.temp_min_c == 10.0
    assert summary.temp_max_c == 22.0
    assert summary.rain is True  # from the 6/2 entry
    assert summary.days_with_forecast == 2


# --- generate_packing_list ---


def test_packs_one_top_per_day_capped_by_availability() -> None:
    wardrobe = _wardrobe(top=10, bottom=10, shoes=2)
    result = generate_packing_list(wardrobe, num_days=5, forecast=[], start=_START, end=_END)

    tops = next(c for c in result.categories if c.category == "top")
    assert len(tops.garment_ids) == 5
    assert tops.short_by == 0


def test_flags_a_shortfall_when_the_wardrobe_has_too_few() -> None:
    wardrobe = _wardrobe(top=2, bottom=1, shoes=1)
    result = generate_packing_list(wardrobe, num_days=5, forecast=[], start=_START, end=_END)

    tops = next(c for c in result.categories if c.category == "top")
    assert len(tops.garment_ids) == 2
    assert tops.short_by == 3  # wanted 5, only had 2


def test_bottoms_target_is_half_the_trip_rounded_up() -> None:
    wardrobe = _wardrobe(top=10, bottom=10, shoes=2)
    result = generate_packing_list(wardrobe, num_days=5, forecast=[], start=_START, end=_END)

    bottoms = next(c for c in result.categories if c.category == "bottom")
    assert len(bottoms.garment_ids) == 3  # ceil(5/2)


def test_picks_the_least_worn_garments_first() -> None:
    wardrobe = [
        PackableGarment(id=1, category="top", wear_count=5),
        PackableGarment(id=2, category="top", wear_count=0),
        PackableGarment(id=3, category="top", wear_count=2),
        _garment(4, "bottom"),
        _garment(5, "shoes"),
    ]
    result = generate_packing_list(wardrobe, num_days=2, forecast=[], start=_START, end=_END)

    tops = next(c for c in result.categories if c.category == "top")
    assert tops.garment_ids == [2, 3]  # wear_count 0, then 2 — not the 5


def test_no_forecast_defaults_to_needing_outerwear_but_not_rain_gear() -> None:
    wardrobe = _wardrobe(top=2, bottom=2, shoes=1, outerwear=1)
    result = generate_packing_list(wardrobe, num_days=2, forecast=[], start=_START, end=_END)

    assert result.needs_outerwear is True
    assert result.needs_rain_gear is False
    outerwear = next(c for c in result.categories if c.category == "outerwear")
    assert len(outerwear.garment_ids) == 1


def test_warm_forecast_skips_outerwear() -> None:
    wardrobe = _wardrobe(top=2, bottom=2, shoes=1, outerwear=1)
    forecast = [
        {"date": d, "temp_min_c": 22.0, "temp_max_c": 28.0, "rain": False}
        for d in (_START, date(2026, 6, 2))
    ]
    result = generate_packing_list(
        wardrobe, num_days=2, forecast=forecast, start=_START, end=date(2026, 6, 2)
    )

    assert result.needs_outerwear is False
    assert not any(c.category == "outerwear" for c in result.categories)


def test_rain_in_the_forecast_is_flagged() -> None:
    wardrobe = _wardrobe(top=1, bottom=1, shoes=1)
    forecast = [{"date": _START, "temp_min_c": 20.0, "temp_max_c": 25.0, "rain": True}]
    result = generate_packing_list(
        wardrobe, num_days=1, forecast=forecast, start=_START, end=_START
    )

    assert result.needs_rain_gear is True


def test_dresses_are_offered_as_extras_not_counted_against_tops_and_bottoms() -> None:
    wardrobe = _wardrobe(top=5, bottom=3, dress=2, shoes=1)
    result = generate_packing_list(wardrobe, num_days=3, forecast=[], start=_START, end=_END)

    dresses = next(c for c in result.categories if c.category == "dress")
    assert len(dresses.garment_ids) == 2  # capped by availability, not reduced by tops/bottoms
    tops = next(c for c in result.categories if c.category == "top")
    assert len(tops.garment_ids) == 3  # unaffected by the dresses being available


def test_shoes_are_capped_at_two_pairs() -> None:
    wardrobe = _wardrobe(top=1, bottom=1, shoes=5)
    result = generate_packing_list(wardrobe, num_days=10, forecast=[], start=_START, end=_END)

    shoes = next(c for c in result.categories if c.category == "shoes")
    assert len(shoes.garment_ids) == 2
    assert shoes.short_by == 0


def test_empty_wardrobe_produces_only_shortfall_categories() -> None:
    result = generate_packing_list([], num_days=3, forecast=[], start=_START, end=_END)

    # No forecast -> needs_outerwear defaults True, so outerwear is attempted
    # (and comes back a pure shortfall) even though nothing's available.
    assert {c.category for c in result.categories} == {"top", "bottom", "shoes", "outerwear"}
    assert all(c.garment_ids == [] and c.short_by > 0 for c in result.categories)
