"""Stable identifiers used by the domain model."""

from dataclasses import dataclass


def _validate_identifier(value: str, field_name: str) -> str:
    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} must not be empty")

    return normalized


@dataclass(frozen=True, slots=True)
class ClientId:
    """Stable identifier for one isolated client boundary."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_identifier(self.value, "client_id"),
        )


@dataclass(frozen=True, slots=True)
class InstagramUserId:
    """Stable Instagram user or account identifier."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_identifier(self.value, "instagram_user_id"),
        )


@dataclass(frozen=True, slots=True)
class InstagramEventId:
    """Stable Instagram comment or webhook event identifier."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_identifier(self.value, "instagram_event_id"),
        )


@dataclass(frozen=True, slots=True)
class InstagramMediaId:
    """Stable Instagram post or reel identifier."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_identifier(self.value, "instagram_media_id"),
        )
