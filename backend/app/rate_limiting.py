"""Shared slowapi `Limiter` instance.

A separate module (not defined in `main.py`) so routers can import `limiter`
for their own `@limiter.limit(...)` decorators without a circular import —
`main.py` imports the routers, so a router importing `limiter` back out of
`main.py` would be circular.
"""

import sys

from slowapi import Limiter
from slowapi.util import get_remote_address

# Disabled whenever running under pytest: the test suite drives dozens of
# signup/login calls in quick succession through TestClient's single fake
# "IP" (Starlette gives every TestClient request the same client host), so
# a real per-IP limit would trip partway through an unrelated test and make
# pass/fail depend on execution order. "pytest" is reliably present in
# sys.modules by the time any app code is imported during a test run —
# pytest always imports itself before it imports/collects test modules —
# unlike an env var such as PYTEST_CURRENT_TEST, which pytest only sets
# around each individual test's execution, not at collection/import time
# (when `from app.main import app` actually runs). test_rate_limiting.py
# re-enables this explicitly to verify the real enforcement.
limiter = Limiter(key_func=get_remote_address, enabled="pytest" not in sys.modules)
