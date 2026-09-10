"""Anthropic adapter for structured interaction classification."""

import json
from dataclasses import dataclass

from anthropic import Anthropic
from pydantic import BaseModel, Field

from lead_pipeline.domain.catalogue import CatalogueContext
from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.enums import ClassificationLabel
from lead_pipeline.domain.interactions import InstagramInteraction

SYSTEM_PROMPT = """You classify English Instagram comments for an authorized
beauty and skin-care business.

The user message is JSON containing:
- comment: the minimized Instagram comment.
- catalogue_context: relevant items retrieved from this client's catalogue.

Catalogue context is supporting evidence only. It may clarify product names,
categories, descriptions, availability-related meaning, or suitability
questions, but it must never determine the final label by itself. If catalogue
context is empty, classify from the comment alone. Never classify a comment as
a sales lead merely because a related catalogue item exists.

Choose exactly one top-level label:

SALES_LEAD:
The user expresses purchase intent or asks about price, availability, shipping,
where to buy, or whether a product suits an explicitly stated need.

CUSTOMER_CARE:
The user reports a complaint, delivery problem, adverse experience, damaged
product, refund issue, or support request.

IRRELEVANT:
The comment has no meaningful sales or customer-care relevance.

SPAM:
The comment is promotional spam, manipulation, repetition, or unrelated
solicitation.

UNCERTAIN:
The available text is genuinely ambiguous or insufficient for a reliable
classification.

Do not infer medical diagnoses. Do not invent context. Do not copy usernames or
quote the complete comment in the reason. Keep the reason short and explain only
the classification evidence."""


class AnthropicClassificationOutput(BaseModel):
    """Schema-constrained classification returned by Anthropic."""

    label: ClassificationLabel
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)


class InvalidAnthropicClassificationError(RuntimeError):
    """Raised when Anthropic returns no usable structured result."""


@dataclass(slots=True)
class AnthropicClassificationProvider:
    """Classify interactions through Anthropic structured outputs."""

    client: Anthropic
    model: str
    prompt_version: str
    max_tokens: int = 256

    def __post_init__(self) -> None:
        self.model = self.model.strip()
        self.prompt_version = self.prompt_version.strip()

        if not self.model:
            raise ValueError("model must not be empty")

        if not self.prompt_version:
            raise ValueError("prompt_version must not be empty")

        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

    def classify(
        self,
        interaction: InstagramInteraction,
        *,
        catalogue_context: CatalogueContext,
    ) -> ClassificationResult:
        """Classify one minimized interaction with grounded context."""

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
            output_format=AnthropicClassificationOutput,
        )
        output = response.parsed_output

        if output is None:
            raise InvalidAnthropicClassificationError(
                "Anthropic returned no structured classification"
            )

        return ClassificationResult(
            label=output.label,
            confidence=output.confidence,
            reason=output.reason,
            model_name="anthropic",
            model_version=self.model,
            prompt_version=self.prompt_version,
        )
