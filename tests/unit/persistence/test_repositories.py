"""Tests for persistence interfaces."""

from datetime import UTC, datetime

from lead_pipeline.domain.enums import SourceType
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.persistence.repositories import InteractionRepository


class InMemoryInteractionRepository:
    """Minimal test implementation of the repository protocol."""

    def __init__(self) -> None:
        self._items: dict[InstagramEventId, InstagramInteraction] = {}

    def add(self, interaction: InstagramInteraction) -> None:
        self._items.setdefault(interaction.event_id, interaction)

    def get_by_event_id(
        self,
        event_id: InstagramEventId,
    ) -> InstagramInteraction | None:
        return self._items.get(event_id)


def build_interaction() -> InstagramInteraction:
    return InstagramInteraction(
        event_id=InstagramEventId("event-1"),
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        media_id=InstagramMediaId("media-1"),
        source_type=SourceType.POST_COMMENT,
        text="Is this available?",
        source_timestamp=datetime(2026, 8, 4, 7, 30, tzinfo=UTC),
        collected_at=datetime(2026, 8, 4, 7, 31, tzinfo=UTC),
    )


def use_repository(repository: InteractionRepository) -> None:
    interaction = build_interaction()

    repository.add(interaction)

    assert repository.get_by_event_id(interaction.event_id) == interaction


def test_in_memory_repository_satisfies_protocol() -> None:
    use_repository(InMemoryInteractionRepository())
