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


def test_reset_laundry_moves_only_laundry_garments_to_clean() -> None:
    token = _signup()
    laundry_garment = _upload(token).json()
    clean_garment = _upload(token).json()

    client.post(
        f"/garments/{laundry_garment['id']}/state",
        json={"state": "laundry"},
        headers=_auth(token),
    )

    response = client.post("/garments/laundry/reset", headers=_auth(token))

    assert response.status_code == 200
    body = response.json()
    assert [g["id"] for g in body] == [laundry_garment["id"]]
    assert body[0]["state"] == "clean"

    # The garment that was never in laundry is untouched.
    untouched = client.get(f"/garments/{clean_garment['id']}", headers=_auth(token)).json()
    assert untouched["state"] == "clean"


def test_reset_laundry_is_scoped_to_the_current_user() -> None:
    token_a = _signup()
    token_b = _signup()
    garment_a = _upload(token_a).json()
    client.post(
        f"/garments/{garment_a['id']}/state", json={"state": "laundry"}, headers=_auth(token_a)
    )

    response = client.post("/garments/laundry/reset", headers=_auth(token_b))

    assert response.status_code == 200
    assert response.json() == []


def test_reset_laundry_with_nothing_to_reset_returns_empty_list() -> None:
    token = _signup()
    response = client.post("/garments/laundry/reset", headers=_auth(token))
    assert response.status_code == 200
    assert response.json() == []


def test_analytics_on_an_empty_wardrobe() -> None:
    token = _signup()
    response = client.get("/garments/analytics", headers=_auth(token))

    assert response.status_code == 200
    body = response.json()
    assert body["total_garments"] == 0
    assert body["most_worn"] == []
    assert body["never_worn"] == []
    assert sorted(body["category_gaps"]) == ["bottom", "dress", "outerwear", "shoes", "top"]


def test_analytics_most_worn_is_ranked_by_wear_count_desc() -> None:
    token = _signup()
    low = _upload(token).json()
    high = _upload(token).json()

    for _ in range(3):
        client.post(f"/garments/{high['id']}/state", json={"state": "worn"}, headers=_auth(token))
    client.post(f"/garments/{low['id']}/state", json={"state": "worn"}, headers=_auth(token))

    body = client.get("/garments/analytics", headers=_auth(token)).json()

    assert [g["id"] for g in body["most_worn"]] == [high["id"], low["id"]]
    assert body["never_worn"] == []
    assert body["worn_count"] == 2


def test_analytics_never_worn_excludes_anything_with_wear_count() -> None:
    token = _signup()
    worn = _upload(token).json()
    unworn = _upload(token).json()
    client.post(f"/garments/{worn['id']}/state", json={"state": "worn"}, headers=_auth(token))

    body = client.get("/garments/analytics", headers=_auth(token)).json()

    assert [g["id"] for g in body["never_worn"]] == [unworn["id"]]


def test_analytics_category_gaps_close_as_clean_tagged_garments_are_added() -> None:
    token = _signup()
    top = _upload(token).json()
    client.patch(
        f"/garments/{top['id']}/tags", json={"category": "top"}, headers=_auth(token)
    )

    body = client.get("/garments/analytics", headers=_auth(token)).json()

    assert "top" not in body["category_gaps"]
    assert "bottom" in body["category_gaps"]


def test_analytics_category_gaps_ignore_untagged_or_non_clean_garments() -> None:
    token = _signup()
    _upload(token)  # never tagged, so its category stays None

    laundry = _upload(token).json()
    client.patch(
        f"/garments/{laundry['id']}/tags", json={"category": "shoes"}, headers=_auth(token)
    )
    client.post(
        f"/garments/{laundry['id']}/state", json={"state": "laundry"}, headers=_auth(token)
    )

    body = client.get("/garments/analytics", headers=_auth(token)).json()

    # Tagged but in laundry, and untagged clean — neither counts toward
    # closing the "shoes" gap.
    assert "shoes" in body["category_gaps"]


def test_analytics_is_scoped_to_the_current_user() -> None:
    token_a = _signup()
    token_b = _signup()
    garment_a = _upload(token_a).json()
    client.post(
        f"/garments/{garment_a['id']}/state", json={"state": "worn"}, headers=_auth(token_a)
    )

    body_b = client.get("/garments/analytics", headers=_auth(token_b)).json()

    assert body_b["total_garments"] == 0
    assert body_b["most_worn"] == []
