"""Application orchestration for interest extraction and escalation."""

from dataclasses import dataclass

from lead_pipeline.domain.catalogue import CatalogueContext
from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.enums import ClassificationLabel, InterestType
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.domain.interests import InterestEvidence
from lead_pipeline.processing.interest_extraction import (
    InterestExtractionProvider,
)


@dataclass(frozen=True, slots=True)
class InterestExtractionOutcome:
    """Confirmed and unresolved interests from one interaction."""

    primary_interests: tuple[InterestEvidence, ...]
    confirmed_interests: tuple[InterestEvidence, ...]
    stronger_interests: tuple[InterestEvidence, ...] = ()
    unresolved_interests: tuple[InterestEvidence, ...] = ()

    @property
    def was_escalated(self) -> bool:
        """Return whether stronger-model reevaluation occurred."""

        return bool(self.stronger_interests or self.unresolved_interests)


@dataclass(slots=True)
class ExtractInterests:
    """Extract interests and escalate low-confidence inferred evidence."""

    primary_provider: InterestExtractionProvider
    stronger_provider: InterestExtractionProvider
    inferred_confidence_threshold: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.inferred_confidence_threshold <= 1.0:
            raise ValueError(
                "inferred_confidence_threshold must be between 0.0 and 1.0"
            )

    def execute(
        self,
        interaction: InstagramInteraction,
        *,
        classification: ClassificationResult,
        catalogue_context: CatalogueContext | None = None,
    ) -> InterestExtractionOutcome:
        """Return confirmed interests only for a final sales classification."""

        if classification.label is not ClassificationLabel.SALES_LEAD:
            return InterestExtractionOutcome(
                primary_interests=(),
                confirmed_interests=(),
            )

        context = catalogue_context
        if context is None:
            context = CatalogueContext(
                client_id=interaction.client_id,
            )

        if context.client_id != interaction.client_id:
            raise ValueError("catalogue context must belong to the interaction client")

        primary_interests = self.primary_provider.extract(
            interaction,
            catalogue_context=context,
        )
        self._ensure_source_event(
            interaction=interaction,
            interests=primary_interests,
        )

        confirmed_primary = tuple(
            interest
            for interest in primary_interests
            if interest.interest_type is InterestType.EXPLICIT
            or interest.confidence >= self.inferred_confidence_threshold
        )
        low_confidence_inferred = tuple(
            interest
            for interest in primary_interests
            if interest.interest_type is InterestType.INFERRED
            and interest.confidence < self.inferred_confidence_threshold
        )

        if not low_confidence_inferred:
            return InterestExtractionOutcome(
                primary_interests=primary_interests,
                confirmed_interests=confirmed_primary,
            )

        stronger_interests = self.stronger_provider.extract(
            interaction,
            catalogue_context=context,
            candidates=low_confidence_inferred,
        )
        self._ensure_source_event(
            interaction=interaction,
            interests=stronger_interests,
        )

        confirmed_stronger = tuple(
            interest
            for interest in stronger_interests
            if interest.interest_type is InterestType.EXPLICIT
            or interest.confidence >= self.inferred_confidence_threshold
        )
        unresolved_interests = tuple(
            interest
            for interest in stronger_interests
            if interest.interest_type is InterestType.INFERRED
            and interest.confidence < self.inferred_confidence_threshold
        )

        return InterestExtractionOutcome(
            primary_interests=primary_interests,
            stronger_interests=stronger_interests,
            confirmed_interests=(
                *confirmed_primary,
                *confirmed_stronger,
            ),
            unresolved_interests=unresolved_interests,
        )

    @staticmethod
    def _ensure_source_event(
        *,
        interaction: InstagramInteraction,
        interests: tuple[InterestEvidence, ...],
    ) -> None:
        for interest in interests:
            if interest.source_event_id != interaction.event_id:
                raise ValueError(
                    "interest evidence must reference the interaction event"
                )
