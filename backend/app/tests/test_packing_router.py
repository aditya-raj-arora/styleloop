"""GET /packing-list — request validation, garment eligibility, and
weather wiring. services/packing.py's own algorithm is covered by
test_packing.py (pure, no DB); these tests are about the endpoint contract.
"""

from datetime import date

import pytest

from app.security import create_access_token
from app.services import weather as weather_service
from app.tests.conftest import make_garment, make_user

_MILD_FORECAST = [
    {"date": date(2026, 6, 1), "temp_min_c": 18.0, "temp_max_c": 24.0, "rain": False},
]


@pytest.fixture(autouse=True)
def _fake_forecast(monkeypatch):
    monkeypatch.setattr(weather_service, "get_forecast", lambda lat, lon: [])


def _auth_headers(user) -> dict:
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def _wardrobe(db, user) -> None:
    make_garment(db, user, category="top", state="clean")
    make_garment(db, user, category="top", state="clean")
    make_garment(db, user, category="bottom", state="clean")
    make_garment(db, user, category="shoes", state="clean")


def test_packing_list_for_a_valid_trip(client, db_session) -> None:
    user = make_user(db_session)
    _wardrobe(db_session, user)
    db_session.commit()

    response = client.get(
        "/packing-list?start_date=2026-06-01&end_date=2026-06-03",
        headers=_auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["num_days"] == 3
    assert body["start_date"] == "2026-06-01"
    assert body["end_date"] == "2026-06-03"
    categories = {c["category"]: c for c in body["categories"]}
    assert len(categories["top"]["garments"]) == 2
    assert categories["top"]["short_by"] == 1  # wanted 3, wardrobe has 2


def test_packing_list_requires_auth(client) -> None:
    response = client.get("/packing-list?start_date=2026-06-01&end_date=2026-06-03")
    assert response.status_code == 401


def test_packing_list_rejects_end_before_start(client, db_session) -> None:
    user = make_user(db_session)
    db_session.commit()

    response = client.get(
        "/packing-list?start_date=2026-06-05&end_date=2026-06-01",
        headers=_auth_headers(user),
    )
    assert response.status_code == 400


def test_packing_list_rejects_an_unreasonably_long_trip(client, db_session) -> None:
    user = make_user(db_session)
    db_session.commit()

    response = client.get(
        "/packing-list?start_date=2026-01-01&end_date=2027-01-01",
        headers=_auth_headers(user),
    )
    assert response.status_code == 400


def test_packing_list_422s_with_no_clean_tagged_garments(client, db_session) -> None:
    user = make_user(db_session)
    db_session.commit()

    response = client.get(
        "/packing-list?start_date=2026-06-01&end_date=2026-06-03",
        headers=_auth_headers(user),
    )
    assert response.status_code == 422


def test_packing_list_ignores_untagged_and_non_clean_garments(client, db_session) -> None:
    user = make_user(db_session)
    make_garment(db_session, user, category=None, state="clean")  # untagged
    make_garment(db_session, user, category="top", state="laundry")  # in laundry
    tagged_clean = make_garment(db_session, user, category="top", state="clean")
    db_session.commit()

    response = client.get(
        "/packing-list?start_date=2026-06-01&end_date=2026-06-01",
        headers=_auth_headers(user),
    )

    assert response.status_code == 200
    tops = next(c for c in response.json()["categories"] if c["category"] == "top")
    assert [g["id"] for g in tops["garments"]] == [tagged_clean.id]


def test_packing_list_is_scoped_to_the_current_user(client, db_session) -> None:
    user_a = make_user(db_session)
    user_b = make_user(db_session)
    _wardrobe(db_session, user_a)
    db_session.commit()

    response = client.get(
        "/packing-list?start_date=2026-06-01&end_date=2026-06-01",
        headers=_auth_headers(user_b),
    )
    assert response.status_code == 422  # user_b has no wardrobe of their own


def test_packing_list_uses_the_forecast_for_the_trip_dates(client, db_session, monkeypatch) -> None:
    monkeypatch.setattr(weather_service, "get_forecast", lambda lat, lon: _MILD_FORECAST)
    user = make_user(db_session)
    _wardrobe(db_session, user)
    db_session.commit()

    response = client.get(
        "/packing-list?start_date=2026-06-01&end_date=2026-06-01",
        headers=_auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["weather"]["temp_min_c"] == 18.0
    assert body["weather"]["days_with_forecast"] == 1
    assert body["needs_outerwear"] is False  # 18C is above the cold threshold
