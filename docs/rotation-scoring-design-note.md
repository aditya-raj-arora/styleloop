# Rotation scoring — design note (Sprint 1 spike)

**Owner:** ML/Engine (Dev C) · **Status:** spike validated, ready for Sprint 2 integration

## Goal

De-risk Sprint 2's rotation engine by validating the scoring formula and the
per-day-determinism requirement *before* wiring it into real candidate
generation over the DB. `score_outfit` in `backend/app/services/rotation.py`
is the result — a pure function over synthetic garments, fully covered by
`backend/app/tests/test_rotation.py`.

## The formula

```
score = validity + recency_penalty + fairness + taste_weight + day_jitter
```

| Term | Range | What it rewards |
|---|---|---|
| `validity` | `[0, 1]` | Weather-appropriate garments (season vs. today's temperature). `all_season` never mismatches. |
| `recency_penalty` | `(-1, 0]` | Nothing — it only *subtracts*, for garments worn in the last 7 days (linearly decaying to 0 at day 7). Never-worn garments aren't touched. |
| `fairness` | `[0, ∞)`, dominated by `(0, 1]` in practice | Under-worn garments (`1 / (1 + wear_count)`), so the whole wardrobe cycles through instead of a favorite few dominating. |
| `taste_weight` | unbounded, caller-supplied | Categories the user has liked/disliked (Sprint 3 computes the real weights from `FeedbackEvent`; this spike just applies whatever mapping it's given). |
| `day_jitter` | `[-0.05, 0.05]` | Nothing real — see below. |

Higher is better. All five terms are summed directly, per the formula
sketched in `rotation.py`'s original docstring.

## Why `day_jitter` exists

Without it, the *same* wardrobe state (nothing worn, nothing liked, same
weather) produces the *same* top-ranked outfit every single day — which
directly undermines "fresh, non-repeating" suggestions even when nothing else
has changed. `day_jitter` is a small deterministic nudge derived from
`sha256(user_id, day, sorted(garment_ids))`, so:

- **Same day, same user, same candidate outfit → identical jitter.** A page
  refresh or a retry doesn't reshuffle the suggestion.
- **Different day → different jitter**, breaking ties between
  otherwise-identical candidates without needing any real state change.
- **Magnitude capped at ±0.05** — small enough that it can only break ties or
  nudge close calls, never override a real signal like `validity` or
  `fairness`. Verified by `test_jitter_varies_across_days_but_stays_small`.

This is *not* a substitute for real novelty optimization (Sprint 2's
candidate search still needs to actually diversify garment combinations) —
it's a cheap guarantee that ranking isn't perfectly static day to day.

## What Sprint 2 still needs to do

- Candidate *generation* — this spike only scores a given outfit; searching
  the space of valid combinations (one top + one bottom + optional outerwear,
  etc.) over a user's `clean` garments is unbuilt.
- Persisting scored `Outfit` rows (`generated_for`, `score`, `garment_ids`).
- Wiring `taste_weights` up from real `FeedbackEvent` aggregation (Sprint 3
  per `docs/TASKS.md`, though a naive Sprint 2 version — e.g. simple
  like/dislike counts per category — would already slot into the existing
  `taste_weights: dict[str, float]` parameter with no signature change).
- Deciding how many candidates to score before picking the top `limit` — the
  formula itself doesn't care, but performance at real wardrobe sizes does.

## Validated by

`backend/app/tests/test_rotation.py` — weather mismatch penalties in both
directions, recency penalty decay (and its 7-day cutoff), fairness ordering,
taste weight sign, same-day determinism, and cross-day/cross-user jitter
variation bounded to the documented magnitude.
