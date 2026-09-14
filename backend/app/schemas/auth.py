"""Auth API schemas.

owner: Backend/Infra
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    """Response for signup/login — the JWT to send as `Authorization: Bearer <token>`."""

    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    """Serialized user — never includes `hashed_password`. Built manually by
    the router (not `from_attributes`): `base_photo_url` must go through
    `storage.presigned_download_url` first, same rule as `GarmentOut` — the
    raw storage key never leaves the server. None until
    `POST /auth/me/photo` is called; `base_photo_version` is the try-on
    cache key's version component (see models/tryon.py) and starts at 0.
    """

    id: int
    email: str
    base_photo_url: str | None = None
    base_photo_version: int
    created_at: datetime
