"""Auth flow: signup -> login -> call a protected endpoint with the Bearer token.

Runs against a real Postgres (DATABASE_URL), migrated via `alembic upgrade head` —
see .github/workflows/ci.yml. Each test uses a unique email so it's safe to run
repeatedly against a persistent dev DB, not just an ephemeral CI one.
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import storage

client = TestClient(app)

_fake_bucket: dict[str, bytes] = {}


@pytest.fixture
def _fake_storage(monkeypatch):
    _fake_bucket.clear()
    monkeypatch.setattr(
        storage, "upload_bytes", lambda key, data, ct: _fake_bucket.__setitem__(key, data)
    )
    monkeypatch.setattr(
        storage,
        "presigned_download_url",
        lambda key, expires_seconds=900: f"https://fake.test/{key}",
    )
    yield _fake_bucket


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


def _signup_token() -> str:
    response = client.post(
        "/auth/signup", json={"email": _unique_email(), "password": "correct-horse"}
    )
    return response.json()["access_token"]


def test_me_has_no_base_photo_before_any_upload() -> None:
    token = _signup_token()
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    body = response.json()
    assert body["base_photo_url"] is None
    assert body["base_photo_version"] == 0


def test_upload_base_photo_sets_url_and_bumps_version(_fake_storage) -> None:
    token = _signup_token()
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("me.png", io.BytesIO(b"not-really-a-png"), "image/png")}

    response = client.post("/auth/me/photo", files=files, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["base_photo_url"].startswith("https://fake.test/users/")
    assert body["base_photo_version"] == 1


def test_upload_base_photo_again_bumps_version_further(_fake_storage) -> None:
    token = _signup_token()
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("me.png", io.BytesIO(b"not-really-a-png"), "image/png")}

    client.post("/auth/me/photo", files=files, headers=headers)
    second = client.post("/auth/me/photo", files=files, headers=headers)

    assert second.json()["base_photo_version"] == 2


def test_upload_base_photo_rejects_unsupported_content_type(_fake_storage) -> None:
    token = _signup_token()
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("me.pdf", io.BytesIO(b"data"), "application/pdf")}

    response = client.post("/auth/me/photo", files=files, headers=headers)
    assert response.status_code == 415
