"""Password hashing + JWT helpers. Pure functions — no DB needed."""

import time

import pytest

from app.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_is_not_plaintext_and_verifies() -> None:
    hashed = hash_password("correct-horse")
    assert hashed != "correct-horse"
    assert verify_password("correct-horse", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip() -> None:
    token = create_access_token(user_id=42)
    assert decode_access_token(token) == 42


def test_decode_rejects_garbage_token() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-real-jwt")


def test_decode_rejects_token_signed_with_wrong_secret() -> None:
    import jwt as pyjwt

    bad_token = pyjwt.encode({"sub": "1"}, "wrong-secret", algorithm="HS256")
    with pytest.raises(InvalidTokenError):
        decode_access_token(bad_token)


def test_decode_rejects_expired_token() -> None:
    import jwt as pyjwt

    from app.config import settings

    expired = pyjwt.encode(
        {"sub": "1", "exp": int(time.time()) - 60},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(expired)
