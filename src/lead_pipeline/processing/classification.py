"""Provider-independent classification boundary."""

from typing import Protocol

from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.interactions import InstagramInteraction


class ClassificationProvider(Protocol):
    """Classify one authorized Instagram interaction."""

    def classify(
        self,
        interaction: InstagramInteraction,
    ) -> ClassificationResult:
        """Return one versioned top-level classification result."""

        ...
