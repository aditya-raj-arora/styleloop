"""Scoring spike (Sprint 1 de-risking work for Sprint 2's rotation engine).

Pure function, synthetic garments, no DB — see rotation.py's module docstring
and docs/rotation-scoring-design-note.md for the design writeup.
"""

from datetime import date, timedelta

from app.services.rotation import (
    ScoringGarment,
    generate_candidates,
    generate_outfits,
    score_outfit,
)

_TODAY = date(2026, 1, 15)
_MILD_WEATHER = {"temp_c": 18.0, "condition": "Clear", "rain": False}
_COLD_WEATHER = {"temp_c": 2.0, "condition": "Clear", "rain": False}
_HOT_WEATHER = {"temp_c": 30.0, "condition": "Clear", "rain": False}


def _garment(**overrides) -> ScoringGarment:
    defaults = {
        "id": 1,
        "season": "all_season",
        "formality": "casual",
        "wear_count": 0,
        "last_worn_at": None,
        "category": "top",
    }
    defaults.update(overrides)
    return ScoringGarment(**defaults)


def test_all_season_never_mismatches_weather() -> None:
    outfit = [_garment(season="all_season")]
    hot = score_outfit(outfit, weather=_HOT_WEATHER, today=_TODAY, user_id=1)
    cold = score_outfit(outfit, weather=_COLD_WEATHER, today=_TODAY, user_id=1)
    mild = score_outfit(outfit, weather=_MILD_WEATHER, today=_TODAY, user_id=1)
    # Validity term is identical across all three — only the (tiny) jitter can differ.
    assert abs(hot - mild) < 0.2
    assert abs(cold - mild) < 0.2


def test_summer_garment_is_penalized_in_cold_weather() -> None:
    warm_outfit = [_garment(id=1, season="summer")]
    neutral_outfit = [_garment(id=1, season="all_season")]

    warm_score = score_outfit(warm_outfit, weather=_COLD_WEATHER, today=_TODAY, user_id=1)
    neutral_score = score_outfit(neutral_outfit, weather=_COLD_WEATHER, today=_TODAY, user_id=1)

    assert warm_score < neutral_score


def test_winter_garment_is_penalized_in_hot_weather() -> None:
    cold_outfit = [_garment(id=1, season="winter")]
    neutral_outfit = [_garment(id=1, season="all_season")]

    cold_score = score_outfit(cold_outfit, weather=_HOT_WEATHER, today=_TODAY, user_id=1)
    neutral_score = score_outfit(neutral_outfit, weather=_HOT_WEATHER, today=_TODAY, user_id=1)

    assert cold_score < neutral_score


def test_recently_worn_garment_scores_lower_than_never_worn() -> None:
    recent = [_garment(id=1, last_worn_at=_TODAY - timedelta(days=1))]
    never_worn = [_garment(id=1, last_worn_at=None)]

    recent_score = score_outfit(recent, weather=_MILD_WEATHER, today=_TODAY, user_id=1)
    never_worn_score = score_outfit(never_worn, weather=_MILD_WEATHER, today=_TODAY, user_id=1)

    assert recent_score < never_worn_score


def test_worn_a_week_ago_is_not_penalized() -> None:
    a_week_ago = [_garment(id=1, last_worn_at=_TODAY - timedelta(days=7))]
    never_worn = [_garment(id=1, last_worn_at=None)]

    week_score = score_outfit(a_week_ago, weather=_MILD_WEATHER, today=_TODAY, user_id=1)
    never_worn_score = score_outfit(never_worn, weather=_MILD_WEATHER, today=_TODAY, user_id=1)

    assert abs(week_score - never_worn_score) < 0.01


def test_underworn_garment_scores_higher_than_overworn() -> None:
    underworn = [_garment(id=1, wear_count=0)]
    overworn = [_garment(id=1, wear_count=20)]

    underworn_score = score_outfit(underworn, weather=_MILD_WEATHER, today=_TODAY, user_id=1)
    overworn_score = score_outfit(overworn, weather=_MILD_WEATHER, today=_TODAY, user_id=1)

    assert underworn_score > overworn_score


def test_taste_weight_rewards_liked_categories() -> None:
    outfit = [_garment(id=1, category="dress")]

    liked = score_outfit(
        outfit, weather=_MILD_WEATHER, today=_TODAY, user_id=1, taste_weights={"dress": 2.0}
    )
    disliked = score_outfit(
        outfit, weather=_MILD_WEATHER, today=_TODAY, user_id=1, taste_weights={"dress": -2.0}
    )
    neutral = score_outfit(outfit, weather=_MILD_WEATHER, today=_TODAY, user_id=1)

    assert liked > neutral > disliked


def test_score_is_deterministic_for_the_same_day() -> None:
    outfit = [_garment(id=1), _garment(id=2, category="bottom")]
    first = score_outfit(outfit, weather=_MILD_WEATHER, today=_TODAY, user_id=7)
    second = score_outfit(outfit, weather=_MILD_WEATHER, today=_TODAY, user_id=7)
    assert first == second


def test_jitter_varies_across_days_but_stays_small() -> None:
    outfit = [_garment(id=1), _garment(id=2, category="bottom")]
    scores = {
        score_outfit(
            outfit,
            weather=_MILD_WEATHER,
            today=_TODAY + timedelta(days=offset),
            user_id=7,
        )
        for offset in range(10)
    }
    # Different days should not all collapse to the exact same score...
    assert len(scores) > 1
    # ...but the spread should stay small relative to the real scoring terms
    # (jitter is a tie-breaker, not a second scoring signal).
    assert max(scores) - min(scores) < 0.2


def test_jitter_varies_across_users_for_the_same_day() -> None:
    outfit = [_garment(id=1), _garment(id=2, category="bottom")]
    score_user_a = score_outfit(outfit, weather=_MILD_WEATHER, today=_TODAY, user_id=1)
    score_user_b = score_outfit(outfit, weather=_MILD_WEATHER, today=_TODAY, user_id=2)
    assert score_user_a != score_user_b


# --- generate_candidates / generate_outfits (Sprint 2 candidate search) -----


def test_no_candidates_without_a_top_bottom_or_dress() -> None:
    wardrobe = [_garment(id=1, category="shoes"), _garment(id=2, category="outerwear")]
    candidates = generate_candidates(wardrobe, weather=_MILD_WEATHER, today=_TODAY, user_id=1)
    assert candidates == []


def test_top_and_bottom_form_a_candidate() -> None:
    wardrobe = [_garment(id=1, category="top"), _garment(id=2, category="bottom")]
    candidates = generate_candidates(wardrobe, weather=_MILD_WEATHER, today=_TODAY, user_id=1)
    assert len(candidates) == 1
    assert set(candidates[0][0]) == {1, 2}


def test_dress_alone_forms_a_candidate() -> None:
    wardrobe = [_garment(id=1, category="dress")]
    candidates = generate_candidates(wardrobe, weather=_MILD_WEATHER, today=_TODAY, user_id=1)
    assert len(candidates) == 1
    assert candidates[0][0] == (1,)


def test_shoes_are_added_when_available() -> None:
    wardrobe = [
        _garment(id=1, category="top"),
        _garment(id=2, category="bottom"),
        _garment(id=3, category="shoes"),
    ]
    candidates = generate_candidates(wardrobe, weather=_MILD_WEATHER, today=_TODAY, user_id=1)
    assert set(candidates[0][0]) == {1, 2, 3}


def test_outerwear_added_only_when_cold() -> None:
    wardrobe = [
        _garment(id=1, category="top"),
        _garment(id=2, category="bottom"),
        _garment(id=3, category="outerwear"),
    ]
    mild = generate_candidates(wardrobe, weather=_MILD_WEATHER, today=_TODAY, user_id=1)
    cold = generate_candidates(wardrobe, weather=_COLD_WEATHER, today=_TODAY, user_id=1)
    assert 3 not in mild[0][0]
    assert 3 in cold[0][0]


def test_candidates_do_not_share_garments() -> None:
    wardrobe = [
        _garment(id=1, category="top"),
        _garment(id=2, category="top"),
        _garment(id=3, category="bottom"),
        _garment(id=4, category="bottom"),
    ]
    candidates = generate_candidates(
        wardrobe, weather=_MILD_WEATHER, today=_TODAY, user_id=1, limit=3
    )
    seen: set[int] = set()
    for ids, _score in candidates:
        assert seen.isdisjoint(ids)
        seen.update(ids)


def test_exclude_combos_is_preferred_but_not_absolute() -> None:
    # Only one valid combo exists — excluding it can't remove it, so the
    # fallback path (return it anyway) has to kick in.
    wardrobe = [_garment(id=1, category="top"), _garment(id=2, category="bottom")]
    candidates = generate_candidates(
        wardrobe,
        weather=_MILD_WEATHER,
        today=_TODAY,
        user_id=1,
        exclude_combos=frozenset({frozenset({1, 2})}),
    )
    assert len(candidates) == 1
    assert set(candidates[0][0]) == {1, 2}


def test_exclude_combos_picks_a_different_combo_when_one_exists() -> None:
    wardrobe = [
        _garment(id=1, category="top", wear_count=0),
        _garment(id=2, category="top", wear_count=0),
        _garment(id=3, category="bottom", wear_count=0),
    ]
    without_exclusion = generate_candidates(
        wardrobe, weather=_MILD_WEATHER, today=_TODAY, user_id=1
    )
    previous_combo = frozenset(without_exclusion[0][0])

    candidates = generate_candidates(
        wardrobe,
        weather=_MILD_WEATHER,
        today=_TODAY,
        user_id=1,
        exclude_combos=frozenset({previous_combo}),
    )
    assert frozenset(candidates[0][0]) != previous_combo


def test_exclude_combos_can_rule_out_multiple_recent_outfits() -> None:
    wardrobe = [
        _garment(id=1, category="top", wear_count=0),
        _garment(id=2, category="top", wear_count=0),
        _garment(id=3, category="top", wear_count=0),
        _garment(id=4, category="bottom", wear_count=0),
    ]
    ranked = generate_candidates(wardrobe, weather=_MILD_WEATHER, today=_TODAY, user_id=1, limit=3)
    top_two = frozenset(frozenset(ids) for ids, _score in ranked[:2])

    candidates = generate_candidates(
        wardrobe, weather=_MILD_WEATHER, today=_TODAY, user_id=1, exclude_combos=top_two
    )
    assert frozenset(candidates[0][0]) not in top_two


def test_generate_outfits_delegates_to_generate_candidates() -> None:
    wardrobe = [_garment(id=1, category="top"), _garment(id=2, category="bottom")]
    candidates = generate_outfits(1, _TODAY, _MILD_WEATHER, wardrobe)
    assert len(candidates) == 1
    assert set(candidates[0][0]) == {1, 2}
