"""Tests for client-scoped lead profiles."""

import pytest

from lead_pipeline.domain.enums import InterestType
from lead_pipeline.domain.identifiers import (
    ClientId,
    InstagramEventId,
    InstagramUserId,
)
from lead_pipeline.domain.interests import InterestEvidence
from lead_pipeline.domain.leads import LeadProfile


def build_interest(name: str = "Vitamin C serum") -> InterestEvidence:
    return InterestEvidence(
        name=name,
        interest_type=InterestType.EXPLICIT,
        confidence=0.92,
        source_event_id=InstagramEventId("event-1"),
        model_name="interest-extractor",
        model_version="1.0.0",
    )


def test_profile_normalizes_username() -> None:
    profile = LeadProfile(
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        username="  beauty_user  ",
    )

    assert profile.username == "beauty_user"


def test_blank_username_becomes_none() -> None:
    profile = LeadProfile(
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        username="   ",
    )

    assert profile.username is None


def test_new_profile_has_no_interests() -> None:
    profile = LeadProfile(
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
    )

    assert profile.interests == ()


def test_add_interest_returns_updated_profile() -> None:
    profile = LeadProfile(
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
        username="beauty_user",
    )
    interest = build_interest()

    updated = profile.add_interest(interest)

    assert updated.client_id == profile.client_id
    assert updated.user_id == profile.user_id
    assert updated.username == profile.username
    assert updated.interests == (interest,)


def test_add_interest_does_not_mutate_original_profile() -> None:
    profile = LeadProfile(
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
    )

    updated = profile.add_interest(build_interest())

    assert profile.interests == ()
    assert len(updated.interests) == 1


def test_multiple_interests_preserve_history() -> None:
    profile = LeadProfile(
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
    )

    first = build_interest("Vitamin C serum")
    second = build_interest("Moisturizer")

    updated = profile.add_interest(first).add_interest(second)

    assert updated.interests == (first, second)


def test_profile_is_immutable() -> None:
    profile = LeadProfile(
        client_id=ClientId("client-1"),
        user_id=InstagramUserId("user-1"),
    )

    with pytest.raises(AttributeError):
        profile.username = "changed"  # type: ignore[misc]
