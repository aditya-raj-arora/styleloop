"""Application settings, read from environment / .env via pydantic-settings.

Defaults are dev-friendly so the app (and the test suite) can import and boot
without a populated .env. Real secrets are supplied via .env or the deployment
environment and must never be committed.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg2://styleloop:styleloop@localhost:5432/styleloop"

    # --- Redis / RQ ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Object storage (private buckets, signed URLs only) ---
    STORAGE_BUCKET: str = "styleloop-media"
    STORAGE_ACCESS_KEY: str = ""
    STORAGE_SECRET_KEY: str = ""
    STORAGE_ENDPOINT_URL: str = ""
    STORAGE_REGION: str = "us-east-1"

    # --- External APIs ---
    OPENWEATHER_API_KEY: str = ""
    # A fal.ai API key (not a FASHN-issued one) — FASHN's try-on model is
    # called through fal.ai's queue API. See services/tryon.py.
    FASHN_API_KEY: str = ""

    # --- Virtual try-on (services/tryon.py, routers/outfits.py) ---
    # Plain per-user count of tryon_renders rows created "today" (UTC).
    # Cache hits don't count against it — re-serving a cached render costs
    # nothing. Keep low: each generation is a real (queued, few-second) API
    # call per garment in the outfit.
    TRYON_DAILY_CAP: int = 5

    # --- Rotation engine (services/rotation.py, routers/outfits.py) ---
    # Fallback coordinates for GET /outfits/daily and POST /outfits/generate
    # when the client doesn't supply lat/lon (e.g. geolocation denied) —
    # defaults to New York City so weather-awareness degrades gracefully
    # instead of failing the request outright.
    DEFAULT_LAT: float = 40.7128
    DEFAULT_LON: float = -74.0060

    # --- Vision tagging (Gemini API) ---
    # Used by services.tagging for category/pattern/fabric/season/formality
    # zero-shot classification. Blank disables vision tagging (colors are still
    # computed deterministically without it). Verify VISION_MODEL against the
    # current model list at ai.google.dev if it 404s — Gemini model names get
    # retired/renamed over time.
    GEMINI_API_KEY: str = ""
    VISION_MODEL: str = "gemini-3.5-flash-lite"

    # --- Background removal fallback ---
    # rembg (local, U2Net) is tried first; if it's unavailable or fails, fall
    # back to the DeepAI background-remover HTTP API using this key.
    DEEPAI_API_KEY: str = ""

    # Below this confidence, fabric is stored as None rather than a guess.
    FABRIC_CONFIDENCE_THRESHOLD: float = 0.5

    # --- Auth ---
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # --- CORS ---
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    # Additionally allow origins matching this regex (full-matched against the
    # Origin header) — used to permit Vercel preview deployments. Blank disables it.
    FRONTEND_ORIGIN_REGEX: str = r"https://styleloop-[a-z0-9-]+\.vercel\.app"

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        """Ensure SQLAlchemy uses the psycopg2 driver.

        Managed Postgres providers (Railway, Heroku, ...) hand out `postgres://`
        or `postgresql://` URLs, but our engine is configured for psycopg2. Rewrite
        the scheme so the app boots against those URLs unchanged. URLs that already
        name a driver (e.g. `postgresql+psycopg2://`, `postgresql+asyncpg://`) are
        left untouched.
        """
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg2://" + v[len("postgresql://") :]
        return v

    @field_validator("FRONTEND_ORIGIN")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        """Normalize the CORS origin.

        Browsers send the `Origin` header with no trailing slash and no path, so a
        stray slash in the env var (e.g. `https://app.vercel.app/`) would silently
        fail CORS matching. Strip it so the value matches what browsers actually send.
        """
        return v.rstrip("/")


settings = Settings()
