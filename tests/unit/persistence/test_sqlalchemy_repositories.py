"""Tests for concrete SQLAlchemy persistence adapters."""

from datetime import UTC, datetime
from typing import cast
from unittest.mock import Mock

from sqlalchemy.orm import Session

from lead_pipeline.domain.enums import ProcessingStatus, SourceType
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.persistence.models import InteractionRow
from lead_pipeline.persistence.sqlalchemy_repositories import (
    SqlAlchemyInteractionRepository,
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
