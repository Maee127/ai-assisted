"""Tests for unresolved classification records."""

from datetime import UTC, datetime

import pytest

from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.enums import ClassificationLabel
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramUserId,
)
from lead_pipeline.domain.unresolved import UnresolvedRecord


def build_result(
    model_name: str,
    confidence: float,
) -> ClassificationResult:
    return ClassificationResult(
        label=ClassificationLabel.UNCERTAIN,
        confidence=confidence,
        reason="The available evidence is insufficient.",
        model_name=model_name,
        model_version="1.0.0",
        prompt_version="prompt-v1",
    )


def build_record(**overrides: object) -> UnresolvedRecord:
    values: dict[str, object] = {
        "client_id": ClientId("client-1"),
        "user_id": InstagramUserId("user-1"),
        "source_event_id": InstagramEventId("event-1"),
        "primary_result": build_result("primary-classifier", 0.45),
        "stronger_result": build_result("stronger-classifier", 0.52),
        "created_at": datetime(2026, 8, 3, 18, 30, tzinfo=UTC),
    }
    values.update(overrides)

    return UnresolvedRecord(**values)  # type: ignore[arg-type]


def test_unresolved_record_preserves_both_results() -> None:
    record = build_record()

    assert record.primary_result.model_name == "primary-classifier"
    assert record.stronger_result.model_name == "stronger-classifier"


def test_naive_created_at_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="created_at must be timezone-aware",
    ):
        build_record(
            created_at=datetime(2026, 8, 3, 18, 30),  # noqa: DTZ001
        )


def test_unresolved_record_is_immutable() -> None:
    record = build_record()

    with pytest.raises(AttributeError):
        record.created_at = datetime.now(UTC)  # type: ignore[misc]
