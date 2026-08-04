"""Tests for SQLAlchemy persistence models."""

from typing import cast

from sqlalchemy import DateTime, String, Table, Text

from lead_pipeline.persistence.database import Base
from lead_pipeline.persistence.models import InteractionRow


def test_interaction_table_is_registered() -> None:
    assert "interactions" in Base.metadata.tables


def test_event_id_is_the_primary_key() -> None:
    table = cast(Table, InteractionRow.__table__)

    assert [column.name for column in table.primary_key.columns] == ["event_id"]


def test_interaction_table_has_expected_columns() -> None:
    table = cast(Table, InteractionRow.__table__)

    assert set(table.columns.keys()) == {
        "event_id",
        "client_id",
        "user_id",
        "media_id",
        "source_type",
        "text",
        "source_timestamp",
        "collected_at",
        "processing_status",
        "username",
    }


def test_interaction_column_types() -> None:
    table = cast(Table, InteractionRow.__table__)

    assert isinstance(table.c.event_id.type, String)
    assert isinstance(table.c.client_id.type, String)
    assert isinstance(table.c.user_id.type, String)
    assert isinstance(table.c.media_id.type, String)
    assert isinstance(table.c.source_type.type, String)
    assert isinstance(table.c.text.type, Text)
    assert isinstance(table.c.source_timestamp.type, DateTime)
    assert isinstance(table.c.collected_at.type, DateTime)
    assert isinstance(table.c.processing_status.type, String)
    assert isinstance(table.c.username.type, String)


def test_interaction_timestamps_are_timezone_aware() -> None:
    table = cast(Table, InteractionRow.__table__)
    source_timestamp_type = cast(DateTime, table.c.source_timestamp.type)
    collected_at_type = cast(DateTime, table.c.collected_at.type)

    assert source_timestamp_type.timezone is True
    assert collected_at_type.timezone is True


def test_interaction_indexes_are_defined() -> None:
    table = cast(Table, InteractionRow.__table__)

    assert {index.name for index in table.indexes} == {
        "ix_interactions_client_status",
        "ix_interactions_client_user",
    }
