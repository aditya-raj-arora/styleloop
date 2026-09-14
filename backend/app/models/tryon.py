"""TryonRender — a cached virtual try-on image.

A row is the cache: `(user_id, outfit_id, photo_version)` identifies one
render. `photo_version` freezes which base-photo version this render was made
against, so re-uploading a base photo (which bumps `User.base_photo_version`)
naturally invalidates old renders — they just stop matching the current
lookup, without needing a delete/cleanup pass.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TryonRender(Base):
    __tablename__ = "tryon_renders"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "outfit_id", "photo_version", name="uq_tryon_renders_cache_key"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    outfit_id: Mapped[int] = mapped_column(
        ForeignKey("outfits.id", ondelete="CASCADE"), index=True, nullable=False
    )
    photo_version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Storage key of the rendered image (never a literal URL — see
    # services/storage.py; the API mints a presigned URL at response time).
    rendered_url: Mapped[str] = mapped_column(String(1024), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="tryon_renders")  # noqa: F821
