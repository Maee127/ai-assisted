"""Transactional persistence for completed classification outcomes."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from lead_pipeline.application.classify_interaction import (
    ClassificationOutcome,
    ClassifyInteraction,
)
from lead_pipeline.application.extract_interests import (
    ExtractInterests,
    InterestExtractionOutcome,
)
from lead_pipeline.application.persist_classification_outcome import (
    ClassificationPersistenceReceipt,
    PersistClassificationOutcome,
)
from lead_pipeline.application.persist_interest_outcome import (
    InterestPersistenceReceipt,
    PersistInterestExtractionOutcome,
)
from lead_pipeline.domain.catalogue import CatalogueContext
from lead_pipeline.domain.enums import ProcessingStatus
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.persistence.sqlalchemy_repositories import (
    SqlAlchemyCatalogueRepository,
    SqlAlchemyClassificationRepository,
    SqlAlchemyInteractionRepository,
    SqlAlchemyInterestEvidenceRepository,
    SqlAlchemyLeadProfileRepository,
    SqlAlchemyUnresolvedRecordRepository,
)
from lead_pipeline.persistence.transactions import SessionTransactionFactory


@dataclass(frozen=True, slots=True)
class TransactionalClassificationResult:
    """Classification and interest outcomes persisted for one interaction."""

    outcome: ClassificationOutcome
    receipt: ClassificationPersistenceReceipt
    interest_outcome: InterestExtractionOutcome
    interest_receipt: InterestPersistenceReceipt


@dataclass(slots=True)
class TransactionalInteractionClassifier:
    """Retrieve context, run models safely, and persist atomically."""

    session_factory: SessionTransactionFactory
    classifier: ClassifyInteraction
    interest_extractor: ExtractInterests
    clock: Callable[[], datetime]

    def execute(
        self,
        interaction: InstagramInteraction,
    ) -> TransactionalClassificationResult:
        """Classify, extract interests, and atomically persist one interaction."""

        with self.session_factory.begin() as session:
            interaction_repository = SqlAlchemyInteractionRepository(
                session=session,
            )
            interaction_repository.transition_status(
                event_id=interaction.event_id,
                target=ProcessingStatus.QUEUED,
            )
            interaction_repository.transition_status(
                event_id=interaction.event_id,
                target=ProcessingStatus.PROCESSING,
            )

        try:
            with self.session_factory.begin() as session:
                catalogue_repository = SqlAlchemyCatalogueRepository(
                    session=session,
                )
                catalogue_items = catalogue_repository.search(
                    client_id=interaction.client_id,
                    query=interaction.text,
                    limit=5,
                )

            catalogue_context = CatalogueContext(
                client_id=interaction.client_id,
                items=catalogue_items,
            )
            outcome = self.classifier.execute(
                interaction,
                catalogue_context=catalogue_context,
            )
            interest_outcome = self.interest_extractor.execute(
                interaction,
                classification=outcome.final_result,
                catalogue_context=catalogue_context,
            )

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
                lead_profile_repository = SqlAlchemyLeadProfileRepository(
                    session=session,
                )
                interest_repository = SqlAlchemyInterestEvidenceRepository(
                    session=session,
                )

                classification_persistence = PersistClassificationOutcome(
                    classification_repository=classification_repository,
                    unresolved_repository=unresolved_repository,
                    clock=self.clock,
                )
                interest_persistence = PersistInterestExtractionOutcome(
                    lead_profile_repository=lead_profile_repository,
                    interest_repository=interest_repository,
                    clock=self.clock,
                )

                receipt = classification_persistence.execute(
                    interaction=interaction,
                    outcome=outcome,
                )
                interest_receipt = interest_persistence.execute(
                    interaction=interaction,
                    outcome=interest_outcome,
                )
                interaction_repository.transition_status(
                    event_id=interaction.event_id,
                    target=ProcessingStatus.COMPLETED,
                )
        except Exception:
            with self.session_factory.begin() as session:
                interaction_repository = SqlAlchemyInteractionRepository(
                    session=session,
                )
                interaction_repository.transition_status(
                    event_id=interaction.event_id,
                    target=ProcessingStatus.RETRYABLE_FAILURE,
                )

            raise

        return TransactionalClassificationResult(
            outcome=outcome,
            receipt=receipt,
            interest_outcome=interest_outcome,
            interest_receipt=interest_receipt,
        )
