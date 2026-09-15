"""shareable outfit links - outfits.share_token

owner: ML/Engine

Revision ID: 0003_outfit_share
Revises: 0002_tryon
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_outfit_share"
down_revision: str | None = "0002_tryon"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "outfits",
        sa.Column("share_token", sa.String(length=43), nullable=True),
    )
    op.create_index(
        "ix_outfits_share_token", "outfits", ["share_token"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_outfits_share_token", table_name="outfits")
    op.drop_column("outfits", "share_token")
