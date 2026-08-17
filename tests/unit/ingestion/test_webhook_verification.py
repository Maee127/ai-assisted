"""Tests for Meta webhook request verification."""

import hashlib
import hmac

import pytest

from lead_pipeline.ingestion.exceptions import (
    InvalidCallbackVerificationError,
    InvalidWebhookSignatureError,
)
from lead_pipeline.ingestion.webhook_verification import (
    verify_callback_challenge,
    verify_webhook_signature,
)


def build_signature(raw_body: bytes, app_secret: str) -> str:
    digest = hmac.new(
        app_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def test_valid_callback_verification_returns_challenge() -> None:
    challenge = verify_callback_challenge(
        mode="subscribe",
        verify_token="verify-secret",
        challenge="challenge-123",
        expected_verify_token="verify-secret",
    )

    assert challenge == "challenge-123"


@pytest.mark.parametrize(
    ("mode", "verify_token", "challenge"),
    [
        (None, "verify-secret", "challenge-123"),
        ("publish", "verify-secret", "challenge-123"),
        ("subscribe", None, "challenge-123"),
        ("subscribe", "wrong-secret", "challenge-123"),
        ("subscribe", "verify-secret", None),
        ("subscribe", "verify-secret", ""),
    ],
)
def test_invalid_callback_verification_is_rejected(
    mode: str | None,
    verify_token: str | None,
    challenge: str | None,
) -> None:
    with pytest.raises(
        InvalidCallbackVerificationError,
        match="webhook callback verification failed",
    ):
        verify_callback_challenge(
            mode=mode,
            verify_token=verify_token,
            challenge=challenge,
            expected_verify_token="verify-secret",
        )


def test_empty_expected_verify_token_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="expected_verify_token must not be empty",
    ):
        verify_callback_challenge(
            mode="subscribe",
            verify_token="verify-secret",
            challenge="challenge-123",
            expected_verify_token=" ",
        )


def test_valid_webhook_signature_is_accepted() -> None:
    raw_body = '{"text":"Crème disponible?"}'.encode()
    app_secret = "app-secret"

    verify_webhook_signature(
        raw_body=raw_body,
        signature=build_signature(raw_body, app_secret),
        app_secret=app_secret,
    )


def test_signature_is_checked_against_exact_raw_body() -> None:
    raw_body = b'{"entry":[]}'
    signature = build_signature(raw_body, "app-secret")

    with pytest.raises(
        InvalidWebhookSignatureError,
        match="webhook signature verification failed",
    ):
        verify_webhook_signature(
            raw_body=b'{ "entry": [] }',
            signature=signature,
            app_secret="app-secret",
        )


@pytest.mark.parametrize(
    "signature",
    [
        None,
        "",
        "sha1=invalid",
        "sha256=not-a-valid-digest",
    ],
)
def test_missing_or_malformed_signature_is_rejected(
    signature: str | None,
) -> None:
    with pytest.raises(
        InvalidWebhookSignatureError,
        match="webhook signature verification failed",
    ):
        verify_webhook_signature(
            raw_body=b'{"entry":[]}',
            signature=signature,
            app_secret="app-secret",
        )


def test_empty_app_secret_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="app_secret must not be empty",
    ):
        verify_webhook_signature(
            raw_body=b'{"entry":[]}',
            signature="sha256=unused",
            app_secret=" ",
        )
