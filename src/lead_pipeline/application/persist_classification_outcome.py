"""Application orchestration for persisting classification outcomes."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from lead_pipeline.application.classify_interaction import (
    ClassificationOutcome,
)
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.persistence.repositories import (
    ClassificationRepository,
    UnresolvedRecordRepository,
)


@dataclass(frozen=True, slots=True)
class ClassificationPersistenceReceipt:
    """Identifiers created while persisting one classification outcome."""

    primary_classification_id: str
    stronger_classification_id: str | None = None
    unresolved_id: str | None = None


@dataclass(slots=True)
class PersistClassificationOutcome:
    """Persist one complete classification outcome atomically."""

    classification_repository: ClassificationRepository
    unresolved_repository: UnresolvedRecordRepository
    clock: Callable[[], datetime]

    def execute(
        self,
        *,
        interaction: InstagramInteraction,
        outcome: ClassificationOutcome,
    ) -> ClassificationPersistenceReceipt:
        """Stage all rows required by the classification outcome."""

        created_at = (
            outcome.unresolved_record.created_at
            if outcome.unresolved_record is not None
            else self.clock()
        )
        primary_classification_id = self.classification_repository.add(
            source_event_id=interaction.event_id,
            client_id=interaction.client_id,
            result=outcome.primary_result,
            created_at=created_at,
        )

        if outcome.stronger_result is None:
            return ClassificationPersistenceReceipt(
                primary_classification_id=primary_classification_id,
            )

        stronger_classification_id = self.classification_repository.add(
            source_event_id=interaction.event_id,
            client_id=interaction.client_id,
            result=outcome.stronger_result,
            created_at=created_at,
        )
        unresolved_id: str | None = None

        if outcome.unresolved_record is not None:
            unresolved_id = self.unresolved_repository.add(
                record=outcome.unresolved_record,
                primary_classification_id=primary_classification_id,
                stronger_classification_id=stronger_classification_id,
            )

        return ClassificationPersistenceReceipt(
            primary_classification_id=primary_classification_id,
            stronger_classification_id=stronger_classification_id,
            unresolved_id=unresolved_id,
        )
