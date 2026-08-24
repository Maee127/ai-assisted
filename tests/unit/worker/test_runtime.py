"""Tests for classification worker runtime composition."""

from unittest.mock import Mock, patch

import pytest
from anthropic import Anthropic
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from lead_pipeline.processing.anthropic_classifier import (
    AnthropicClassificationProvider,
)
from lead_pipeline.worker.classification_job import ClassificationJob
from lead_pipeline.worker.runtime import create_classification_runtime


def configure_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@db:5432/lead_pipeline",
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    monkeypatch.setenv("PRIMARY_CLASSIFIER_MODEL", "primary-model")
    monkeypatch.setenv("STRONGER_CLASSIFIER_MODEL", "stronger-model")
    monkeypatch.setenv(
        "CLASSIFICATION_PROMPT_VERSION",
        "classification-test-v1",
    )
    monkeypatch.setenv("CLASSIFICATION_MAX_TOKENS", "321")


def test_create_runtime_composes_configured_classification_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_environment(monkeypatch)
    engine = Mock(spec=Engine)
    configured_session_factory = Mock(spec=sessionmaker[Session])
    anthropic_client = Mock(spec=Anthropic)

    with (
        patch(
            "lead_pipeline.worker.runtime.create_engine",
            return_value=engine,
        ) as create_engine_mock,
        patch(
            "lead_pipeline.worker.runtime.sessionmaker",
            return_value=configured_session_factory,
        ) as sessionmaker_mock,
        patch(
            "lead_pipeline.worker.runtime.Anthropic",
            return_value=anthropic_client,
        ) as anthropic_mock,
    ):
        runtime = create_classification_runtime()

    create_engine_mock.assert_called_once_with(
        "postgresql+psycopg://postgres:postgres@db:5432/lead_pipeline",
        pool_pre_ping=True,
    )
    sessionmaker_mock.assert_called_once_with(
        bind=engine,
        expire_on_commit=False,
    )
    anthropic_mock.assert_called_once_with(
        api_key="anthropic-secret",
    )

    assert runtime.engine is engine
    assert runtime.session_factory is configured_session_factory
    assert runtime.runner.session_factory is configured_session_factory
    assert isinstance(runtime.job, ClassificationJob)
    assert runtime.job.session_factory is configured_session_factory
    assert runtime.job.runner is runtime.runner

    primary_provider = runtime.runner.classifier.primary_provider
    stronger_provider = runtime.runner.classifier.stronger_provider

    assert isinstance(
        primary_provider,
        AnthropicClassificationProvider,
    )
    assert isinstance(
        stronger_provider,
        AnthropicClassificationProvider,
    )
    assert primary_provider.client is anthropic_client
    assert stronger_provider.client is anthropic_client
    assert primary_provider.model == "primary-model"
    assert stronger_provider.model == "stronger-model"
    assert primary_provider.prompt_version == "classification-test-v1"
    assert stronger_provider.prompt_version == "classification-test-v1"
    assert primary_provider.max_tokens == 321
    assert stronger_provider.max_tokens == 321
