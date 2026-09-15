"""`/outfits` endpoint tests.

Uses the transactional fixtures from conftest.py (real Postgres, rolled back
per test) so garments can be created directly with specific
category/season/wear_count via `make_garment`, rather than round-tripping
through the upload+tagging pipeline. `weather.get_weather` is monkeypatched —
these tests are about the rotation/persistence contract, not OpenWeatherMap.
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.config import settings
from app.models.garment import Garment
from app.models.tryon import TryonRender
from app.security import create_access_token
from app.services import weather as weather_service
from app.tests.conftest import make_garment, make_user

_MILD_WEATHER = {"temp_c": 18.0, "condition": "Clear", "rain": False}


@pytest.fixture(autouse=True)
def _fake_weather(monkeypatch):
    monkeypatch.setattr(weather_service, "get_weather", lambda lat, lon: _MILD_WEATHER)


def _auth_headers(user) -> dict:
    # Tests build the User directly via the ORM (make_user), so there's no
    # plaintext password round-trip; get_current_user only needs a valid JWT
    # for that user's id, which security.create_access_token supplies.
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def _outfit_wardrobe(db, user) -> None:
    make_garment(db, user, category="top", season="all_season", formality="casual")
    make_garment(db, user, category="bottom", season="all_season", formality="casual")
    make_garment(db, user, category="shoes", season="all_season", formality="casual")


def test_daily_generates_and_persists_when_none_exists(client, db_session) -> None:
    user = make_user(db_session)
    _outfit_wardrobe(db_session, user)
    db_session.commit()

    response = client.get("/outfits/daily", headers=_auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user.id
    assert len(body["garment_ids"]) == 3
    assert body["generated_for"] == date.today().isoformat()


def test_daily_is_idempotent_within_the_same_day(client, db_session) -> None:
    user = make_user(db_session)
    _outfit_wardrobe(db_session, user)
    db_session.commit()

    first = client.get("/outfits/daily", headers=_auth_headers(user)).json()
    second = client.get("/outfits/daily", headers=_auth_headers(user)).json()

    assert first["id"] == second["id"]


def test_daily_422s_with_no_clean_tagged_garments(client, db_session) -> None:
    user = make_user(db_session)
    db_session.commit()

    response = client.get("/outfits/daily", headers=_auth_headers(user))
    assert response.status_code == 422


def test_generate_prefers_garments_excluded_from_todays_outfit(client, db_session) -> None:
    user = make_user(db_session)
    make_garment(db_session, user, category="top", season="all_season")
    make_garment(db_session, user, category="top", season="all_season")
    make_garment(db_session, user, category="bottom", season="all_season")
    db_session.commit()

    first = client.get("/outfits/daily", headers=_auth_headers(user)).json()
    second = client.post("/outfits/generate", headers=_auth_headers(user)).json()

    assert second["id"] != first["id"]
    # The regenerated outfit shouldn't reuse the exact same top when a second one exists.
    assert set(second["garment_ids"]) != set(first["garment_ids"])


def test_feedback_records_an_event(client, db_session) -> None:
    user = make_user(db_session)
    _outfit_wardrobe(db_session, user)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()

    response = client.post(
        f"/outfits/{outfit['id']}/feedback",
        json={"action": "like"},
        headers=_auth_headers(user),
    )
    assert response.status_code == 201


def test_feedback_rejects_unknown_action(client, db_session) -> None:
    user = make_user(db_session)
    _outfit_wardrobe(db_session, user)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()

    response = client.post(
        f"/outfits/{outfit['id']}/feedback",
        json={"action": "shrug"},
        headers=_auth_headers(user),
    )
    assert response.status_code == 400


def test_feedback_404s_for_another_users_outfit(client, db_session) -> None:
    owner = make_user(db_session)
    other = make_user(db_session)
    _outfit_wardrobe(db_session, owner)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(owner)).json()

    response = client.post(
        f"/outfits/{outfit['id']}/feedback",
        json={"action": "like"},
        headers=_auth_headers(other),
    )
    assert response.status_code == 404


def test_wear_bumps_wear_count_and_state_on_each_garment(client, db_session) -> None:
    user = make_user(db_session)
    _outfit_wardrobe(db_session, user)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()

    response = client.post(f"/outfits/{outfit['id']}/wear", headers=_auth_headers(user))
    assert response.status_code == 200
    assert set(response.json()["garment_ids"]) == set(outfit["garment_ids"])

    # Check via the ORM directly, not GET /garments — that endpoint mints
    # presigned URLs, which needs real storage credentials this test doesn't
    # have (and doesn't care about).
    db_session.expire_all()
    worn_garments = db_session.query(Garment).filter(Garment.id.in_(outfit["garment_ids"])).all()
    assert len(worn_garments) == len(outfit["garment_ids"])
    for garment in worn_garments:
        assert garment.state == "worn"
        assert garment.wear_count == 1
        assert garment.last_worn_at is not None


def test_wear_404s_for_another_users_outfit(client, db_session) -> None:
    owner = make_user(db_session)
    other = make_user(db_session)
    _outfit_wardrobe(db_session, owner)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(owner)).json()

    response = client.post(f"/outfits/{outfit['id']}/wear", headers=_auth_headers(other))
    assert response.status_code == 404


# --- /outfits/{id}/tryon --------------------------------------------------


class _FakeQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple] = []

    def enqueue(self, func_path: str, *args, **kwargs) -> None:
        self.enqueued.append((func_path, args, kwargs))


@pytest.fixture
def _fake_tryon_infra(monkeypatch):
    fake_queue = _FakeQueue()
    monkeypatch.setattr("app.routers.outfits.get_queue", lambda: fake_queue)
    monkeypatch.setattr(
        "app.routers.outfits.storage.presigned_download_url",
        lambda key, expires_seconds=900: f"https://fake.test/{key}",
    )
    return fake_queue


def test_tryon_requires_a_base_photo(client, db_session, _fake_tryon_infra) -> None:
    user = make_user(db_session)
    _outfit_wardrobe(db_session, user)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()

    response = client.post(f"/outfits/{outfit['id']}/tryon", headers=_auth_headers(user))

    assert response.status_code == 422
    assert _fake_tryon_infra.enqueued == []


def test_tryon_enqueues_and_returns_pending(client, db_session, _fake_tryon_infra) -> None:
    user = make_user(db_session)
    user.base_photo_url = "users/1/base.png"
    _outfit_wardrobe(db_session, user)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()

    response = client.post(f"/outfits/{outfit['id']}/tryon", headers=_auth_headers(user))

    assert response.status_code == 202
    assert response.json() == {"status": "pending", "rendered_url": None}
    assert _fake_tryon_infra.enqueued == [
        ("app.workers.tasks.generate_tryon", (user.id, outfit["id"]), {})
    ]


def test_tryon_returns_cached_render_without_enqueueing(
    client, db_session, _fake_tryon_infra
) -> None:
    user = make_user(db_session)
    user.base_photo_url = "users/1/base.png"
    _outfit_wardrobe(db_session, user)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()

    db_session.add(
        TryonRender(
            user_id=user.id,
            outfit_id=outfit["id"],
            photo_version=user.base_photo_version,
            rendered_url="tryon/1/cached.png",
        )
    )
    db_session.commit()

    response = client.post(f"/outfits/{outfit['id']}/tryon", headers=_auth_headers(user))

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "ready"
    assert body["rendered_url"] == "https://fake.test/tryon/1/cached.png"
    assert _fake_tryon_infra.enqueued == []  # cache hit - never touched the queue


def test_tryon_ignores_a_render_cached_against_a_mismatched_photo_version(
    client, db_session, _fake_tryon_infra
) -> None:
    user = make_user(db_session)
    user.base_photo_url = "users/1/base.png"
    _outfit_wardrobe(db_session, user)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()

    db_session.add(
        TryonRender(
            user_id=user.id,
            outfit_id=outfit["id"],
            photo_version=user.base_photo_version + 1,  # a future/mismatched version
            rendered_url="tryon/1/stale.png",
        )
    )
    db_session.commit()

    response = client.post(f"/outfits/{outfit['id']}/tryon", headers=_auth_headers(user))

    assert response.json()["status"] == "pending"
    assert len(_fake_tryon_infra.enqueued) == 1


def test_tryon_enforces_the_daily_cap(client, db_session, _fake_tryon_infra, monkeypatch) -> None:
    monkeypatch.setattr(settings, "TRYON_DAILY_CAP", 1)

    user = make_user(db_session)
    user.base_photo_url = "users/1/base.png"
    # Two tops so /outfits/generate below can produce a genuinely different
    # second outfit rather than falling back to the same combination.
    make_garment(db_session, user, category="top", season="all_season")
    make_garment(db_session, user, category="top", season="all_season")
    make_garment(db_session, user, category="bottom", season="all_season")
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()

    first = client.post(f"/outfits/{outfit['id']}/tryon", headers=_auth_headers(user))
    assert first.status_code == 202

    # Simulate the worker having actually generated the first one (this test
    # mocks the queue, so the job never really runs) - a real cached row is
    # what the cap counts, and it needs a real outfit_id (FK constraint).
    db_session.add(
        TryonRender(
            user_id=user.id,
            outfit_id=outfit["id"],
            photo_version=user.base_photo_version,
            rendered_url="tryon/1/outfit.png",
            created_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    second_outfit = client.post("/outfits/generate", headers=_auth_headers(user)).json()
    second = client.post(f"/outfits/{second_outfit['id']}/tryon", headers=_auth_headers(user))
    assert second.status_code == 429


def test_tryon_cap_only_counts_todays_renders(
    client, db_session, _fake_tryon_infra, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "TRYON_DAILY_CAP", 1)

    user = make_user(db_session)
    user.base_photo_url = "users/1/base.png"
    _outfit_wardrobe(db_session, user)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()

    db_session.add(
        TryonRender(
            user_id=user.id,
            outfit_id=outfit["id"],
            photo_version=99,  # won't match, so this isn't a cache hit either
            rendered_url="tryon/1/yesterday.png",
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
    )
    db_session.commit()

    response = client.post(f"/outfits/{outfit['id']}/tryon", headers=_auth_headers(user))
    assert response.status_code == 202  # yesterday's render doesn't count against today's cap


def test_tryon_404s_for_another_users_outfit(client, db_session, _fake_tryon_infra) -> None:
    owner = make_user(db_session)
    other = make_user(db_session)
    other.base_photo_url = "users/2/base.png"
    _outfit_wardrobe(db_session, owner)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(owner)).json()

    response = client.post(f"/outfits/{outfit['id']}/tryon", headers=_auth_headers(other))
    assert response.status_code == 404


def test_get_tryon_is_pending_until_a_render_is_cached(
    client, db_session, _fake_tryon_infra
) -> None:
    user = make_user(db_session)
    user.base_photo_url = "users/1/base.png"
    _outfit_wardrobe(db_session, user)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()

    pending = client.get(f"/outfits/{outfit['id']}/tryon", headers=_auth_headers(user))
    assert pending.json() == {"status": "pending", "rendered_url": None}

    db_session.add(
        TryonRender(
            user_id=user.id,
            outfit_id=outfit["id"],
            photo_version=user.base_photo_version,
            rendered_url="tryon/1/ready.png",
        )
    )
    db_session.commit()

    ready = client.get(f"/outfits/{outfit['id']}/tryon", headers=_auth_headers(user))
    assert ready.json()["status"] == "ready"
    assert ready.json()["rendered_url"] == "https://fake.test/tryon/1/ready.png"


# --- Shareable outfit links (Sprint 6) ---


@pytest.fixture
def _fake_share_storage(monkeypatch):
    monkeypatch.setattr(
        "app.routers.outfits.storage.presigned_download_url",
        lambda key, expires_seconds=900: f"https://fake.test/{key}",
    )


def test_share_creates_a_token_and_url(client, db_session) -> None:
    user = make_user(db_session)
    _outfit_wardrobe(db_session, user)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()

    response = client.post(f"/outfits/{outfit['id']}/share", headers=_auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert body["share_token"]
    assert body["share_url"] == f"{settings.FRONTEND_ORIGIN}/shared/{body['share_token']}"


def test_share_is_idempotent(client, db_session) -> None:
    user = make_user(db_session)
    _outfit_wardrobe(db_session, user)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()

    first = client.post(f"/outfits/{outfit['id']}/share", headers=_auth_headers(user)).json()
    second = client.post(f"/outfits/{outfit['id']}/share", headers=_auth_headers(user)).json()

    assert first["share_token"] == second["share_token"]


def test_share_404s_for_another_users_outfit(client, db_session) -> None:
    owner = make_user(db_session)
    other = make_user(db_session)
    _outfit_wardrobe(db_session, owner)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(owner)).json()

    response = client.post(f"/outfits/{outfit['id']}/share", headers=_auth_headers(other))
    assert response.status_code == 404


def test_unshare_revokes_the_link(client, db_session) -> None:
    user = make_user(db_session)
    _outfit_wardrobe(db_session, user)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()
    share = client.post(f"/outfits/{outfit['id']}/share", headers=_auth_headers(user)).json()

    revoke = client.delete(f"/outfits/{outfit['id']}/share", headers=_auth_headers(user))
    assert revoke.status_code == 204

    public = client.get(f"/outfits/shared/{share['share_token']}")
    assert public.status_code == 404


def test_unshare_404s_for_another_users_outfit(client, db_session) -> None:
    owner = make_user(db_session)
    other = make_user(db_session)
    _outfit_wardrobe(db_session, owner)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(owner)).json()

    response = client.delete(f"/outfits/{outfit['id']}/share", headers=_auth_headers(other))
    assert response.status_code == 404


def test_unshare_on_a_never_shared_outfit_is_not_an_error(client, db_session) -> None:
    user = make_user(db_session)
    _outfit_wardrobe(db_session, user)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()

    response = client.delete(f"/outfits/{outfit['id']}/share", headers=_auth_headers(user))
    assert response.status_code == 204


def test_get_shared_outfit_needs_no_auth_and_hides_owner_fields(
    client, db_session, _fake_share_storage
) -> None:
    user = make_user(db_session)
    _outfit_wardrobe(db_session, user)
    db_session.commit()
    outfit = client.get("/outfits/daily", headers=_auth_headers(user)).json()
    share = client.post(f"/outfits/{outfit['id']}/share", headers=_auth_headers(user)).json()

    response = client.get(f"/outfits/shared/{share['share_token']}")

    assert response.status_code == 200
    body = response.json()
    assert body["generated_for"] == outfit["generated_for"]
    assert len(body["garments"]) == len(outfit["garment_ids"])
    for garment in body["garments"]:
        assert "state" not in garment
        assert "wear_count" not in garment
        assert "user_id" not in garment


def test_get_shared_outfit_404s_for_an_unknown_token(client, db_session) -> None:
    response = client.get("/outfits/shared/not-a-real-token")
    assert response.status_code == 404
