"""Password hashing and JWT helpers.

owner: Backend/Infra

Passwords are hashed with argon2 (via passlib) and never stored or logged in
plaintext. JWTs are signed with `JWT_SECRET`/`JWT_ALGORITHM` and carry the user id
as `sub`; access tokens expire after `JWT_EXPIRE_MINUTES`.
"""

from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class InvalidTokenError(Exception):
    """Raised when a JWT is missing, malformed, expired, or has a bad signature."""


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(password, hashed_password)


def create_access_token(user_id: int) -> str:
    """Issue a signed JWT for `user_id`, expiring after JWT_EXPIRE_MINUTES."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    """Decode and validate a JWT, returning the user id encoded in `sub`.

    Raises InvalidTokenError on any failure (bad signature, expired, malformed) —
    callers should treat that uniformly as "unauthenticated", not leak which.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError) as exc:
        raise InvalidTokenError(str(exc)) from exc
