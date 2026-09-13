"""Shared pytest fixtures: an ephemeral-per-test DB session and small factory
helpers, so tests don't have to hand-roll unique emails/keys (like the
existing signup-based tests do) just to avoid colliding with each other.

`db_session` wraps each test in an outer transaction that's rolled back
afterward — but application code (routers) calls `db.commit()`, which would
normally end that outer transaction early. The fix is the standard SQLAlchemy
recipe for this ("Joining a Session into an External Transaction"): nest a
SAVEPOINT and transparently restart it every time the session's transaction
ends, so an app-level commit only ever closes the SAVEPOINT, never the real
one. See test_conftest_harness.py for a test that proves this actually
isolates data across tests (not just in theory).

Requires DATABASE_URL to point at an already-migrated Postgres — see
.github/workflows/ci.yml, which runs `alembic upgrade head` before pytest.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.database import engine, get_db
from app.main import app
from app.models.garment import DEFAULT_STATE, Garment
from app.models.user import User
from app.security import hash_password


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """A Session bound to a single connection/transaction, rolled back after
    the test — nothing a test writes (directly or via the API) is ever
    visible to another test."""
    connection = engine.connect()
    outer_transaction = connection.begin()

    TestingSessionLocal = sessionmaker(
        bind=connection, autoflush=False, autocommit=False, future=True
    )
    session = TestingSessionLocal()

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess: Session, transaction) -> None:
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """A TestClient whose requests run inside `db_session`'s transaction, so
    HTTP-driven test data rolls back the same way ORM-driven data does."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def make_user(
    db: Session, *, email: str | None = None, password: str = "correct-horse-battery"
) -> User:
    """Create and flush a User directly via the ORM (no HTTP round-trip)."""
    user = User(
        email=email or f"{uuid.uuid4().hex}@example.com",
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def make_garment(db: Session, user: User, **overrides) -> Garment:
    """Create and flush a Garment for `user`, with sensible defaults for
    whatever fields the caller doesn't override."""
    defaults: dict = {
        "image_url": f"garments/{user.id}/{uuid.uuid4().hex}-raw.jpg",
        "state": DEFAULT_STATE,
    }
    defaults.update(overrides)
    garment = Garment(user_id=user.id, **defaults)
    db.add(garment)
    db.flush()
    db.refresh(garment)
    return garment
