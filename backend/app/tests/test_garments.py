"""Garment upload/list/get/tags/state flow.

Runs against a real Postgres (DATABASE_URL) like test_auth.py. Object storage
and the RQ queue are faked out via monkeypatch — this is an API-contract test,
not an integration test of S3 or Redis (the worker's own behavior belongs in
its own test once Dev C's test harness lands).
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import storage

client = TestClient(app)

_fake_bucket: dict[str, bytes] = {}


class _FakeQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple] = []

    def enqueue(self, func_path: str, *args, **kwargs) -> None:
        self.enqueued.append((func_path, args, kwargs))


@pytest.fixture(autouse=True)
def _fake_storage_and_queue(monkeypatch):
    _fake_bucket.clear()
    monkeypatch.setattr(
        storage, "upload_bytes", lambda key, data, ct: _fake_bucket.__setitem__(key, data)
    )
    monkeypatch.setattr(storage, "download_bytes", lambda key: _fake_bucket[key])
    monkeypatch.setattr(
        storage,
        "presigned_download_url",
        lambda key, expires_seconds=900: f"https://fake.test/{key}",
    )
    fake_queue = _FakeQueue()
    monkeypatch.setattr("app.routers.garments.get_queue", lambda: fake_queue)
    yield fake_queue


def _signup() -> str:
    email = f"{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "correct-horse-battery"}
    response = client.post("/auth/signup", json=payload)
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _upload(token: str, content_type: str = "image/png") -> dict:
    files = {"file": ("shirt.png", io.BytesIO(b"not-really-a-png"), content_type)}
    response = client.post("/garments", files=files, headers=_auth(token))
    return response


def test_create_garment_returns_202_with_null_processed_url(_fake_storage_and_queue) -> None:
    token = _signup()
    response = _upload(token)

    assert response.status_code == 202
    body = response.json()
    assert body["processed_url"] is None
    assert body["state"] == "clean"
    assert body["image_url"].startswith("https://fake.test/garments/")

    # Enqueued exactly one process_garment job for this garment.
    assert _fake_storage_and_queue.enqueued == [
        ("app.workers.tasks.process_garment", (body["id"],), {})
    ]


def test_create_garment_rejects_unsupported_content_type() -> None:
    token = _signup()
    response = _upload(token, content_type="application/pdf")
    assert response.status_code == 415


def test_create_garment_requires_auth() -> None:
    files = {"file": ("shirt.png", io.BytesIO(b"data"), "image/png")}
    response = client.post("/garments", files=files)
    assert response.status_code == 401


def test_list_garments_is_scoped_to_the_current_user() -> None:
    token_a = _signup()
    token_b = _signup()

    _upload(token_a)
    _upload(token_a)
    _upload(token_b)

    garments_a = client.get("/garments", headers=_auth(token_a)).json()
    garments_b = client.get("/garments", headers=_auth(token_b)).json()

    assert len(garments_a) == 2
    assert len(garments_b) == 1
    assert {g["user_id"] for g in garments_a} == {garments_a[0]["user_id"]}


def test_get_garment_404s_for_another_users_garment() -> None:
    owner_token = _signup()
    other_token = _signup()

    garment = _upload(owner_token).json()

    own_view = client.get(f"/garments/{garment['id']}", headers=_auth(owner_token))
    other_view = client.get(f"/garments/{garment['id']}", headers=_auth(other_token))

    assert own_view.status_code == 200
    assert other_view.status_code == 404


def test_get_garment_404s_for_unknown_id() -> None:
    token = _signup()
    response = client.get("/garments/999999999", headers=_auth(token))
    assert response.status_code == 404


def test_update_tags_applies_partial_update() -> None:
    token = _signup()
    garment = _upload(token).json()

    response = client.patch(
        f"/garments/{garment['id']}/tags",
        json={"category": "top", "colors": ["red", "white"]},
        headers=_auth(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "top"
    assert body["colors"] == ["red", "white"]
    assert body["pattern"] is None  # untouched field stays as-is


def test_set_state_to_worn_bumps_wear_count_and_last_worn_at() -> None:
    token = _signup()
    garment = _upload(token).json()
    assert garment["wear_count"] == 0
    assert garment["last_worn_at"] is None

    response = client.post(
        f"/garments/{garment['id']}/state", json={"state": "worn"}, headers=_auth(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "worn"
    assert body["wear_count"] == 1
    assert body["last_worn_at"] is not None


def test_set_state_rejects_invalid_state() -> None:
    token = _signup()
    garment = _upload(token).json()

    response = client.post(
        f"/garments/{garment['id']}/state", json={"state": "sparkling"}, headers=_auth(token)
    )
    assert response.status_code == 400
