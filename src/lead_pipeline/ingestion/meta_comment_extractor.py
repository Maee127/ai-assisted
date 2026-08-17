"""Extract minimized domain interactions from Meta comment webhooks."""

from datetime import UTC, datetime
from typing import cast

from lead_pipeline.domain.enums import SourceType
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.ingestion.exceptions import (
    InvalidWebhookPayloadError,
    UnauthorizedWebhookAccountError,
)


def _require_object(
    value: object,
    field_name: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise InvalidWebhookPayloadError(f"{field_name} must be a JSON object")

    return cast(dict[str, object], value)


def _require_list(
    value: object,
    field_name: str,
) -> list[object]:
    if not isinstance(value, list):
        raise InvalidWebhookPayloadError(f"{field_name} must be a JSON array")

    return cast(list[object], value)


def _require_non_empty_string(
    value: object,
    field_name: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidWebhookPayloadError(f"{field_name} must be a non-empty string")

    return value.strip()


def _optional_string(
    value: object,
    field_name: str,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise InvalidWebhookPayloadError(f"{field_name} must be a string")

    normalized = value.strip()
    return normalized or None


def _parse_webhook_timestamp(value: object) -> datetime:
    if isinstance(value, bool):
        raise InvalidWebhookPayloadError(
            "webhook timestamp must be an epoch integer or ISO-8601 string"
        )

    if isinstance(value, int):
        timestamp = value / 1000 if value > 10_000_000_000 else value

        try:
            return datetime.fromtimestamp(timestamp, tz=UTC)
        except (OSError, OverflowError, ValueError):
            raise InvalidWebhookPayloadError("webhook timestamp is invalid") from None

    if isinstance(value, str):
        try:
            parsed_timestamp = datetime.fromisoformat(value)
        except ValueError:
            raise InvalidWebhookPayloadError("webhook timestamp is invalid") from None

        if parsed_timestamp.tzinfo is None:
            raise InvalidWebhookPayloadError("webhook timestamp must be timezone-aware")

        return parsed_timestamp

    raise InvalidWebhookPayloadError(
        "webhook timestamp must be an epoch integer or ISO-8601 string"
    )


def _source_type_for_media(
    media_product_type: str,
) -> SourceType | None:
    normalized = media_product_type.upper()

    if normalized == "FEED":
        return SourceType.POST_COMMENT

    if normalized == "REELS":
        return SourceType.REEL_COMMENT

    return None


def _entry_changes(
    entry: dict[str, object],
) -> tuple[dict[str, object], ...]:
    if "changes" in entry:
        changes = _require_list(
            entry["changes"],
            "webhook entry changes",
        )
        return tuple(_require_object(change, "webhook change") for change in changes)

    if "field" in entry:
        return (entry,)

    raise InvalidWebhookPayloadError(
        "webhook entry must contain field/value or changes"
    )


def _interaction_from_change(
    *,
    change: dict[str, object],
    entry_time: object,
    client_id: ClientId,
    collected_at: datetime,
) -> InstagramInteraction | None:
    field = _require_non_empty_string(
        change.get("field"),
        "webhook field",
    )

    if field != "comments":
        return None

    value = _require_object(
        change.get("value"),
        "webhook comment value",
    )
    media = _require_object(
        value.get("media"),
        "comment media",
    )
    media_product_type = _require_non_empty_string(
        media.get("media_product_type"),
        "media product type",
    )
    source_type = _source_type_for_media(media_product_type)

    if source_type is None:
        return None

    commenter = _require_object(
        value.get("from"),
        "commenter",
    )

    return InstagramInteraction(
        event_id=InstagramEventId(
            _require_non_empty_string(
                value.get("id"),
                "comment id",
            )
        ),
        client_id=client_id,
        user_id=InstagramUserId(
            _require_non_empty_string(
                commenter.get("id"),
                "commenter id",
            )
        ),
        media_id=InstagramMediaId(
            _require_non_empty_string(
                media.get("id"),
                "media id",
            )
        ),
        source_type=source_type,
        text=_require_non_empty_string(
            value.get("text"),
            "comment text",
        ),
        source_timestamp=_parse_webhook_timestamp(value.get("timestamp", entry_time)),
        collected_at=collected_at,
        username=_optional_string(
            commenter.get("username"),
            "commenter username",
        ),
    )


def extract_comment_interactions(
    *,
    payload: dict[str, object],
    client_id: ClientId,
    authorized_business_account_id: str,
    collected_at: datetime,
) -> tuple[InstagramInteraction, ...]:
    """Extract authorized Feed/Reels comments into domain interactions."""

    authorized_account_id = authorized_business_account_id.strip()

    if not authorized_account_id:
        raise ValueError("authorized_business_account_id must not be empty")

    if collected_at.tzinfo is None:
        raise ValueError("collected_at must be timezone-aware")

    if payload.get("object") != "instagram":
        raise InvalidWebhookPayloadError("webhook object must be instagram")

    entries = _require_list(
        payload.get("entry"),
        "webhook entry",
    )
    interactions: list[InstagramInteraction] = []

    for raw_entry in entries:
        entry = _require_object(
            raw_entry,
            "webhook entry item",
        )
        account_id = _require_non_empty_string(
            entry.get("id"),
            "webhook account id",
        )

        if account_id != authorized_account_id:
            raise UnauthorizedWebhookAccountError(
                "webhook entry does not belong to the authorized account"
            )

        for change in _entry_changes(entry):
            interaction = _interaction_from_change(
                change=change,
                entry_time=entry.get("time"),
                client_id=client_id,
                collected_at=collected_at,
            )

            if interaction is not None:
                interactions.append(interaction)

    return tuple(interactions)
