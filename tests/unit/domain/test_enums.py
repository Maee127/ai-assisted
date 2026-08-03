"""Tests for domain enumerations."""

from lead_pipeline.domain.enums import (
    ClassificationLabel,
    InterestType,
    ProcessingStatus,
    SourceType,
)


def test_source_type_values() -> None:
    assert {item.value for item in SourceType} == {
        "POST_COMMENT",
        "REEL_COMMENT",
        "MENTION",
    }


def test_classification_label_values() -> None:
    assert {item.value for item in ClassificationLabel} == {
        "SALES_LEAD",
        "CUSTOMER_CARE",
        "IRRELEVANT",
        "SPAM",
        "UNCERTAIN",
    }


def test_interest_type_values() -> None:
    assert {item.value for item in InterestType} == {
        "EXPLICIT",
        "INFERRED",
    }


def test_processing_status_values() -> None:
    assert {item.value for item in ProcessingStatus} == {
        "RECEIVED",
        "QUEUED",
        "PROCESSING",
        "COMPLETED",
        "RETRYABLE_FAILURE",
        "PERMANENT_FAILURE",
    }
