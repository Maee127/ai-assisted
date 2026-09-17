"""Application orchestration for classification and uncertainty."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from lead_pipeline.domain.catalogue import CatalogueContext
from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.enums import ClassificationLabel
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.domain.unresolved import UnresolvedRecord
from lead_pipeline.processing.classification import ClassificationProvider


@dataclass(frozen=True, slots=True)
class ClassificationOutcome:
    """Complete result of primary and optional stronger classification."""

    primary_result: ClassificationResult
    final_result: ClassificationResult
    stronger_result: ClassificationResult | None = None
    unresolved_record: UnresolvedRecord | None = None

    @property
    def was_escalated(self) -> bool:
        """Return whether the stronger classifier was called."""

        return self.stronger_result is not None

    @property
    def is_unresolved(self) -> bool:
        """Return whether both classifiers remained uncertain."""

        return self.unresolved_record is not None


@dataclass(slots=True)
class ClassifyInteraction:
    """Classify interactions and gate sales-lead promotion by confidence."""

    primary_provider: ClassificationProvider
    stronger_provider: ClassificationProvider
    clock: Callable[[], datetime]
    sales_lead_confidence_threshold: float = 0.9

    def __post_init__(self) -> None:
        if not 0.0 <= self.sales_lead_confidence_threshold <= 1.0:
            raise ValueError(
                "sales_lead_confidence_threshold must be between 0.0 and 1.0"
            )

    def execute(
        self,
        interaction: InstagramInteraction,
        *,
        catalogue_context: CatalogueContext | None = None,
    ) -> ClassificationOutcome:
        """Return the final classification decision."""

        context = catalogue_context

        if context is None:
            context = CatalogueContext(
                client_id=interaction.client_id,
            )

        if context.client_id != interaction.client_id:
            raise ValueError("catalogue context must belong to the interaction client")

        primary_result = self._apply_sales_lead_promotion_gate(
            self.primary_provider.classify(
                interaction,
                catalogue_context=context,
            )
        )

        if primary_result.label is not ClassificationLabel.UNCERTAIN:
            return ClassificationOutcome(
                primary_result=primary_result,
                final_result=primary_result,
            )

        stronger_result = self._apply_sales_lead_promotion_gate(
            self.stronger_provider.classify(
                interaction,
                catalogue_context=context,
            )
        )

        if stronger_result.label is not ClassificationLabel.UNCERTAIN:
            return ClassificationOutcome(
                primary_result=primary_result,
                stronger_result=stronger_result,
                final_result=stronger_result,
            )

        unresolved_record = UnresolvedRecord(
            client_id=interaction.client_id,
            user_id=interaction.user_id,
            source_event_id=interaction.event_id,
            primary_result=primary_result,
            stronger_result=stronger_result,
            created_at=self.clock(),
        )

        return ClassificationOutcome(
            primary_result=primary_result,
            stronger_result=stronger_result,
            final_result=stronger_result,
            unresolved_record=unresolved_record,
        )

    def _apply_sales_lead_promotion_gate(
        self,
        result: ClassificationResult,
    ) -> ClassificationResult:
        if (
            result.label is not ClassificationLabel.SALES_LEAD
            or result.confidence >= self.sales_lead_confidence_threshold
        ):
            return result

        return ClassificationResult(
            label=ClassificationLabel.UNCERTAIN,
            confidence=result.confidence,
            reason="Sales-lead confidence is below the promotion threshold.",
            model_name=result.model_name,
            model_version=result.model_version,
            prompt_version=result.prompt_version,
        )
