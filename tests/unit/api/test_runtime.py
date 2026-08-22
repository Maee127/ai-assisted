"""Tests for production webhook application composition."""

from unittest.mock import Mock, patch

import pytest
from flask import Flask
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from lead_pipeline.api.runtime import create_app


def configure_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@db:5432/lead_pipeline",
    )
    monkeypatch.setenv(
        "META_APP_SECRET",
        "app-secret",
    )
    monkeypatch.setenv(
        "WEBHOOK_VERIFY_TOKEN",
        "verify-secret",
    )
    monkeypatch.setenv(
        "IG_BUSINESS_ACCOUNT_ID",
        "business-1",
    )
    monkeypatch.setenv(
        "MAX_WEBHOOK_PAYLOAD_BYTES",
        "4096",
    )


def test_create_app_composes_configured_webhook_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_environment(monkeypatch)
    engine = Mock(spec=Engine)
    configured_session_factory = Mock(spec=sessionmaker[Session])

    with (
        patch(
            "lead_pipeline.api.runtime.create_engine",
            return_value=engine,
        ) as create_engine_mock,
        patch(
            "lead_pipeline.api.runtime.sessionmaker",
            return_value=configured_session_factory,
        ) as sessionmaker_mock,
    ):
        app = create_app()

    assert isinstance(app, Flask)
    create_engine_mock.assert_called_once_with(
        "postgresql+psycopg://postgres:postgres@db:5432/lead_pipeline",
        pool_pre_ping=True,
    )
    sessionmaker_mock.assert_called_once_with(
        bind=engine,
        expire_on_commit=False,
    )
    assert app.extensions["sqlalchemy_engine"] is engine
    assert app.extensions["sqlalchemy_session_factory"] is configured_session_factory


def test_composed_app_serves_callback_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_environment(monkeypatch)

    with (
        patch("lead_pipeline.api.runtime.create_engine"),
        patch("lead_pipeline.api.runtime.sessionmaker"),
    ):
        app = create_app()

    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get(
        "/webhook",
        query_string={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-secret",
            "hub.challenge": "challenge-123",
        },
    )

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "challenge-123"
