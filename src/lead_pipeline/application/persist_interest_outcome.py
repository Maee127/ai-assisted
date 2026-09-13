"""Application orchestration for persisting confirmed interests."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from lead_pipeline.application.extract_interests import (
    InterestExtractionOutcome,
)
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.persistence.repositories import (
    InterestEvidenceRepository,
    LeadProfileRepository,
)


@dataclass(frozen=True, slots=True)
class InterestPersistenceReceipt:
    """Identifiers created while persisting confirmed interests."""

    lead_id: str | None = None
    interest_ids: tuple[str, ...] = ()


@dataclass(slots=True)
class PersistInterestExtractionOutcome:
    """Persist only confirmed interests into one lead profile."""

    lead_profile_repository: LeadProfileRepository
    interest_repository: InterestEvidenceRepository
    clock: Callable[[], datetime]

    def execute(
        self,
        *,
        interaction: InstagramInteraction,
        outcome: InterestExtractionOutcome,
    ) -> InterestPersistenceReceipt:
        """Stage confirmed profile and interest rows."""

        if not outcome.confirmed_interests:
            return InterestPersistenceReceipt()

        recorded_at = self.clock()
        lead_id = self.lead_profile_repository.get_or_create(
            client_id=interaction.client_id,
            user_id=interaction.user_id,
            username=interaction.username,
            updated_at=recorded_at,
        )
        interest_ids = tuple(
            self.interest_repository.add(
                lead_id=lead_id,
                interest=interest,
                created_at=recorded_at,
            )
            for interest in outcome.confirmed_interests
        )

        return InterestPersistenceReceipt(
            lead_id=lead_id,
            interest_ids=interest_ids,
        )
