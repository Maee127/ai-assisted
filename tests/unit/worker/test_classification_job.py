"""Tests for loading and classifying one persisted interaction."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from lead_pipeline.domain.enums import ProcessingStatus, SourceType
from lead_pipeline.domain.identifiers import InstagramEventId
from lead_pipeline.persistence.exceptions import InteractionNotFoundError
from lead_pipeline.persistence.models import InteractionRow
from lead_pipeline.persistence.transactional_classification import (
    TransactionalClassificationResult,
    TransactionalInteractionClassifier,
)
from lead_pipeline.worker.classification_job import ClassificationJob


@dataclass
class RecordingTransactionFactory:
    """Record whether the interaction-loading transaction is active."""

    session: Session
    entries: int = 0
    exits: int = 0
    active: bool = False

    @contextmanager
    def begin(self) -> Iterator[Session]:
        self.entries += 1
        self.active = True

        try:
            yield self.session
        finally:
            self.active = False
            self.exits += 1


def build_row() -> InteractionRow:
    return InteractionRow(
        event_id="event-1",
        client_id="client-1",
        user_id="user-1",
        media_id="media-1",
        source_type=SourceType.POST_COMMENT.value,
        text="How much does this cost?",
        source_timestamp=datetime(2026, 8, 24, 9, 0, tzinfo=UTC),
        collected_at=datetime(2026, 8, 24, 9, 1, tzinfo=UTC),
        processing_status=ProcessingStatus.RECEIVED.value,
        username="beauty_user",
    )


def test_job_loads_interaction_before_running_classification() -> None:
    session_mock = Mock(spec=Session)
    session_mock.get.return_value = build_row()
    transaction_factory = RecordingTransactionFactory(
        session=cast(Session, session_mock),
    )
    runner_mock = Mock(spec=TransactionalInteractionClassifier)
    expected_result = Mock(spec=TransactionalClassificationResult)
    transaction_states: list[bool] = []

    def execute_runner(
        interaction: object,
    ) -> TransactionalClassificationResult:
        transaction_states.append(transaction_factory.active)
        return cast(TransactionalClassificationResult, expected_result)

    runner_mock.execute.side_effect = execute_runner
    job = ClassificationJob(
        session_factory=transaction_factory,
        runner=cast(TransactionalInteractionClassifier, runner_mock),
    )

    result = job.execute(
        InstagramEventId("event-1"),
    )

    assert result is expected_result
    assert transaction_factory.entries == 1
    assert transaction_factory.exits == 1
    assert transaction_states == [False]
    session_mock.get.assert_called_once_with(
        InteractionRow,
        "event-1",
    )

    loaded_interaction = runner_mock.execute.call_args.args[0]
    assert loaded_interaction.event_id == InstagramEventId("event-1")
    assert loaded_interaction.status is ProcessingStatus.RECEIVED


def test_missing_interaction_is_rejected_without_running_classifier() -> None:
    session_mock = Mock(spec=Session)
    session_mock.get.return_value = None
    transaction_factory = RecordingTransactionFactory(
        session=cast(Session, session_mock),
    )
    runner_mock = Mock(spec=TransactionalInteractionClassifier)
    job = ClassificationJob(
        session_factory=transaction_factory,
        runner=cast(TransactionalInteractionClassifier, runner_mock),
    )

    with pytest.raises(
        InteractionNotFoundError,
        match="interaction was not found",
    ) as error_info:
        job.execute(
            InstagramEventId("private-event-id"),
        )

    assert transaction_factory.entries == 1
    assert transaction_factory.exits == 1
    assert "private-event-id" not in str(error_info.value)
    runner_mock.execute.assert_not_called()
