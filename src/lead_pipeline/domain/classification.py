"""Domain model for classification results."""

from dataclasses import dataclass

from lead_pipeline.domain.enums import ClassificationLabel


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Versioned and explainable classification output."""

    label: ClassificationLabel
    confidence: float
    reason: str
    model_name: str
    model_version: str
    prompt_version: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        normalized_reason = self.reason.strip()
        normalized_model_name = self.model_name.strip()
        normalized_model_version = self.model_version.strip()
        normalized_prompt_version = (
            self.prompt_version.strip() if self.prompt_version is not None else None
        )

        if not normalized_reason:
            raise ValueError("reason must not be empty")

        if not normalized_model_name:
            raise ValueError("model_name must not be empty")

        if not normalized_model_version:
            raise ValueError("model_version must not be empty")

        if normalized_prompt_version == "":
            normalized_prompt_version = None

        object.__setattr__(self, "reason", normalized_reason)
        object.__setattr__(self, "model_name", normalized_model_name)
        object.__setattr__(self, "model_version", normalized_model_version)
        object.__setattr__(
            self,
            "prompt_version",
            normalized_prompt_version,
        )
