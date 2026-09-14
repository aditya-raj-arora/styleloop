"""Taste weighting — aggregates `FeedbackEvent` history into the
`taste_weights: dict[str, float]` shape `rotation.score_outfit` has accepted
since Sprint 1 (as a spike parameter, unpopulated by any real caller until
now).

Algorithm:
    - Each `FeedbackEvent` (like/dislike/skip) applies to every category
      present in its outfit's `garment_ids` — the event doesn't target a
      single garment, so we can't be more precise than "the whole outfit".
    - `like` is +1, `dislike` is -1, `skip` is ignored (0) — a skip likely
      means "not today", not "never wear this category"; revisit once real
      usage data shows whether that's actually true.
    - Recent events matter more than old ones: each event's contribution is
      halved every `_HALF_LIFE_DAYS`, so a bad week doesn't permanently sink
      a category — exponential decay, not a flat running sum.

Runs a couple of DB queries (events + their outfits + those garments), so —
unlike rotation.py's score_outfit — this is *not* a pure function. Called
once per outfit generation by routers/outfits.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.garment import Garment
from app.models.outfit import FeedbackEvent, Outfit

_ACTION_WEIGHTS: dict[str, float] = {"like": 1.0, "dislike": -1.0}
_HALF_LIFE_DAYS = 14.0


def compute_taste_weights(db: Session, user_id: int) -> dict[str, float]:
    """Per-category preference weights from `user_id`'s feedback history.
    Empty dict (not an error) when there's no feedback yet — `score_outfit`
    treats that as neutral."""
    events = db.query(FeedbackEvent).filter(FeedbackEvent.user_id == user_id).all()
    if not events:
        return {}

    outfit_ids = {e.outfit_id for e in events}
    outfits = db.query(Outfit).filter(Outfit.id.in_(outfit_ids)).all()
    outfit_by_id = {o.id: o for o in outfits}

    garment_ids: set[int] = set()
    for outfit in outfits:
        garment_ids.update(outfit.garment_ids)
    garments = db.query(Garment).filter(Garment.id.in_(garment_ids)).all()
    category_by_id = {g.id: g.category for g in garments}

    now = datetime.now(timezone.utc)
    weights: dict[str, float] = {}

    for event in events:
        base = _ACTION_WEIGHTS.get(event.action)
        if not base:
            continue  # unweighted action (skip, or anything future/unknown)

        outfit = outfit_by_id.get(event.outfit_id)
        if outfit is None:
            continue  # outfit since deleted — nothing to attribute this to

        days_ago = max(0.0, (now - event.created_at).total_seconds() / 86400)
        decayed = base * (0.5 ** (days_ago / _HALF_LIFE_DAYS))

        for garment_id in outfit.garment_ids:
            category = category_by_id.get(garment_id)
            if category is None:
                continue
            weights[category] = weights.get(category, 0.0) + decayed

    return weights
