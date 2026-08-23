"""Tests for classification and uncertainty orchestration."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from lead_pipeline.application.classify_interaction import (
    ClassifyInteraction,
)
from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.enums import ClassificationLabel, SourceType
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction

CREATED_AT = datetime(2026, 8, 23, 10, 0, tzinfo=UTC)


@dataclass
class RecordingClassificationProvider:
    """Classifier test double recording every interaction."""

    result: ClassificationResult
    calls: list[InstagramInteraction] = field(default_factory=list)

    def classify(
        self,
        interaction: InstagramInteraction,
    ) -> ClassificationResult:
        self.calls.append(interaction)
        return self.result


def build_interaction(
    *,
    text: str = "Is this available?",
) -> InstagramInteraction:
    return InstagramInteraction(
        event_id=InstagramEventId("event-1"),
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        media_id=InstagramMediaId("media-1"),
        source_type=SourceType.POST_COMMENT,
        text=text,
        source_timestamp=datetime(2026, 8, 23, 9, 58, tzinfo=UTC),
        collected_at=datetime(2026, 8, 23, 9, 59, tzinfo=UTC),
        username="beauty_user",
    )


def build_result(
    label: ClassificationLabel,
    *,
    model_name: str,
    confidence: float = 0.9,
) -> ClassificationResult:
    return ClassificationResult(
        label=label,
        confidence=confidence,
        reason=f"The classifier selected {label.value}.",
        model_name=model_name,
        model_version="1.0.0",
        prompt_version="prompt-v1",
    )


def build_use_case(
    primary_result: ClassificationResult,
    stronger_result: ClassificationResult,
) -> tuple[
    ClassifyInteraction,
    RecordingClassificationProvider,
    RecordingClassificationProvider,
]:
    primary_provider = RecordingClassificationProvider(
        result=primary_result,
    )
    stronger_provider = RecordingClassificationProvider(
        result=stronger_result,
    )
    use_case = ClassifyInteraction(
        primary_provider=primary_provider,
        stronger_provider=stronger_provider,
        clock=lambda: CREATED_AT,
    )

    return use_case, primary_provider, stronger_provider


@pytest.mark.parametrize(
    "label",
    [
        ClassificationLabel.SALES_LEAD,
        ClassificationLabel.CUSTOMER_CARE,
        ClassificationLabel.IRRELEVANT,
        ClassificationLabel.SPAM,
    ],
)
def test_resolved_primary_result_is_final(
    label: ClassificationLabel,
) -> None:
    primary_result = build_result(
        label,
        model_name="primary-classifier",
    )
    stronger_result = build_result(
        ClassificationLabel.SALES_LEAD,
        model_name="stronger-classifier",
    )
    use_case, primary_provider, stronger_provider = build_use_case(
        primary_result,
        stronger_result,
    )
    interaction = build_interaction()

    outcome = use_case.execute(interaction)

    assert outcome.primary_result is primary_result
    assert outcome.final_result is primary_result
    assert outcome.stronger_result is None
    assert outcome.was_escalated is False
    assert outcome.is_unresolved is False
    assert primary_provider.calls == [interaction]
    assert stronger_provider.calls == []


def test_every_interaction_enters_primary_classification() -> None:
    primary_result = build_result(
        ClassificationLabel.IRRELEVANT,
        model_name="primary-classifier",
    )
    stronger_result = build_result(
        ClassificationLabel.SALES_LEAD,
        model_name="stronger-classifier",
    )
    use_case, primary_provider, _ = build_use_case(
        primary_result,
        stronger_result,
    )
    interaction = build_interaction(
        text="Beautiful!",
    )

    use_case.execute(interaction)

    assert primary_provider.calls == [interaction]


def test_primary_uncertainty_is_resolved_by_stronger_classifier() -> None:
    primary_result = build_result(
        ClassificationLabel.UNCERTAIN,
        model_name="primary-classifier",
        confidence=0.45,
    )
    stronger_result = build_result(
        ClassificationLabel.CUSTOMER_CARE,
        model_name="stronger-classifier",
        confidence=0.88,
    )
    use_case, primary_provider, stronger_provider = build_use_case(
        primary_result,
        stronger_result,
    )
    interaction = build_interaction()

    outcome = use_case.execute(interaction)

    assert outcome.primary_result is primary_result
    assert outcome.stronger_result is stronger_result
    assert outcome.final_result is stronger_result
    assert outcome.was_escalated is True
    assert outcome.is_unresolved is False
    assert outcome.unresolved_record is None
    assert primary_provider.calls == [interaction]
    assert stronger_provider.calls == [interaction]


def test_double_uncertainty_creates_unresolved_record() -> None:
    primary_result = build_result(
        ClassificationLabel.UNCERTAIN,
        model_name="primary-classifier",
        confidence=0.45,
    )
    stronger_result = build_result(
        ClassificationLabel.UNCERTAIN,
        model_name="stronger-classifier",
        confidence=0.52,
    )
    use_case, _, _ = build_use_case(
        primary_result,
        stronger_result,
    )
    interaction = build_interaction()

    outcome = use_case.execute(interaction)

    assert outcome.final_result is stronger_result
    assert outcome.was_escalated is True
    assert outcome.is_unresolved is True
    assert outcome.unresolved_record is not None
    assert outcome.unresolved_record.client_id == interaction.client_id
    assert outcome.unresolved_record.user_id == interaction.user_id
    assert outcome.unresolved_record.source_event_id == interaction.event_id
    assert outcome.unresolved_record.primary_result is primary_result
    assert outcome.unresolved_record.stronger_result is stronger_result
    assert outcome.unresolved_record.created_at == CREATED_AT
