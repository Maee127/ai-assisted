"""Tests for extracting minimized interactions from Meta comment events."""

from datetime import UTC, datetime

import pytest

from lead_pipeline.domain.enums import SourceType
from lead_pipeline.domain.identifiers import ClientId
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.ingestion.exceptions import (
    InvalidWebhookPayloadError,
    UnauthorizedWebhookAccountError,
)
from lead_pipeline.ingestion.meta_comment_extractor import (
    extract_comment_interactions,
)

SOURCE_TIMESTAMP = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)
COLLECTED_AT = datetime(2026, 8, 17, 12, 1, tzinfo=UTC)
ENTRY_TIME_SECONDS = int(SOURCE_TIMESTAMP.timestamp())


def build_comment_value(
    **overrides: object,
) -> dict[str, object]:
    value: dict[str, object] = {
        "id": "comment-1",
        "from": {
            "id": "user-1",
            "username": "beauty_user",
        },
        "text": "Is this available?",
        "media": {
            "id": "media-1",
            "media_product_type": "FEED",
        },
    }
    value.update(overrides)
    return value


def build_direct_payload(
    *,
    value: dict[str, object] | None = None,
    entry_overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    entry: dict[str, object] = {
        "id": "business-1",
        "time": ENTRY_TIME_SECONDS,
        "field": "comments",
        "value": value or build_comment_value(),
    }
    entry.update(entry_overrides or {})

    return {
        "object": "instagram",
        "entry": [entry],
    }


def extract(
    payload: dict[str, object],
) -> tuple[InstagramInteraction, ...]:
    return extract_comment_interactions(
        payload=payload,
        client_id=ClientId("client-1"),
        authorized_business_account_id="business-1",
        collected_at=COLLECTED_AT,
    )


def test_direct_feed_comment_is_mapped_to_minimized_interaction() -> None:
    interactions = extract(build_direct_payload())

    assert len(interactions) == 1
    interaction = interactions[0]
    assert interaction.event_id.value == "comment-1"
    assert interaction.client_id == ClientId("client-1")
    assert interaction.user_id.value == "user-1"
    assert interaction.media_id.value == "media-1"
    assert interaction.source_type is SourceType.POST_COMMENT
    assert interaction.text == "Is this available?"
    assert interaction.username == "beauty_user"
    assert interaction.source_timestamp == SOURCE_TIMESTAMP
    assert interaction.collected_at == COLLECTED_AT


def test_nested_changes_reel_comment_is_supported() -> None:
    payload: dict[str, object] = {
        "object": "instagram",
        "entry": [
            {
                "id": "business-1",
                "time": ENTRY_TIME_SECONDS,
                "changes": [
                    {
                        "field": "comments",
                        "value": build_comment_value(
                            media={
                                "id": "media-1",
                                "media_product_type": "REELS",
                            }
                        ),
                    }
                ],
            }
        ],
    }

    interactions = extract(payload)

    assert len(interactions) == 1
    assert interactions[0].source_type is SourceType.REEL_COMMENT


def test_millisecond_entry_timestamp_is_supported() -> None:
    payload = build_direct_payload(
        entry_overrides={
            "time": ENTRY_TIME_SECONDS * 1000,
        }
    )

    interactions = extract(payload)

    assert interactions[0].source_timestamp == SOURCE_TIMESTAMP


def test_comment_timestamp_is_preferred_when_supplied() -> None:
    comment_timestamp = datetime(2026, 8, 17, 11, 59, tzinfo=UTC)
    payload = build_direct_payload(
        value=build_comment_value(
            timestamp=comment_timestamp.isoformat(),
        )
    )

    interactions = extract(payload)

    assert interactions[0].source_timestamp == comment_timestamp


def test_event_for_another_business_account_is_rejected() -> None:
    payload = build_direct_payload(
        entry_overrides={
            "id": "other-business",
        }
    )

    with pytest.raises(
        UnauthorizedWebhookAccountError,
        match="webhook entry does not belong to the authorized account",
    ):
        extract(payload)


def test_non_instagram_webhook_object_is_rejected() -> None:
    payload = build_direct_payload()
    payload["object"] = "page"

    with pytest.raises(
        InvalidWebhookPayloadError,
        match="webhook object must be instagram",
    ):
        extract(payload)


def test_missing_stable_commenter_id_is_rejected() -> None:
    payload = build_direct_payload(
        value=build_comment_value(
            **{
                "from": {
                    "username": "beauty_user",
                }
            }
        )
    )

    with pytest.raises(
        InvalidWebhookPayloadError,
        match="commenter id must be a non-empty string",
    ):
        extract(payload)


def test_username_is_optional() -> None:
    payload = build_direct_payload(
        value=build_comment_value(
            **{
                "from": {
                    "id": "user-1",
                }
            }
        )
    )

    interactions = extract(payload)

    assert interactions[0].username is None


def test_unrelated_webhook_field_is_ignored() -> None:
    payload = build_direct_payload(
        entry_overrides={
            "field": "messages",
        }
    )

    assert extract(payload) == ()


def test_unsupported_comment_media_type_is_ignored() -> None:
    payload = build_direct_payload(
        value=build_comment_value(
            media={
                "id": "media-1",
                "media_product_type": "STORY",
            }
        )
    )

    assert extract(payload) == ()


def test_distinct_comment_ids_with_identical_content_are_preserved() -> None:
    first_entry: dict[str, object] = {
        "id": "business-1",
        "time": ENTRY_TIME_SECONDS,
        "field": "comments",
        "value": build_comment_value(),
    }
    second_entry = {
        "id": "business-1",
        "time": ENTRY_TIME_SECONDS,
        "field": "comments",
        "value": build_comment_value(id="comment-2"),
    }
    payload: dict[str, object] = {
        "object": "instagram",
        "entry": [
            first_entry,
            second_entry,
        ],
    }

    interactions = extract(payload)

    assert [interaction.event_id.value for interaction in interactions] == [
        "comment-1",
        "comment-2",
    ]


def test_unnecessary_profile_fields_are_not_mapped() -> None:
    payload = build_direct_payload(
        value=build_comment_value(
            **{
                "from": {
                    "id": "user-1",
                    "username": "beauty_user",
                    "birthday": "not-retained",
                    "biography": "not-retained",
                },
                "raw_payload": "not-retained",
            }
        )
    )

    interaction = extract(payload)[0]

    assert not hasattr(interaction, "birthday")
    assert not hasattr(interaction, "biography")
    assert not hasattr(interaction, "raw_payload")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"object": "instagram"},
        {"object": "instagram", "entry": "not-a-list"},
        {"object": "instagram", "entry": ["not-an-object"]},
    ],
)
def test_malformed_payload_structure_is_rejected(
    payload: dict[str, object],
) -> None:
    with pytest.raises(InvalidWebhookPayloadError):
        extract(payload)
