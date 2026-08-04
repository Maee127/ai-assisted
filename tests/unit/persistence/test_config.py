"""Tests for database configuration."""

import pytest

from lead_pipeline.persistence.config import (
    DEFAULT_DATABASE_URL,
    get_database_url,
)


def test_default_database_url_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert get_database_url() == DEFAULT_DATABASE_URL


def test_environment_database_url_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:password@db:5432/app",
    )

    assert get_database_url() == "postgresql+psycopg://user:password@db:5432/app"


def test_blank_database_url_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "   ")

    with pytest.raises(
        ValueError,
        match="DATABASE_URL must not be empty",
    ):
        get_database_url()
