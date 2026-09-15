"""Tests for promoted sales-lead evaluation metrics."""

import pytest

from lead_pipeline.domain.enums import ClassificationLabel
from lead_pipeline.evaluation.classification import (
    ClassificationEvaluationExample,
    evaluate_sales_lead_promotions,
)


def example(
    example_id: str,
    expected: ClassificationLabel,
    predicted: ClassificationLabel,
) -> ClassificationEvaluationExample:
    return ClassificationEvaluationExample(
        example_id=example_id,
        expected_label=expected,
        predicted_label=predicted,
    )


def test_evaluation_calculates_binary_sales_lead_counts() -> None:
    evaluation = evaluate_sales_lead_promotions(
        [
            example(
                "true-positive",
                ClassificationLabel.SALES_LEAD,
                ClassificationLabel.SALES_LEAD,
            ),
            example(
                "false-positive",
                ClassificationLabel.CUSTOMER_CARE,
                ClassificationLabel.SALES_LEAD,
            ),
            example(
                "false-negative",
                ClassificationLabel.SALES_LEAD,
                ClassificationLabel.UNCERTAIN,
            ),
            example(
                "true-negative",
                ClassificationLabel.SPAM,
                ClassificationLabel.IRRELEVANT,
            ),
        ]
    )

    assert evaluation.dataset_size == 4
    assert evaluation.true_positives == 1
    assert evaluation.false_positives == 1
    assert evaluation.false_negatives == 1
    assert evaluation.true_negatives == 1
    assert evaluation.promoted_sales_leads == 2
    assert evaluation.actual_sales_leads == 2
    assert evaluation.precision == 0.5
    assert evaluation.recall == 0.5
    assert evaluation.target_met is False


def test_exactly_ninety_percent_precision_meets_target() -> None:
    examples = [
        example(
            f"true-positive-{index}",
            ClassificationLabel.SALES_LEAD,
            ClassificationLabel.SALES_LEAD,
        )
        for index in range(9)
    ]
    examples.append(
        example(
            "false-positive",
            ClassificationLabel.IRRELEVANT,
            ClassificationLabel.SALES_LEAD,
        )
    )

    evaluation = evaluate_sales_lead_promotions(examples)

    assert evaluation.precision == pytest.approx(0.9)
    assert evaluation.target_met is True


def test_precision_below_target_fails() -> None:
    evaluation = evaluate_sales_lead_promotions(
        [
            example(
                "true-positive",
                ClassificationLabel.SALES_LEAD,
                ClassificationLabel.SALES_LEAD,
            ),
            example(
                "false-positive",
                ClassificationLabel.SPAM,
                ClassificationLabel.SALES_LEAD,
            ),
        ],
        target_precision=0.6,
    )

    assert evaluation.precision == 0.5
    assert evaluation.target_met is False


def test_no_promotions_produces_no_precision_claim() -> None:
    evaluation = evaluate_sales_lead_promotions(
        [
            example(
                "non-lead",
                ClassificationLabel.IRRELEVANT,
                ClassificationLabel.IRRELEVANT,
            )
        ]
    )

    assert evaluation.promoted_sales_leads == 0
    assert evaluation.precision is None
    assert evaluation.target_met is False


def test_dataset_without_actual_sales_leads_has_no_recall() -> None:
    evaluation = evaluate_sales_lead_promotions(
        [
            example(
                "non-lead",
                ClassificationLabel.CUSTOMER_CARE,
                ClassificationLabel.IRRELEVANT,
            )
        ]
    )

    assert evaluation.actual_sales_leads == 0
    assert evaluation.recall is None


def test_non_sales_misclassification_is_a_binary_true_negative() -> None:
    evaluation = evaluate_sales_lead_promotions(
        [
            example(
                "non-sales-error",
                ClassificationLabel.CUSTOMER_CARE,
                ClassificationLabel.SPAM,
            )
        ]
    )

    assert evaluation.true_negatives == 1


def test_example_id_is_normalized() -> None:
    evaluation_example = example(
        "  example-1  ",
        ClassificationLabel.SALES_LEAD,
        ClassificationLabel.SALES_LEAD,
    )

    assert evaluation_example.example_id == "example-1"


def test_blank_example_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="example_id must not be empty"):
        example(
            "   ",
            ClassificationLabel.SALES_LEAD,
            ClassificationLabel.SALES_LEAD,
        )


def test_duplicate_example_ids_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="evaluation example IDs must be unique",
    ):
        evaluate_sales_lead_promotions(
            [
                example(
                    "duplicate",
                    ClassificationLabel.SALES_LEAD,
                    ClassificationLabel.SALES_LEAD,
                ),
                example(
                    "duplicate",
                    ClassificationLabel.IRRELEVANT,
                    ClassificationLabel.IRRELEVANT,
                ),
            ]
        )


def test_empty_dataset_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="evaluation dataset must not be empty",
    ):
        evaluate_sales_lead_promotions([])


@pytest.mark.parametrize("target_precision", [-0.01, 1.01])
def test_invalid_precision_target_is_rejected(
    target_precision: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="target_precision must be between 0.0 and 1.0",
    ):
        evaluate_sales_lead_promotions(
            [
                example(
                    "example-1",
                    ClassificationLabel.SALES_LEAD,
                    ClassificationLabel.SALES_LEAD,
                )
            ],
            target_precision=target_precision,
        )
