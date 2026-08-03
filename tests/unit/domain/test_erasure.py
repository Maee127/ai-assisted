"""Tests for verified erasure requests."""

from datetime import UTC, datetime

import pytest

from lead_pipeline.domain.erasure import ErasureRequest
from lead_pipeline.domain.identifiers import ClientId, InstagramUserId


def build_request(**overrides: object) -> ErasureRequest:
    values: dict[str, object] = {
        "client_id": ClientId("client-1"),
        "user_id": InstagramUserId("user-1"),
        "requested_at": datetime(2026, 8, 3, 18, 0, tzinfo=UTC),
        "verified_at": datetime(2026, 8, 3, 18, 5, tzinfo=UTC),
        "completed_at": None,
    }
    values.update(overrides)

    return ErasureRequest(**values)  # type: ignore[arg-type]


def test_new_request_is_not_completed() -> None:
    request = build_request()

    assert request.is_completed is False


def test_completed_request_is_completed() -> None:
    request = build_request(
        completed_at=datetime(2026, 8, 3, 18, 10, tzinfo=UTC),
    )

    assert request.is_completed is True


@pytest.mark.parametrize(
    ("field_name", "message"),
    [
        ("requested_at", "requested_at must be timezone-aware"),
        ("verified_at", "verified_at must be timezone-aware"),
        ("completed_at", "completed_at must be timezone-aware"),
    ],
)
def test_naive_timestamps_are_rejected(
    field_name: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_request(
            **{
                field_name: datetime(  # noqa: DTZ001
                    2026,
                    8,
                    3,
                    18,
                    0,
                )
            }
        )


def test_verified_at_before_requested_at_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="verified_at must not be before requested_at",
    ):
        build_request(
            verified_at=datetime(2026, 8, 3, 17, 59, tzinfo=UTC),
        )


def test_completed_at_before_verified_at_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="completed_at must not be before verified_at",
    ):
        build_request(
            completed_at=datetime(2026, 8, 3, 18, 4, tzinfo=UTC),
        )


def test_erasure_request_is_immutable() -> None:
    request = build_request()

    with pytest.raises(AttributeError):
        request.completed_at = datetime.now(UTC)  # type: ignore[misc]
