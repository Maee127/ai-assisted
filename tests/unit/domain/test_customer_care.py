"""Tests for customer-care cases."""

from datetime import UTC, datetime

import pytest

from lead_pipeline.domain.customer_care import CustomerCareCase
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramUserId,
)


def build_case(**overrides: object) -> CustomerCareCase:
    values: dict[str, object] = {
        "client_id": ClientId("client-1"),
        "user_id": InstagramUserId("user-1"),
        "source_event_id": InstagramEventId("event-1"),
        "summary": "  The customer reports skin irritation.  ",
        "created_at": datetime(2026, 8, 3, 18, 0, tzinfo=UTC),
        "username": "  beauty_user  ",
    }
    values.update(overrides)

    return CustomerCareCase(**values)  # type: ignore[arg-type]


def test_case_normalizes_summary_and_username() -> None:
    case = build_case()

    assert case.summary == "The customer reports skin irritation."
    assert case.username == "beauty_user"


def test_blank_username_becomes_none() -> None:
    case = build_case(username="   ")

    assert case.username is None


@pytest.mark.parametrize("summary", ["", "   ", "\t", "\n"])
def test_blank_summary_is_rejected(summary: str) -> None:
    with pytest.raises(ValueError, match="summary must not be empty"):
        build_case(summary=summary)


def test_naive_created_at_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="created_at must be timezone-aware",
    ):
        build_case(
            created_at=datetime(2026, 8, 3, 18, 0),  # noqa: DTZ001
        )


def test_case_is_immutable() -> None:
    case = build_case()

    with pytest.raises(AttributeError):
        case.summary = "changed"  # type: ignore[misc]
