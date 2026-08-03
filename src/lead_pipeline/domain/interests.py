"""Domain model for beauty-related interests."""

from dataclasses import dataclass

from lead_pipeline.domain.enums import InterestType
from lead_pipeline.domain.identifiers import InstagramEventId


@dataclass(frozen=True, slots=True)
class InterestEvidence:
    """Versioned evidence for one beauty-related interest."""

    name: str
    interest_type: InterestType
    confidence: float
    source_event_id: InstagramEventId
    model_name: str
    model_version: str
    catalogue_evidence: str | None = None
    prompt_version: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        normalized_name = self.name.strip()
        normalized_model_name = self.model_name.strip()
        normalized_model_version = self.model_version.strip()
        normalized_catalogue_evidence = (
            self.catalogue_evidence.strip()
            if self.catalogue_evidence is not None
            else None
        )
        normalized_prompt_version = (
            self.prompt_version.strip() if self.prompt_version is not None else None
        )

        if not normalized_name:
            raise ValueError("name must not be empty")

        if not normalized_model_name:
            raise ValueError("model_name must not be empty")

        if not normalized_model_version:
            raise ValueError("model_version must not be empty")

        if normalized_catalogue_evidence == "":
            normalized_catalogue_evidence = None

        if normalized_prompt_version == "":
            normalized_prompt_version = None

        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "model_name", normalized_model_name)
        object.__setattr__(self, "model_version", normalized_model_version)
        object.__setattr__(
            self,
            "catalogue_evidence",
            normalized_catalogue_evidence,
        )
        object.__setattr__(
            self,
            "prompt_version",
            normalized_prompt_version,
        )
