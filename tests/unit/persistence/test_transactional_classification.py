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
from lead_pipeline.domain.catalogue import CatalogueContext
from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.enums import ClassificationLabel, ProcessingStatus, SourceType
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.persistence.models import (
    CatalogueItemRow,
    ClassificationRow,
    InteractionRow,
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
        self.catalogue_contexts: list[CatalogueContext] = []
        self.transaction_states: list[bool] = []

    def classify(
        self,
        interaction: InstagramInteraction,
        *,
        catalogue_context: CatalogueContext,
    ) -> ClassificationResult:
        self.calls.append(interaction)
        self.catalogue_contexts.append(catalogue_context)
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


@pytest.mark.parametrize(
    "initial_status",
    [
        ProcessingStatus.RECEIVED,
        ProcessingStatus.RETRYABLE_FAILURE,
    ],
)
def test_provider_calls_run_between_lifecycle_transactions(
    initial_status: ProcessingStatus,
) -> None:
    session_mock = Mock(spec=Session)
    session_mock.scalars.return_value.all.return_value = []
    processing_row = Mock(spec=InteractionRow)
    processing_row.processing_status = initial_status.value
    session_mock.get.return_value = processing_row
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
    assert transaction_factory.entries == 3
    assert transaction_factory.exits == 3
    assert transaction_factory.exception_types == []
    assert session_mock.add.call_count == 1
    assert processing_row.processing_status == ProcessingStatus.COMPLETED.value
    assert result.outcome.final_result.label is ClassificationLabel.SALES_LEAD
    assert result.receipt.primary_classification_id
    assert primary_provider.catalogue_contexts == [
        CatalogueContext(client_id=ClientId("client-1"))
    ]


def test_double_uncertainty_stages_all_rows_in_one_transaction() -> None:
    session_mock = Mock(spec=Session)
    session_mock.scalars.return_value.all.return_value = []
    processing_row = Mock(spec=InteractionRow)
    processing_row.processing_status = ProcessingStatus.RECEIVED.value
    session_mock.get.return_value = processing_row

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
    assert transaction_factory.entries == 3
    assert transaction_factory.exits == 3
    assert session_mock.add.call_count == 3
    assert processing_row.processing_status == ProcessingStatus.COMPLETED.value

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


def test_provider_failure_marks_interaction_retryable() -> None:
    session_mock = Mock(spec=Session)
    session_mock.scalars.return_value.all.return_value = []
    processing_row = Mock(spec=InteractionRow)
    processing_row.processing_status = ProcessingStatus.RECEIVED.value
    session_mock.get.return_value = processing_row
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

    assert primary_provider.transaction_states == [False]
    assert transaction_factory.entries == 3
    assert transaction_factory.exits == 3
    assert transaction_factory.exception_types == []
    assert processing_row.processing_status == (
        ProcessingStatus.RETRYABLE_FAILURE.value
    )
    session_mock.add.assert_not_called()


def test_persistence_failure_marks_interaction_retryable() -> None:
    session_mock = Mock(spec=Session)
    session_mock.scalars.return_value.all.return_value = []
    processing_row = Mock(spec=InteractionRow)
    processing_row.processing_status = ProcessingStatus.RECEIVED.value
    session_mock.get.return_value = processing_row
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
    assert transaction_factory.entries == 4
    assert transaction_factory.exits == 4
    assert transaction_factory.exception_types == [RuntimeError]
    assert processing_row.processing_status == (
        ProcessingStatus.RETRYABLE_FAILURE.value
    )


def test_retrieved_catalogue_items_reach_provider_outside_transaction() -> None:
    session_mock = Mock(spec=Session)
    processing_row = Mock(spec=InteractionRow)
    processing_row.processing_status = ProcessingStatus.RECEIVED.value
    session_mock.get.return_value = processing_row

    catalogue_row = Mock(spec=CatalogueItemRow)
    catalogue_row.client_id = "client-1"
    catalogue_row.catalogue_item_id = "item-1"
    catalogue_row.name = "Vitamin C Serum"
    catalogue_row.category = "Serums"
    catalogue_row.description = "Brightening serum for dull-looking skin."
    session_mock.scalars.return_value.all.return_value = [catalogue_row]

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

    runner.execute(build_interaction())

    assert primary_provider.transaction_states == [False]
    assert len(primary_provider.catalogue_contexts) == 1

    context = primary_provider.catalogue_contexts[0]
    assert context.client_id == ClientId("client-1")
    assert len(context.items) == 1
    assert context.items[0].catalogue_item_id.value == "item-1"
    assert context.items[0].client_id == ClientId("client-1")
    assert context.items[0].name == "Vitamin C Serum"
    assert context.items[0].category == "Serums"
    assert context.items[0].description == ("Brightening serum for dull-looking skin.")


def test_catalogue_retrieval_failure_marks_interaction_retryable() -> None:
    session_mock = Mock(spec=Session)
    processing_row = Mock(spec=InteractionRow)
    processing_row.processing_status = ProcessingStatus.RECEIVED.value
    session_mock.get.return_value = processing_row
    session_mock.scalars.side_effect = RuntimeError("catalogue unavailable")

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

    with pytest.raises(RuntimeError, match="catalogue unavailable"):
        runner.execute(build_interaction())

    assert primary_provider.calls == []
    assert stronger_provider.calls == []
    assert transaction_factory.entries == 3
    assert transaction_factory.exits == 3
    assert transaction_factory.exception_types == [RuntimeError]
    assert processing_row.processing_status == (
        ProcessingStatus.RETRYABLE_FAILURE.value
    )
    session_mock.add.assert_not_called()
