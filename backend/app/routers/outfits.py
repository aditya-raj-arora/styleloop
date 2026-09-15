"""Outfit routes.

owner: ML/Engine

The daily suggestion comes from the novelty-optimizing rotation engine
(services/rotation.py). `GET /outfits/daily` generates-and-persists on first
request per day and is idempotent afterwards (repeat calls return the same
row); `POST /outfits/generate` always produces a fresh one for "regenerate",
preferring garments not already used in today's outfit. Feedback records swipe
actions; wear marks each of the outfit's garments worn.
"""

import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.garment import Garment
from app.models.outfit import FeedbackEvent, Outfit
from app.models.tryon import TryonRender
from app.models.user import User
from app.queue import get_queue
from app.schemas.outfit import (
    FeedbackIn,
    OutfitOut,
    SharedGarmentOut,
    SharedOutfitOut,
    ShareOut,
)
from app.schemas.tryon import TryonOut
from app.services import storage
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

_SHARE_TOKEN_COLLISION_RETRIES = 3


def _share_url(token: str) -> str:
    return f"{settings.FRONTEND_ORIGIN}/shared/{token}"


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


@router.post("/{outfit_id}/share", response_model=ShareOut)
def share_outfit(
    outfit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShareOut:
    """Create (or return the existing) public share link for this outfit.
    Idempotent — calling it again on an already-shared outfit returns the
    same token rather than rotating it, so a link the owner already handed
    out doesn't silently break."""
    outfit = db.get(Outfit, outfit_id)
    if outfit is None or outfit.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outfit not found")

    if outfit.share_token is None:
        for _ in range(_SHARE_TOKEN_COLLISION_RETRIES):
            outfit.share_token = secrets.token_urlsafe(32)
            try:
                db.commit()
                break
            except IntegrityError:
                # Astronomically unlikely (32 random bytes), but a token
                # collision must not 500 — just draw another.
                db.rollback()
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate a unique share link — try again.",
            )
        db.refresh(outfit)

    return ShareOut(share_token=outfit.share_token, share_url=_share_url(outfit.share_token))


@router.delete("/{outfit_id}/share", status_code=status.HTTP_204_NO_CONTENT)
def unshare_outfit(
    outfit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Revoke a share link — the token stops resolving immediately.
    Not an error to call on an already-unshared (or never-shared) outfit."""
    outfit = db.get(Outfit, outfit_id)
    if outfit is None or outfit.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outfit not found")

    outfit.share_token = None
    db.commit()


@router.get("/shared/{token}", response_model=SharedOutfitOut)
def get_shared_outfit(token: str, db: Session = Depends(get_db)) -> SharedOutfitOut:
    """Public, unauthenticated view of a shared outfit — no ownership check,
    deliberately: the whole point of the token is that it substitutes for
    auth. Garments come back stripped of anything that describes the
    owner's habits (state, wear_count, last_worn_at) — see SharedGarmentOut."""
    outfit = db.query(Outfit).filter(Outfit.share_token == token).first()
    if outfit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    # Preserve the outfit's own garment order rather than the query's.
    garments_by_id = {
        g.id: g for g in db.query(Garment).filter(Garment.id.in_(outfit.garment_ids)).all()
    }
    garments = [garments_by_id[gid] for gid in outfit.garment_ids if gid in garments_by_id]

    return SharedOutfitOut(
        generated_for=outfit.generated_for,
        score=outfit.score,
        garments=[
            SharedGarmentOut(
                image_url=storage.presigned_download_url(g.image_url),
                processed_url=(
                    storage.presigned_download_url(g.processed_url) if g.processed_url else None
                ),
                category=g.category,
                colors=g.colors,
                pattern=g.pattern,
                season=g.season,
                formality=g.formality,
            )
            for g in garments
        ],
    )


def _cached_tryon(db: Session, user: User, outfit_id: int) -> TryonRender | None:
    """The render matching this outfit + the user's *current* base photo —
    keyed by (user_id, outfit_id, photo_version), so a stale render from a
    since-replaced base photo never counts as a hit."""
    return (
        db.query(TryonRender)
        .filter(
            TryonRender.user_id == user.id,
            TryonRender.outfit_id == outfit_id,
            TryonRender.photo_version == user.base_photo_version,
        )
        .first()
    )


def _tryon_ready(render: TryonRender) -> TryonOut:
    return TryonOut(
        status="ready", rendered_url=storage.presigned_download_url(render.rendered_url)
    )


@router.post("/{outfit_id}/tryon", status_code=status.HTTP_202_ACCEPTED, response_model=TryonOut)
def request_tryon(
    outfit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TryonOut:
    """Kick off a try-on render, or return the cached one if this exact
    outfit + base photo combination has already been rendered. Enforces the
    daily cap only on the *generate* path — re-serving a cache hit is free."""
    outfit = db.get(Outfit, outfit_id)
    if outfit is None or outfit.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outfit not found")

    if current_user.base_photo_url is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Upload a base photo (POST /auth/me/photo) before requesting a try-on.",
        )

    cached = _cached_tryon(db, current_user, outfit_id)
    if cached is not None:
        return _tryon_ready(cached)

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = (
        db.query(TryonRender)
        .filter(TryonRender.user_id == current_user.id, TryonRender.created_at >= today_start)
        .count()
    )
    if today_count >= settings.TRYON_DAILY_CAP:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily try-on limit ({settings.TRYON_DAILY_CAP}) reached — try again tomorrow.",
        )

    get_queue().enqueue("app.workers.tasks.generate_tryon", current_user.id, outfit_id)
    return TryonOut(status="pending")


@router.get("/{outfit_id}/tryon", response_model=TryonOut)
def get_tryon(
    outfit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TryonOut:
    """Poll for a render kicked off by `POST .../tryon`. Stays "pending"
    forever if generation failed (see workers/tasks.generate_tryon) — the
    frontend is expected to give up after a reasonable number of polls and
    fall back to the flat outfit view."""
    outfit = db.get(Outfit, outfit_id)
    if outfit is None or outfit.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outfit not found")

    cached = _cached_tryon(db, current_user, outfit_id)
    if cached is None:
        return TryonOut(status="pending")
    return _tryon_ready(cached)
