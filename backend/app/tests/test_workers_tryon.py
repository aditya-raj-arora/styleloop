"""workers.tasks.generate_tryon — run directly (not via RQ) against the real
transactional DB fixtures, with services.storage and services.tryon
monkeypatched so no real bucket or FASHN call happens. Focuses on the
idempotency/ordering/error-handling logic this task owns, not on rendering
itself (see test_tryon.py for that).
"""

from __future__ import annotations

from datetime import date

from app import database as database_module
from app.models.outfit import Outfit
from app.models.tryon import TryonRender
from app.services import storage
from app.services import tryon as tryon_service
from app.tests.conftest import make_garment, make_user
from app.workers.tasks import generate_tryon


class _NonClosingSession:
    """Wraps the `db_session` fixture so the task's own `db.close()` doesn't
    tear down the session the test still needs afterward for assertions —
    the fixture's rollback (not this task) is what actually cleans up."""

    def __init__(self, session):
        self._session = session

    def __getattr__(self, name):
        return getattr(self._session, name)

    def close(self) -> None:
        pass


def _make_outfit(db, user, garments) -> Outfit:
    outfit = Outfit(
        user_id=user.id,
        garment_ids=[g.id for g in garments],
        score=1.0,
        generated_for=date.today(),
    )
    db.add(outfit)
    db.flush()
    db.refresh(outfit)
    return outfit


def _patch_session_and_storage(monkeypatch, db_session):
    # generate_tryon does `from app.database import SessionLocal` *inside*
    # the function body (lazy import, matching process_garment's existing
    # style), so the patch target is the real module attribute, not
    # whatever `app.workers.tasks` happens to have bound at import time.
    monkeypatch.setattr(database_module, "SessionLocal", lambda: _NonClosingSession(db_session))
    uploaded: dict[str, bytes] = {}
    monkeypatch.setattr(
        storage, "upload_bytes", lambda key, data, ct: uploaded.__setitem__(key, data)
    )
    monkeypatch.setattr(
        storage, "presigned_download_url", lambda key, expires_seconds=900: f"https://fake.test/{key}"
    )
    return uploaded


def test_generate_tryon_skips_when_user_has_no_base_photo(monkeypatch, db_session) -> None:
    user = make_user(db_session)
    top = make_garment(db_session, user, category="top")
    bottom = make_garment(db_session, user, category="bottom")
    outfit = _make_outfit(db_session, user, [top, bottom])
    db_session.commit()

    _patch_session_and_storage(monkeypatch, db_session)
    calls: list[object] = []
    monkeypatch.setattr(tryon_service, "render_tryon", lambda *a, **k: calls.append(1))

    generate_tryon(user.id, outfit.id)

    assert calls == []  # never even attempted - no base photo to render onto
    assert db_session.query(TryonRender).count() == 0


def test_generate_tryon_persists_a_render(monkeypatch, db_session) -> None:
    user = make_user(db_session)
    user.base_photo_url = "users/1/base.png"
    top = make_garment(db_session, user, category="top")
    bottom = make_garment(db_session, user, category="bottom")
    outfit = _make_outfit(db_session, user, [top, bottom])
    db_session.commit()

    _patch_session_and_storage(monkeypatch, db_session)

    rendered_with: list[list[str]] = []

    def fake_render(base_photo_url, garments):
        rendered_with.append([g.category for g in garments])
        return b"rendered-bytes"

    monkeypatch.setattr(tryon_service, "render_tryon", fake_render)

    generate_tryon(user.id, outfit.id)

    renders = db_session.query(TryonRender).filter(TryonRender.outfit_id == outfit.id).all()
    assert len(renders) == 1
    assert renders[0].photo_version == user.base_photo_version
    # top before bottom, per the render-order rule.
    assert rendered_with == [["top", "bottom"]]


def test_generate_tryon_is_idempotent_for_an_already_cached_render(monkeypatch, db_session) -> None:
    user = make_user(db_session)
    user.base_photo_url = "users/1/base.png"
    top = make_garment(db_session, user, category="top")
    outfit = _make_outfit(db_session, user, [top])
    db_session.add(
        TryonRender(
            user_id=user.id,
            outfit_id=outfit.id,
            photo_version=user.base_photo_version,
            rendered_url="tryon/1/cached.png",
        )
    )
    db_session.commit()

    _patch_session_and_storage(monkeypatch, db_session)
    calls: list[object] = []
    monkeypatch.setattr(tryon_service, "render_tryon", lambda *a, **k: calls.append(1) or b"x")

    generate_tryon(user.id, outfit.id)

    assert calls == []  # never re-rendered - the cache hit short-circuited it
    assert db_session.query(TryonRender).filter(TryonRender.outfit_id == outfit.id).count() == 1


def test_generate_tryon_does_not_crash_or_persist_on_render_failure(
    monkeypatch, db_session
) -> None:
    user = make_user(db_session)
    user.base_photo_url = "users/1/base.png"
    top = make_garment(db_session, user, category="top")
    bottom = make_garment(db_session, user, category="bottom")
    outfit = _make_outfit(db_session, user, [top, bottom])
    db_session.commit()

    _patch_session_and_storage(monkeypatch, db_session)

    def failing_render(*a, **k):
        raise tryon_service.TryonError("boom")

    monkeypatch.setattr(tryon_service, "render_tryon", failing_render)

    generate_tryon(user.id, outfit.id)  # must not raise

    assert db_session.query(TryonRender).count() == 0
