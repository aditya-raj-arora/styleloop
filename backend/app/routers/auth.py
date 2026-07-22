"""Auth routes.

owner: Backend/Infra

JWT-based auth. Signup hashes the password and creates a User; login verifies and
returns a JWT to be sent as `Authorization: Bearer <token>`. Stubbed for Sprint 1.
"""

from fastapi import APIRouter, status

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup() -> None:
    # TODO(Backend/Infra): validate email, hash password, create User, return token.
    raise NotImplementedError


@router.post("/login")
def login() -> None:
    # TODO(Backend/Infra): verify credentials, issue JWT (Authorization: Bearer).
    raise NotImplementedError
