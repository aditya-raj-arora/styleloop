"""Observability: structured logging + Sentry error tracking.

Both are opt-in via settings so local dev/CI never needs either configured:
`SENTRY_DSN` blank disables Sentry entirely (same convention as
`GEMINI_API_KEY`/`FASHN_API_KEY` — see config.py), `LOG_LEVEL` defaults to
`INFO`.

`configure_logging`/`configure_sentry` are called explicitly, once, as early
as possible from each process entrypoint (`app.main` for the API,
`app.workers.run` for the RQ worker) — not as an import-time side effect, so
importing `app.main` in a test doesn't silently start reporting to Sentry or
reconfigure logging out from under pytest's own capture.
"""

from __future__ import annotations

import logging

from app.config import settings


def configure_logging() -> None:
    """Give every logger in the process an explicit level and format.

    Without this, a standalone process (the RQ worker in particular — it
    gets none of uvicorn's own logging setup) has no configured handler at
    all beyond Python's silent "last resort" one, which only prints
    WARNING+ with no timestamp or source. `process_garment`/`generate_tryon`
    already log real failures (see workers/tasks.py) that were effectively
    going nowhere useful.
    """
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        # basicConfig no-ops if the root logger already has a handler
        # (e.g. from whatever imported this module first, or a previous
        # call). force=True makes this call authoritative every time
        # instead of a silent no-op depending on import order.
        force=True,
    )


def configure_sentry(*, service_name: str, integrations: list | None = None) -> None:
    """No-op when `SENTRY_DSN` is unset. `service_name` tags which process
    (`api` vs `worker`) an event came from, since both report to the same
    Sentry project.

    `send_default_pii=False` and no request-body capture: same "never log
    user photos" rule that applies everywhere else in this codebase (see
    services/storage.py's module docstring) — an uploaded garment or base
    photo must never end up attached to an error report.
    """
    if not settings.SENTRY_DSN:
        return

    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        server_name=service_name,
        integrations=integrations or [],
        traces_sample_rate=0.0,  # error tracking only, not performance tracing
        send_default_pii=False,
        max_request_body_size="never",
    )
