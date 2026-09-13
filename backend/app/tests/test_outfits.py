"""`/outfits` endpoint tests.

Uses the transactional fixtures from conftest.py (real Postgres, rolled back
per test) so garments can be created directly with specific
category/season/wear_count via `make_garment`, rather than round-tripping
through the upload+tagging pipeline. `weather.get_weather` is monkeypatched —
these tests are about the rotation/persistence contract, not OpenWeatherMap.
"""

from datetime import date

import pytest

from app.models.garment import Garment
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
