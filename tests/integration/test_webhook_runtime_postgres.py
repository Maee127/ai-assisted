"""PostgreSQL integration test for the complete webhook runtime."""

import hashlib
import hmac
import json
import os
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from lead_pipeline.api.runtime import create_app
from lead_pipeline.persistence.models import InteractionRow


def get_test_database_url() -> str:
    """Return the opt-in integration database URL."""

    database_url = os.environ.get("TEST_DATABASE_URL")

    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    return database_url


def build_signed_delivery(
    event_id: str,
) -> tuple[bytes, str]:
    """Build a minimized synthetic Meta comment delivery."""

    raw_body = json.dumps(
        {
            "object": "instagram",
            "entry": [
                {
                    "id": "business-integration-test",
                    "time": int(
                        datetime(
                            2026,
                            8,
                            23,
                            9,
                            0,
                            tzinfo=UTC,
                        ).timestamp()
                    ),
                    "field": "comments",
                    "value": {
                        "id": event_id,
                        "from": {
                            "id": "user-integration-test",
                            "username": "integration_user",
                        },
                        "text": "Is this integration test product available?",
                        "media": {
                            "id": "media-integration-test",
                            "media_product_type": "FEED",
                        },
                    },
                }
            ],
        },
        separators=(",", ":"),
    ).encode()

    digest = hmac.new(
        b"integration-app-secret",
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return raw_body, f"sha256={digest}"


def test_signed_webhook_is_persisted_idempotently_in_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = get_test_database_url()
    event_id = f"integration-{uuid4()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv(
        "META_APP_SECRET",
        "integration-app-secret",
    )
    monkeypatch.setenv(
        "WEBHOOK_VERIFY_TOKEN",
        "integration-verify-token",
    )
    monkeypatch.setenv(
        "IG_BUSINESS_ACCOUNT_ID",
        "business-integration-test",
    )
    monkeypatch.setenv(
        "MAX_WEBHOOK_PAYLOAD_BYTES",
        "4096",
    )

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    engine = cast(
        Engine,
        app.extensions["sqlalchemy_engine"],
    )
    raw_body, signature = build_signed_delivery(event_id)

    try:
        first_response = client.post(
            "/webhook",
            data=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
            },
        )
        duplicate_response = client.post(
            "/webhook",
            data=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
            },
        )

        assert first_response.status_code == 200
        assert duplicate_response.status_code == 200

        with Session(engine) as session:
            row = session.get(
                InteractionRow,
                event_id,
            )
            stored_count = session.scalar(
                select(func.count())
                .select_from(InteractionRow)
                .where(InteractionRow.event_id == event_id)
            )

            assert row is not None
            assert stored_count == 1
            assert row.client_id == "business-integration-test"
            assert row.user_id == "user-integration-test"
            assert row.media_id == "media-integration-test"
            assert row.source_type == "POST_COMMENT"
            assert row.text == "Is this integration test product available?"
            assert row.username == "integration_user"
            assert row.source_timestamp.tzinfo is not None
            assert row.collected_at.tzinfo is not None
            assert not hasattr(row, "raw_payload")
    finally:
        with Session(engine) as session:
            row = session.get(
                InteractionRow,
                event_id,
            )

            if row is not None:
                session.delete(row)
                session.commit()

        engine.dispose()
