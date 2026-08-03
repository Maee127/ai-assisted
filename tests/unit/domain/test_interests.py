"""Tests for beauty-related interest evidence."""

import pytest

from lead_pipeline.domain.enums import InterestType
from lead_pipeline.domain.identifiers import InstagramEventId
from lead_pipeline.domain.interests import InterestEvidence


def build_interest(**overrides: object) -> InterestEvidence:
    values: dict[str, object] = {
        "name": "  Vitamin C serum  ",
        "interest_type": InterestType.EXPLICIT,
        "confidence": 0.92,
        "source_event_id": InstagramEventId("event-1"),
        "model_name": "  interest-extractor  ",
        "model_version": "  1.0.0  ",
        "catalogue_evidence": "  Product SKU VC-10  ",
        "prompt_version": "  prompt-v1  ",
    }
    values.update(overrides)

    return InterestEvidence(**values)  # type: ignore[arg-type]


def test_interest_normalizes_text_fields() -> None:
    interest = build_interest()

    assert interest.name == "Vitamin C serum"
    assert interest.model_name == "interest-extractor"
    assert interest.model_version == "1.0.0"
    assert interest.catalogue_evidence == "Product SKU VC-10"
    assert interest.prompt_version == "prompt-v1"


@pytest.mark.parametrize(
    "field_name",
    ["catalogue_evidence", "prompt_version"],
)
def test_blank_optional_field_becomes_none(field_name: str) -> None:
    interest = build_interest(**{field_name: "   "})

    assert getattr(interest, field_name) is None


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_outside_range_is_rejected(confidence: float) -> None:
    with pytest.raises(
        ValueError,
        match="confidence must be between 0.0 and 1.0",
    ):
        build_interest(confidence=confidence)


@pytest.mark.parametrize(
    ("field_name", "message"),
    [
        ("name", "name must not be empty"),
        ("model_name", "model_name must not be empty"),
        ("model_version", "model_version must not be empty"),
    ],
)
def test_required_fields_reject_blank_values(
    field_name: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_interest(**{field_name: "   "})


@pytest.mark.parametrize("confidence", [0.0, 1.0])
def test_confidence_boundaries_are_allowed(confidence: float) -> None:
    interest = build_interest(confidence=confidence)

    assert interest.confidence == confidence


def test_interest_is_immutable() -> None:
    interest = build_interest()

    with pytest.raises(AttributeError):
        interest.name = "changed"  # type: ignore[misc]
