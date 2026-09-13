# Rotation scoring — design note (Sprint 1 spike → Sprint 2 engine)

**Owner:** ML/Engine (Dev C) · **Status:** scoring spike + candidate generation + persistence shipped

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

## Sprint 2: candidate generation + persistence

`generate_candidates` (in `rotation.py`, tested in `test_rotation.py`) builds
the search space this spike didn't need to: valid outfit *shapes* over a
user's tagged, `clean` garments —

- **top + bottom**, or a **dress** alone, as the required base;
- **+ outerwear** only when `weather.temp_c` is below the same cold threshold
  `score_outfit`'s `validity` term already uses (no separate knob);
- **+ shoes** whenever any are available.

Every base combination (each top × each bottom, plus each dress) is expanded
with those optional slots, scored via `score_outfit`, and sorted. The top
`limit` are returned with **no shared garment across them**, so "3 candidates"
really are 3 distinct outfits rather than the same one with a shoe swapped.

`exclude_combo` (an exact garment-id set, e.g. today's current outfit) lets
"regenerate" ask for something else: it's skipped when ranking, but only
removes an *exact* match — a small wardrobe (one pair of shoes, one bottom)
may not have a fully disjoint alternative, and this still rotates whatever
part of the outfit *can* change instead of erroring out.

This all stays a pure function — `generate_outfits(user_id, day, weather,
garments, ...)` takes an already-fetched `list[ScoringGarment]` and returns
`list[(garment_ids, score)]`, no DB access. `backend/app/routers/outfits.py`
owns the I/O:

- `GET /outfits/daily` returns the existing row for today if one exists
  (generate-once-per-day, idempotent on refresh), else generates and
  persists the top-1 candidate.
- `POST /outfits/generate` always generates again, passing today's existing
  outfit (if any) as `exclude_combo` — the "regenerate" button.
- `POST /outfits/{id}/feedback` and `POST /outfits/{id}/wear` are unchanged
  from the Sprint 1 stub shape (record a `FeedbackEvent`; bump
  `wear_count`/`last_worn_at`/`state` on each garment in the outfit).

Untagged garments (`category is None`) are excluded from the candidate pool —
the engine can't place something it doesn't know the shape of yet.

## Still open (Sprint 3+)

- `taste_weights` is wired as a parameter throughout but nothing populates it
  yet — Sprint 3 aggregates real weights from `FeedbackEvent` history.
- Lat/lon come from the browser's geolocation when granted, else fall back to
  a fixed default city (`settings.DEFAULT_LAT`/`DEFAULT_LON`) — no per-user
  saved location yet.
- Candidate volume is small (a handful of tops × bottoms, optionally ×
  outerwear × shoes) — fine at demo-wardrobe sizes; revisit if real wardrobes
  make the full cross-product expensive.

## Validated by

`backend/app/tests/test_rotation.py` — weather mismatch penalties in both
directions, recency penalty decay (and its 7-day cutoff), fairness ordering,
taste weight sign, same-day determinism, and cross-day/cross-user jitter
variation bounded to the documented magnitude.
