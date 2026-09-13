"""Proves the conftest fixtures actually isolate tests from each other — not
just that the SAVEPOINT recipe is textbook-correct. Both tests below use the
exact same hardcoded email; if `db_session`/`client` leaked data between
tests, whichever of these two ran second would fail with a unique-constraint
violation. Order-independent: run in either order, both must pass.
"""

from app.tests.conftest import make_garment, make_user

_SHARED_EMAIL = "harness-isolation@example.com"


def test_orm_isolation_attempt_one(db_session) -> None:
    user = make_user(db_session, email=_SHARED_EMAIL)
    assert user.id is not None


def test_orm_isolation_attempt_two(db_session) -> None:
    # Would raise IntegrityError (unique email) if attempt_one's row leaked in.
    user = make_user(db_session, email=_SHARED_EMAIL)
    assert user.id is not None


def test_http_isolation_attempt_one(client) -> None:
    response = client.post(
        "/auth/signup", json={"email": _SHARED_EMAIL, "password": "correct-horse-battery"}
    )
    assert response.status_code == 201


def test_http_isolation_attempt_two(client) -> None:
    # Would 409 (email already registered) if attempt_one's commit leaked out
    # of its transaction — proves app-level db.commit() only closes the
    # SAVEPOINT, not the real outer transaction.
    response = client.post(
        "/auth/signup", json={"email": _SHARED_EMAIL, "password": "correct-horse-battery"}
    )
    assert response.status_code == 201


def test_make_garment_factory_defaults_and_overrides(db_session) -> None:
    user = make_user(db_session)
    garment = make_garment(db_session, user, category="top", wear_count=3)

    assert garment.user_id == user.id
    assert garment.state == "clean"  # factory default
    assert garment.category == "top"  # override applied
    assert garment.wear_count == 3


def test_deleting_user_cascades_to_garments(db_session) -> None:
    user = make_user(db_session)
    garment = make_garment(db_session, user)
    garment_id = garment.id

    db_session.delete(user)
    db_session.flush()

    from app.models.garment import Garment

    assert db_session.get(Garment, garment_id) is None
