"""Deterministic metrics for promoted sales-lead evaluation."""

from collections.abc import Iterable
from dataclasses import dataclass

from lead_pipeline.domain.enums import ClassificationLabel


@dataclass(frozen=True, slots=True)
class ClassificationEvaluationExample:
    """One human-labeled prediction used for offline evaluation."""

    example_id: str
    expected_label: ClassificationLabel
    predicted_label: ClassificationLabel

    def __post_init__(self) -> None:
        normalized_example_id = self.example_id.strip()

        if not normalized_example_id:
            raise ValueError("example_id must not be empty")

        object.__setattr__(self, "example_id", normalized_example_id)


@dataclass(frozen=True, slots=True)
class SalesLeadEvaluation:
    """Binary evaluation of the SALES_LEAD promotion decision."""

    dataset_size: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    target_precision: float

    def __post_init__(self) -> None:
        counts = (
            self.true_positives,
            self.false_positives,
            self.false_negatives,
            self.true_negatives,
        )

        if self.dataset_size <= 0:
            raise ValueError("dataset_size must be positive")

        if any(count < 0 for count in counts):
            raise ValueError("evaluation counts must not be negative")

        if sum(counts) != self.dataset_size:
            raise ValueError("evaluation counts must equal dataset_size")

        if not 0.0 <= self.target_precision <= 1.0:
            raise ValueError("target_precision must be between 0.0 and 1.0")

    @property
    def promoted_sales_leads(self) -> int:
        """Return the number of predictions promoted as sales leads."""

        return self.true_positives + self.false_positives

    @property
    def actual_sales_leads(self) -> int:
        """Return the number of human-labeled sales leads."""

        return self.true_positives + self.false_negatives

    @property
    def precision(self) -> float | None:
        """Return promoted-lead precision, or None when nothing was promoted."""

        if self.promoted_sales_leads == 0:
            return None

        return self.true_positives / self.promoted_sales_leads

    @property
    def recall(self) -> float | None:
        """Return sales-lead recall, or None when the dataset has no sales leads."""

        if self.actual_sales_leads == 0:
            return None

        return self.true_positives / self.actual_sales_leads

    @property
    def target_met(self) -> bool:
        """Return whether measurable precision reaches the configured target."""

        return self.precision is not None and self.precision >= self.target_precision


def evaluate_sales_lead_promotions(
    examples: Iterable[ClassificationEvaluationExample],
    *,
    target_precision: float = 0.9,
) -> SalesLeadEvaluation:
    """Evaluate SALES_LEAD as a binary promotion decision."""

    if not 0.0 <= target_precision <= 1.0:
        raise ValueError("target_precision must be between 0.0 and 1.0")

    evaluated_examples = tuple(examples)

    if not evaluated_examples:
        raise ValueError("evaluation dataset must not be empty")

    example_ids = [example.example_id for example in evaluated_examples]

    if len(example_ids) != len(set(example_ids)):
        raise ValueError("evaluation example IDs must be unique")

    true_positives = 0
    false_positives = 0
    false_negatives = 0
    true_negatives = 0

    for example in evaluated_examples:
        expected_sales_lead = example.expected_label is ClassificationLabel.SALES_LEAD
        predicted_sales_lead = example.predicted_label is ClassificationLabel.SALES_LEAD

        if expected_sales_lead and predicted_sales_lead:
            true_positives += 1
        elif not expected_sales_lead and predicted_sales_lead:
            false_positives += 1
        elif expected_sales_lead:
            false_negatives += 1
        else:
            true_negatives += 1

    return SalesLeadEvaluation(
        dataset_size=len(evaluated_examples),
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        true_negatives=true_negatives,
        target_precision=target_precision,
    )
