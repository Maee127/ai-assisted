"""SQLAlchemy persistence models."""

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from lead_pipeline.persistence.database import Base


class InteractionRow(Base):
    """Persisted authorized Instagram interaction."""

    __tablename__ = "interactions"

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    media_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    processing_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_interactions_client_user",
            "client_id",
            "user_id",
        ),
        Index(
            "ix_interactions_client_status",
            "client_id",
            "processing_status",
        ),
    )
