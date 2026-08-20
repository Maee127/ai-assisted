"""Concrete SQLAlchemy persistence adapters."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from lead_pipeline.domain.enums import ProcessingStatus, SourceType
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.persistence.models import InteractionRow


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
