"""Tests for interest extraction and stronger-model escalation."""

from dataclasses import dataclass, field

import pytest

from lead_pipeline.application.extract_interests import ExtractInterests
from lead_pipeline.domain.catalogue import CatalogueContext
from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.enums import (
    ClassificationLabel,
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


@dataclass(slots=True)
class RecordingInterestProvider:
    """Record extraction calls and return configured interests."""

    interests: tuple[InterestEvidence, ...]
    calls: list[tuple[InterestEvidence, ...]] = field(default_factory=list)

    def extract(
        self,
        interaction: InstagramInteraction,
        *,
        catalogue_context: CatalogueContext,
        candidates: tuple[InterestEvidence, ...] = (),
    ) -> tuple[InterestEvidence, ...]:
        self.calls.append(candidates)
        return self.interests


def build_interaction() -> InstagramInteraction:
    return InstagramInteraction(
        event_id=InstagramEventId("event-1"),
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        media_id=InstagramMediaId("media-1"),
        source_type=SourceType.POST_COMMENT,
        text="I need a serum for my dry-looking skin.",
        source_timestamp=None,
        collected_at=None,
        status=ProcessingStatus.RECEIVED,
    )


def build_classification(
    label: ClassificationLabel = ClassificationLabel.SALES_LEAD,
) -> ClassificationResult:
    return ClassificationResult(
        label=label,
        confidence=0.95,
        reason="Purchase interest.",
        model_name="classifier",
        model_version="classifier-v1",
    )


def build_interest(
    *,
    interest_type: InterestType,
    confidence: float,
    source_event_id: str = "event-1",
    model_version: str = "primary-v1",
) -> InterestEvidence:
    return InterestEvidence(
        name="Calming serum",
        interest_type=interest_type,
        confidence=confidence,
        source_event_id=InstagramEventId(source_event_id),
        model_name="interest-extractor",
        model_version=model_version,
        prompt_version="interest-v1",
        catalogue_evidence="catalogue-item-1",
    )


def build_use_case(
    *,
    primary: tuple[InterestEvidence, ...],
    stronger: tuple[InterestEvidence, ...] = (),
    threshold: float = 0.8,
) -> tuple[
    ExtractInterests,
    RecordingInterestProvider,
    RecordingInterestProvider,
]:
    primary_provider = RecordingInterestProvider(primary)
    stronger_provider = RecordingInterestProvider(stronger)
    use_case = ExtractInterests(
        primary_provider=primary_provider,
        stronger_provider=stronger_provider,
        inferred_confidence_threshold=threshold,
    )
    return use_case, primary_provider, stronger_provider


def test_non_sales_interaction_is_not_extracted() -> None:
    use_case, primary_provider, stronger_provider = build_use_case(
        primary=(
            build_interest(
                interest_type=InterestType.EXPLICIT,
                confidence=0.9,
            ),
        ),
    )

    outcome = use_case.execute(
        build_interaction(),
        classification=build_classification(
            ClassificationLabel.CUSTOMER_CARE,
        ),
    )

    assert outcome.confirmed_interests == ()
    assert primary_provider.calls == []
    assert stronger_provider.calls == []


def test_explicit_interest_is_confirmed_without_escalation() -> None:
    interest = build_interest(
        interest_type=InterestType.EXPLICIT,
        confidence=0.7,
    )
    use_case, primary_provider, stronger_provider = build_use_case(
        primary=(interest,),
    )

    outcome = use_case.execute(
        build_interaction(),
        classification=build_classification(),
    )

    assert outcome.confirmed_interests == (interest,)
    assert primary_provider.calls == [()]
    assert stronger_provider.calls == []
    assert not outcome.was_escalated


def test_high_confidence_inferred_interest_is_confirmed() -> None:
    interest = build_interest(
        interest_type=InterestType.INFERRED,
        confidence=0.8,
    )
    use_case, _, stronger_provider = build_use_case(
        primary=(interest,),
    )

    outcome = use_case.execute(
        build_interaction(),
        classification=build_classification(),
    )

    assert outcome.confirmed_interests == (interest,)
    assert stronger_provider.calls == []


def test_low_confidence_inferred_interest_is_escalated() -> None:
    primary_interest = build_interest(
        interest_type=InterestType.INFERRED,
        confidence=0.6,
    )
    stronger_interest = build_interest(
        interest_type=InterestType.INFERRED,
        confidence=0.9,
        model_version="stronger-v1",
    )
    use_case, _, stronger_provider = build_use_case(
        primary=(primary_interest,),
        stronger=(stronger_interest,),
    )

    outcome = use_case.execute(
        build_interaction(),
        classification=build_classification(),
    )

    assert stronger_provider.calls == [(primary_interest,)]
    assert outcome.confirmed_interests == (stronger_interest,)
    assert outcome.unresolved_interests == ()
    assert outcome.was_escalated


def test_unresolved_inferred_interest_stays_unconfirmed() -> None:
    primary_interest = build_interest(
        interest_type=InterestType.INFERRED,
        confidence=0.6,
    )
    stronger_interest = build_interest(
        interest_type=InterestType.INFERRED,
        confidence=0.7,
        model_version="stronger-v1",
    )
    use_case, _, _ = build_use_case(
        primary=(primary_interest,),
        stronger=(stronger_interest,),
    )

    outcome = use_case.execute(
        build_interaction(),
        classification=build_classification(),
    )

    assert outcome.confirmed_interests == ()
    assert outcome.unresolved_interests == (stronger_interest,)


def test_empty_stronger_result_rejects_candidate() -> None:
    primary_interest = build_interest(
        interest_type=InterestType.INFERRED,
        confidence=0.6,
    )
    use_case, _, _ = build_use_case(
        primary=(primary_interest,),
    )

    outcome = use_case.execute(
        build_interaction(),
        classification=build_classification(),
    )

    assert outcome.confirmed_interests == ()
    assert outcome.unresolved_interests == ()
    assert outcome.was_escalated is False


def test_catalogue_context_must_match_client() -> None:
    use_case, _, _ = build_use_case(primary=())

    with pytest.raises(
        ValueError,
        match="catalogue context must belong to the interaction client",
    ):
        use_case.execute(
            build_interaction(),
            classification=build_classification(),
            catalogue_context=CatalogueContext(
                client_id=ClientId("another-client"),
            ),
        )


def test_interest_must_reference_source_event() -> None:
    use_case, _, _ = build_use_case(
        primary=(
            build_interest(
                interest_type=InterestType.EXPLICIT,
                confidence=0.9,
                source_event_id="another-event",
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="interest evidence must reference the interaction event",
    ):
        use_case.execute(
            build_interaction(),
            classification=build_classification(),
        )


@pytest.mark.parametrize("threshold", [-0.01, 1.01])
def test_invalid_threshold_is_rejected(threshold: float) -> None:
    with pytest.raises(
        ValueError,
        match="inferred_confidence_threshold must be between 0.0 and 1.0",
    ):
        build_use_case(
            primary=(),
            threshold=threshold,
        )
