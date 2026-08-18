"""Tests for orchestrating verified Meta webhook ingestion."""

import hashlib
import hmac
import json
from datetime import UTC, datetime

import pytest

from lead_pipeline.application.ingest_interaction import IngestInteraction
from lead_pipeline.domain.identifiers import ClientId, InstagramEventId
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.ingestion.exceptions import (
    InvalidWebhookPayloadError,
    InvalidWebhookSignatureError,
    UnauthorizedWebhookAccountError,
    WebhookPayloadTooLargeError,
)
from lead_pipeline.ingestion.meta_webhook_ingestor import MetaWebhookIngestor

APP_SECRET = "app-secret"
SOURCE_TIMESTAMP = datetime(2026, 8, 18, 8, 0, tzinfo=UTC)
COLLECTED_AT = datetime(2026, 8, 18, 8, 1, tzinfo=UTC)


class IdempotentRecordingRepository:
    """Repository double keyed by stable Instagram event ID."""

    def __init__(self) -> None:
        self.stored: dict[str, InstagramInteraction] = {}

    def add(self, interaction: InstagramInteraction) -> None:
        self.stored.setdefault(
            interaction.event_id.value,
            interaction,
        )

    def get_by_event_id(
        self,
        event_id: InstagramEventId,
    ) -> InstagramInteraction | None:
        return self.stored.get(event_id.value)


def build_payload(
    *,
    account_id: str = "business-1",
    field: str = "comments",
    media_product_type: str = "FEED",
    commenter_overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    commenter: dict[str, object] = {
        "id": "user-1",
        "username": "beauty_user",
    }
    commenter.update(commenter_overrides or {})

    return {
        "object": "instagram",
        "entry": [
            {
                "id": account_id,
                "time": int(SOURCE_TIMESTAMP.timestamp()),
                "field": field,
                "value": {
                    "id": "comment-1",
                    "from": commenter,
                    "text": "Is this available?",
                    "media": {
                        "id": "media-1",
                        "media_product_type": media_product_type,
                    },
                },
            }
        ],
    }


def encode_payload(payload: dict[str, object]) -> bytes:
    return json.dumps(
        payload,
        separators=(",", ":"),
    ).encode("utf-8")


def build_signature(raw_body: bytes) -> str:
    digest = hmac.new(
        APP_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def build_ingestor(
    repository: IdempotentRecordingRepository,
    *,
    max_payload_bytes: int = 4096,
) -> MetaWebhookIngestor:
    return MetaWebhookIngestor(
        app_secret=APP_SECRET,
        client_id=ClientId("client-1"),
        authorized_business_account_id="business-1",
        max_payload_bytes=max_payload_bytes,
        ingest_interaction=IngestInteraction(
            repository=repository,
        ),
        clock=lambda: COLLECTED_AT,
    )


def test_valid_signed_comment_is_ingested() -> None:
    repository = IdempotentRecordingRepository()
    ingestor = build_ingestor(repository)
    raw_body = encode_payload(build_payload())

    accepted_count = ingestor.ingest(
        raw_body=raw_body,
        signature=build_signature(raw_body),
    )

    assert accepted_count == 1
    assert list(repository.stored) == ["comment-1"]
    interaction = repository.stored["comment-1"]
    assert interaction.client_id == ClientId("client-1")
    assert interaction.collected_at == COLLECTED_AT


def test_invalid_signature_is_rejected_before_persistence() -> None:
    repository = IdempotentRecordingRepository()
    ingestor = build_ingestor(repository)
    raw_body = encode_payload(build_payload())

    with pytest.raises(InvalidWebhookSignatureError):
        ingestor.ingest(
            raw_body=raw_body,
            signature="sha256=invalid",
        )

    assert repository.stored == {}


def test_oversized_body_is_rejected_before_signature_work() -> None:
    repository = IdempotentRecordingRepository()
    ingestor = build_ingestor(
        repository,
        max_payload_bytes=4,
    )

    with pytest.raises(WebhookPayloadTooLargeError):
        ingestor.ingest(
            raw_body=b'{"entry":[]}',
            signature=None,
        )

    assert repository.stored == {}


def test_invalid_json_is_rejected_after_valid_signature() -> None:
    repository = IdempotentRecordingRepository()
    ingestor = build_ingestor(repository)
    raw_body = b"not-json"

    with pytest.raises(InvalidWebhookPayloadError):
        ingestor.ingest(
            raw_body=raw_body,
            signature=build_signature(raw_body),
        )

    assert repository.stored == {}


def test_other_business_account_is_rejected_before_persistence() -> None:
    repository = IdempotentRecordingRepository()
    ingestor = build_ingestor(repository)
    raw_body = encode_payload(build_payload(account_id="other-business"))

    with pytest.raises(UnauthorizedWebhookAccountError):
        ingestor.ingest(
            raw_body=raw_body,
            signature=build_signature(raw_body),
        )

    assert repository.stored == {}


def test_signature_covers_exact_raw_body() -> None:
    repository = IdempotentRecordingRepository()
    ingestor = build_ingestor(repository)
    signed_body = encode_payload(build_payload())

    with pytest.raises(InvalidWebhookSignatureError):
        ingestor.ingest(
            raw_body=signed_body + b" ",
            signature=build_signature(signed_body),
        )

    assert repository.stored == {}


def test_duplicate_delivery_remains_idempotent() -> None:
    repository = IdempotentRecordingRepository()
    ingestor = build_ingestor(repository)
    raw_body = encode_payload(build_payload())
    signature = build_signature(raw_body)

    ingestor.ingest(
        raw_body=raw_body,
        signature=signature,
    )
    ingestor.ingest(
        raw_body=raw_body,
        signature=signature,
    )

    assert list(repository.stored) == ["comment-1"]


def test_unrelated_event_field_is_safely_ignored() -> None:
    repository = IdempotentRecordingRepository()
    ingestor = build_ingestor(repository)
    raw_body = encode_payload(build_payload(field="messages"))

    accepted_count = ingestor.ingest(
        raw_body=raw_body,
        signature=build_signature(raw_body),
    )

    assert accepted_count == 0
    assert repository.stored == {}


def test_complete_payload_and_extra_profile_fields_are_not_stored() -> None:
    repository = IdempotentRecordingRepository()
    ingestor = build_ingestor(repository)
    raw_body = encode_payload(
        build_payload(
            commenter_overrides={
                "birthday": "not-retained",
                "biography": "not-retained",
            }
        )
    )

    ingestor.ingest(
        raw_body=raw_body,
        signature=build_signature(raw_body),
    )

    interaction = repository.stored["comment-1"]
    assert not hasattr(interaction, "birthday")
    assert not hasattr(interaction, "biography")
    assert not hasattr(interaction, "raw_body")
    assert not hasattr(interaction, "payload")
