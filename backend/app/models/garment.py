"""Garment model — a single item of clothing owned by a user."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# 'clean' garments are eligible for the rotation engine; 'worn'/'laundry' are not.
DEFAULT_STATE = "clean"


class Garment(Base):
    __tablename__ = "garments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Raw upload and background-removed / processed render.
    image_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    processed_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Auto-tagging outputs (see services/tagging.py).
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    colors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    pattern: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fabric: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fabric_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    season: Mapped[str | None] = mapped_column(String(32), nullable=True)
    formality: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Laundry / wear tracking.
    state: Mapped[str] = mapped_column(String(32), default=DEFAULT_STATE, nullable=False)
    wear_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_worn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="garments")  # noqa: F821
