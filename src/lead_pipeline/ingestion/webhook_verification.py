"""Verification helpers for Meta webhook requests."""

import hashlib
import hmac

from lead_pipeline.ingestion.exceptions import (
    InvalidCallbackVerificationError,
    InvalidWebhookSignatureError,
)


def _require_secret(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")

    return value


def verify_callback_challenge(
    *,
    mode: str | None,
    verify_token: str | None,
    challenge: str | None,
    expected_verify_token: str,
) -> str:
    """Validate Meta's callback handshake and return its challenge."""

    expected_token = _require_secret(
        expected_verify_token,
        "expected_verify_token",
    )
    supplied_token = verify_token or ""
    token_matches = hmac.compare_digest(
        supplied_token.encode("utf-8"),
        expected_token.encode("utf-8"),
    )

    if mode != "subscribe" or not token_matches or not challenge:
        raise InvalidCallbackVerificationError("webhook callback verification failed")

    return challenge


def verify_webhook_signature(
    *,
    raw_body: bytes,
    signature: str | None,
    app_secret: str,
) -> None:
    """Verify an HMAC-SHA256 signature against the exact request body."""

    secret = _require_secret(app_secret, "app_secret")
    expected_signature = (
        "sha256="
        + hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
    )
    supplied_signature = signature or ""

    if not hmac.compare_digest(
        supplied_signature.encode("utf-8"),
        expected_signature.encode("utf-8"),
    ):
        raise InvalidWebhookSignatureError("webhook signature verification failed")
