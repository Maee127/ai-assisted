"""Production composition root for the webhook API."""

from datetime import UTC, datetime

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from lead_pipeline.api.transactional_webhook_ingestor import (
    TransactionalMetaWebhookIngestor,
)
from lead_pipeline.api.webhook_routes import create_webhook_app
from lead_pipeline.domain.identifiers import ClientId
from lead_pipeline.ingestion.config import (
    get_instagram_business_account_id,
    get_max_webhook_payload_bytes,
    get_meta_app_secret,
    get_webhook_verify_token,
)
from lead_pipeline.persistence.config import get_database_url


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""

    return datetime.now(UTC)


def create_app() -> Flask:
    """Create the configured production Flask application."""

    database_url = get_database_url()
    app_secret = get_meta_app_secret()
    verify_token = get_webhook_verify_token()
    business_account_id = get_instagram_business_account_id()
    max_payload_bytes = get_max_webhook_payload_bytes()

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )
    session_factory: sessionmaker[Session] = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )
    ingestor = TransactionalMetaWebhookIngestor(
        session_factory=session_factory,
        app_secret=app_secret,
        client_id=ClientId(business_account_id),
        authorized_business_account_id=business_account_id,
        max_payload_bytes=max_payload_bytes,
        clock=_utc_now,
    )
    app = create_webhook_app(
        verify_token=verify_token,
        ingestor=ingestor,
    )

    app.extensions["sqlalchemy_engine"] = engine
    app.extensions["sqlalchemy_session_factory"] = session_factory

    return app
