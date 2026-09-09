"""Auth flow: signup -> login -> call a protected endpoint with the Bearer token.

Runs against a real Postgres (DATABASE_URL), migrated via `alembic upgrade head` —
see .github/workflows/ci.yml. Each test uses a unique email so it's safe to run
repeatedly against a persistent dev DB, not just an ephemeral CI one.
"""

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _unique_email() -> str:
    return f"{uuid.uuid4().hex}@example.com"


def test_signup_returns_jwt() -> None:
    response = client.post(
        "/auth/signup", json={"email": _unique_email(), "password": "correct-horse"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_signup_duplicate_email_conflicts() -> None:
    email = _unique_email()
    payload = {"email": email, "password": "correct-horse"}
    assert client.post("/auth/signup", json=payload).status_code == 201
    assert client.post("/auth/signup", json=payload).status_code == 409


def test_login_wrong_password_rejected() -> None:
    email = _unique_email()
    client.post("/auth/signup", json={"email": email, "password": "correct-horse"})
    response = client.post("/auth/login", json={"email": email, "password": "wrong"})
    assert response.status_code == 401


def test_login_unknown_email_rejected() -> None:
    response = client.post(
        "/auth/login", json={"email": _unique_email(), "password": "whatever"}
    )
    assert response.status_code == 401


def test_signup_login_then_call_protected_endpoint() -> None:
    email = _unique_email()
    password = "correct-horse-battery-staple"

    signup = client.post("/auth/signup", json={"email": email, "password": password})
    assert signup.status_code == 201

    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_protected_endpoint_without_token_rejected() -> None:
    assert client.get("/auth/me").status_code == 401


def test_protected_endpoint_with_garbage_token_rejected() -> None:
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert response.status_code == 401
