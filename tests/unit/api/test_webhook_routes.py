"""Tests for the Flask Meta webhook transport adapter."""

from dataclasses import dataclass, field

import pytest

from lead_pipeline.api.webhook_routes import create_webhook_app
from lead_pipeline.ingestion.exceptions import (
    InvalidWebhookPayloadError,
    InvalidWebhookSignatureError,
    UnauthorizedWebhookAccountError,
    WebhookPayloadTooLargeError,
)


@dataclass
class RecordingWebhookIngestor:
    """Test double recording exact webhook transport inputs."""

    result: int = 1
    error: Exception | None = None
    calls: list[tuple[bytes, str | None]] = field(default_factory=list)

    def ingest(
        self,
        *,
        raw_body: bytes,
        signature: str | None,
    ) -> int:
        self.calls.append((raw_body, signature))

        if self.error is not None:
            raise self.error

        return self.result


def build_client(
    ingestor: RecordingWebhookIngestor,
):
    app = create_webhook_app(
        verify_token="verify-secret",
        ingestor=ingestor,
    )
    app.config["TESTING"] = True
    return app.test_client()


def test_valid_callback_verification_returns_challenge() -> None:
    client = build_client(RecordingWebhookIngestor())

    response = client.get(
        "/webhook",
        query_string={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-secret",
            "hub.challenge": "challenge-123",
        },
    )

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "challenge-123"


def test_invalid_callback_verification_returns_forbidden() -> None:
    client = build_client(RecordingWebhookIngestor())

    response = client.get(
        "/webhook",
        query_string={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-secret",
            "hub.challenge": "challenge-123",
        },
    )

    assert response.status_code == 403
    assert response.get_data() == b""


def test_delivery_passes_exact_body_and_signature_to_ingestor() -> None:
    ingestor = RecordingWebhookIngestor()
    client = build_client(ingestor)
    raw_body = b'{"object":"instagram","entry":[]}'

    response = client.post(
        "/webhook",
        data=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=signature",
        },
    )

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "EVENT_RECEIVED"
    assert ingestor.calls == [
        (
            raw_body,
            "sha256=signature",
        )
    ]


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (
            InvalidWebhookSignatureError("webhook signature verification failed"),
            403,
        ),
        (
            UnauthorizedWebhookAccountError(
                "webhook entry does not belong to the authorized account"
            ),
            403,
        ),
        (
            InvalidWebhookPayloadError("webhook payload must contain valid JSON"),
            400,
        ),
        (
            WebhookPayloadTooLargeError(
                "webhook payload exceeds configured size limit"
            ),
            413,
        ),
    ],
)
def test_expected_ingestion_errors_map_to_safe_http_responses(
    error: Exception,
    expected_status: int,
) -> None:
    client = build_client(
        RecordingWebhookIngestor(
            error=error,
        )
    )

    response = client.post(
        "/webhook",
        data=b"private-comment-content",
        headers={
            "X-Hub-Signature-256": "sha256=signature",
        },
    )

    assert response.status_code == expected_status
    assert response.get_data() == b""
    assert b"private-comment-content" not in response.get_data()


def test_unexpected_ingestion_error_is_not_hidden() -> None:
    client = build_client(
        RecordingWebhookIngestor(
            error=RuntimeError("database unavailable"),
        )
    )

    with pytest.raises(
        RuntimeError,
        match="database unavailable",
    ):
        client.post(
            "/webhook",
            data=b'{"object":"instagram","entry":[]}',
        )
