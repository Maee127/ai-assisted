"""Configuration for model-based processing."""

import os

DEFAULT_PRIMARY_CLASSIFIER_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_STRONGER_CLASSIFIER_MODEL = "claude-sonnet-5"
DEFAULT_CLASSIFICATION_PROMPT_VERSION = "classification-v1"
DEFAULT_CLASSIFICATION_MAX_TOKENS = 256

DEFAULT_PRIMARY_INTEREST_EXTRACTOR_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_STRONGER_INTEREST_EXTRACTOR_MODEL = "claude-sonnet-5"
DEFAULT_INTEREST_PROMPT_VERSION = "interest-v1"
DEFAULT_INTEREST_MAX_TOKENS = 512
DEFAULT_INFERRED_INTEREST_CONFIDENCE_THRESHOLD = 0.8


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


def _get_positive_integer(
    name: str,
    default: int,
) -> int:
    configured_value = os.environ.get(
        name,
        str(default),
    ).strip()

    try:
        value = int(configured_value)
    except ValueError as error:
        raise ValueError(f"{name} must be a positive integer") from error

    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")

    return value


def get_anthropic_api_key() -> str:
    """Return the required Anthropic API key."""

    return _get_required_environment_value("ANTHROPIC_API_KEY")


def get_primary_classifier_model() -> str:
    """Return the configured economical primary classifier."""

    return _get_configured_value(
        "PRIMARY_CLASSIFIER_MODEL",
        DEFAULT_PRIMARY_CLASSIFIER_MODEL,
    )


def get_stronger_classifier_model() -> str:
    """Return the configured stronger uncertainty classifier."""

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
    """Return the token budget per classification."""

    return _get_positive_integer(
        "CLASSIFICATION_MAX_TOKENS",
        DEFAULT_CLASSIFICATION_MAX_TOKENS,
    )


def get_primary_interest_extractor_model() -> str:
    """Return the configured economical primary interest extractor."""

    return _get_configured_value(
        "PRIMARY_INTEREST_EXTRACTOR_MODEL",
        DEFAULT_PRIMARY_INTEREST_EXTRACTOR_MODEL,
    )


def get_stronger_interest_extractor_model() -> str:
    """Return the configured stronger interest extractor."""

    return _get_configured_value(
        "STRONGER_INTEREST_EXTRACTOR_MODEL",
        DEFAULT_STRONGER_INTEREST_EXTRACTOR_MODEL,
    )


def get_interest_prompt_version() -> str:
    """Return the version assigned to interest-extraction prompts."""

    return _get_configured_value(
        "INTEREST_PROMPT_VERSION",
        DEFAULT_INTEREST_PROMPT_VERSION,
    )


def get_interest_max_tokens() -> int:
    """Return the token budget per interest extraction."""

    return _get_positive_integer(
        "INTEREST_MAX_TOKENS",
        DEFAULT_INTEREST_MAX_TOKENS,
    )


def get_inferred_interest_confidence_threshold() -> float:
    """Return the confirmation threshold for inferred interests."""

    environment_name = "INFERRED_INTEREST_CONFIDENCE_THRESHOLD"
    configured_value = os.environ.get(
        environment_name,
        str(DEFAULT_INFERRED_INTEREST_CONFIDENCE_THRESHOLD),
    ).strip()

    try:
        threshold = float(configured_value)
    except ValueError as error:
        raise ValueError(
            f"{environment_name} must be a number between 0.0 and 1.0"
        ) from error

    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"{environment_name} must be a number between 0.0 and 1.0")

    return threshold
