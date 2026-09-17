"""Tests for model-classification configuration."""

from collections.abc import Callable

import pytest

from lead_pipeline.processing.config import (
    DEFAULT_CLASSIFICATION_MAX_TOKENS,
    DEFAULT_CLASSIFICATION_PROMPT_VERSION,
    DEFAULT_INFERRED_INTEREST_CONFIDENCE_THRESHOLD,
    DEFAULT_INTEREST_MAX_TOKENS,
    DEFAULT_INTEREST_PROMPT_VERSION,
    DEFAULT_PRIMARY_CLASSIFIER_MODEL,
    DEFAULT_PRIMARY_INTEREST_EXTRACTOR_MODEL,
    DEFAULT_SALES_LEAD_CONFIDENCE_THRESHOLD,
    DEFAULT_STRONGER_CLASSIFIER_MODEL,
    DEFAULT_STRONGER_INTEREST_EXTRACTOR_MODEL,
    get_anthropic_api_key,
    get_classification_max_tokens,
    get_classification_prompt_version,
    get_inferred_interest_confidence_threshold,
    get_interest_max_tokens,
    get_interest_prompt_version,
    get_primary_classifier_model,
    get_primary_interest_extractor_model,
    get_sales_lead_confidence_threshold,
    get_stronger_classifier_model,
    get_stronger_interest_extractor_model,
)


def test_anthropic_api_key_is_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "  private-key  ")

    assert get_anthropic_api_key() == "private-key"


@pytest.mark.parametrize("configured_value", [None, "", "   "])
def test_missing_or_blank_anthropic_api_key_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    configured_value: str | None,
) -> None:
    if configured_value is None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    else:
        monkeypatch.setenv("ANTHROPIC_API_KEY", configured_value)

    with pytest.raises(
        ValueError,
        match="ANTHROPIC_API_KEY must not be empty",
    ):
        get_anthropic_api_key()


def test_default_classifier_configuration_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PRIMARY_CLASSIFIER_MODEL", raising=False)
    monkeypatch.delenv("STRONGER_CLASSIFIER_MODEL", raising=False)
    monkeypatch.delenv("CLASSIFICATION_PROMPT_VERSION", raising=False)
    monkeypatch.delenv("CLASSIFICATION_MAX_TOKENS", raising=False)
    monkeypatch.delenv("SALES_LEAD_CONFIDENCE_THRESHOLD", raising=False)

    assert get_primary_classifier_model() == DEFAULT_PRIMARY_CLASSIFIER_MODEL
    assert get_stronger_classifier_model() == DEFAULT_STRONGER_CLASSIFIER_MODEL
    assert get_classification_prompt_version() == DEFAULT_CLASSIFICATION_PROMPT_VERSION
    assert get_classification_max_tokens() == DEFAULT_CLASSIFICATION_MAX_TOKENS
    assert (
        get_sales_lead_confidence_threshold() == DEFAULT_SALES_LEAD_CONFIDENCE_THRESHOLD
    )


@pytest.mark.parametrize(
    ("environment_name", "configured_value", "getter"),
    [
        (
            "PRIMARY_CLASSIFIER_MODEL",
            "primary-model",
            get_primary_classifier_model,
        ),
        (
            "STRONGER_CLASSIFIER_MODEL",
            "stronger-model",
            get_stronger_classifier_model,
        ),
        (
            "CLASSIFICATION_PROMPT_VERSION",
            "prompt-v2",
            get_classification_prompt_version,
        ),
    ],
)
def test_configured_text_value_is_normalized(
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
        ("PRIMARY_CLASSIFIER_MODEL", get_primary_classifier_model),
        ("STRONGER_CLASSIFIER_MODEL", get_stronger_classifier_model),
        (
            "CLASSIFICATION_PROMPT_VERSION",
            get_classification_prompt_version,
        ),
    ],
)
def test_blank_configured_text_value_is_rejected(
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


def test_configured_max_tokens_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLASSIFICATION_MAX_TOKENS", "512")

    assert get_classification_max_tokens() == 512


@pytest.mark.parametrize(
    "configured_value",
    ["", " ", "0", "-1", "1.5", "invalid"],
)
def test_invalid_max_tokens_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    configured_value: str,
) -> None:
    monkeypatch.setenv(
        "CLASSIFICATION_MAX_TOKENS",
        configured_value,
    )

    with pytest.raises(
        ValueError,
        match="CLASSIFICATION_MAX_TOKENS must be a positive integer",
    ):
        get_classification_max_tokens()


def test_default_interest_configuration_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PRIMARY_INTEREST_EXTRACTOR_MODEL", raising=False)
    monkeypatch.delenv("STRONGER_INTEREST_EXTRACTOR_MODEL", raising=False)
    monkeypatch.delenv("INTEREST_PROMPT_VERSION", raising=False)
    monkeypatch.delenv("INTEREST_MAX_TOKENS", raising=False)
    monkeypatch.delenv(
        "INFERRED_INTEREST_CONFIDENCE_THRESHOLD",
        raising=False,
    )

    assert (
        get_primary_interest_extractor_model()
        == DEFAULT_PRIMARY_INTEREST_EXTRACTOR_MODEL
    )
    assert (
        get_stronger_interest_extractor_model()
        == DEFAULT_STRONGER_INTEREST_EXTRACTOR_MODEL
    )
    assert get_interest_prompt_version() == DEFAULT_INTEREST_PROMPT_VERSION
    assert get_interest_max_tokens() == DEFAULT_INTEREST_MAX_TOKENS
    assert (
        get_inferred_interest_confidence_threshold()
        == DEFAULT_INFERRED_INTEREST_CONFIDENCE_THRESHOLD
    )


@pytest.mark.parametrize(
    ("environment_name", "configured_value", "getter"),
    [
        (
            "PRIMARY_INTEREST_EXTRACTOR_MODEL",
            "primary-interest-model",
            get_primary_interest_extractor_model,
        ),
        (
            "STRONGER_INTEREST_EXTRACTOR_MODEL",
            "stronger-interest-model",
            get_stronger_interest_extractor_model,
        ),
        (
            "INTEREST_PROMPT_VERSION",
            "interest-v2",
            get_interest_prompt_version,
        ),
    ],
)
def test_configured_interest_text_value_is_normalized(
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
        (
            "PRIMARY_INTEREST_EXTRACTOR_MODEL",
            get_primary_interest_extractor_model,
        ),
        (
            "STRONGER_INTEREST_EXTRACTOR_MODEL",
            get_stronger_interest_extractor_model,
        ),
        (
            "INTEREST_PROMPT_VERSION",
            get_interest_prompt_version,
        ),
    ],
)
def test_blank_interest_text_value_is_rejected(
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


def test_configured_interest_max_tokens_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INTEREST_MAX_TOKENS", "768")

    assert get_interest_max_tokens() == 768


@pytest.mark.parametrize(
    "configured_value",
    ["", " ", "0", "-1", "1.5", "invalid"],
)
def test_invalid_interest_max_tokens_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    configured_value: str,
) -> None:
    monkeypatch.setenv(
        "INTEREST_MAX_TOKENS",
        configured_value,
    )

    with pytest.raises(
        ValueError,
        match="INTEREST_MAX_TOKENS must be a positive integer",
    ):
        get_interest_max_tokens()


def test_configured_interest_confidence_threshold_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "INFERRED_INTEREST_CONFIDENCE_THRESHOLD",
        " 0.85 ",
    )

    assert get_inferred_interest_confidence_threshold() == 0.85


@pytest.mark.parametrize(
    "configured_value",
    ["", " ", "-0.01", "1.01", "nan", "inf", "invalid"],
)
def test_invalid_interest_confidence_threshold_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    configured_value: str,
) -> None:
    monkeypatch.setenv(
        "INFERRED_INTEREST_CONFIDENCE_THRESHOLD",
        configured_value,
    )

    with pytest.raises(
        ValueError,
        match=(
            "INFERRED_INTEREST_CONFIDENCE_THRESHOLD "
            "must be a number between 0.0 and 1.0"
        ),
    ):
        get_inferred_interest_confidence_threshold()


def test_configured_sales_lead_confidence_threshold_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "SALES_LEAD_CONFIDENCE_THRESHOLD",
        " 0.94 ",
    )

    assert get_sales_lead_confidence_threshold() == 0.94


@pytest.mark.parametrize(
    "configured_value",
    ["", " ", "-0.01", "1.01", "nan", "inf", "invalid"],
)
def test_invalid_sales_lead_confidence_threshold_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    configured_value: str,
) -> None:
    monkeypatch.setenv(
        "SALES_LEAD_CONFIDENCE_THRESHOLD",
        configured_value,
    )

    with pytest.raises(
        ValueError,
        match=("SALES_LEAD_CONFIDENCE_THRESHOLD must be a number between 0.0 and 1.0"),
    ):
        get_sales_lead_confidence_threshold()
