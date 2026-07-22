"""Application settings, read from environment / .env via pydantic-settings.

Defaults are dev-friendly so the app (and the test suite) can import and boot
without a populated .env. Real secrets are supplied via .env or the deployment
environment and must never be committed.
"""

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
    FASHN_API_KEY: str = ""

    # --- Auth ---
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # --- CORS ---
    FRONTEND_ORIGIN: str = "http://localhost:5173"


settings = Settings()
