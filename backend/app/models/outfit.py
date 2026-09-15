"""Outfit and FeedbackEvent models.

An Outfit is a scored combination of garments generated for a given day by the
rotation engine (see services/rotation.py). FeedbackEvent records swipe actions
that feed the taste-weighting term of the score.
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Outfit(Base):
    __tablename__ = "outfits"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Ordered list of garment ids composing this outfit.
    garment_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    generated_for: Mapped[date] = mapped_column(Date, index=True, nullable=False)

    # Set only once the owner requests a shareable link (POST .../share);
    # null means "never shared" or "revoked". A random opaque token, not the
    # outfit id, so a share link can be revoked without the id itself
    # changing meaning, and doesn't leak how many outfits exist.
    share_token: Mapped[str | None] = mapped_column(
        String(43), unique=True, index=True, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="outfits")  # noqa: F821
    feedback_events: Mapped[list["FeedbackEvent"]] = relationship(
        back_populates="outfit", cascade="all, delete-orphan"
    )


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    outfit_id: Mapped[int] = mapped_column(
        ForeignKey("outfits.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Swipe action, e.g. 'like' | 'dislike' | 'wore' | 'skip'.
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    outfit: Mapped["Outfit"] = relationship(back_populates="feedback_events")
