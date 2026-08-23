"""Tests for concrete SQLAlchemy persistence adapters."""

from datetime import UTC, datetime
from typing import cast
from unittest.mock import Mock
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.enums import (
    ClassificationLabel,
    ProcessingStatus,
    SourceType,
)
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.domain.unresolved import UnresolvedRecord
from lead_pipeline.persistence.models import (
    ClassificationRow,
    InteractionRow,
    UnresolvedRecordRow,
)
from lead_pipeline.persistence.sqlalchemy_repositories import (
    SqlAlchemyClassificationRepository,
    SqlAlchemyInteractionRepository,
    SqlAlchemyUnresolvedRecordRepository,
)


def build_interaction(
    *,
    event_id: str = "event-1",
) -> InstagramInteraction:
    return InstagramInteraction(
        event_id=InstagramEventId(event_id),
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        media_id=InstagramMediaId("media-1"),
        source_type=SourceType.POST_COMMENT,
        text="Is this available?",
        source_timestamp=datetime(2026, 8, 20, 10, 0, tzinfo=UTC),
        collected_at=datetime(2026, 8, 20, 10, 1, tzinfo=UTC),
        status=ProcessingStatus.RECEIVED,
        username="beauty_user",
    )


def build_row() -> InteractionRow:
    return InteractionRow(
        event_id="event-1",
        client_id="client-1",
        user_id="user-1",
        media_id="media-1",
        source_type=SourceType.POST_COMMENT.value,
        text="Is this available?",
        source_timestamp=datetime(2026, 8, 20, 10, 0, tzinfo=UTC),
        collected_at=datetime(2026, 8, 20, 10, 1, tzinfo=UTC),
        processing_status=ProcessingStatus.RECEIVED.value,
        username="beauty_user",
    )


def test_add_maps_domain_interaction_to_persistence_row() -> None:
    session = Mock(spec=Session)
    session.get.return_value = None
    repository = SqlAlchemyInteractionRepository(session=session)

    repository.add(build_interaction())

    session.get.assert_called_once_with(
        InteractionRow,
        "event-1",
    )
    session.add.assert_called_once()

    row = cast(
        InteractionRow,
        session.add.call_args.args[0],
    )

    assert row.event_id == "event-1"
    assert row.client_id == "client-1"
    assert row.user_id == "user-1"
    assert row.media_id == "media-1"
    assert row.source_type == SourceType.POST_COMMENT.value
    assert row.text == "Is this available?"
    assert row.processing_status == ProcessingStatus.RECEIVED.value
    assert row.username == "beauty_user"


def test_add_ignores_existing_event_id() -> None:
    session = Mock(spec=Session)
    session.get.return_value = build_row()
    repository = SqlAlchemyInteractionRepository(session=session)

    repository.add(build_interaction())

    session.add.assert_not_called()


def test_add_does_not_own_transaction_commit() -> None:
    session = Mock(spec=Session)
    session.get.return_value = None
    repository = SqlAlchemyInteractionRepository(session=session)

    repository.add(build_interaction())

    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_get_by_event_id_maps_row_to_domain_interaction() -> None:
    session = Mock(spec=Session)
    session.get.return_value = build_row()
    repository = SqlAlchemyInteractionRepository(session=session)

    interaction = repository.get_by_event_id(
        InstagramEventId("event-1"),
    )

    assert interaction == build_interaction()


def test_get_by_event_id_returns_none_when_missing() -> None:
    session = Mock(spec=Session)
    session.get.return_value = None
    repository = SqlAlchemyInteractionRepository(session=session)

    interaction = repository.get_by_event_id(
        InstagramEventId("missing-event"),
    )

    assert interaction is None


CLASSIFICATION_ID = UUID("00000000-0000-0000-0000-000000000001")
UNRESOLVED_ID = UUID("00000000-0000-0000-0000-000000000002")
CREATED_AT = datetime(2026, 8, 23, 9, 0, tzinfo=UTC)


def build_classification_result(
    *,
    model_name: str = "anthropic",
    model_version: str = "claude-haiku-4-5-20251001",
) -> ClassificationResult:
    return ClassificationResult(
        label=ClassificationLabel.UNCERTAIN,
        confidence=0.51,
        reason="The comment is genuinely ambiguous.",
        model_name=model_name,
        model_version=model_version,
        prompt_version="classification-v1",
    )


def build_unresolved_record() -> UnresolvedRecord:
    return UnresolvedRecord(
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        source_event_id=InstagramEventId("event-1"),
        primary_result=build_classification_result(),
        stronger_result=build_classification_result(
            model_version="claude-sonnet-5",
        ),
        created_at=CREATED_AT,
    )


def test_classification_add_maps_result_and_returns_identifier() -> None:
    session = Mock(spec=Session)
    repository = SqlAlchemyClassificationRepository(
        session=session,
        id_factory=lambda: CLASSIFICATION_ID,
    )
    result = build_classification_result()

    classification_id = repository.add(
        source_event_id=InstagramEventId("event-1"),
        client_id=ClientId("client-1"),
        result=result,
        created_at=CREATED_AT,
    )

    assert classification_id == str(CLASSIFICATION_ID)
    session.add.assert_called_once()

    row = cast(
        ClassificationRow,
        session.add.call_args.args[0],
    )

    assert row.classification_id == str(CLASSIFICATION_ID)
    assert row.source_event_id == "event-1"
    assert row.client_id == "client-1"
    assert row.label == ClassificationLabel.UNCERTAIN.value
    assert row.confidence == 0.51
    assert row.reason == "The comment is genuinely ambiguous."
    assert row.model_name == "anthropic"
    assert row.model_version == "claude-haiku-4-5-20251001"
    assert row.prompt_version == "classification-v1"
    assert row.created_at == CREATED_AT
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_classification_add_rejects_naive_created_at() -> None:
    session = Mock(spec=Session)
    repository = SqlAlchemyClassificationRepository(session=session)

    with pytest.raises(
        ValueError,
        match="created_at must be timezone-aware",
    ):
        repository.add(
            source_event_id=InstagramEventId("event-1"),
            client_id=ClientId("client-1"),
            result=build_classification_result(),
            created_at=datetime(2026, 8, 23, 9, 0),  # noqa: DTZ001
        )

    session.add.assert_not_called()


def test_unresolved_add_maps_record_and_returns_identifier() -> None:
    session = Mock(spec=Session)
    repository = SqlAlchemyUnresolvedRecordRepository(
        session=session,
        id_factory=lambda: UNRESOLVED_ID,
    )

    unresolved_id = repository.add(
        record=build_unresolved_record(),
        primary_classification_id="primary-classification",
        stronger_classification_id="stronger-classification",
    )

    assert unresolved_id == str(UNRESOLVED_ID)
    session.add.assert_called_once()

    row = cast(
        UnresolvedRecordRow,
        session.add.call_args.args[0],
    )

    assert row.unresolved_id == str(UNRESOLVED_ID)
    assert row.client_id == "client-1"
    assert row.user_id == "user-1"
    assert row.source_event_id == "event-1"
    assert row.primary_classification_id == "primary-classification"
    assert row.stronger_classification_id == "stronger-classification"
    assert row.created_at == CREATED_AT
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


@pytest.mark.parametrize(
    ("primary_id", "stronger_id", "message"),
    [
        (
            " ",
            "stronger-classification",
            "primary_classification_id must not be empty",
        ),
        (
            "primary-classification",
            " ",
            "stronger_classification_id must not be empty",
        ),
    ],
)
def test_unresolved_add_rejects_blank_classification_identifiers(
    primary_id: str,
    stronger_id: str,
    message: str,
) -> None:
    session = Mock(spec=Session)
    repository = SqlAlchemyUnresolvedRecordRepository(session=session)

    with pytest.raises(ValueError, match=message):
        repository.add(
            record=build_unresolved_record(),
            primary_classification_id=primary_id,
            stronger_classification_id=stronger_id,
        )

    session.add.assert_not_called()
