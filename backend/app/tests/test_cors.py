"""CORS behavior: exact production origin + Vercel preview regex, others rejected."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def _allowed_origin(origin: str) -> str | None:
    """Return the echoed Access-Control-Allow-Origin for a request from `origin`."""
    resp = client.get("/health", headers={"Origin": origin})
    return resp.headers.get("access-control-allow-origin")


def test_exact_production_origin_allowed() -> None:
    assert _allowed_origin(settings.FRONTEND_ORIGIN) == settings.FRONTEND_ORIGIN


def test_vercel_preview_origin_allowed() -> None:
    preview = "https://styleloop-git-develop-acme.vercel.app"
    assert _allowed_origin(preview) == preview


def test_unknown_origin_rejected() -> None:
    assert _allowed_origin("https://evil.example.com") is None


def test_lookalike_suffix_rejected() -> None:
    # Full-match must anchor the end so a trailing domain can't sneak through.
    assert _allowed_origin("https://styleloop-x.vercel.app.evil.com") is None
