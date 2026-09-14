"""`compute_taste_weights` — aggregates FeedbackEvent history into per-category
preference weights. Real Postgres via the transactional fixtures (conftest.py):
FeedbackEvent.created_at is inserted explicitly (overriding the server_default)
so decay can be tested deterministically instead of depending on wall-clock
timing.
"""

from datetime import datetime, timedelta, timezone

from app.models.outfit import FeedbackEvent, Outfit
from app.services.taste import compute_taste_weights
from app.tests.conftest import make_garment, make_user


def _make_outfit(db, user, garments) -> Outfit:
    outfit = Outfit(
        user_id=user.id,
        garment_ids=[g.id for g in garments],
        score=1.0,
        generated_for=datetime.now(timezone.utc).date(),
    )
    db.add(outfit)
    db.flush()
    db.refresh(outfit)
    return outfit


def _make_feedback(db, user, outfit, action, *, days_ago: float = 0.0) -> FeedbackEvent:
    event = FeedbackEvent(
        user_id=user.id,
        outfit_id=outfit.id,
        action=action,
        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    db.add(event)
    db.flush()
    return event


def test_no_feedback_returns_empty_dict(db_session) -> None:
    user = make_user(db_session)
    assert compute_taste_weights(db_session, user.id) == {}


def test_like_gives_a_positive_weight_to_outfit_categories(db_session) -> None:
    user = make_user(db_session)
    top = make_garment(db_session, user, category="top")
    bottom = make_garment(db_session, user, category="bottom")
    outfit = _make_outfit(db_session, user, [top, bottom])
    _make_feedback(db_session, user, outfit, "like")

    weights = compute_taste_weights(db_session, user.id)

    assert weights["top"] > 0
    assert weights["bottom"] > 0


def test_dislike_gives_a_negative_weight(db_session) -> None:
    user = make_user(db_session)
    dress = make_garment(db_session, user, category="dress")
    outfit = _make_outfit(db_session, user, [dress])
    _make_feedback(db_session, user, outfit, "dislike")

    weights = compute_taste_weights(db_session, user.id)
    assert weights["dress"] < 0


def test_skip_is_ignored(db_session) -> None:
    user = make_user(db_session)
    top = make_garment(db_session, user, category="top")
    outfit = _make_outfit(db_session, user, [top])
    _make_feedback(db_session, user, outfit, "skip")

    weights = compute_taste_weights(db_session, user.id)
    assert weights == {}


def test_recent_feedback_outweighs_old_feedback(db_session) -> None:
    user = make_user(db_session)
    top = make_garment(db_session, user, category="top")

    recent_outfit = _make_outfit(db_session, user, [top])
    _make_feedback(db_session, user, recent_outfit, "like", days_ago=0)

    old_outfit = _make_outfit(db_session, user, [top])
    _make_feedback(db_session, user, old_outfit, "dislike", days_ago=365)

    weights = compute_taste_weights(db_session, user.id)
    # A year-old dislike has decayed to nearly nothing next to today's like —
    # the net should still read positive.
    assert weights["top"] > 0


def test_untagged_garment_in_an_outfit_contributes_nothing(db_session) -> None:
    user = make_user(db_session)
    untagged = make_garment(db_session, user, category=None)
    outfit = _make_outfit(db_session, user, [untagged])
    _make_feedback(db_session, user, outfit, "like")

    weights = compute_taste_weights(db_session, user.id)
    assert weights == {}
