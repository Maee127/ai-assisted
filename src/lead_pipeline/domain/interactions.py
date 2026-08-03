"""Domain model for authorized Instagram interactions."""

from dataclasses import dataclass
from datetime import datetime

from lead_pipeline.domain.enums import ProcessingStatus, SourceType
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)


@dataclass(frozen=True, slots=True)
class InstagramInteraction:
    """A minimal authorized Instagram comment or mention."""

    event_id: InstagramEventId
    client_id: ClientId
    user_id: InstagramUserId
    media_id: InstagramMediaId
    source_type: SourceType
    text: str
    source_timestamp: datetime
    collected_at: datetime
    status: ProcessingStatus = ProcessingStatus.RECEIVED
    username: str | None = None

    def __post_init__(self) -> None:
        normalized_text = self.text.strip()

        if not normalized_text:
            raise ValueError("text must not be empty")

        if self.source_timestamp.tzinfo is None:
            raise ValueError("source_timestamp must be timezone-aware")

        if self.collected_at.tzinfo is None:
            raise ValueError("collected_at must be timezone-aware")

        normalized_username = (
            self.username.strip() if self.username is not None else None
        )

        if normalized_username == "":
            normalized_username = None

        object.__setattr__(self, "text", normalized_text)
        object.__setattr__(self, "username", normalized_username)
