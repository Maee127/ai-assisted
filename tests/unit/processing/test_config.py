"""Tests for model-classification configuration."""

from collections.abc import Callable

import pytest

from lead_pipeline.processing.config import (
    DEFAULT_CLASSIFICATION_MAX_TOKENS,
    DEFAULT_CLASSIFICATION_PROMPT_VERSION,
    DEFAULT_PRIMARY_CLASSIFIER_MODEL,
    DEFAULT_STRONGER_CLASSIFIER_MODEL,
    get_anthropic_api_key,
    get_classification_max_tokens,
    get_classification_prompt_version,
    get_primary_classifier_model,
    get_stronger_classifier_model,
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

    assert get_primary_classifier_model() == DEFAULT_PRIMARY_CLASSIFIER_MODEL
    assert get_stronger_classifier_model() == DEFAULT_STRONGER_CLASSIFIER_MODEL
    assert get_classification_prompt_version() == DEFAULT_CLASSIFICATION_PROMPT_VERSION
    assert get_classification_max_tokens() == DEFAULT_CLASSIFICATION_MAX_TOKENS


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
