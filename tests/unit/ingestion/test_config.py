"""Tests for webhook ingestion configuration."""

from collections.abc import Callable

import pytest

from lead_pipeline.ingestion.config import (
    DEFAULT_MAX_WEBHOOK_PAYLOAD_BYTES,
    get_instagram_business_account_id,
    get_max_webhook_payload_bytes,
    get_meta_app_secret,
    get_webhook_verify_token,
)


@pytest.mark.parametrize(
    ("environment_name", "configured_value", "getter"),
    [
        ("META_APP_SECRET", "app-secret", get_meta_app_secret),
        (
            "WEBHOOK_VERIFY_TOKEN",
            "verify-token",
            get_webhook_verify_token,
        ),
        (
            "IG_BUSINESS_ACCOUNT_ID",
            "business-account-1",
            get_instagram_business_account_id,
        ),
    ],
)
def test_required_environment_value_is_normalized(
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
    configured_value: str,
    getter: Callable[[], str],
) -> None:
    monkeypatch.setenv(
        environment_name,
        f"  {configured_value}  ",
    )

    assert getter() == configured_value


@pytest.mark.parametrize(
    ("environment_name", "getter"),
    [
        ("META_APP_SECRET", get_meta_app_secret),
        ("WEBHOOK_VERIFY_TOKEN", get_webhook_verify_token),
        (
            "IG_BUSINESS_ACCOUNT_ID",
            get_instagram_business_account_id,
        ),
    ],
)
def test_missing_required_environment_value_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
    getter: Callable[[], str],
) -> None:
    monkeypatch.delenv(environment_name, raising=False)

    with pytest.raises(
        ValueError,
        match=f"{environment_name} must not be empty",
    ):
        getter()


@pytest.mark.parametrize(
    ("environment_name", "getter"),
    [
        ("META_APP_SECRET", get_meta_app_secret),
        ("WEBHOOK_VERIFY_TOKEN", get_webhook_verify_token),
        (
            "IG_BUSINESS_ACCOUNT_ID",
            get_instagram_business_account_id,
        ),
    ],
)
def test_blank_required_environment_value_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
    getter: Callable[[], str],
) -> None:
    monkeypatch.setenv(environment_name, "   ")

    with pytest.raises(
        ValueError,
        match=f"{environment_name} must not be empty",
    ):
        getter()


def test_default_payload_size_limit_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MAX_WEBHOOK_PAYLOAD_BYTES", raising=False)

    assert get_max_webhook_payload_bytes() == DEFAULT_MAX_WEBHOOK_PAYLOAD_BYTES


def test_configured_payload_size_limit_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_WEBHOOK_PAYLOAD_BYTES", "2048")

    assert get_max_webhook_payload_bytes() == 2048


@pytest.mark.parametrize(
    "configured_value",
    ["", " ", "0", "-1", "1.5", "invalid"],
)
def test_invalid_payload_size_limit_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    configured_value: str,
) -> None:
    monkeypatch.setenv(
        "MAX_WEBHOOK_PAYLOAD_BYTES",
        configured_value,
    )

    with pytest.raises(
        ValueError,
        match="MAX_WEBHOOK_PAYLOAD_BYTES must be a positive integer",
    ):
        get_max_webhook_payload_bytes()
