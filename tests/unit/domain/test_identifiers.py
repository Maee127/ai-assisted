"""Tests for stable domain identifiers."""

import pytest

from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)


@pytest.mark.parametrize(
    ("identifier_type", "value"),
    [
        (ClientId, "client-123"),
        (InstagramUserId, "user-456"),
        (InstagramEventId, "event-789"),
        (InstagramMediaId, "media-012"),
    ],
)
def test_identifier_accepts_non_empty_value(
    identifier_type: type[
        ClientId | InstagramUserId | InstagramEventId | InstagramMediaId
    ],
    value: str,
) -> None:
    identifier = identifier_type(value)

    assert identifier.value == value


@pytest.mark.parametrize(
    "identifier_type",
    [
        ClientId,
        InstagramUserId,
        InstagramEventId,
        InstagramMediaId,
    ],
)
@pytest.mark.parametrize("value", ["", "   ", "\t", "\n"])
def test_identifier_rejects_blank_value(
    identifier_type: type[
        ClientId | InstagramUserId | InstagramEventId | InstagramMediaId
    ],
    value: str,
) -> None:
    with pytest.raises(ValueError):
        identifier_type(value)


def test_identifier_strips_surrounding_whitespace() -> None:
    identifier = ClientId("  client-123  ")

    assert identifier.value == "client-123"


def test_identifiers_are_immutable() -> None:
    identifier = ClientId("client-123")

    with pytest.raises(AttributeError):
        identifier.value = "changed"  # type: ignore[misc]
