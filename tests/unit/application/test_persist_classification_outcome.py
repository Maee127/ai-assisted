"""Tests for classification-outcome persistence orchestration."""

from datetime import UTC, datetime

from lead_pipeline.application.classify_interaction import (
    ClassificationOutcome,
)
from lead_pipeline.application.persist_classification_outcome import (
    PersistClassificationOutcome,
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
from lead_pipeline.domain.unresolved import UnresolvedRecord

PERSISTED_AT = datetime(2026, 8, 23, 10, 0, tzinfo=UTC)
UNRESOLVED_AT = datetime(2026, 8, 23, 10, 1, tzinfo=UTC)


class RecordingClassificationRepository:
    """Record classification writes and return prepared identifiers."""

    def __init__(self, identifiers: list[str]) -> None:
        self.identifiers = identifiers
        self.writes: list[
            tuple[
                InstagramEventId,
                ClientId,
                ClassificationResult,
                datetime,
            ]
        ] = []

    def add(
        self,
        *,
        source_event_id: InstagramEventId,
        client_id: ClientId,
        result: ClassificationResult,
        created_at: datetime,
    ) -> str:
        self.writes.append(
            (
                source_event_id,
                client_id,
                result,
                created_at,
            )
        )
        return self.identifiers[len(self.writes) - 1]


class RecordingUnresolvedRepository:
    """Record unresolved writes and return a prepared identifier."""

    def __init__(self) -> None:
        self.writes: list[tuple[UnresolvedRecord, str, str]] = []

    def add(
        self,
        *,
        record: UnresolvedRecord,
        primary_classification_id: str,
        stronger_classification_id: str,
    ) -> str:
        self.writes.append(
            (
                record,
                primary_classification_id,
                stronger_classification_id,
            )
        )
        return "unresolved-id"


def build_interaction() -> InstagramInteraction:
    return InstagramInteraction(
        event_id=InstagramEventId("event-1"),
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        media_id=InstagramMediaId("media-1"),
        source_type=SourceType.POST_COMMENT,
        text="Is this product available?",
        source_timestamp=datetime(2026, 8, 23, 9, 58, tzinfo=UTC),
        collected_at=datetime(2026, 8, 23, 9, 59, tzinfo=UTC),
    )


def build_result(
    *,
    label: ClassificationLabel,
    model_version: str,
) -> ClassificationResult:
    return ClassificationResult(
        label=label,
        confidence=0.8,
        reason="Classification evidence.",
        model_name="anthropic",
        model_version=model_version,
        prompt_version="classification-v1",
    )


def test_primary_only_outcome_persists_one_classification() -> None:
    primary_result = build_result(
        label=ClassificationLabel.SALES_LEAD,
        model_version="claude-haiku-4-5-20251001",
    )
    classification_repository = RecordingClassificationRepository(["primary-id"])
    unresolved_repository = RecordingUnresolvedRepository()
    use_case = PersistClassificationOutcome(
        classification_repository=classification_repository,
        unresolved_repository=unresolved_repository,
        clock=lambda: PERSISTED_AT,
    )

    receipt = use_case.execute(
        interaction=build_interaction(),
        outcome=ClassificationOutcome(
            primary_result=primary_result,
            final_result=primary_result,
        ),
    )

    assert receipt.primary_classification_id == "primary-id"
    assert receipt.stronger_classification_id is None
    assert receipt.unresolved_id is None
    assert classification_repository.writes == [
        (
            InstagramEventId("event-1"),
            ClientId("client-1"),
            primary_result,
            PERSISTED_AT,
        )
    ]
    assert unresolved_repository.writes == []


def test_resolved_escalation_persists_both_classifications() -> None:
    primary_result = build_result(
        label=ClassificationLabel.UNCERTAIN,
        model_version="claude-haiku-4-5-20251001",
    )
    stronger_result = build_result(
        label=ClassificationLabel.CUSTOMER_CARE,
        model_version="claude-sonnet-5",
    )
    classification_repository = RecordingClassificationRepository(
        [
            "primary-id",
            "stronger-id",
        ]
    )
    unresolved_repository = RecordingUnresolvedRepository()
    use_case = PersistClassificationOutcome(
        classification_repository=classification_repository,
        unresolved_repository=unresolved_repository,
        clock=lambda: PERSISTED_AT,
    )

    receipt = use_case.execute(
        interaction=build_interaction(),
        outcome=ClassificationOutcome(
            primary_result=primary_result,
            stronger_result=stronger_result,
            final_result=stronger_result,
        ),
    )

    assert receipt.primary_classification_id == "primary-id"
    assert receipt.stronger_classification_id == "stronger-id"
    assert receipt.unresolved_id is None
    assert [write[2] for write in classification_repository.writes] == [
        primary_result,
        stronger_result,
    ]
    assert {write[3] for write in classification_repository.writes} == {PERSISTED_AT}
    assert unresolved_repository.writes == []


def test_double_uncertainty_persists_linked_unresolved_record() -> None:
    interaction = build_interaction()
    primary_result = build_result(
        label=ClassificationLabel.UNCERTAIN,
        model_version="claude-haiku-4-5-20251001",
    )
    stronger_result = build_result(
        label=ClassificationLabel.UNCERTAIN,
        model_version="claude-sonnet-5",
    )
    unresolved_record = UnresolvedRecord(
        client_id=interaction.client_id,
        user_id=interaction.user_id,
        source_event_id=interaction.event_id,
        primary_result=primary_result,
        stronger_result=stronger_result,
        created_at=UNRESOLVED_AT,
    )
    classification_repository = RecordingClassificationRepository(
        [
            "primary-id",
            "stronger-id",
        ]
    )
    unresolved_repository = RecordingUnresolvedRepository()
    use_case = PersistClassificationOutcome(
        classification_repository=classification_repository,
        unresolved_repository=unresolved_repository,
        clock=lambda: PERSISTED_AT,
    )

    receipt = use_case.execute(
        interaction=interaction,
        outcome=ClassificationOutcome(
            primary_result=primary_result,
            stronger_result=stronger_result,
            final_result=stronger_result,
            unresolved_record=unresolved_record,
        ),
    )

    assert receipt.primary_classification_id == "primary-id"
    assert receipt.stronger_classification_id == "stronger-id"
    assert receipt.unresolved_id == "unresolved-id"
    assert {write[3] for write in classification_repository.writes} == {UNRESOLVED_AT}
    assert unresolved_repository.writes == [
        (
            unresolved_record,
            "primary-id",
            "stronger-id",
        )
    ]
