"""FastAPI application entrypoint.

Wires CORS for the local frontend, mounts the API routers, and exposes a health
check. Business logic lives in the routers/services and is stubbed for Sprint 1.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, garments, outfits

app = FastAPI(title="StyleLoop API", version="0.1.0")

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
