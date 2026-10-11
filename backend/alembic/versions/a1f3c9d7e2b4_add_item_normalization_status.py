"""add item normalization status

Revision ID: a1f3c9d7e2b4
Revises: c85b56f637fc
Create Date: 2026-10-10 19:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1f3c9d7e2b4"
down_revision: str | None = "c85b56f637fc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column(
            "normalization_status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
    )
    # Existing rows that already have a normalized title are marked normalized;
    # everything else stays 'pending' (the column default).
    op.execute(
        "UPDATE items SET normalization_status = 'normalized' "
        "WHERE normalized_title IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("items", "normalization_status")
