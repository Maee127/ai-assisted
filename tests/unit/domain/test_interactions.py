"""Tests for authorized Instagram interactions."""

from datetime import UTC, datetime

import pytest

from lead_pipeline.domain.enums import ProcessingStatus, SourceType
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction


def build_interaction(**overrides: object) -> InstagramInteraction:
    values: dict[str, object] = {
        "event_id": InstagramEventId("event-1"),
        "client_id": ClientId("client-1"),
        "user_id": InstagramUserId("user-1"),
        "media_id": InstagramMediaId("media-1"),
        "source_type": SourceType.POST_COMMENT,
        "text": "  Is this available?  ",
        "source_timestamp": datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
        "collected_at": datetime(2026, 8, 1, 10, 1, tzinfo=UTC),
    }
    values.update(overrides)

    return InstagramInteraction(**values)  # type: ignore[arg-type]


def test_interaction_normalizes_text_and_username() -> None:
    interaction = build_interaction(username="  beauty_user  ")

    assert interaction.text == "Is this available?"
    assert interaction.username == "beauty_user"


def test_blank_username_becomes_none() -> None:
    interaction = build_interaction(username="   ")

    assert interaction.username is None


def test_default_status_is_received() -> None:
    interaction = build_interaction()

    assert interaction.status is ProcessingStatus.RECEIVED


@pytest.mark.parametrize("text", ["", "   ", "\t", "\n"])
def test_blank_text_is_rejected(text: str) -> None:
    with pytest.raises(ValueError, match="text must not be empty"):
        build_interaction(text=text)


def test_naive_source_timestamp_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="source_timestamp must be timezone-aware",
    ):
        build_interaction(
            source_timestamp=datetime(2026, 8, 1, 10, 0),  # noqa: DTZ001
        )


def test_naive_collected_at_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="collected_at must be timezone-aware",
    ):
        build_interaction(
            collected_at=datetime(2026, 8, 1, 10, 1),  # noqa: DTZ001
        )


def test_interaction_is_immutable() -> None:
    interaction = build_interaction()

    with pytest.raises(AttributeError):
        interaction.text = "changed"  # type: ignore[misc]
