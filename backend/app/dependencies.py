"""Shared FastAPI dependencies.

owner: Backend/Infra

`get_current_user` decodes the `Authorization: Bearer <jwt>` header, loads the
`User` from the DB, and 401s on any failure (missing header, bad/expired token,
deleted user). Import this from any router that needs an authenticated user —
Dev B (garments) and Dev C (outfits) both build their protected routes on it.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.security import InvalidTokenError, decode_access_token

# auto_error=False so a missing header falls through to our own 401 (with a
# consistent body) instead of FastAPI's default 403.
_bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _UNAUTHORIZED

    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise _UNAUTHORIZED from exc

    user = db.get(User, user_id)
    if user is None:
        raise _UNAUTHORIZED
    return user
