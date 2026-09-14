"""Auth routes.

owner: Backend/Infra

JWT-based auth. Signup hashes the password and creates a User; login verifies and
returns a JWT to be sent as `Authorization: Bearer <token>`.
"""

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.rate_limiting import limiter
from app.schemas.auth import LoginRequest, SignupRequest, Token, UserOut
from app.security import create_access_token, hash_password, verify_password
from app.services import storage

router = APIRouter(prefix="/auth", tags=["auth"])

# Base photo upload — same size/type rules as garments.py's garment upload.
_MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10 MB
_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        base_photo_url=(
            storage.presigned_download_url(user.base_photo_url) if user.base_photo_url else None
        ),
        base_photo_version=user.base_photo_version,
        created_at=user.created_at,
    )


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def signup(request: Request, payload: SignupRequest, db: Session = Depends(get_db)) -> Token:
    user = User(email=payload.email.lower(), hashed_password=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        ) from exc
    db.refresh(user)
    return Token(access_token=create_access_token(user.id))


@router.post("/login", response_model=Token)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        # Same error for "no such user" and "wrong password" — don't leak which.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Return the authenticated user. Also serves as the reference protected route."""
    return _user_out(current_user)


@router.post("/me/photo", response_model=UserOut)
def upload_base_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    """Set (or replace) the user's virtual try-on base photo. Bumps
    `base_photo_version` — that's what invalidates old cached try-on renders
    (see models/tryon.py) without needing to delete anything."""
    extension = _CONTENT_TYPE_EXTENSIONS.get(file.content_type or "")
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type: {file.content_type}. Use JPEG, PNG, or WebP.",
        )

    data = file.file.read(_MAX_PHOTO_BYTES + 1)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(data) > _MAX_PHOTO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image exceeds the 10 MB upload limit",
        )

    current_user.base_photo_version += 1
    key = f"users/{current_user.id}/base-photo-v{current_user.base_photo_version}{extension}"
    storage.upload_bytes(key, data, file.content_type)
    current_user.base_photo_url = key

    db.commit()
    db.refresh(current_user)
    return _user_out(current_user)
