"""Tests for transactional classification persistence."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from lead_pipeline.application.classify_interaction import ClassifyInteraction
from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.enums import ClassificationLabel, SourceType
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.persistence.models import (
    ClassificationRow,
    UnresolvedRecordRow,
)
from lead_pipeline.persistence.transactional_classification import (
    TransactionalInteractionClassifier,
)

CLASSIFIED_AT = datetime(2026, 8, 23, 11, 0, tzinfo=UTC)


@dataclass
class RecordingTransactionFactory:
    """Record transaction timing and propagated failures."""

    session: Session
    entries: int = 0
    exits: int = 0
    active: bool = False
    exception_types: list[type[BaseException]] = field(default_factory=list)

    @contextmanager
    def begin(self) -> Iterator[Session]:
        self.entries += 1
        self.active = True

        try:
            yield self.session
        except BaseException as error:
            self.exception_types.append(type(error))
            raise
        finally:
            self.active = False
            self.exits += 1


class RecordingProvider:
    """Return a configured result and record transaction state."""

    def __init__(
        self,
        *,
        result: ClassificationResult | None,
        transaction_factory: RecordingTransactionFactory,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.transaction_factory = transaction_factory
        self.error = error
        self.calls: list[InstagramInteraction] = []
        self.transaction_states: list[bool] = []

    def classify(
        self,
        interaction: InstagramInteraction,
    ) -> ClassificationResult:
        self.calls.append(interaction)
        self.transaction_states.append(self.transaction_factory.active)

        if self.error is not None:
            raise self.error

        if self.result is None:
            raise AssertionError("test provider has no result")

        return self.result


def build_interaction() -> InstagramInteraction:
    return InstagramInteraction(
        event_id=InstagramEventId("event-1"),
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        media_id=InstagramMediaId("media-1"),
        source_type=SourceType.POST_COMMENT,
        text="How much does this cost?",
        source_timestamp=datetime(2026, 8, 23, 10, 58, tzinfo=UTC),
        collected_at=datetime(2026, 8, 23, 10, 59, tzinfo=UTC),
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


def build_runner(
    *,
    transaction_factory: RecordingTransactionFactory,
    primary_provider: RecordingProvider,
    stronger_provider: RecordingProvider,
) -> TransactionalInteractionClassifier:
    classifier = ClassifyInteraction(
        primary_provider=primary_provider,
        stronger_provider=stronger_provider,
        clock=lambda: CLASSIFIED_AT,
    )
    return TransactionalInteractionClassifier(
        session_factory=transaction_factory,
        classifier=classifier,
        clock=lambda: CLASSIFIED_AT,
    )


def test_provider_call_finishes_before_transaction_begins() -> None:
    session_mock = Mock(spec=Session)
    transaction_factory = RecordingTransactionFactory(
        session=cast(Session, session_mock),
    )
    primary_provider = RecordingProvider(
        result=build_result(
            label=ClassificationLabel.SALES_LEAD,
            model_version="claude-haiku-4-5-20251001",
        ),
        transaction_factory=transaction_factory,
    )
    stronger_provider = RecordingProvider(
        result=None,
        transaction_factory=transaction_factory,
    )
    runner = build_runner(
        transaction_factory=transaction_factory,
        primary_provider=primary_provider,
        stronger_provider=stronger_provider,
    )

    result = runner.execute(build_interaction())

    assert primary_provider.transaction_states == [False]
    assert stronger_provider.calls == []
    assert transaction_factory.entries == 1
    assert transaction_factory.exits == 1
    assert transaction_factory.exception_types == []
    assert session_mock.add.call_count == 1
    assert result.outcome.final_result.label is ClassificationLabel.SALES_LEAD
    assert result.receipt.primary_classification_id


def test_double_uncertainty_stages_all_rows_in_one_transaction() -> None:
    session_mock = Mock(spec=Session)
    transaction_factory = RecordingTransactionFactory(
        session=cast(Session, session_mock),
    )
    primary_provider = RecordingProvider(
        result=build_result(
            label=ClassificationLabel.UNCERTAIN,
            model_version="claude-haiku-4-5-20251001",
        ),
        transaction_factory=transaction_factory,
    )
    stronger_provider = RecordingProvider(
        result=build_result(
            label=ClassificationLabel.UNCERTAIN,
            model_version="claude-sonnet-5",
        ),
        transaction_factory=transaction_factory,
    )
    runner = build_runner(
        transaction_factory=transaction_factory,
        primary_provider=primary_provider,
        stronger_provider=stronger_provider,
    )

    result = runner.execute(build_interaction())

    assert primary_provider.transaction_states == [False]
    assert stronger_provider.transaction_states == [False]
    assert transaction_factory.entries == 1
    assert transaction_factory.exits == 1
    assert session_mock.add.call_count == 3

    primary_row = cast(
        ClassificationRow,
        session_mock.add.call_args_list[0].args[0],
    )
    stronger_row = cast(
        ClassificationRow,
        session_mock.add.call_args_list[1].args[0],
    )
    unresolved_row = cast(
        UnresolvedRecordRow,
        session_mock.add.call_args_list[2].args[0],
    )

    assert unresolved_row.primary_classification_id == (primary_row.classification_id)
    assert unresolved_row.stronger_classification_id == (stronger_row.classification_id)
    assert result.receipt.unresolved_id == unresolved_row.unresolved_id


def test_provider_failure_does_not_open_transaction() -> None:
    session_mock = Mock(spec=Session)
    transaction_factory = RecordingTransactionFactory(
        session=cast(Session, session_mock),
    )
    primary_provider = RecordingProvider(
        result=None,
        error=RuntimeError("provider unavailable"),
        transaction_factory=transaction_factory,
    )
    stronger_provider = RecordingProvider(
        result=None,
        transaction_factory=transaction_factory,
    )
    runner = build_runner(
        transaction_factory=transaction_factory,
        primary_provider=primary_provider,
        stronger_provider=stronger_provider,
    )

    with pytest.raises(RuntimeError, match="provider unavailable"):
        runner.execute(build_interaction())

    assert transaction_factory.entries == 0
    assert transaction_factory.exits == 0
    session_mock.add.assert_not_called()


def test_persistence_failure_exits_transaction_with_error() -> None:
    session_mock = Mock(spec=Session)
    session_mock.add.side_effect = RuntimeError("database unavailable")
    transaction_factory = RecordingTransactionFactory(
        session=cast(Session, session_mock),
    )
    primary_provider = RecordingProvider(
        result=build_result(
            label=ClassificationLabel.SALES_LEAD,
            model_version="claude-haiku-4-5-20251001",
        ),
        transaction_factory=transaction_factory,
    )
    stronger_provider = RecordingProvider(
        result=None,
        transaction_factory=transaction_factory,
    )
    runner = build_runner(
        transaction_factory=transaction_factory,
        primary_provider=primary_provider,
        stronger_provider=stronger_provider,
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        runner.execute(build_interaction())

    assert primary_provider.transaction_states == [False]
    assert transaction_factory.entries == 1
    assert transaction_factory.exits == 1
    assert transaction_factory.exception_types == [RuntimeError]
