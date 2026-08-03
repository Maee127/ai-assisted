"""Tests for classification results."""

import pytest

from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.enums import ClassificationLabel


def build_result(**overrides: object) -> ClassificationResult:
    values: dict[str, object] = {
        "label": ClassificationLabel.SALES_LEAD,
        "confidence": 0.91,
        "reason": "  The user asks about product availability.  ",
        "model_name": "  primary-classifier  ",
        "model_version": "  1.0.0  ",
        "prompt_version": "  prompt-v1  ",
    }
    values.update(overrides)

    return ClassificationResult(**values)  # type: ignore[arg-type]


def test_classification_normalizes_text_fields() -> None:
    result = build_result()

    assert result.reason == "The user asks about product availability."
    assert result.model_name == "primary-classifier"
    assert result.model_version == "1.0.0"
    assert result.prompt_version == "prompt-v1"


def test_blank_prompt_version_becomes_none() -> None:
    result = build_result(prompt_version="   ")

    assert result.prompt_version is None


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_outside_range_is_rejected(confidence: float) -> None:
    with pytest.raises(
        ValueError,
        match="confidence must be between 0.0 and 1.0",
    ):
        build_result(confidence=confidence)


@pytest.mark.parametrize(
    ("field_name", "message"),
    [
        ("reason", "reason must not be empty"),
        ("model_name", "model_name must not be empty"),
        ("model_version", "model_version must not be empty"),
    ],
)
def test_required_text_fields_reject_blank_values(
    field_name: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_result(**{field_name: "   "})


@pytest.mark.parametrize("confidence", [0.0, 1.0])
def test_confidence_boundary_values_are_allowed(confidence: float) -> None:
    result = build_result(confidence=confidence)

    assert result.confidence == confidence


def test_classification_result_is_immutable() -> None:
    result = build_result()

    with pytest.raises(AttributeError):
        result.confidence = 0.5  # type: ignore[misc]
