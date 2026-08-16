"""SQLAlchemy persistence models."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
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


class ClassificationRow(Base):
    """Persisted classification result for an interaction."""

    __tablename__ = "classifications"

    classification_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    source_event_id: Mapped[str] = mapped_column(
        ForeignKey(
            "interactions.event_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    client_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    model_version: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    prompt_version: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="confidence_range",
        ),
        Index(
            "ix_classifications_client_event",
            "client_id",
            "source_event_id",
        ),
        Index(
            "ix_classifications_client_label",
            "client_id",
            "label",
        ),
    )


class CustomerCareRow(Base):
    """Persisted customer-care case kept separate from lead data."""

    __tablename__ = "customer_care_cases"

    case_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    source_event_id: Mapped[str] = mapped_column(
        ForeignKey(
            "interactions.event_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    client_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_customer_care_client_user",
            "client_id",
            "user_id",
        ),
        Index(
            "ix_customer_care_client_created",
            "client_id",
            "created_at",
        ),
    )


class LeadProfileRow(Base):
    """Persisted client-scoped lead profile."""

    __tablename__ = "lead_profiles"

    lead_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    client_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "user_id",
            name="lead_profile_identity",
        ),
        Index(
            "ix_lead_profiles_client_updated",
            "client_id",
            "updated_at",
        ),
    )


class InterestEvidenceRow(Base):
    """Persisted evidence for one lead interest."""

    __tablename__ = "interest_evidence"

    interest_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    lead_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lead_profiles.lead_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    source_event_id: Mapped[str] = mapped_column(
        ForeignKey(
            "interactions.event_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    interest_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    model_version: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    catalogue_evidence: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    prompt_version: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="confidence_range",
        ),
        Index(
            "ix_interest_evidence_lead_created",
            "lead_id",
            "created_at",
        ),
        Index(
            "ix_interest_evidence_event",
            "source_event_id",
        ),
    )


class UnresolvedRecordRow(Base):
    """Persisted record for interactions unresolved after escalation."""

    __tablename__ = "unresolved_records"

    unresolved_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    client_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    source_event_id: Mapped[str] = mapped_column(
        ForeignKey(
            "interactions.event_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    primary_classification_id: Mapped[str] = mapped_column(
        ForeignKey(
            "classifications.classification_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    stronger_classification_id: Mapped[str] = mapped_column(
        ForeignKey(
            "classifications.classification_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_unresolved_client_created",
            "client_id",
            "created_at",
        ),
        Index(
            "ix_unresolved_client_user",
            "client_id",
            "user_id",
        ),
    )


class ErasureRequestRow(Base):
    """Persisted verified erasure request within one client boundary."""

    __tablename__ = "erasure_requests"

    request_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    client_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "verified_at >= requested_at",
            name="verified_not_before_requested",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= verified_at",
            name="completed_not_before_verified",
        ),
        Index(
            "ix_erasure_requests_client_user",
            "client_id",
            "user_id",
        ),
        Index(
            "ix_erasure_requests_client_requested",
            "client_id",
            "requested_at",
        ),
    )
