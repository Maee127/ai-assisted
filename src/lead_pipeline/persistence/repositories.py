"""Persistence interfaces used by the application layer."""

from typing import Protocol

from lead_pipeline.domain.identifiers import InstagramEventId
from lead_pipeline.domain.interactions import InstagramInteraction


class InteractionRepository(Protocol):
    """Persistence boundary for authorized Instagram interactions."""

    def add(self, interaction: InstagramInteraction) -> None:
        """Persist an interaction idempotently."""

        ...

    def get_by_event_id(
        self,
        event_id: InstagramEventId,
    ) -> InstagramInteraction | None:
        """Return an interaction by its stable event identifier."""

        ...
