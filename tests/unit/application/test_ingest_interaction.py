"""Tests for the interaction-ingestion use case."""

from datetime import UTC, datetime

from lead_pipeline.application.ingest_interaction import IngestInteraction
from lead_pipeline.domain.enums import SourceType
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction


class RecordingRepository:
    """Repository test double that records added interactions."""

    def __init__(self) -> None:
        self.added: list[InstagramInteraction] = []

    def add(self, interaction: InstagramInteraction) -> None:
        self.added.append(interaction)

    def get_by_event_id(
        self,
        event_id: InstagramEventId,
    ) -> InstagramInteraction | None:
        return next(
            (
                interaction
                for interaction in self.added
                if interaction.event_id == event_id
            ),
            None,
        )


def build_interaction() -> InstagramInteraction:
    return InstagramInteraction(
        event_id=InstagramEventId("event-1"),
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        media_id=InstagramMediaId("media-1"),
        source_type=SourceType.POST_COMMENT,
        text="Is this available?",
        source_timestamp=datetime(2026, 8, 4, 7, 45, tzinfo=UTC),
        collected_at=datetime(2026, 8, 4, 7, 46, tzinfo=UTC),
    )


def test_execute_passes_interaction_to_repository() -> None:
    repository = RecordingRepository()
    use_case = IngestInteraction(repository=repository)
    interaction = build_interaction()

    use_case.execute(interaction)

    assert repository.added == [interaction]
