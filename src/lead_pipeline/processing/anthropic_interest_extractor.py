"""Anthropic adapter for structured interest extraction."""

import json
from dataclasses import dataclass

from anthropic import Anthropic
from pydantic import BaseModel, Field

from lead_pipeline.domain.catalogue import CatalogueContext
from lead_pipeline.domain.enums import InterestType
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.domain.interests import InterestEvidence

SYSTEM_PROMPT = """You extract beauty- and skin-care-related interests from
English Instagram comments belonging to an authorized business account.

The user message is JSON containing:
- comment: the minimized Instagram comment.
- catalogue_context: relevant items from this client's catalogue.
- candidates: low-confidence inferred interests requiring reevaluation.

When candidates is empty, extract interests from the comment. When candidates
is not empty, reevaluate only those candidates and do not introduce new
interests. Return an empty interests list when no candidate remains supported.

Permitted evidence includes:
- Explicit product or product-category interests.
- Reasonably inferred product interests.
- Skin concerns only when explicitly stated by the user.
- Preferences or budget signals expressed in the comment.

Use EXPLICIT only when the interest or concern is directly expressed. Use
INFERRED only when the inference is reasonable and supported by the comment.

Never infer a medical diagnosis, disease, disorder, allergy, or clinical
condition. For example, "my skin feels dry" may support an explicitly stated
dry-skin concern, but it must not become a medical diagnosis.

Catalogue context is supporting evidence only. Never invent catalogue items.
Only return catalogue_item_ids that appear in catalogue_context. Do not include
usernames, user IDs, client IDs, or the complete source comment in output."""


class AnthropicInterestItemOutput(BaseModel):
    """One structured interest returned by Anthropic."""

    name: str = Field(min_length=1, max_length=255)
    interest_type: InterestType
    confidence: float = Field(ge=0.0, le=1.0)
    catalogue_item_ids: list[str] = Field(
        default_factory=list,
        max_length=5,
    )


class AnthropicInterestExtractionOutput(BaseModel):
    """Complete structured interest-extraction response."""

    interests: list[AnthropicInterestItemOutput] = Field(
        default_factory=list,
        max_length=10,
    )


class InvalidAnthropicInterestExtractionError(RuntimeError):
    """Raised when Anthropic returns unusable interest evidence."""


@dataclass(slots=True)
class AnthropicInterestExtractionProvider:
    """Extract structured interest evidence through Anthropic."""

    client: Anthropic
    model: str
    prompt_version: str
    max_tokens: int = 512

    def __post_init__(self) -> None:
        self.model = self.model.strip()
        self.prompt_version = self.prompt_version.strip()

        if not self.model:
            raise ValueError("model must not be empty")

        if not self.prompt_version:
            raise ValueError("prompt_version must not be empty")

        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

    def extract(
        self,
        interaction: InstagramInteraction,
        *,
        catalogue_context: CatalogueContext,
        candidates: tuple[InterestEvidence, ...] = (),
    ) -> tuple[InterestEvidence, ...]:
        """Extract interests or reevaluate supplied inferred candidates."""

        if catalogue_context.client_id != interaction.client_id:
            raise ValueError("catalogue context must belong to the interaction client")

        content = json.dumps(
            {
                "comment": interaction.text,
                "catalogue_context": [
                    {
                        "catalogue_item_id": item.catalogue_item_id.value,
                        "name": item.name,
                        "category": item.category,
                        "description": item.description,
                    }
                    for item in catalogue_context.items
                ],
                "candidates": [
                    {
                        "name": candidate.name,
                        "interest_type": candidate.interest_type.value,
                        "confidence": candidate.confidence,
                        "catalogue_evidence": candidate.catalogue_evidence,
                    }
                    for candidate in candidates
                ],
            },
            ensure_ascii=True,
            separators=(",", ":"),
        )

        response = self.client.messages.parse(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            output_format=AnthropicInterestExtractionOutput,
        )
        output = response.parsed_output

        if output is None:
            raise InvalidAnthropicInterestExtractionError(
                "Anthropic returned no structured interest extraction"
            )

        allowed_catalogue_ids = {
            item.catalogue_item_id.value for item in catalogue_context.items
        }
        candidate_keys = {
            (
                candidate.name.casefold(),
                candidate.interest_type,
            )
            for candidate in candidates
        }

        interests: list[InterestEvidence] = []

        for item in output.interests:
            item_key = (
                item.name.strip().casefold(),
                item.interest_type,
            )

            if candidates and item_key not in candidate_keys:
                raise InvalidAnthropicInterestExtractionError(
                    "Anthropic returned an interest outside reevaluation candidates"
                )

            catalogue_item_ids: list[str] = []

            for raw_item_id in item.catalogue_item_ids:
                catalogue_item_id = raw_item_id.strip()

                if (
                    not catalogue_item_id
                    or catalogue_item_id not in allowed_catalogue_ids
                ):
                    raise InvalidAnthropicInterestExtractionError(
                        "Anthropic returned unknown catalogue evidence"
                    )

                if catalogue_item_id not in catalogue_item_ids:
                    catalogue_item_ids.append(catalogue_item_id)

            catalogue_evidence = (
                json.dumps(
                    catalogue_item_ids,
                    ensure_ascii=True,
                    separators=(",", ":"),
                )
                if catalogue_item_ids
                else None
            )

            interests.append(
                InterestEvidence(
                    name=item.name,
                    interest_type=item.interest_type,
                    confidence=item.confidence,
                    source_event_id=interaction.event_id,
                    model_name="anthropic",
                    model_version=self.model,
                    catalogue_evidence=catalogue_evidence,
                    prompt_version=self.prompt_version,
                )
            )

        return tuple(interests)
