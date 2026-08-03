"""Domain model for client-scoped lead profiles."""

from dataclasses import dataclass

from lead_pipeline.domain.identifiers import ClientId, InstagramUserId
from lead_pipeline.domain.interests import InterestEvidence


@dataclass(frozen=True, slots=True)
class LeadProfile:
    """One evolving sales-lead profile within a single client boundary."""

    client_id: ClientId
    user_id: InstagramUserId
    interests: tuple[InterestEvidence, ...] = ()
    username: str | None = None

    def __post_init__(self) -> None:
        normalized_username = (
            self.username.strip() if self.username is not None else None
        )

        if normalized_username == "":
            normalized_username = None

        object.__setattr__(self, "username", normalized_username)

    def add_interest(self, interest: InterestEvidence) -> "LeadProfile":
        """Return a new profile containing the additional interest evidence."""

        return LeadProfile(
            client_id=self.client_id,
            user_id=self.user_id,
            username=self.username,
            interests=(*self.interests, interest),
        )
