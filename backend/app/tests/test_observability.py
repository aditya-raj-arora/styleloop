"""app.observability — both functions are no-ops safe to call repeatedly
(pytest imports app.main, which calls them, once per test-collection
process), so these tests focus on the actual branching logic: Sentry stays
off without a DSN, and turns on with the right options when one's set.
"""

from __future__ import annotations

import logging

import sentry_sdk

from app import observability
from app.config import settings


def test_configure_logging_sets_the_configured_level(monkeypatch) -> None:
    monkeypatch.setattr(settings, "LOG_LEVEL", "DEBUG")
    observability.configure_logging()
    assert logging.getLogger().getEffectiveLevel() == logging.DEBUG


def test_configure_sentry_is_a_noop_without_a_dsn(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SENTRY_DSN", "")
    calls: list[dict] = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: calls.append(kwargs))

    observability.configure_sentry(service_name="api")

    assert calls == []


def test_configure_sentry_initializes_with_a_dsn(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://fake@sentry.example/1")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    calls: list[dict] = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: calls.append(kwargs))

    observability.configure_sentry(service_name="worker")

    assert len(calls) == 1
    kwargs = calls[0]
    assert kwargs["dsn"] == "https://fake@sentry.example/1"
    assert kwargs["environment"] == "production"
    assert kwargs["server_name"] == "worker"
    # Never let a photo end up attached to an error report.
    assert kwargs["send_default_pii"] is False
    assert kwargs["max_request_body_size"] == "never"


def test_configure_sentry_passes_through_integrations(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://fake@sentry.example/1")
    calls: list[dict] = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: calls.append(kwargs))

    sentinel = object()
    observability.configure_sentry(service_name="worker", integrations=[sentinel])

    assert calls[0]["integrations"] == [sentinel]
