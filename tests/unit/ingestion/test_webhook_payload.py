"""Tests for safe Meta webhook payload parsing."""

import pytest

from lead_pipeline.ingestion.exceptions import (
    InvalidWebhookPayloadError,
    WebhookPayloadTooLargeError,
)
from lead_pipeline.ingestion.webhook_payload import (
    parse_webhook_payload,
    validate_webhook_payload_size,
)


def test_size_validation_does_not_parse_body() -> None:
    validate_webhook_payload_size(
        raw_body=b"not-json",
        max_payload_bytes=1024,
    )


def test_standalone_size_validation_rejects_large_body() -> None:
    with pytest.raises(
        WebhookPayloadTooLargeError,
        match="webhook payload exceeds configured size limit",
    ):
        validate_webhook_payload_size(
            raw_body=b"12345",
            max_payload_bytes=4,
        )


def test_valid_json_object_is_parsed() -> None:
    raw_body = b'{"object":"instagram","entry":[]}'

    payload = parse_webhook_payload(
        raw_body=raw_body,
        max_payload_bytes=1024,
    )

    assert payload == {
        "object": "instagram",
        "entry": [],
    }


def test_payload_at_exact_size_limit_is_accepted() -> None:
    raw_body = b"{}"

    payload = parse_webhook_payload(
        raw_body=raw_body,
        max_payload_bytes=len(raw_body),
    )

    assert payload == {}


def test_payload_above_size_limit_is_rejected() -> None:
    with pytest.raises(
        WebhookPayloadTooLargeError,
        match="webhook payload exceeds configured size limit",
    ):
        parse_webhook_payload(
            raw_body=b'{"entry":[]}',
            max_payload_bytes=4,
        )


@pytest.mark.parametrize(
    "max_payload_bytes",
    [0, -1],
)
def test_non_positive_size_limit_is_rejected(
    max_payload_bytes: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="max_payload_bytes must be positive",
    ):
        parse_webhook_payload(
            raw_body=b"{}",
            max_payload_bytes=max_payload_bytes,
        )


@pytest.mark.parametrize(
    "raw_body",
    [
        b"",
        b"{",
        b"[]",
        b'"text"',
        b"null",
        b"\xff",
    ],
)
def test_invalid_or_non_object_payload_is_rejected(
    raw_body: bytes,
) -> None:
    with pytest.raises(InvalidWebhookPayloadError):
        parse_webhook_payload(
            raw_body=raw_body,
            max_payload_bytes=1024,
        )


def test_payload_error_does_not_include_request_content() -> None:
    private_content = "private-comment-text"

    with pytest.raises(InvalidWebhookPayloadError) as error_info:
        parse_webhook_payload(
            raw_body=private_content.encode(),
            max_payload_bytes=1024,
        )

    assert private_content not in str(error_info.value)
