"""Application use case for storing authorized interactions."""

from dataclasses import dataclass

from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.persistence.repositories import InteractionRepository


@dataclass(slots=True)
class IngestInteraction:
    """Store an authorized interaction through the persistence boundary."""

    repository: InteractionRepository

    def execute(self, interaction: InstagramInteraction) -> None:
        """Persist the interaction idempotently."""

        self.repository.add(interaction)
