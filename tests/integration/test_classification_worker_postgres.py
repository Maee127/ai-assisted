"""PostgreSQL integration test for the classification worker path."""

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from lead_pipeline.application.classify_interaction import ClassifyInteraction
from lead_pipeline.application.extract_interests import ExtractInterests
from lead_pipeline.domain.catalogue import CatalogueContext
from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.enums import (
    ClassificationLabel,
    InterestType,
    ProcessingStatus,
    SourceType,
)
from lead_pipeline.domain.identifiers import InstagramEventId
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.domain.interests import InterestEvidence
from lead_pipeline.persistence.models import (
    CatalogueItemRow,
    ClassificationRow,
    InteractionRow,
    InterestEvidenceRow,
    LeadProfileRow,
    UnresolvedRecordRow,
)
from lead_pipeline.persistence.transactional_classification import (
    TransactionalInteractionClassifier,
)
from lead_pipeline.worker.classification_job import ClassificationJob

CLASSIFIED_AT = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)


def get_test_database_url() -> str:
    """Return the opt-in integration database URL."""

    database_url = os.environ.get("TEST_DATABASE_URL")

    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    return database_url


@dataclass
class StaticProvider:
    """Return one deterministic result without external API access."""

    result: ClassificationResult
    calls: list[InstagramInteraction] = field(default_factory=list)
    catalogue_contexts: list[CatalogueContext] = field(default_factory=list)

    def classify(
        self,
        interaction: InstagramInteraction,
        *,
        catalogue_context: CatalogueContext,
    ) -> ClassificationResult:
        self.calls.append(interaction)
        self.catalogue_contexts.append(catalogue_context)
        return self.result


def build_uncertain_result(
    model_version: str,
) -> ClassificationResult:
    return ClassificationResult(
        label=ClassificationLabel.UNCERTAIN,
        confidence=0.5,
        reason="The available evidence is insufficient.",
        model_name="integration-provider",
        model_version=model_version,
        prompt_version="classification-integration-v1",
    )


def build_sales_result() -> ClassificationResult:
    return ClassificationResult(
        label=ClassificationLabel.SALES_LEAD,
        confidence=0.94,
        reason="The user explicitly asks about a suitable product.",
        model_name="integration-provider",
        model_version="sales-integration",
        prompt_version="classification-integration-v1",
    )


def test_double_uncertainty_is_persisted_and_completed_in_postgres() -> None:
    database_url = get_test_database_url()
    event_id = f"classification-integration-{uuid4()}"
    catalogue_item_id = f"classification-catalogue-{uuid4()}"
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )
    session_factory: sessionmaker[Session] = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )
    primary_provider = StaticProvider(
        result=build_uncertain_result("primary-integration"),
    )
    stronger_provider = StaticProvider(
        result=build_uncertain_result("stronger-integration"),
    )
    classifier = ClassifyInteraction(
        primary_provider=primary_provider,
        stronger_provider=stronger_provider,
        clock=lambda: CLASSIFIED_AT,
    )
    unexpected_interest_provider = UnexpectedInterestProvider()

    @dataclass
    class StaticInterestProvider:
        """Return deterministic interest evidence without external API access."""

        result: tuple[InterestEvidence, ...]
        calls: list[InstagramInteraction] = field(default_factory=list)
        catalogue_contexts: list[CatalogueContext] = field(default_factory=list)
        candidate_batches: list[tuple[InterestEvidence, ...]] = field(
            default_factory=list
        )

    def extract(
        self,
        interaction: InstagramInteraction,
        *,
        catalogue_context: CatalogueContext,
        candidates: tuple[InterestEvidence, ...] = (),
    ) -> tuple[InterestEvidence, ...]:
        self.calls.append(interaction)
        self.catalogue_contexts.append(catalogue_context)
        self.candidate_batches.append(candidates)
        return self.result

    interest_extractor = ExtractInterests(
        primary_provider=unexpected_interest_provider,
        stronger_provider=unexpected_interest_provider,
        inferred_confidence_threshold=0.8,
    )
    runner = TransactionalInteractionClassifier(
        session_factory=session_factory,
        classifier=classifier,
        interest_extractor=interest_extractor,
        clock=lambda: CLASSIFIED_AT,
    )
    job = ClassificationJob(
        session_factory=session_factory,
        runner=runner,
    )

    try:
        with session_factory.begin() as session:
            session.add(
                InteractionRow(
                    event_id=event_id,
                    client_id="client-integration-test",
                    user_id="user-integration-test",
                    media_id="media-integration-test",
                    source_type=SourceType.POST_COMMENT.value,
                    text="Could this product suit my stated concern?",
                    source_timestamp=datetime(
                        2026,
                        8,
                        25,
                        9,
                        58,
                        tzinfo=UTC,
                    ),
                    collected_at=datetime(
                        2026,
                        8,
                        25,
                        9,
                        59,
                        tzinfo=UTC,
                    ),
                    processing_status=ProcessingStatus.RECEIVED.value,
                    username="integration_user",
                )
            )
            session.add(
                CatalogueItemRow(
                    client_id="client-integration-test",
                    catalogue_item_id=catalogue_item_id,
                    name="Calming Skin Serum",
                    category="Serums",
                    description="A product for a stated dry-looking skin concern.",
                )
            )

        result = job.execute(
            InstagramEventId(event_id),
        )

        assert result.outcome.is_unresolved
        assert result.outcome.was_escalated
        assert len(primary_provider.calls) == 1
        assert len(stronger_provider.calls) == 1
        assert len(primary_provider.catalogue_contexts) == 1
        assert len(stronger_provider.catalogue_contexts) == 1

        primary_context = primary_provider.catalogue_contexts[0]
        stronger_context = stronger_provider.catalogue_contexts[0]

        assert primary_context == stronger_context
        assert primary_context.client_id.value == "client-integration-test"
        assert len(primary_context.items) == 1
        assert primary_context.items[0].catalogue_item_id.value == catalogue_item_id
        assert primary_context.items[0].name == "Calming Skin Serum"

        with Session(engine) as session:
            interaction_row = session.get(
                InteractionRow,
                event_id,
            )
            classification_rows = list(
                session.scalars(
                    select(ClassificationRow).where(
                        ClassificationRow.source_event_id == event_id
                    )
                )
            )
            unresolved_row = session.scalar(
                select(UnresolvedRecordRow).where(
                    UnresolvedRecordRow.source_event_id == event_id
                )
            )

            assert interaction_row is not None
            assert interaction_row.processing_status == (
                ProcessingStatus.COMPLETED.value
            )
            assert len(classification_rows) == 2
            assert unresolved_row is not None

            rows_by_model = {row.model_version: row for row in classification_rows}
            primary_row = rows_by_model["primary-integration"]
            stronger_row = rows_by_model["stronger-integration"]

            assert primary_row.label == ClassificationLabel.UNCERTAIN.value
            assert stronger_row.label == ClassificationLabel.UNCERTAIN.value
            assert unresolved_row.primary_classification_id == (
                primary_row.classification_id
            )
            assert unresolved_row.stronger_classification_id == (
                stronger_row.classification_id
            )
            assert result.receipt.unresolved_id == unresolved_row.unresolved_id
    finally:
        with session_factory.begin() as session:
            interaction_row = session.get(
                InteractionRow,
                event_id,
            )
            catalogue_row = session.get(
                CatalogueItemRow,
                ("client-integration-test", catalogue_item_id),
            )

            if catalogue_row is not None:
                session.delete(catalogue_row)

            if interaction_row is not None:
                session.delete(interaction_row)

        engine.dispose()


def test_confirmed_interest_updates_lead_profile_in_postgres() -> None:
    database_url = get_test_database_url()
    event_id = f"interest-integration-{uuid4()}"
    user_id = f"interest-user-{uuid4()}"
    catalogue_item_id = f"interest-catalogue-{uuid4()}"
    client_id = "client-interest-integration"

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )
    session_factory: sessionmaker[Session] = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    primary_provider = StaticProvider(
        result=build_sales_result(),
    )
    stronger_provider = StaticProvider(
        result=build_sales_result(),
    )
    classifier = ClassifyInteraction(
        primary_provider=primary_provider,
        stronger_provider=stronger_provider,
        clock=lambda: CLASSIFIED_AT,
    )

    interest = InterestEvidence(
        name="Calming Skin Serum",
        interest_type=InterestType.EXPLICIT,
        confidence=0.93,
        source_event_id=InstagramEventId(event_id),
        model_name="integration-interest-provider",
        model_version="interest-primary-integration",
        catalogue_evidence=catalogue_item_id,
        prompt_version="interest-integration-v1",
    )
    primary_interest_provider = StaticInterestProvider(
        result=(interest,),
    )
    stronger_interest_provider = StaticInterestProvider(
        result=(),
    )
    interest_extractor = ExtractInterests(
        primary_provider=primary_interest_provider,
        stronger_provider=stronger_interest_provider,
        inferred_confidence_threshold=0.8,
    )
    runner = TransactionalInteractionClassifier(
        session_factory=session_factory,
        classifier=classifier,
        interest_extractor=interest_extractor,
        clock=lambda: CLASSIFIED_AT,
    )
    job = ClassificationJob(
        session_factory=session_factory,
        runner=runner,
    )

    try:
        with session_factory.begin() as session:
            session.add(
                InteractionRow(
                    event_id=event_id,
                    client_id=client_id,
                    user_id=user_id,
                    media_id="interest-media-integration",
                    source_type=SourceType.POST_COMMENT.value,
                    text="Would this calming serum suit my dry-looking skin?",
                    source_timestamp=datetime(
                        2026,
                        8,
                        25,
                        9,
                        58,
                        tzinfo=UTC,
                    ),
                    collected_at=datetime(
                        2026,
                        8,
                        25,
                        9,
                        59,
                        tzinfo=UTC,
                    ),
                    processing_status=ProcessingStatus.RECEIVED.value,
                    username="interest_integration_user",
                )
            )
            session.add(
                CatalogueItemRow(
                    client_id=client_id,
                    catalogue_item_id=catalogue_item_id,
                    name="Calming Skin Serum",
                    category="Serums",
                    description="A calming serum for dry-looking skin.",
                )
            )

        result = job.execute(
            InstagramEventId(event_id),
        )

        assert result.outcome.final_result.label is ClassificationLabel.SALES_LEAD
        assert result.interest_outcome.confirmed_interests == (interest,)
        assert result.interest_outcome.unresolved_interests == ()
        assert result.interest_receipt.lead_id is not None
        assert len(result.interest_receipt.interest_ids) == 1

        assert len(primary_interest_provider.calls) == 1
        assert stronger_interest_provider.calls == []
        assert primary_interest_provider.candidate_batches == [()]
        assert len(primary_interest_provider.catalogue_contexts) == 1

        catalogue_context = primary_interest_provider.catalogue_contexts[0]
        assert catalogue_context.client_id.value == client_id
        assert len(catalogue_context.items) == 1
        assert catalogue_context.items[0].catalogue_item_id.value == catalogue_item_id

        with Session(engine) as session:
            interaction_row = session.get(
                InteractionRow,
                event_id,
            )
            classification_row = session.scalar(
                select(ClassificationRow).where(
                    ClassificationRow.source_event_id == event_id
                )
            )
            lead_row = session.scalar(
                select(LeadProfileRow).where(
                    LeadProfileRow.client_id == client_id,
                    LeadProfileRow.user_id == user_id,
                )
            )
            interest_row = session.scalar(
                select(InterestEvidenceRow).where(
                    InterestEvidenceRow.source_event_id == event_id
                )
            )

            assert interaction_row is not None
            assert interaction_row.processing_status == (
                ProcessingStatus.COMPLETED.value
            )
            assert classification_row is not None
            assert classification_row.label == ClassificationLabel.SALES_LEAD.value

            assert lead_row is not None
            assert lead_row.lead_id == result.interest_receipt.lead_id
            assert lead_row.client_id == client_id
            assert lead_row.user_id == user_id
            assert lead_row.username == "interest_integration_user"

            assert interest_row is not None
            assert interest_row.interest_id in (result.interest_receipt.interest_ids)
            assert interest_row.lead_id == lead_row.lead_id
            assert interest_row.source_event_id == event_id
            assert interest_row.name == "Calming Skin Serum"
            assert interest_row.interest_type == InterestType.EXPLICIT.value
            assert interest_row.confidence == 0.93
            assert interest_row.model_version == "interest-primary-integration"
            assert interest_row.catalogue_evidence == catalogue_item_id
            assert interest_row.prompt_version == "interest-integration-v1"
    finally:
        with session_factory.begin() as session:
            session.execute(
                delete(InterestEvidenceRow).where(
                    InterestEvidenceRow.source_event_id == event_id
                )
            )
            session.execute(
                delete(LeadProfileRow).where(
                    LeadProfileRow.client_id == client_id,
                    LeadProfileRow.user_id == user_id,
                )
            )
            session.execute(
                delete(CatalogueItemRow).where(
                    CatalogueItemRow.client_id == client_id,
                    CatalogueItemRow.catalogue_item_id == catalogue_item_id,
                )
            )
            session.execute(
                delete(InteractionRow).where(InteractionRow.event_id == event_id)
            )

        engine.dispose()


class UnexpectedInterestProvider:
    """Fail if interest extraction runs for a non-sales classification."""

    def extract(
        self,
        interaction: InstagramInteraction,
        *,
        catalogue_context: CatalogueContext,
        candidates: tuple[InterestEvidence, ...] = (),
    ) -> tuple[InterestEvidence, ...]:
        raise AssertionError(
            "interest extraction must not run for an uncertain classification"
        )


@dataclass
class StaticInterestProvider:
    """Return deterministic interest evidence without external API access."""

    result: tuple[InterestEvidence, ...]
    calls: list[InstagramInteraction] = field(default_factory=list)
    catalogue_contexts: list[CatalogueContext] = field(default_factory=list)
    candidate_batches: list[tuple[InterestEvidence, ...]] = field(default_factory=list)

    def extract(
        self,
        interaction: InstagramInteraction,
        *,
        catalogue_context: CatalogueContext,
        candidates: tuple[InterestEvidence, ...] = (),
    ) -> tuple[InterestEvidence, ...]:
        self.calls.append(interaction)
        self.catalogue_contexts.append(catalogue_context)
        self.candidate_batches.append(candidates)

        return self.result
