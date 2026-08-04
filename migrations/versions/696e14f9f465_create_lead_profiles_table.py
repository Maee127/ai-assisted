"""Create lead profiles table.

Revision ID: 696e14f9f465
Revises: 5cc98576aeb1
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "696e14f9f465"
down_revision: str | Sequence[str] | None = "5cc98576aeb1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the lead profiles table."""
    op.create_table(
        "lead_profiles",
        sa.Column(
            "lead_id",
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
            "username",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "lead_id",
            name=op.f("pk_lead_profiles"),
        ),
        sa.UniqueConstraint(
            "client_id",
            "user_id",
            name="lead_profile_identity",
        ),
    )
    op.create_index(
        "ix_lead_profiles_client_updated",
        "lead_profiles",
        ["client_id", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the lead profiles table."""
    op.drop_index(
        "ix_lead_profiles_client_updated",
        table_name="lead_profiles",
    )
    op.drop_table("lead_profiles")
