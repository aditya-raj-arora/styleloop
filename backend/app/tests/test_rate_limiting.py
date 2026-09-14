"""Rate limiting on /auth/signup and /auth/login.

The limiter is disabled by default under pytest (see app/rate_limiting.py)
so the rest of the suite isn't affected by every test sharing TestClient's
single fake "IP" — this file explicitly re-enables it to verify the actual
enforcement, and resets its counters before/after so it never leaks into
(or is affected by) any other test.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.rate_limiting import limiter

client = TestClient(app)

_LIMIT = int(settings.AUTH_RATE_LIMIT.split("/")[0])


@pytest.fixture(autouse=True)
def _rate_limiting_enabled():
    limiter.enabled = True
    limiter.reset()
    try:
        yield
    finally:
        limiter.reset()
        limiter.enabled = False


def _signup_payload() -> dict:
    return {"email": f"{uuid.uuid4().hex}@example.com", "password": "correct-horse-battery"}


def test_signup_is_rate_limited_per_ip() -> None:
    for _ in range(_LIMIT):
        response = client.post("/auth/signup", json=_signup_payload())
        assert response.status_code == 201

    blocked = client.post("/auth/signup", json=_signup_payload())
    assert blocked.status_code == 429


def test_login_is_rate_limited_per_ip() -> None:
    # Wrong credentials still count against the limit — the point is
    # blocking repeated *attempts*, not just successful ones.
    payload = {"email": "nobody@example.com", "password": "wrong"}

    for _ in range(_LIMIT):
        response = client.post("/auth/login", json=payload)
        assert response.status_code == 401

    blocked = client.post("/auth/login", json=payload)
    assert blocked.status_code == 429


def test_rate_limit_is_scoped_to_each_endpoint_independently() -> None:
    # Exhausting signup's limit shouldn't also block login - they're
    # decorated (and therefore keyed) independently.
    for _ in range(_LIMIT):
        client.post("/auth/signup", json=_signup_payload())
    assert client.post("/auth/signup", json=_signup_payload()).status_code == 429

    still_allowed = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
    )
    assert still_allowed.status_code == 401
