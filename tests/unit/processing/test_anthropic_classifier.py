"""Tests for the Anthropic structured classification adapter."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest
from anthropic import Anthropic
from pydantic import ValidationError

from lead_pipeline.domain.enums import ClassificationLabel, SourceType
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.processing.anthropic_classifier import (
    AnthropicClassificationOutput,
    AnthropicClassificationProvider,
    InvalidAnthropicClassificationError,
)


def build_interaction() -> InstagramInteraction:
    return InstagramInteraction(
        event_id=InstagramEventId("event-1"),
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        media_id=InstagramMediaId("media-1"),
        source_type=SourceType.POST_COMMENT,
        text="How much is this serum?",
        source_timestamp=datetime(2026, 8, 23, 8, 0, tzinfo=UTC),
        collected_at=datetime(2026, 8, 23, 8, 1, tzinfo=UTC),
        username="private-user",
    )


def build_provider(
    client_mock: MagicMock,
) -> AnthropicClassificationProvider:
    return AnthropicClassificationProvider(
        client=cast(Anthropic, client_mock),
        model="claude-haiku-4-5-20251001",
        prompt_version="classification-v1",
    )


def test_structured_output_is_mapped_to_domain_result() -> None:
    client_mock = MagicMock()
    client_mock.messages.parse.return_value = SimpleNamespace(
        parsed_output=AnthropicClassificationOutput(
            label=ClassificationLabel.SALES_LEAD,
            confidence=0.94,
            reason="The user asks about product price.",
        )
    )
    provider = build_provider(client_mock)

    result = provider.classify(build_interaction())

    assert result.label is ClassificationLabel.SALES_LEAD
    assert result.confidence == 0.94
    assert result.reason == "The user asks about product price."
    assert result.model_name == "anthropic"
    assert result.model_version == "claude-haiku-4-5-20251001"
    assert result.prompt_version == "classification-v1"


def test_only_minimized_comment_text_is_sent() -> None:
    client_mock = MagicMock()
    client_mock.messages.parse.return_value = SimpleNamespace(
        parsed_output=AnthropicClassificationOutput(
            label=ClassificationLabel.SALES_LEAD,
            confidence=0.9,
            reason="The user asks about price.",
        )
    )
    provider = build_provider(client_mock)

    provider.classify(build_interaction())

    arguments = client_mock.messages.parse.call_args.kwargs
    assert arguments["messages"] == [
        {
            "role": "user",
            "content": "How much is this serum?",
        }
    ]
    assert arguments["output_format"] is AnthropicClassificationOutput
    assert "private-user" not in str(arguments)


def test_missing_parsed_output_is_rejected() -> None:
    client_mock = MagicMock()
    client_mock.messages.parse.return_value = SimpleNamespace(
        parsed_output=None,
    )
    provider = build_provider(client_mock)

    with pytest.raises(
        InvalidAnthropicClassificationError,
        match="Anthropic returned no structured classification",
    ):
        provider.classify(build_interaction())


def test_provider_failures_are_not_hidden() -> None:
    client_mock = MagicMock()
    client_mock.messages.parse.side_effect = RuntimeError("provider unavailable")
    provider = build_provider(client_mock)

    with pytest.raises(RuntimeError, match="provider unavailable"):
        provider.classify(build_interaction())


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_output_schema_rejects_invalid_confidence(
    confidence: float,
) -> None:
    with pytest.raises(ValidationError):
        AnthropicClassificationOutput(
            label=ClassificationLabel.UNCERTAIN,
            confidence=confidence,
            reason="Insufficient evidence.",
        )


def test_blank_model_is_rejected() -> None:
    with pytest.raises(ValueError, match="model must not be empty"):
        AnthropicClassificationProvider(
            client=cast(Anthropic, MagicMock()),
            model=" ",
            prompt_version="classification-v1",
        )


def test_blank_prompt_version_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="prompt_version must not be empty",
    ):
        AnthropicClassificationProvider(
            client=cast(Anthropic, MagicMock()),
            model="claude-haiku-4-5-20251001",
            prompt_version=" ",
        )


def test_non_positive_max_tokens_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_tokens must be positive"):
        AnthropicClassificationProvider(
            client=cast(Anthropic, MagicMock()),
            model="claude-haiku-4-5-20251001",
            prompt_version="classification-v1",
            max_tokens=0,
        )
