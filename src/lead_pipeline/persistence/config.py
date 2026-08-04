"""Database configuration."""

import os

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://postgres:postgres@localhost:5432/lead_pipeline"
)


def get_database_url() -> str:
    """Return the configured SQLAlchemy database URL."""

    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL).strip()

    if not database_url:
        raise ValueError("DATABASE_URL must not be empty")

    return database_url
