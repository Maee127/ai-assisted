"""Transactional persistence for completed classification outcomes."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from lead_pipeline.application.classify_interaction import (
    ClassificationOutcome,
    ClassifyInteraction,
)
from lead_pipeline.application.persist_classification_outcome import (
    ClassificationPersistenceReceipt,
    PersistClassificationOutcome,
)
from lead_pipeline.domain.enums import ProcessingStatus
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.persistence.sqlalchemy_repositories import (
    SqlAlchemyClassificationRepository,
    SqlAlchemyInteractionRepository,
    SqlAlchemyUnresolvedRecordRepository,
)
from lead_pipeline.persistence.transactions import (
    SessionTransactionFactory,
)


@dataclass(frozen=True, slots=True)
class TransactionalClassificationResult:
    """Classification decision and identifiers persisted for it."""

    outcome: ClassificationOutcome
    receipt: ClassificationPersistenceReceipt


@dataclass(slots=True)
class TransactionalInteractionClassifier:
    """Classify outside a transaction, then persist atomically."""

    session_factory: SessionTransactionFactory
    classifier: ClassifyInteraction
    clock: Callable[[], datetime]

    def execute(
        self,
        interaction: InstagramInteraction,
    ) -> TransactionalClassificationResult:
        """Classify an interaction and atomically persist its outcome."""

        outcome = self.classifier.execute(interaction)

        with self.session_factory.begin() as session:
            interaction_repository = SqlAlchemyInteractionRepository(
                session=session,
            )
            classification_repository = SqlAlchemyClassificationRepository(
                session=session,
            )
            unresolved_repository = SqlAlchemyUnresolvedRecordRepository(
                session=session,
            )
            persistence = PersistClassificationOutcome(
                classification_repository=classification_repository,
                unresolved_repository=unresolved_repository,
                clock=self.clock,
            )
            receipt = persistence.execute(
                interaction=interaction,
                outcome=outcome,
            )
            interaction_repository.transition_status(
                event_id=interaction.event_id,
                target=ProcessingStatus.COMPLETED,
            )

        return TransactionalClassificationResult(
            outcome=outcome,
            receipt=receipt,
        )
