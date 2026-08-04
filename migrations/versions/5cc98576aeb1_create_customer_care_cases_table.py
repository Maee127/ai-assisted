"""Create customer care cases table.

Revision ID: 5cc98576aeb1
Revises: 0fed4962a84e
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5cc98576aeb1"
down_revision: str | Sequence[str] | None = "0fed4962a84e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the customer care cases table."""
    op.create_table(
        "customer_care_cases",
        sa.Column(
            "case_id",
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
            "user_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "summary",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "username",
            sa.String(length=255),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["source_event_id"],
            ["interactions.event_id"],
            name=op.f("fk_customer_care_cases_source_event_id_interactions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "case_id",
            name=op.f("pk_customer_care_cases"),
        ),
    )
    op.create_index(
        "ix_customer_care_client_created",
        "customer_care_cases",
        ["client_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_customer_care_client_user",
        "customer_care_cases",
        ["client_id", "user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the customer care cases table."""
    op.drop_index(
        "ix_customer_care_client_user",
        table_name="customer_care_cases",
    )
    op.drop_index(
        "ix_customer_care_client_created",
        table_name="customer_care_cases",
    )
    op.drop_table("customer_care_cases")
