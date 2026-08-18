"""Safe parsing for verified Meta webhook request bodies."""

import json
from typing import cast

from lead_pipeline.ingestion.exceptions import (
    InvalidWebhookPayloadError,
    WebhookPayloadTooLargeError,
)


def validate_webhook_payload_size(
    *,
    raw_body: bytes,
    max_payload_bytes: int,
) -> None:
    """Reject a request body that exceeds the configured byte limit."""

    if max_payload_bytes <= 0:
        raise ValueError("max_payload_bytes must be positive")

    if len(raw_body) > max_payload_bytes:
        raise WebhookPayloadTooLargeError(
            "webhook payload exceeds configured size limit"
        )


def parse_webhook_payload(
    *,
    raw_body: bytes,
    max_payload_bytes: int,
) -> dict[str, object]:
    """Return a verified-size JSON object without retaining raw content."""

    validate_webhook_payload_size(
        raw_body=raw_body,
        max_payload_bytes=max_payload_bytes,
    )

    try:
        parsed_payload: object = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise InvalidWebhookPayloadError(
            "webhook payload must contain valid JSON"
        ) from None

    if not isinstance(parsed_payload, dict):
        raise InvalidWebhookPayloadError("webhook payload must be a JSON object")

    return cast(dict[str, object], parsed_payload)
