"""Worker job for classifying one persisted interaction."""

from dataclasses import dataclass
from typing import Protocol

from lead_pipeline.domain.identifiers import InstagramEventId
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.persistence.exceptions import InteractionNotFoundError
from lead_pipeline.persistence.sqlalchemy_repositories import (
    SqlAlchemyInteractionRepository,
)
from lead_pipeline.persistence.transactional_classification import (
    TransactionalClassificationResult,
)
from lead_pipeline.persistence.transactions import (
    SessionTransactionFactory,
)


class ClassificationRunner(Protocol):
    """Execute retry-safe classification for one interaction."""

    def execute(
        self,
        interaction: InstagramInteraction,
    ) -> TransactionalClassificationResult:
        """Classify and persist one interaction."""

        ...


@dataclass(slots=True)
class ClassificationJob:
    """Load one interaction and execute classification outside the read transaction."""

    session_factory: SessionTransactionFactory
    runner: ClassificationRunner

    def execute(
        self,
        event_id: InstagramEventId,
    ) -> TransactionalClassificationResult:
        """Load and classify one interaction by stable event identifier."""

        with self.session_factory.begin() as session:
            repository = SqlAlchemyInteractionRepository(
                session=session,
            )
            interaction = repository.get_by_event_id(
                event_id,
            )

            if interaction is None:
                raise InteractionNotFoundError("interaction was not found")

        return self.runner.execute(interaction)
