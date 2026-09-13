"""Rotation engine — THE DIFFERENTIATOR.

Generates fresh, non-repeating, weather-aware daily outfit suggestions by scoring
candidate garment combinations and optimizing for novelty.

Score for a candidate outfit:

    score = validity
          + recency_penalty      # penalize recently/frequently worn items -> novelty
          + fairness             # boost under-worn items so the whole wardrobe rotates
          + taste_weight         # nudge toward items the user has liked (FeedbackEvent)
          + day_jitter           # tiny per-(user, day) deterministic tie-breaker

Constraints:
    - Only 'clean' garments are eligible (respect laundry state).
    - Weather-aware: filter/weight by season + formality against today's weather
      (see services/weather.py).
    - Deterministic per day: seed the sampler with (user_id, generated_for) so a
      given day yields a stable suggestion, while different days differ.

`score_outfit` below is the Sprint 1 scoring *spike* — it validates the formula
and the per-day-seed approach against synthetic garments (no DB), so Sprint 2
can wire it into `generate_outfits` with confidence instead of designing the
scoring math and the real integration at the same time. See
docs/rotation-scoring-design-note.md for the full writeup.

`generate_outfits` itself (candidate generation over real 'clean' garments,
persistence) is Sprint 2 scope and still stubbed here.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date

_WARM_SEASONS = {"summer", "spring"}
_COLD_SEASONS = {"winter", "fall"}

# Below this temperature, a summer-only garment is a validity mismatch (and
# vice versa above it for winter-only) — chosen loosely, not from real data.
_COLD_THRESHOLD_C = 12.0
_WARM_THRESHOLD_C = 24.0

_JITTER_MAGNITUDE = 0.05  # small relative to a well-formed outfit's real score


@dataclass(frozen=True)
class ScoringGarment:
    """A garment as seen by the scorer — just the fields scoring needs, so the
    spike can run against synthetic data without touching the DB or the
    Garment ORM model."""

    id: int
    season: str  # 'spring' | 'summer' | 'fall' | 'winter' | 'all_season'
    formality: str  # 'casual' | 'smart_casual' | 'formal'
    wear_count: int = 0
    last_worn_at: date | None = None
    category: str | None = None  # used only for taste_weight lookups


def _day_seed(user_id: int, day: date) -> int:
    """Deterministic integer seed for (user_id, day) — same inputs always
    produce the same seed, so anything derived from it is reproducible for a
    given day and shifts predictably on the next one."""
    digest = hashlib.sha256(f"{user_id}:{day.isoformat()}".encode()).hexdigest()
    return int(digest[:16], 16)


def _day_jitter(garments: tuple[ScoringGarment, ...], user_id: int, day: date) -> float:
    """A small deterministic per-(user, day, outfit) nudge in
    [-_JITTER_MAGNITUDE, _JITTER_MAGNITUDE]. Breaks ties between
    otherwise-identical candidates so the same outfit isn't suggested forever
    when nothing else about the wardrobe changes — without swamping the real
    scoring signal above it.
    """
    garment_ids = sorted(g.id for g in garments)
    seed_input = f"{_day_seed(user_id, day)}:{garment_ids}"
    digest = hashlib.sha256(seed_input.encode()).hexdigest()
    unit_interval = int(digest[:8], 16) / 0xFFFFFFFF  # in [0, 1]
    return (unit_interval - 0.5) * 2 * _JITTER_MAGNITUDE


def _validity(garments: tuple[ScoringGarment, ...], weather: dict) -> float:
    """1.0 for a perfectly weather-appropriate outfit, penalized per garment
    whose season doesn't suit today's temperature. 'all_season' never
    mismatches."""
    temp_c = weather.get("temp_c")
    if temp_c is None:
        return 1.0  # no weather signal — don't penalize what we can't judge

    mismatches = 0
    for garment in garments:
        if garment.season == "all_season":
            continue
        if temp_c < _COLD_THRESHOLD_C and garment.season in _WARM_SEASONS:
            mismatches += 1
        elif temp_c > _WARM_THRESHOLD_C and garment.season in _COLD_SEASONS:
            mismatches += 1

    return max(0.0, 1.0 - 0.3 * mismatches)


def _recency_penalty(garments: tuple[ScoringGarment, ...], today: date) -> float:
    """Non-positive. Recently-worn garments drag the score down (encouraging
    novelty); never-worn garments (last_worn_at is None) contribute nothing —
    they're novel by definition, not penalized."""
    penalty = 0.0
    for garment in garments:
        if garment.last_worn_at is None:
            continue
        days_since = (today - garment.last_worn_at).days
        if days_since < 7:
            penalty -= (7 - days_since) / 7
    return penalty


def _fairness(garments: tuple[ScoringGarment, ...]) -> float:
    """Non-negative. Rewards under-worn garments so the whole wardrobe rotates
    rather than a favorite few dominating every suggestion."""
    return sum(1.0 / (1.0 + g.wear_count) for g in garments)


def _taste_weight(
    garments: tuple[ScoringGarment, ...], taste_weights: dict[str, float] | None
) -> float:
    """Sum of per-category preference weights (positive = liked, negative =
    disliked), aggregated from FeedbackEvent history. Sprint 3 computes the
    real weights; this spike just applies whatever mapping it's given."""
    if not taste_weights:
        return 0.0
    return sum(taste_weights.get(g.category, 0.0) for g in garments if g.category)


def score_outfit(
    garments: list[ScoringGarment],
    *,
    weather: dict,
    today: date,
    user_id: int,
    taste_weights: dict[str, float] | None = None,
) -> float:
    """Score one candidate outfit. Higher is better. Pure function — no DB, no
    I/O — so Sprint 2's candidate search can call it in a tight loop.
    """
    garments_key = tuple(garments)
    return (
        _validity(garments_key, weather)
        + _recency_penalty(garments_key, today)
        + _fairness(garments_key)
        + _taste_weight(garments_key, taste_weights)
        + _day_jitter(garments_key, user_id, today)
    )


def generate_outfits(user_id: int, day, weather: dict, limit: int = 3) -> list:
    # TODO(ML/Engine, Sprint 2): candidate search over real 'clean' garments,
    #   scored via score_outfit above, persisted as Outfit rows.
    raise NotImplementedError
