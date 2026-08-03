"""Domain model for verified erasure requests."""

from dataclasses import dataclass
from datetime import datetime

from lead_pipeline.domain.identifiers import ClientId, InstagramUserId


@dataclass(frozen=True, slots=True)
class ErasureRequest:
    """A verified request to erase data within one client boundary."""

    client_id: ClientId
    user_id: InstagramUserId
    requested_at: datetime
    verified_at: datetime
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.requested_at.tzinfo is None:
            raise ValueError("requested_at must be timezone-aware")

        if self.verified_at.tzinfo is None:
            raise ValueError("verified_at must be timezone-aware")

        if self.completed_at is not None and self.completed_at.tzinfo is None:
            raise ValueError("completed_at must be timezone-aware")

        if self.verified_at < self.requested_at:
            raise ValueError("verified_at must not be before requested_at")

        if self.completed_at is not None and self.completed_at < self.verified_at:
            raise ValueError("completed_at must not be before verified_at")

    @property
    def is_completed(self) -> bool:
        """Return whether the erasure operation has completed."""

        return self.completed_at is not None
