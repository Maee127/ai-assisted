"""Configuration for model-based classification."""

import os

DEFAULT_PRIMARY_CLASSIFIER_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_STRONGER_CLASSIFIER_MODEL = "claude-sonnet-5"
DEFAULT_CLASSIFICATION_PROMPT_VERSION = "classification-v1"
DEFAULT_CLASSIFICATION_MAX_TOKENS = 256


def _get_required_environment_value(name: str) -> str:
    value = os.environ.get(name, "").strip()

    if not value:
        raise ValueError(f"{name} must not be empty")

    return value


def _get_configured_value(
    name: str,
    default: str,
) -> str:
    configured_value = os.environ.get(name)

    if configured_value is None:
        return default

    normalized_value = configured_value.strip()

    if not normalized_value:
        raise ValueError(f"{name} must not be empty")

    return normalized_value


def get_anthropic_api_key() -> str:
    """Return the required Anthropic API key."""

    return _get_required_environment_value("ANTHROPIC_API_KEY")


def get_primary_classifier_model() -> str:
    """Return the configured economical primary model."""

    return _get_configured_value(
        "PRIMARY_CLASSIFIER_MODEL",
        DEFAULT_PRIMARY_CLASSIFIER_MODEL,
    )


def get_stronger_classifier_model() -> str:
    """Return the configured stronger uncertainty model."""

    return _get_configured_value(
        "STRONGER_CLASSIFIER_MODEL",
        DEFAULT_STRONGER_CLASSIFIER_MODEL,
    )


def get_classification_prompt_version() -> str:
    """Return the version assigned to classification prompts."""

    return _get_configured_value(
        "CLASSIFICATION_PROMPT_VERSION",
        DEFAULT_CLASSIFICATION_PROMPT_VERSION,
    )


def get_classification_max_tokens() -> int:
    """Return the maximum output-token budget per classification."""

    configured_value = os.environ.get(
        "CLASSIFICATION_MAX_TOKENS",
        str(DEFAULT_CLASSIFICATION_MAX_TOKENS),
    ).strip()

    try:
        max_tokens = int(configured_value)
    except ValueError as error:
        raise ValueError(
            "CLASSIFICATION_MAX_TOKENS must be a positive integer"
        ) from error

    if max_tokens <= 0:
        raise ValueError("CLASSIFICATION_MAX_TOKENS must be a positive integer")

    return max_tokens
