"""Auth API schemas.

owner: Backend/Infra
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
    """Serialized user — never includes `hashed_password`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime
