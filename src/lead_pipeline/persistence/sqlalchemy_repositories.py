"""Concrete SQLAlchemy persistence adapters."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.enums import ProcessingStatus, SourceType
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.domain.unresolved import UnresolvedRecord
from lead_pipeline.persistence.models import (
    ClassificationRow,
    InteractionRow,
    UnresolvedRecordRow,
)


@dataclass(slots=True)
class SqlAlchemyInteractionRepository:
    """Persist interactions through an existing SQLAlchemy transaction."""

    session: Session

    def add(self, interaction: InstagramInteraction) -> None:
        """Stage an interaction unless its stable event ID already exists."""

        event_id = interaction.event_id.value

        if self.session.get(InteractionRow, event_id) is not None:
            return

        self.session.add(
            InteractionRow(
                event_id=event_id,
                client_id=interaction.client_id.value,
                user_id=interaction.user_id.value,
                media_id=interaction.media_id.value,
                source_type=interaction.source_type.value,
                text=interaction.text,
                source_timestamp=interaction.source_timestamp,
                collected_at=interaction.collected_at,
                processing_status=interaction.status.value,
                username=interaction.username,
            )
        )

    def get_by_event_id(
        self,
        event_id: InstagramEventId,
    ) -> InstagramInteraction | None:
        """Return an interaction by its stable event identifier."""

        row = self.session.get(
            InteractionRow,
            event_id.value,
        )

        if row is None:
            return None

        return InstagramInteraction(
            event_id=InstagramEventId(row.event_id),
            client_id=ClientId(row.client_id),
            user_id=InstagramUserId(row.user_id),
            media_id=InstagramMediaId(row.media_id),
            source_type=SourceType(row.source_type),
            text=row.text,
            source_timestamp=row.source_timestamp,
            collected_at=row.collected_at,
            status=ProcessingStatus(row.processing_status),
            username=row.username,
        )


@dataclass(slots=True)
class SqlAlchemyClassificationRepository:
    """Persist versioned classifications in an existing transaction."""

    session: Session
    id_factory: Callable[[], UUID] = uuid4

    def add(
        self,
        *,
        source_event_id: InstagramEventId,
        client_id: ClientId,
        result: ClassificationResult,
        created_at: datetime,
    ) -> str:
        """Stage a classification and return its generated identifier."""

        if created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")

        classification_id = str(self.id_factory())

        self.session.add(
            ClassificationRow(
                classification_id=classification_id,
                source_event_id=source_event_id.value,
                client_id=client_id.value,
                label=result.label.value,
                confidence=result.confidence,
                reason=result.reason,
                model_name=result.model_name,
                model_version=result.model_version,
                prompt_version=result.prompt_version,
                created_at=created_at,
            )
        )

        return classification_id


@dataclass(slots=True)
class SqlAlchemyUnresolvedRecordRepository:
    """Persist unresolved outcomes in an existing transaction."""

    session: Session
    id_factory: Callable[[], UUID] = uuid4

    def add(
        self,
        *,
        record: UnresolvedRecord,
        primary_classification_id: str,
        stronger_classification_id: str,
    ) -> str:
        """Stage an unresolved record and return its generated identifier."""

        primary_id = primary_classification_id.strip()
        stronger_id = stronger_classification_id.strip()

        if not primary_id:
            raise ValueError("primary_classification_id must not be empty")

        if not stronger_id:
            raise ValueError("stronger_classification_id must not be empty")

        unresolved_id = str(self.id_factory())

        self.session.add(
            UnresolvedRecordRow(
                unresolved_id=unresolved_id,
                client_id=record.client_id.value,
                user_id=record.user_id.value,
                source_event_id=record.source_event_id.value,
                primary_classification_id=primary_id,
                stronger_classification_id=stronger_id,
                created_at=record.created_at,
            )
        )

        return unresolved_id
