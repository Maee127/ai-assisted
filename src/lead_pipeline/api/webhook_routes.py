"""Flask transport adapter for Meta webhook requests."""

from typing import Protocol

from flask import Flask, Response, request

from lead_pipeline.ingestion.exceptions import (
    InvalidCallbackVerificationError,
    InvalidWebhookPayloadError,
    InvalidWebhookSignatureError,
    UnauthorizedWebhookAccountError,
    WebhookPayloadTooLargeError,
)
from lead_pipeline.ingestion.webhook_verification import (
    verify_callback_challenge,
)


class WebhookIngestor(Protocol):
    """Transport-facing boundary for verified webhook ingestion."""

    def ingest(
        self,
        *,
        raw_body: bytes,
        signature: str | None,
    ) -> int:
        """Ingest a webhook delivery and return its interaction count."""

        ...


def create_webhook_app(
    *,
    verify_token: str,
    ingestor: WebhookIngestor,
) -> Flask:
    """Create a Flask app with injected webhook dependencies."""

    normalized_verify_token = verify_token.strip()

    if not normalized_verify_token:
        raise ValueError("verify_token must not be empty")

    app = Flask(__name__)

    @app.get("/webhook")
    def verify_webhook() -> Response:
        try:
            challenge = verify_callback_challenge(
                mode=request.args.get("hub.mode"),
                verify_token=request.args.get("hub.verify_token"),
                challenge=request.args.get("hub.challenge"),
                expected_verify_token=normalized_verify_token,
            )
        except InvalidCallbackVerificationError:
            return Response(status=403)

        return Response(
            challenge,
            status=200,
            mimetype="text/plain",
        )

    @app.post("/webhook")
    def receive_webhook() -> Response:
        raw_body = request.get_data(cache=False)
        signature = request.headers.get("X-Hub-Signature-256")

        try:
            ingestor.ingest(
                raw_body=raw_body,
                signature=signature,
            )
        except (
            InvalidWebhookSignatureError,
            UnauthorizedWebhookAccountError,
        ):
            return Response(status=403)
        except InvalidWebhookPayloadError:
            return Response(status=400)
        except WebhookPayloadTooLargeError:
            return Response(status=413)

        return Response(
            "EVENT_RECEIVED",
            status=200,
            mimetype="text/plain",
        )

    return app
