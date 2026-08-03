"""Tests for domain-specific exceptions."""

import pytest

from lead_pipeline.domain.enums import ProcessingStatus
from lead_pipeline.domain.exceptions import InvalidStatusTransitionError
from lead_pipeline.domain.status import ensure_transition_allowed


def test_allowed_transition_does_not_raise() -> None:
    ensure_transition_allowed(
        ProcessingStatus.RECEIVED,
        ProcessingStatus.QUEUED,
    )


def test_invalid_transition_raises_domain_exception() -> None:
    with pytest.raises(
        InvalidStatusTransitionError,
        match="transition from RECEIVED to COMPLETED is not permitted",
    ):
        ensure_transition_allowed(
            ProcessingStatus.RECEIVED,
            ProcessingStatus.COMPLETED,
        )
