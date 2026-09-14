"""FastAPI application entrypoint.

Wires CORS for the local frontend, mounts the API routers, and exposes a health
check. Business logic lives in the routers/services.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.observability import configure_logging, configure_sentry
from app.rate_limiting import limiter
from app.routers import auth, garments, outfits

configure_logging()
configure_sentry(service_name="api")

app = FastAPI(title="VogueVault API", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_origin_regex=settings.FRONTEND_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(garments.router)
app.include_router(outfits.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness probe used by CI, Docker, and the deploy platform."""
    return {"status": "ok"}
