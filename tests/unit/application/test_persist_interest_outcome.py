"""Tests for persisting confirmed interest-extraction outcomes."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from lead_pipeline.application.extract_interests import (
    InterestExtractionOutcome,
)
from lead_pipeline.application.persist_interest_outcome import (
    PersistInterestExtractionOutcome,
)
from lead_pipeline.domain.enums import (
    InterestType,
    ProcessingStatus,
    SourceType,
)
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.domain.interests import InterestEvidence

RECORDED_AT = datetime(2026, 9, 13, 17, 0, tzinfo=UTC)


@dataclass(slots=True)
class RecordingLeadProfileRepository:
    """Record profile persistence calls."""

    lead_id: str = "lead-1"
    calls: list[dict[str, object]] = field(default_factory=list)

    def get_or_create(
        self,
        *,
        client_id: ClientId,
        user_id: InstagramUserId,
        username: str | None,
        updated_at: datetime,
    ) -> str:
        self.calls.append(
            {
                "client_id": client_id,
                "user_id": user_id,
                "username": username,
                "updated_at": updated_at,
            }
        )
        return self.lead_id


@dataclass(slots=True)
class RecordingInterestRepository:
    """Record confirmed interest persistence calls."""

    identifiers: tuple[str, ...] = ("interest-1", "interest-2")
    calls: list[dict[str, object]] = field(default_factory=list)

    def add(
        self,
        *,
        lead_id: str,
        interest: InterestEvidence,
        created_at: datetime,
    ) -> str:
        self.calls.append(
            {
                "lead_id": lead_id,
                "interest": interest,
                "created_at": created_at,
            }
        )
        return self.identifiers[len(self.calls) - 1]


def build_interaction() -> InstagramInteraction:
    return InstagramInteraction(
        event_id=InstagramEventId("event-1"),
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        media_id=InstagramMediaId("media-1"),
        source_type=SourceType.POST_COMMENT,
        text="I want a serum and moisturizer.",
        source_timestamp=datetime(2026, 9, 13, 16, 58, tzinfo=UTC),
        collected_at=datetime(2026, 9, 13, 16, 59, tzinfo=UTC),
        status=ProcessingStatus.RECEIVED,
        username="beauty_user",
    )


def build_interest(
    name: str,
    *,
    confidence: float = 0.9,
) -> InterestEvidence:
    return InterestEvidence(
        name=name,
        interest_type=InterestType.INFERRED,
        confidence=confidence,
        source_event_id=InstagramEventId("event-1"),
        model_name="anthropic",
        model_version="claude-sonnet-5",
        catalogue_evidence='["item-1"]',
        prompt_version="interest-v1",
    )


def build_use_case() -> tuple[
    PersistInterestExtractionOutcome,
    RecordingLeadProfileRepository,
    RecordingInterestRepository,
]:
    lead_repository = RecordingLeadProfileRepository()
    interest_repository = RecordingInterestRepository()
    use_case = PersistInterestExtractionOutcome(
        lead_profile_repository=lead_repository,
        interest_repository=interest_repository,
        clock=lambda: RECORDED_AT,
    )
    return use_case, lead_repository, interest_repository


def test_no_confirmed_interests_create_no_profile() -> None:
    use_case, lead_repository, interest_repository = build_use_case()
    unresolved = build_interest(
        "Possible serum",
        confidence=0.6,
    )
    outcome = InterestExtractionOutcome(
        primary_interests=(unresolved,),
        stronger_interests=(unresolved,),
        confirmed_interests=(),
        unresolved_interests=(unresolved,),
        escalated=True,
    )

    receipt = use_case.execute(
        interaction=build_interaction(),
        outcome=outcome,
    )

    assert receipt.lead_id is None
    assert receipt.interest_ids == ()
    assert lead_repository.calls == []
    assert interest_repository.calls == []


def test_confirmed_interests_create_one_client_scoped_profile() -> None:
    use_case, lead_repository, _ = build_use_case()
    interest = build_interest("Calming serum")
    outcome = InterestExtractionOutcome(
        primary_interests=(interest,),
        confirmed_interests=(interest,),
    )

    receipt = use_case.execute(
        interaction=build_interaction(),
        outcome=outcome,
    )

    assert receipt.lead_id == "lead-1"
    assert lead_repository.calls == [
        {
            "client_id": ClientId("client-1"),
            "user_id": InstagramUserId("user-1"),
            "username": "beauty_user",
            "updated_at": RECORDED_AT,
        }
    ]


def test_all_confirmed_interests_are_persisted_in_order() -> None:
    use_case, _, interest_repository = build_use_case()
    serum = build_interest("Calming serum")
    moisturizer = build_interest("Moisturizer")
    outcome = InterestExtractionOutcome(
        primary_interests=(serum, moisturizer),
        confirmed_interests=(serum, moisturizer),
    )

    receipt = use_case.execute(
        interaction=build_interaction(),
        outcome=outcome,
    )

    assert receipt.interest_ids == (
        "interest-1",
        "interest-2",
    )
    assert interest_repository.calls == [
        {
            "lead_id": "lead-1",
            "interest": serum,
            "created_at": RECORDED_AT,
        },
        {
            "lead_id": "lead-1",
            "interest": moisturizer,
            "created_at": RECORDED_AT,
        },
    ]


def test_unresolved_interests_are_never_persisted() -> None:
    use_case, _, interest_repository = build_use_case()
    confirmed = build_interest("Calming serum")
    unresolved = build_interest(
        "Possible moisturizer",
        confidence=0.6,
    )
    outcome = InterestExtractionOutcome(
        primary_interests=(confirmed, unresolved),
        stronger_interests=(unresolved,),
        confirmed_interests=(confirmed,),
        unresolved_interests=(unresolved,),
        escalated=True,
    )

    receipt = use_case.execute(
        interaction=build_interaction(),
        outcome=outcome,
    )

    assert receipt.interest_ids == ("interest-1",)
    assert len(interest_repository.calls) == 1
    assert interest_repository.calls[0]["interest"] == confirmed
