"""Create classifications table.

Revision ID: 0fed4962a84e
Revises: bce4d3cf000a
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0fed4962a84e"
down_revision: str | Sequence[str] | None = "bce4d3cf000a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the classifications table."""
    op.create_table(
        "classifications",
        sa.Column(
            "classification_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "source_event_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "label",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "reason",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "model_name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "model_version",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "prompt_version",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name=op.f("ck_classifications_confidence_range"),
        ),
        sa.ForeignKeyConstraint(
            ["source_event_id"],
            ["interactions.event_id"],
            name=op.f("fk_classifications_source_event_id_interactions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "classification_id",
            name=op.f("pk_classifications"),
        ),
    )
    op.create_index(
        "ix_classifications_client_event",
        "classifications",
        ["client_id", "source_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_classifications_client_label",
        "classifications",
        ["client_id", "label"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the classifications table."""
    op.drop_index(
        "ix_classifications_client_label",
        table_name="classifications",
    )
    op.drop_index(
        "ix_classifications_client_event",
        table_name="classifications",
    )
    op.drop_table("classifications")
