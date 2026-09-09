"""initial schema - users, garments, outfits, feedback_events

owner: Backend/Infra

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("base_photo_url", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "garments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("image_url", sa.String(length=1024), nullable=False),
        sa.Column("processed_url", sa.String(length=1024), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("colors", postgresql.JSONB(), nullable=True),
        sa.Column("pattern", sa.String(length=64), nullable=True),
        sa.Column("fabric", sa.String(length=64), nullable=True),
        sa.Column("fabric_confidence", sa.Float(), nullable=True),
        sa.Column("season", sa.String(length=32), nullable=True),
        sa.Column("formality", sa.String(length=32), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="clean"),
        sa.Column("wear_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_worn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_garments_user_id", "garments", ["user_id"])

    op.create_table(
        "outfits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("garment_ids", postgresql.JSONB(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("generated_for", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_outfits_user_id", "outfits", ["user_id"])
    op.create_index("ix_outfits_generated_for", "outfits", ["generated_for"])

    op.create_table(
        "feedback_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "outfit_id",
            sa.Integer(),
            sa.ForeignKey("outfits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_feedback_events_user_id", "feedback_events", ["user_id"])
    op.create_index("ix_feedback_events_outfit_id", "feedback_events", ["outfit_id"])


def downgrade() -> None:
    op.drop_table("feedback_events")
    op.drop_table("outfits")
    op.drop_table("garments")
    op.drop_table("users")
