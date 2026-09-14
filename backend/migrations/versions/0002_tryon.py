"""virtual try-on - base_photo_version, tryon_renders

owner: ML/Engine

Revision ID: 0002_tryon
Revises: 0001_initial
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_tryon"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("base_photo_version", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "tryon_renders",
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
        sa.Column("photo_version", sa.Integer(), nullable=False),
        sa.Column("rendered_url", sa.String(length=1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "outfit_id", "photo_version", name="uq_tryon_renders_cache_key"
        ),
    )
    op.create_index("ix_tryon_renders_user_id", "tryon_renders", ["user_id"])
    op.create_index("ix_tryon_renders_outfit_id", "tryon_renders", ["outfit_id"])


def downgrade() -> None:
    op.drop_table("tryon_renders")
    op.drop_column("users", "base_photo_version")
