"""Tests for SQLAlchemy persistence models."""

from typing import cast

from sqlalchemy import DateTime, String, Table, Text, UniqueConstraint

from lead_pipeline.persistence.database import Base
from lead_pipeline.persistence.models import (
    ClassificationRow,
    CustomerCareRow,
    InteractionRow,
    InterestEvidenceRow,
    LeadProfileRow,
    UnresolvedRecordRow,
)


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


def test_classification_table_is_registered() -> None:
    assert "classifications" in Base.metadata.tables


def test_classification_table_has_expected_columns() -> None:
    table = cast(Table, ClassificationRow.__table__)

    assert set(table.columns.keys()) == {
        "classification_id",
        "source_event_id",
        "client_id",
        "label",
        "confidence",
        "reason",
        "model_name",
        "model_version",
        "prompt_version",
        "created_at",
    }


def test_classification_event_foreign_key_cascades() -> None:
    table = cast(Table, ClassificationRow.__table__)
    foreign_keys = list(table.c.source_event_id.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "interactions.event_id"
    assert foreign_keys[0].ondelete == "CASCADE"


def test_classification_constraints_and_indexes_are_defined() -> None:
    table = cast(Table, ClassificationRow.__table__)

    assert "ck_classifications_confidence_range" in {
        constraint.name for constraint in table.constraints
    }
    assert {index.name for index in table.indexes} == {
        "ix_classifications_client_event",
        "ix_classifications_client_label",
    }


def test_classification_timestamp_is_timezone_aware() -> None:
    table = cast(Table, ClassificationRow.__table__)
    created_at_type = cast(DateTime, table.c.created_at.type)

    assert created_at_type.timezone is True


def test_customer_care_table_is_registered() -> None:
    assert "customer_care_cases" in Base.metadata.tables


def test_customer_care_table_has_expected_columns() -> None:
    table = cast(Table, CustomerCareRow.__table__)

    assert set(table.columns.keys()) == {
        "case_id",
        "source_event_id",
        "client_id",
        "user_id",
        "summary",
        "created_at",
        "username",
    }


def test_customer_care_event_foreign_key_cascades() -> None:
    table = cast(Table, CustomerCareRow.__table__)
    foreign_keys = list(table.c.source_event_id.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "interactions.event_id"
    assert foreign_keys[0].ondelete == "CASCADE"


def test_customer_care_timestamp_is_timezone_aware() -> None:
    table = cast(Table, CustomerCareRow.__table__)
    created_at_type = cast(DateTime, table.c.created_at.type)

    assert created_at_type.timezone is True


def test_customer_care_indexes_are_defined() -> None:
    table = cast(Table, CustomerCareRow.__table__)

    assert {index.name for index in table.indexes} == {
        "ix_customer_care_client_created",
        "ix_customer_care_client_user",
    }


def test_lead_profile_table_is_registered() -> None:
    assert "lead_profiles" in Base.metadata.tables


def test_lead_profile_table_has_expected_columns() -> None:
    table = cast(Table, LeadProfileRow.__table__)

    assert set(table.columns.keys()) == {
        "lead_id",
        "client_id",
        "user_id",
        "username",
        "created_at",
        "updated_at",
    }


def test_lead_profile_identity_is_unique_per_client() -> None:
    table = cast(Table, LeadProfileRow.__table__)
    unique_constraints = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "lead_profile_identity" in unique_constraints


def test_lead_profile_timestamps_are_timezone_aware() -> None:
    table = cast(Table, LeadProfileRow.__table__)
    created_at_type = cast(DateTime, table.c.created_at.type)
    updated_at_type = cast(DateTime, table.c.updated_at.type)

    assert created_at_type.timezone is True
    assert updated_at_type.timezone is True


def test_lead_profile_indexes_are_defined() -> None:
    table = cast(Table, LeadProfileRow.__table__)

    assert {index.name for index in table.indexes} == {
        "ix_lead_profiles_client_updated",
    }


def test_interest_evidence_table_is_registered() -> None:
    assert "interest_evidence" in Base.metadata.tables


def test_interest_evidence_table_has_expected_columns() -> None:
    table = cast(Table, InterestEvidenceRow.__table__)

    assert set(table.columns.keys()) == {
        "interest_id",
        "lead_id",
        "source_event_id",
        "name",
        "interest_type",
        "confidence",
        "model_name",
        "model_version",
        "catalogue_evidence",
        "prompt_version",
        "created_at",
    }


def test_interest_evidence_foreign_keys_cascade() -> None:
    table = cast(Table, InterestEvidenceRow.__table__)

    lead_foreign_keys = list(table.c.lead_id.foreign_keys)
    event_foreign_keys = list(table.c.source_event_id.foreign_keys)

    assert len(lead_foreign_keys) == 1
    assert lead_foreign_keys[0].target_fullname == "lead_profiles.lead_id"
    assert lead_foreign_keys[0].ondelete == "CASCADE"

    assert len(event_foreign_keys) == 1
    assert event_foreign_keys[0].target_fullname == "interactions.event_id"
    assert event_foreign_keys[0].ondelete == "CASCADE"


def test_interest_evidence_constraints_and_indexes_are_defined() -> None:
    table = cast(Table, InterestEvidenceRow.__table__)

    assert "ck_interest_evidence_confidence_range" in {
        constraint.name for constraint in table.constraints
    }
    assert {index.name for index in table.indexes} == {
        "ix_interest_evidence_event",
        "ix_interest_evidence_lead_created",
    }


def test_interest_evidence_timestamp_is_timezone_aware() -> None:
    table = cast(Table, InterestEvidenceRow.__table__)
    created_at_type = cast(DateTime, table.c.created_at.type)

    assert created_at_type.timezone is True


def test_unresolved_record_table_is_registered() -> None:
    assert "unresolved_records" in Base.metadata.tables


def test_unresolved_record_table_has_expected_columns() -> None:
    table = cast(Table, UnresolvedRecordRow.__table__)

    assert set(table.columns.keys()) == {
        "unresolved_id",
        "client_id",
        "user_id",
        "source_event_id",
        "primary_classification_id",
        "stronger_classification_id",
        "created_at",
    }


def test_unresolved_record_foreign_keys_cascade() -> None:
    table = cast(Table, UnresolvedRecordRow.__table__)

    source_foreign_keys = list(table.c.source_event_id.foreign_keys)
    primary_foreign_keys = list(table.c.primary_classification_id.foreign_keys)
    stronger_foreign_keys = list(table.c.stronger_classification_id.foreign_keys)

    assert len(source_foreign_keys) == 1
    assert source_foreign_keys[0].target_fullname == "interactions.event_id"
    assert source_foreign_keys[0].ondelete == "CASCADE"

    assert len(primary_foreign_keys) == 1
    assert (
        primary_foreign_keys[0].target_fullname == "classifications.classification_id"
    )
    assert primary_foreign_keys[0].ondelete == "CASCADE"

    assert len(stronger_foreign_keys) == 1
    assert (
        stronger_foreign_keys[0].target_fullname == "classifications.classification_id"
    )
    assert stronger_foreign_keys[0].ondelete == "CASCADE"


def test_unresolved_record_timestamp_is_timezone_aware() -> None:
    table = cast(Table, UnresolvedRecordRow.__table__)
    created_at_type = cast(DateTime, table.c.created_at.type)

    assert created_at_type.timezone is True


def test_unresolved_record_indexes_are_defined() -> None:
    table = cast(Table, UnresolvedRecordRow.__table__)

    assert {index.name for index in table.indexes} == {
        "ix_unresolved_client_created",
        "ix_unresolved_client_user",
    }
