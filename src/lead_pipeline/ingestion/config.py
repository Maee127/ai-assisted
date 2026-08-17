"""Configuration for authorized Meta webhook ingestion."""

import os

DEFAULT_MAX_WEBHOOK_PAYLOAD_BYTES = 1_048_576


def _get_required_environment_value(name: str) -> str:
    value = os.environ.get(name, "").strip()

    if not value:
        raise ValueError(f"{name} must not be empty")

    return value


def get_meta_app_secret() -> str:
    """Return the configured Meta app secret."""

    return _get_required_environment_value("META_APP_SECRET")


def get_webhook_verify_token() -> str:
    """Return the configured webhook callback verification token."""

    return _get_required_environment_value("WEBHOOK_VERIFY_TOKEN")


def get_instagram_business_account_id() -> str:
    """Return the authorized Instagram Business account identifier."""

    return _get_required_environment_value("IG_BUSINESS_ACCOUNT_ID")


def get_max_webhook_payload_bytes() -> int:
    """Return the maximum accepted webhook request-body size."""

    configured_value = os.environ.get(
        "MAX_WEBHOOK_PAYLOAD_BYTES",
        str(DEFAULT_MAX_WEBHOOK_PAYLOAD_BYTES),
    ).strip()

    try:
        payload_limit = int(configured_value)
    except ValueError as error:
        raise ValueError(
            "MAX_WEBHOOK_PAYLOAD_BYTES must be a positive integer"
        ) from error

    if payload_limit <= 0:
        raise ValueError("MAX_WEBHOOK_PAYLOAD_BYTES must be a positive integer")

    return payload_limit
