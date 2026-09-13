"""Tests for the Anthropic structured interest-extraction adapter."""

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest
from anthropic import Anthropic
from pydantic import ValidationError

from lead_pipeline.domain.catalogue import CatalogueContext, CatalogueItem
from lead_pipeline.domain.enums import InterestType, SourceType
from lead_pipeline.domain.identifiers import (
    CatalogueItemId,
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.domain.interests import InterestEvidence
from lead_pipeline.processing.anthropic_interest_extractor import (
    AnthropicInterestExtractionOutput,
    AnthropicInterestExtractionProvider,
    AnthropicInterestItemOutput,
    InvalidAnthropicInterestExtractionError,
)


def build_interaction() -> InstagramInteraction:
    return InstagramInteraction(
        event_id=InstagramEventId("event-1"),
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        media_id=InstagramMediaId("media-1"),
        source_type=SourceType.POST_COMMENT,
        text="I need a calming serum for my dry-looking skin.",
        source_timestamp=datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
        collected_at=datetime(2026, 9, 13, 12, 1, tzinfo=UTC),
        username="private-user",
    )


def build_catalogue_context(
    *,
    client_id: str = "client-1",
) -> CatalogueContext:
    context_client_id = ClientId(client_id)

    return CatalogueContext(
        client_id=context_client_id,
        items=(
            CatalogueItem(
                catalogue_item_id=CatalogueItemId("item-1"),
                client_id=context_client_id,
                name="Calming Serum",
                category="Serums",
                description="Serum for dry-looking skin.",
            ),
        ),
    )


def build_provider(
    client_mock: MagicMock,
    *,
    model: str = "claude-haiku-4-5-20251001",
) -> AnthropicInterestExtractionProvider:
    return AnthropicInterestExtractionProvider(
        client=cast(Anthropic, client_mock),
        model=model,
        prompt_version="interest-v1",
    )


def build_candidate() -> InterestEvidence:
    return InterestEvidence(
        name="Calming serum",
        interest_type=InterestType.INFERRED,
        confidence=0.6,
        source_event_id=InstagramEventId("event-1"),
        model_name="anthropic",
        model_version="primary-model",
        prompt_version="interest-v1",
    )


def test_structured_output_is_mapped_to_interest_evidence() -> None:
    client_mock = MagicMock()
    client_mock.messages.parse.return_value = SimpleNamespace(
        parsed_output=AnthropicInterestExtractionOutput(
            interests=[
                AnthropicInterestItemOutput(
                    name="Calming serum",
                    interest_type=InterestType.EXPLICIT,
                    confidence=0.94,
                    catalogue_item_ids=["item-1"],
                )
            ]
        )
    )
    provider = build_provider(client_mock)

    interests = provider.extract(
        build_interaction(),
        catalogue_context=build_catalogue_context(),
    )

    assert len(interests) == 1
    interest = interests[0]
    assert interest.name == "Calming serum"
    assert interest.interest_type is InterestType.EXPLICIT
    assert interest.confidence == 0.94
    assert interest.source_event_id == InstagramEventId("event-1")
    assert interest.model_name == "anthropic"
    assert interest.model_version == "claude-haiku-4-5-20251001"
    assert interest.prompt_version == "interest-v1"
    assert interest.catalogue_evidence == '["item-1"]'


def test_only_minimized_safe_context_is_sent() -> None:
    client_mock = MagicMock()
    client_mock.messages.parse.return_value = SimpleNamespace(
        parsed_output=AnthropicInterestExtractionOutput(),
    )
    provider = build_provider(client_mock)

    provider.extract(
        build_interaction(),
        catalogue_context=build_catalogue_context(),
    )

    arguments = client_mock.messages.parse.call_args.kwargs
    content = json.loads(arguments["messages"][0]["content"])

    assert content == {
        "comment": "I need a calming serum for my dry-looking skin.",
        "catalogue_context": [
            {
                "catalogue_item_id": "item-1",
                "name": "Calming Serum",
                "category": "Serums",
                "description": "Serum for dry-looking skin.",
            }
        ],
        "candidates": [],
    }
    assert arguments["output_format"] is AnthropicInterestExtractionOutput
    assert "private-user" not in str(arguments)
    assert "user-1" not in str(arguments)
    assert "client-1" not in str(arguments)
    assert "Never infer a medical diagnosis" in arguments["system"]
    assert "reevaluate only those candidates" in arguments["system"]


def test_candidates_are_sent_for_stronger_reevaluation() -> None:
    candidate = build_candidate()
    client_mock = MagicMock()
    client_mock.messages.parse.return_value = SimpleNamespace(
        parsed_output=AnthropicInterestExtractionOutput(
            interests=[
                AnthropicInterestItemOutput(
                    name="Calming serum",
                    interest_type=InterestType.INFERRED,
                    confidence=0.91,
                )
            ]
        )
    )
    provider = build_provider(
        client_mock,
        model="stronger-model",
    )

    interests = provider.extract(
        build_interaction(),
        catalogue_context=build_catalogue_context(),
        candidates=(candidate,),
    )

    arguments = client_mock.messages.parse.call_args.kwargs
    content = json.loads(arguments["messages"][0]["content"])

    assert content["candidates"] == [
        {
            "name": "Calming serum",
            "interest_type": "INFERRED",
            "confidence": 0.6,
            "catalogue_evidence": None,
        }
    ]
    assert interests[0].confidence == 0.91
    assert interests[0].model_version == "stronger-model"


def test_reevaluation_cannot_introduce_new_interest() -> None:
    client_mock = MagicMock()
    client_mock.messages.parse.return_value = SimpleNamespace(
        parsed_output=AnthropicInterestExtractionOutput(
            interests=[
                AnthropicInterestItemOutput(
                    name="Unrelated moisturizer",
                    interest_type=InterestType.INFERRED,
                    confidence=0.95,
                )
            ]
        )
    )
    provider = build_provider(client_mock)

    with pytest.raises(
        InvalidAnthropicInterestExtractionError,
        match="outside reevaluation candidates",
    ):
        provider.extract(
            build_interaction(),
            catalogue_context=build_catalogue_context(),
            candidates=(build_candidate(),),
        )


def test_unknown_catalogue_evidence_is_rejected() -> None:
    client_mock = MagicMock()
    client_mock.messages.parse.return_value = SimpleNamespace(
        parsed_output=AnthropicInterestExtractionOutput(
            interests=[
                AnthropicInterestItemOutput(
                    name="Calming serum",
                    interest_type=InterestType.EXPLICIT,
                    confidence=0.94,
                    catalogue_item_ids=["unknown-item"],
                )
            ]
        )
    )
    provider = build_provider(client_mock)

    with pytest.raises(
        InvalidAnthropicInterestExtractionError,
        match="unknown catalogue evidence",
    ):
        provider.extract(
            build_interaction(),
            catalogue_context=build_catalogue_context(),
        )


def test_missing_parsed_output_is_rejected() -> None:
    client_mock = MagicMock()
    client_mock.messages.parse.return_value = SimpleNamespace(
        parsed_output=None,
    )
    provider = build_provider(client_mock)

    with pytest.raises(
        InvalidAnthropicInterestExtractionError,
        match="Anthropic returned no structured interest extraction",
    ):
        provider.extract(
            build_interaction(),
            catalogue_context=build_catalogue_context(),
        )


def test_cross_client_catalogue_context_is_rejected() -> None:
    client_mock = MagicMock()
    provider = build_provider(client_mock)

    with pytest.raises(
        ValueError,
        match="catalogue context must belong to the interaction client",
    ):
        provider.extract(
            build_interaction(),
            catalogue_context=build_catalogue_context(
                client_id="different-client",
            ),
        )

    client_mock.messages.parse.assert_not_called()


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_output_schema_rejects_invalid_confidence(
    confidence: float,
) -> None:
    with pytest.raises(ValidationError):
        AnthropicInterestItemOutput(
            name="Calming serum",
            interest_type=InterestType.INFERRED,
            confidence=confidence,
        )


@pytest.mark.parametrize(
    ("model", "prompt_version", "max_tokens", "message"),
    [
        (" ", "interest-v1", 512, "model must not be empty"),
        (
            "claude-haiku-4-5-20251001",
            " ",
            512,
            "prompt_version must not be empty",
        ),
        (
            "claude-haiku-4-5-20251001",
            "interest-v1",
            0,
            "max_tokens must be positive",
        ),
    ],
)
def test_invalid_provider_configuration_is_rejected(
    model: str,
    prompt_version: str,
    max_tokens: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        AnthropicInterestExtractionProvider(
            client=cast(Anthropic, MagicMock()),
            model=model,
            prompt_version=prompt_version,
            max_tokens=max_tokens,
        )
