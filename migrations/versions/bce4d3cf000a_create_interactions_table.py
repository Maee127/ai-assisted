"""Create interactions table.

Revision ID: bce4d3cf000a
Revises:
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "bce4d3cf000a"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the interactions table."""
    op.create_table(
        "interactions",
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("media_id", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "source_timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "processing_status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint(
            "event_id",
            name=op.f("pk_interactions"),
        ),
    )
    op.create_index(
        "ix_interactions_client_status",
        "interactions",
        ["client_id", "processing_status"],
        unique=False,
    )
    op.create_index(
        "ix_interactions_client_user",
        "interactions",
        ["client_id", "user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the interactions table."""
    op.drop_index(
        "ix_interactions_client_user",
        table_name="interactions",
    )
    op.drop_index(
        "ix_interactions_client_status",
        table_name="interactions",
    )
    op.drop_table("interactions")
