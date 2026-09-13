"""Provider-independent interest-extraction boundary."""

from typing import Protocol

from lead_pipeline.domain.catalogue import CatalogueContext
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.domain.interests import InterestEvidence


class InterestExtractionProvider(Protocol):
    """Extract beauty-related interests from one sales interaction."""

    def extract(
        self,
        interaction: InstagramInteraction,
        *,
        catalogue_context: CatalogueContext,
        candidates: tuple[InterestEvidence, ...] = (),
    ) -> tuple[InterestEvidence, ...]:
        """Extract interests or reevaluate the supplied candidates."""

        raise NotImplementedError
