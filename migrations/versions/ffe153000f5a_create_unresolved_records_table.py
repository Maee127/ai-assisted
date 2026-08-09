"""Create unresolved records table.

Revision ID: ffe153000f5a
Revises: b6dbec9573a5
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ffe153000f5a"
down_revision: str | Sequence[str] | None = "b6dbec9573a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the unresolved records table."""
    op.create_table(
        "unresolved_records",
        sa.Column(
            "unresolved_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "source_event_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "primary_classification_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "stronger_classification_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_event_id"],
            ["interactions.event_id"],
            name=op.f("fk_unresolved_records_source_event_id_interactions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["primary_classification_id"],
            ["classifications.classification_id"],
            name=op.f(
                "fk_unresolved_records_primary_classification_id_classifications"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["stronger_classification_id"],
            ["classifications.classification_id"],
            name=op.f(
                "fk_unresolved_records_stronger_classification_id_classifications"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "unresolved_id",
            name=op.f("pk_unresolved_records"),
        ),
    )
    op.create_index(
        "ix_unresolved_client_created",
        "unresolved_records",
        ["client_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_unresolved_client_user",
        "unresolved_records",
        ["client_id", "user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the unresolved records table."""
    op.drop_index(
        "ix_unresolved_client_user",
        table_name="unresolved_records",
    )
    op.drop_index(
        "ix_unresolved_client_created",
        table_name="unresolved_records",
    )
    op.drop_table("unresolved_records")
