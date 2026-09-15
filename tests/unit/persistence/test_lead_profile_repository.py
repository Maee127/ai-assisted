"""Tests for lead-profile and interest-evidence repositories."""

from datetime import UTC, datetime
from typing import cast
from unittest.mock import Mock
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from lead_pipeline.domain.enums import InterestType
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramUserId,
)
from lead_pipeline.domain.interests import InterestEvidence
from lead_pipeline.persistence.models import (
    InterestEvidenceRow,
    LeadProfileRow,
)
from lead_pipeline.persistence.sqlalchemy_repositories import (
    SqlAlchemyInterestEvidenceRepository,
    SqlAlchemyLeadProfileRepository,
)

LEAD_ID = UUID("00000000-0000-0000-0000-000000000010")
INTEREST_ID = UUID("00000000-0000-0000-0000-000000000011")
RECORDED_AT = datetime(2026, 9, 13, 15, 0, tzinfo=UTC)
LATER_AT = datetime(2026, 9, 13, 16, 0, tzinfo=UTC)


def build_profile_row() -> LeadProfileRow:
    return LeadProfileRow(
        lead_id=str(LEAD_ID),
        client_id="client-1",
        user_id="user-1",
        username="old_username",
        created_at=RECORDED_AT,
        updated_at=RECORDED_AT,
    )


def build_interest() -> InterestEvidence:
    return InterestEvidence(
        name="Calming serum",
        interest_type=InterestType.INFERRED,
        confidence=0.91,
        source_event_id=InstagramEventId("event-1"),
        model_name="anthropic",
        model_version="claude-sonnet-5",
        catalogue_evidence='["item-1"]',
        prompt_version="interest-v1",
    )


def test_get_or_create_adds_new_client_scoped_profile() -> None:
    session = Mock(spec=Session)
    session.scalar.return_value = None
    repository = SqlAlchemyLeadProfileRepository(
        session=session,
        id_factory=lambda: LEAD_ID,
    )

    lead_id = repository.get_or_create(
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        username="  beauty_user  ",
        updated_at=RECORDED_AT,
    )

    assert lead_id == str(LEAD_ID)
    session.scalar.assert_called_once()
    session.add.assert_called_once()
    session.flush.assert_called_once_with()

    row = cast(
        LeadProfileRow,
        session.add.call_args.args[0],
    )

    assert row.lead_id == str(LEAD_ID)
    assert row.client_id == "client-1"
    assert row.user_id == "user-1"
    assert row.username == "beauty_user"
    assert row.created_at == RECORDED_AT
    assert row.updated_at == RECORDED_AT
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_profile_lookup_contains_client_and_user_boundary() -> None:
    session = Mock(spec=Session)
    session.scalar.return_value = build_profile_row()
    repository = SqlAlchemyLeadProfileRepository(session=session)

    repository.get_or_create(
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        username=None,
        updated_at=LATER_AT,
    )

    statement = session.scalar.call_args.args[0]
    compiled = statement.compile()

    assert "client-1" in compiled.params.values()
    assert "user-1" in compiled.params.values()


def test_get_or_create_updates_existing_profile_metadata() -> None:
    session = Mock(spec=Session)
    row = build_profile_row()
    session.scalar.return_value = row
    repository = SqlAlchemyLeadProfileRepository(session=session)

    lead_id = repository.get_or_create(
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        username="  new_username  ",
        updated_at=LATER_AT,
    )

    assert lead_id == str(LEAD_ID)
    assert row.username == "new_username"
    assert row.created_at == RECORDED_AT
    assert row.updated_at == LATER_AT
    session.add.assert_not_called()
    session.flush.assert_not_called()


def test_missing_username_preserves_existing_metadata() -> None:
    session = Mock(spec=Session)
    row = build_profile_row()
    session.scalar.return_value = row
    repository = SqlAlchemyLeadProfileRepository(session=session)

    repository.get_or_create(
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        username=None,
        updated_at=LATER_AT,
    )

    assert row.username == "old_username"
    assert row.updated_at == LATER_AT


def test_blank_username_becomes_none_for_new_profile() -> None:
    session = Mock(spec=Session)
    session.scalar.return_value = None
    repository = SqlAlchemyLeadProfileRepository(
        session=session,
        id_factory=lambda: LEAD_ID,
    )

    repository.get_or_create(
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        username="   ",
        updated_at=RECORDED_AT,
    )

    row = cast(
        LeadProfileRow,
        session.add.call_args.args[0],
    )

    assert row.username is None


def test_profile_rejects_naive_updated_at() -> None:
    session = Mock(spec=Session)
    repository = SqlAlchemyLeadProfileRepository(session=session)

    with pytest.raises(
        ValueError,
        match="updated_at must be timezone-aware",
    ):
        repository.get_or_create(
            client_id=ClientId("client-1"),
            user_id=InstagramUserId("user-1"),
            username="beauty_user",
            updated_at=datetime(2026, 9, 13, 15, 0),  # noqa: DTZ001
        )

    session.scalar.assert_not_called()
    session.add.assert_not_called()


def test_interest_add_maps_complete_evidence() -> None:
    session = Mock(spec=Session)
    repository = SqlAlchemyInterestEvidenceRepository(
        session=session,
        id_factory=lambda: INTEREST_ID,
    )

    interest_id = repository.add(
        lead_id=str(LEAD_ID),
        interest=build_interest(),
        created_at=RECORDED_AT,
    )

    assert interest_id == str(INTEREST_ID)
    session.add.assert_called_once()

    row = cast(
        InterestEvidenceRow,
        session.add.call_args.args[0],
    )

    assert row.interest_id == str(INTEREST_ID)
    assert row.lead_id == str(LEAD_ID)
    assert row.source_event_id == "event-1"
    assert row.name == "Calming serum"
    assert row.interest_type == InterestType.INFERRED.value
    assert row.confidence == 0.91
    assert row.model_name == "anthropic"
    assert row.model_version == "claude-sonnet-5"
    assert row.catalogue_evidence == '["item-1"]'
    assert row.prompt_version == "interest-v1"
    assert row.created_at == RECORDED_AT
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_interest_add_rejects_blank_lead_id() -> None:
    session = Mock(spec=Session)
    repository = SqlAlchemyInterestEvidenceRepository(session=session)

    with pytest.raises(
        ValueError,
        match="lead_id must not be empty",
    ):
        repository.add(
            lead_id="   ",
            interest=build_interest(),
            created_at=RECORDED_AT,
        )

    session.add.assert_not_called()


def test_interest_add_rejects_naive_created_at() -> None:
    session = Mock(spec=Session)
    repository = SqlAlchemyInterestEvidenceRepository(session=session)

    with pytest.raises(
        ValueError,
        match="created_at must be timezone-aware",
    ):
        repository.add(
            lead_id=str(LEAD_ID),
            interest=build_interest(),
            created_at=datetime(2026, 9, 13, 15, 0),  # noqa: DTZ001
        )

    session.add.assert_not_called()
