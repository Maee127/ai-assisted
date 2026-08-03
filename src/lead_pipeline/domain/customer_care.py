"""Domain model for customer-care cases."""

from dataclasses import dataclass
from datetime import datetime

from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramUserId,
)


@dataclass(frozen=True, slots=True)
class CustomerCareCase:
    """A customer-care issue kept separate from sales-lead data."""

    client_id: ClientId
    user_id: InstagramUserId
    source_event_id: InstagramEventId
    summary: str
    created_at: datetime
    username: str | None = None

    def __post_init__(self) -> None:
        normalized_summary = self.summary.strip()

        if not normalized_summary:
            raise ValueError("summary must not be empty")

        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")

        normalized_username = (
            self.username.strip() if self.username is not None else None
        )

        if normalized_username == "":
            normalized_username = None

        object.__setattr__(self, "summary", normalized_summary)
        object.__setattr__(self, "username", normalized_username)
