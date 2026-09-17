"""Production composition root for classification workers."""

from dataclasses import dataclass
from datetime import UTC, datetime

from anthropic import Anthropic
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from lead_pipeline.application.classify_interaction import ClassifyInteraction
from lead_pipeline.application.extract_interests import ExtractInterests
from lead_pipeline.persistence.config import get_database_url
from lead_pipeline.persistence.transactional_classification import (
    TransactionalInteractionClassifier,
)
from lead_pipeline.processing.anthropic_classifier import (
    AnthropicClassificationProvider,
)
from lead_pipeline.processing.anthropic_interest_extractor import (
    AnthropicInterestExtractionProvider,
)
from lead_pipeline.processing.config import (
    get_anthropic_api_key,
    get_classification_max_tokens,
    get_classification_prompt_version,
    get_inferred_interest_confidence_threshold,
    get_interest_max_tokens,
    get_interest_prompt_version,
    get_primary_classifier_model,
    get_primary_interest_extractor_model,
    get_sales_lead_confidence_threshold,
    get_stronger_classifier_model,
    get_stronger_interest_extractor_model,
)
from lead_pipeline.worker.classification_job import ClassificationJob


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""

    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ClassificationRuntime:
    """Configured resources required by a classification worker."""

    engine: Engine
    session_factory: sessionmaker[Session]
    runner: TransactionalInteractionClassifier
    job: ClassificationJob


def create_classification_runtime() -> ClassificationRuntime:
    """Compose the configured classification worker runtime."""

    primary_interest_model = get_primary_interest_extractor_model()
    stronger_interest_model = get_stronger_interest_extractor_model()
    interest_prompt_version = get_interest_prompt_version()
    interest_max_tokens = get_interest_max_tokens()
    inferred_interest_threshold = get_inferred_interest_confidence_threshold()
    database_url = get_database_url()
    api_key = get_anthropic_api_key()
    primary_model = get_primary_classifier_model()
    stronger_model = get_stronger_classifier_model()
    prompt_version = get_classification_prompt_version()
    max_tokens = get_classification_max_tokens()
    sales_lead_threshold = get_sales_lead_confidence_threshold()

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )
    session_factory: sessionmaker[Session] = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )
    client = Anthropic(
        api_key=api_key,
    )
    primary_provider = AnthropicClassificationProvider(
        client=client,
        model=primary_model,
        prompt_version=prompt_version,
        max_tokens=max_tokens,
    )
    stronger_provider = AnthropicClassificationProvider(
        client=client,
        model=stronger_model,
        prompt_version=prompt_version,
        max_tokens=max_tokens,
    )
    classifier = ClassifyInteraction(
        primary_provider=primary_provider,
        stronger_provider=stronger_provider,
        clock=_utc_now,
        sales_lead_confidence_threshold=sales_lead_threshold,
    )
    primary_interest_provider = AnthropicInterestExtractionProvider(
        client=client,
        model=primary_interest_model,
        prompt_version=interest_prompt_version,
        max_tokens=interest_max_tokens,
    )
    stronger_interest_provider = AnthropicInterestExtractionProvider(
        client=client,
        model=stronger_interest_model,
        prompt_version=interest_prompt_version,
        max_tokens=interest_max_tokens,
    )
    interest_extractor = ExtractInterests(
        primary_provider=primary_interest_provider,
        stronger_provider=stronger_interest_provider,
        inferred_confidence_threshold=inferred_interest_threshold,
    )
    runner = TransactionalInteractionClassifier(
        session_factory=session_factory,
        classifier=classifier,
        interest_extractor=interest_extractor,
        clock=_utc_now,
    )
    job = ClassificationJob(
        session_factory=session_factory,
        runner=runner,
    )

    return ClassificationRuntime(
        engine=engine,
        session_factory=session_factory,
        runner=runner,
        job=job,
    )
