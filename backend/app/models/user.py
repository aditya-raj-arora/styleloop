"""User model."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    base_photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Bumped on every base-photo upload. try-on renders are cached by
    # (user_id, outfit_id, base_photo_version) — see models/tryon.py — so a
    # new photo invalidates old cached renders without deleting them.
    base_photo_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    garments: Mapped[list["Garment"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    outfits: Mapped[list["Outfit"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    tryon_renders: Mapped[list["TryonRender"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
