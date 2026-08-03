"""Domain model for unresolved classification records."""

from dataclasses import dataclass
from datetime import datetime

from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramUserId,
)


@dataclass(frozen=True, slots=True)
class UnresolvedRecord:
    """A record that remains uncertain after stronger-model evaluation."""

    client_id: ClientId
    user_id: InstagramUserId
    source_event_id: InstagramEventId
    primary_result: ClassificationResult
    stronger_result: ClassificationResult
    created_at: datetime

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
