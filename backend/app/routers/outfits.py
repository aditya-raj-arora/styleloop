"""Outfit routes.

owner: ML/Engine

The daily suggestion comes from the novelty-optimizing rotation engine
(services/rotation.py). `GET /outfits/daily` generates-and-persists on first
request per day and is idempotent afterwards (repeat calls return the same
row); `POST /outfits/generate` always produces a fresh one for "regenerate",
preferring garments not already used in today's outfit. Feedback records swipe
actions; wear marks each of the outfit's garments worn.
"""

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.garment import Garment
from app.models.outfit import FeedbackEvent, Outfit
from app.models.user import User
from app.schemas.outfit import FeedbackIn, OutfitOut
from app.services import weather as weather_service
from app.services.rotation import ScoringGarment, generate_outfits
from app.services.taste import compute_taste_weights

router = APIRouter(prefix="/outfits", tags=["outfits"])

_VALID_FEEDBACK_ACTIONS = {"like", "dislike", "skip"}

# How far back "regenerate" looks to avoid repeating a recent outfit verbatim
# (see rotation.generate_candidates' exclude_combos). Small wardrobes may not
# have that many genuinely distinct options — the exact-match-only exclusion
# there degrades to "best available" rather than erroring when they don't.
_LOOKBACK_DAYS = 7


def _outfit_out(outfit: Outfit) -> OutfitOut:
    return OutfitOut.model_validate(outfit)


def _clean_scoring_garments(db: Session, user_id: int) -> list[ScoringGarment]:
    """'Clean' garments the engine may place in an outfit today. Untagged
    garments (category is None — tagging hasn't finished, or was disabled)
    are excluded: the engine can't place something it doesn't know the shape
    of."""
    garments = (
        db.query(Garment).filter(Garment.user_id == user_id, Garment.state == "clean").all()
    )
    return [
        ScoringGarment(
            id=g.id,
            season=g.season or "all_season",
            formality=g.formality or "casual",
            wear_count=g.wear_count,
            last_worn_at=g.last_worn_at.date() if g.last_worn_at else None,
            category=g.category,
        )
        for g in garments
        if g.category is not None
    ]


def _latest_outfit_for_today(db: Session, user_id: int, today: date) -> Outfit | None:
    return (
        db.query(Outfit)
        .filter(Outfit.user_id == user_id, Outfit.generated_for == today)
        .order_by(Outfit.created_at.desc())
        .first()
    )


def _recent_combos(db: Session, user_id: int, today: date) -> frozenset[frozenset[int]]:
    """Exact garment-id sets of every outfit generated for this user in the
    last `_LOOKBACK_DAYS` (today included) — regenerate prefers to avoid all
    of them, not just today's, so a small wardrobe doesn't get handed the
    same pairing every morning just because "today" reset the exclusion."""
    cutoff = today - timedelta(days=_LOOKBACK_DAYS)
    rows = (
        db.query(Outfit.garment_ids)
        .filter(Outfit.user_id == user_id, Outfit.generated_for >= cutoff)
        .all()
    )
    return frozenset(frozenset(ids) for (ids,) in rows)


def _generate_and_persist(
    db: Session,
    user: User,
    *,
    lat: float | None,
    lon: float | None,
    exclude_combos: frozenset[frozenset[int]] = frozenset(),
) -> Outfit:
    today = date.today()
    garments = _clean_scoring_garments(db, user.id)
    if not garments:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Not enough tagged, clean garments to generate an outfit yet.",
        )

    conditions = weather_service.get_weather(
        lat if lat is not None else settings.DEFAULT_LAT,
        lon if lon is not None else settings.DEFAULT_LON,
    )
    taste_weights = compute_taste_weights(db, user.id)
    candidates = generate_outfits(
        user.id,
        today,
        conditions,
        garments,
        limit=1,
        taste_weights=taste_weights,
        exclude_combos=exclude_combos,
    )
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No valid outfit found — need at least a top+bottom or a dress marked clean.",
        )

    garment_ids, score = candidates[0]
    outfit = Outfit(
        user_id=user.id,
        garment_ids=list(garment_ids),
        score=score,
        generated_for=today,
    )
    db.add(outfit)
    db.commit()
    db.refresh(outfit)
    return outfit


@router.get("/daily", response_model=OutfitOut)
def daily(
    lat: float | None = Query(None),
    lon: float | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutfitOut:
    existing = _latest_outfit_for_today(db, current_user.id, date.today())
    if existing is not None:
        return _outfit_out(existing)
    outfit = _generate_and_persist(db, current_user, lat=lat, lon=lon)
    return _outfit_out(outfit)


@router.post("/generate", status_code=status.HTTP_201_CREATED, response_model=OutfitOut)
def generate(
    lat: float | None = Query(None),
    lon: float | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutfitOut:
    today = date.today()
    exclude_combos = _recent_combos(db, current_user.id, today)
    outfit = _generate_and_persist(
        db, current_user, lat=lat, lon=lon, exclude_combos=exclude_combos
    )
    return _outfit_out(outfit)


@router.post("/{outfit_id}/feedback", status_code=status.HTTP_201_CREATED)
def feedback(
    outfit_id: int,
    payload: FeedbackIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if payload.action not in _VALID_FEEDBACK_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"action must be one of {sorted(_VALID_FEEDBACK_ACTIONS)}",
        )

    outfit = db.get(Outfit, outfit_id)
    if outfit is None or outfit.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outfit not found")

    db.add(FeedbackEvent(user_id=current_user.id, outfit_id=outfit_id, action=payload.action))
    db.commit()
    return {"status": "recorded"}


@router.post("/{outfit_id}/wear")
def wear(
    outfit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    outfit = db.get(Outfit, outfit_id)
    if outfit is None or outfit.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outfit not found")

    now = datetime.now(timezone.utc)
    garments = (
        db.query(Garment)
        .filter(Garment.id.in_(outfit.garment_ids), Garment.user_id == current_user.id)
        .all()
    )
    for garment in garments:
        garment.state = "worn"
        garment.wear_count += 1
        garment.last_worn_at = now
    db.commit()

    return {"status": "worn", "garment_ids": [g.id for g in garments]}
