"""Garment routes.

owner: Backend + ML

Upload returns immediately; the RQ worker performs bg-removal + tagging async, so
the frontend shows a placeholder until `processed_url` is populated. Responses use
the frozen `GarmentOut` contract.

`Garment.image_url` / `.processed_url` store private storage *keys*, not literal
URLs — despite the field name (kept as-is; it's the frozen contract). `_garment_out`
below is the only place that turns a key into a short-lived signed URL for the
response, so a stale/long-lived URL is never persisted or logged.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.garment import DEFAULT_STATE, Garment
from app.models.user import User
from app.queue import get_queue
from app.schemas.garment import GarmentOut, StateUpdate, TagUpdate
from app.services import storage

router = APIRouter(prefix="/garments", tags=["garments"])

_VALID_STATES = {"clean", "worn", "laundry"}
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _garment_out(garment: Garment) -> GarmentOut:
    return GarmentOut(
        id=garment.id,
        user_id=garment.user_id,
        image_url=storage.presigned_download_url(garment.image_url),
        processed_url=(
            storage.presigned_download_url(garment.processed_url)
            if garment.processed_url
            else None
        ),
        category=garment.category,
        colors=garment.colors,
        pattern=garment.pattern,
        fabric=garment.fabric,
        fabric_confidence=garment.fabric_confidence,
        season=garment.season,
        formality=garment.formality,
        state=garment.state,
        wear_count=garment.wear_count,
        last_worn_at=garment.last_worn_at,
        created_at=garment.created_at,
    )


def _get_owned_garment(garment_id: int, user: User, db: Session) -> Garment:
    garment = db.get(Garment, garment_id)
    if garment is None or garment.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Garment not found")
    return garment


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=GarmentOut)
def create_garment(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GarmentOut:
    extension = _CONTENT_TYPE_EXTENSIONS.get(file.content_type or "")
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type: {file.content_type}. Use JPEG, PNG, or WebP.",
        )

    data = file.file.read(_MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image exceeds the 10 MB upload limit",
        )

    key = f"garments/{current_user.id}/{uuid4().hex}-raw{extension}"
    storage.upload_bytes(key, data, file.content_type)

    garment = Garment(user_id=current_user.id, image_url=key, state=DEFAULT_STATE)
    db.add(garment)
    db.commit()
    db.refresh(garment)

    get_queue().enqueue("app.workers.tasks.process_garment", garment.id)

    return _garment_out(garment)


@router.get("", response_model=list[GarmentOut])
def list_garments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GarmentOut]:
    garments = (
        db.query(Garment)
        .filter(Garment.user_id == current_user.id)
        .order_by(Garment.created_at.desc())
        .all()
    )
    return [_garment_out(g) for g in garments]


@router.post("/laundry/reset", response_model=list[GarmentOut])
def reset_laundry(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GarmentOut]:
    """Bulk "do laundry": every `laundry`-state garment for this user goes
    back to `clean` in one call, instead of one-by-one via
    `POST /{garment_id}/state`. Returns the garments that were reset (empty
    list if there weren't any — not an error)."""
    garments = (
        db.query(Garment)
        .filter(Garment.user_id == current_user.id, Garment.state == "laundry")
        .all()
    )
    for garment in garments:
        garment.state = DEFAULT_STATE
    db.commit()
    for garment in garments:
        db.refresh(garment)
    return [_garment_out(g) for g in garments]


@router.get("/{garment_id}", response_model=GarmentOut)
def get_garment(
    garment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GarmentOut:
    garment = _get_owned_garment(garment_id, current_user, db)
    return _garment_out(garment)


@router.patch("/{garment_id}/tags", response_model=GarmentOut)
def update_tags(
    garment_id: int,
    payload: TagUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GarmentOut:
    garment = _get_owned_garment(garment_id, current_user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(garment, field, value)
    db.commit()
    db.refresh(garment)
    return _garment_out(garment)


@router.post("/{garment_id}/state", response_model=GarmentOut)
def set_state(
    garment_id: int,
    payload: StateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GarmentOut:
    if payload.state not in _VALID_STATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"state must be one of {sorted(_VALID_STATES)}",
        )

    garment = _get_owned_garment(garment_id, current_user, db)
    garment.state = payload.state
    if payload.state == "worn":
        garment.wear_count += 1
        garment.last_worn_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(garment)
    return _garment_out(garment)
