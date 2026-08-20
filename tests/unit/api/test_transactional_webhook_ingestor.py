"""Tests for transactional Meta webhook ingestion."""

import hashlib
import hmac
import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from lead_pipeline.api.transactional_webhook_ingestor import (
    TransactionalMetaWebhookIngestor,
)
from lead_pipeline.domain.identifiers import ClientId
from lead_pipeline.persistence.models import InteractionRow

COLLECTED_AT = datetime(2026, 8, 20, 10, 1, tzinfo=UTC)
ENTRY_TIME = int(datetime(2026, 8, 20, 10, 0, tzinfo=UTC).timestamp())


@dataclass
class RecordingTransactionFactory:
    """Record transaction entry, exit, and propagated failures."""

    session: Session
    entries: int = 0
    exits: int = 0
    exception_types: list[type[BaseException]] = field(default_factory=list)

    @contextmanager
    def begin(self) -> Iterator[Session]:
        self.entries += 1

        try:
            yield self.session
        except BaseException as error:
            self.exception_types.append(type(error))
            raise
        finally:
            self.exits += 1


def build_payload(
    *event_ids: str,
) -> bytes:
    entries = [
        {
            "id": "business-1",
            "time": ENTRY_TIME,
            "field": "comments",
            "value": {
                "id": event_id,
                "from": {
                    "id": "user-1",
                    "username": "beauty_user",
                },
                "text": "Is this available?",
                "media": {
                    "id": "media-1",
                    "media_product_type": "FEED",
                },
            },
        }
        for event_id in event_ids
    ]

    return json.dumps(
        {
            "object": "instagram",
            "entry": entries,
        },
        separators=(",", ":"),
    ).encode()


def build_signature(
    raw_body: bytes,
) -> str:
    digest = hmac.new(
        b"app-secret",
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return f"sha256={digest}"


def build_ingestor(
    transaction_factory: RecordingTransactionFactory,
) -> TransactionalMetaWebhookIngestor:
    return TransactionalMetaWebhookIngestor(
        session_factory=transaction_factory,
        app_secret="app-secret",
        client_id=ClientId("client-1"),
        authorized_business_account_id="business-1",
        max_payload_bytes=4096,
        clock=lambda: COLLECTED_AT,
    )


def test_delivery_is_persisted_inside_one_transaction() -> None:
    session_mock = Mock(spec=Session)
    session_mock.get.return_value = None
    session = cast(Session, session_mock)
    transaction_factory = RecordingTransactionFactory(
        session=session,
    )
    ingestor = build_ingestor(transaction_factory)
    raw_body = build_payload("comment-1", "comment-2")

    count = ingestor.ingest(
        raw_body=raw_body,
        signature=build_signature(raw_body),
    )

    assert count == 2
    assert transaction_factory.entries == 1
    assert transaction_factory.exits == 1
    assert transaction_factory.exception_types == []
    assert session_mock.add.call_count == 2

    rows = [
        cast(InteractionRow, call.args[0]) for call in session_mock.add.call_args_list
    ]
    assert [row.event_id for row in rows] == [
        "comment-1",
        "comment-2",
    ]


def test_persistence_failure_leaves_transaction_with_error() -> None:
    session_mock = Mock(spec=Session)
    session_mock.get.return_value = None
    session_mock.add.side_effect = [
        None,
        RuntimeError("database unavailable"),
    ]
    session = cast(Session, session_mock)
    transaction_factory = RecordingTransactionFactory(
        session=session,
    )
    ingestor = build_ingestor(transaction_factory)
    raw_body = build_payload("comment-1", "comment-2")

    with pytest.raises(
        RuntimeError,
        match="database unavailable",
    ):
        ingestor.ingest(
            raw_body=raw_body,
            signature=build_signature(raw_body),
        )

    assert transaction_factory.entries == 1
    assert transaction_factory.exits == 1
    assert transaction_factory.exception_types == [RuntimeError]
