"""Create interest evidence table.

Revision ID: b6dbec9573a5
Revises: 696e14f9f465
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b6dbec9573a5"
down_revision: str | Sequence[str] | None = "696e14f9f465"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the interest evidence table."""
    op.create_table(
        "interest_evidence",
        sa.Column(
            "interest_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "lead_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "source_event_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "interest_type",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Float(),
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
            "catalogue_evidence",
            sa.Text(),
            nullable=True,
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
            name=op.f("ck_interest_evidence_confidence_range"),
        ),
        sa.ForeignKeyConstraint(
            ["lead_id"],
            ["lead_profiles.lead_id"],
            name=op.f("fk_interest_evidence_lead_id_lead_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_event_id"],
            ["interactions.event_id"],
            name=op.f("fk_interest_evidence_source_event_id_interactions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "interest_id",
            name=op.f("pk_interest_evidence"),
        ),
    )
    op.create_index(
        "ix_interest_evidence_event",
        "interest_evidence",
        ["source_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_interest_evidence_lead_created",
        "interest_evidence",
        ["lead_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the interest evidence table."""
    op.drop_index(
        "ix_interest_evidence_lead_created",
        table_name="interest_evidence",
    )
    op.drop_index(
        "ix_interest_evidence_event",
        table_name="interest_evidence",
    )
    op.drop_table("interest_evidence")
