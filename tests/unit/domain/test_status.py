"""Tests for processing-status transition rules."""

import pytest

from lead_pipeline.domain.enums import ProcessingStatus
from lead_pipeline.domain.status import can_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ProcessingStatus.RECEIVED, ProcessingStatus.QUEUED),
        (
            ProcessingStatus.RECEIVED,
            ProcessingStatus.PERMANENT_FAILURE,
        ),
        (ProcessingStatus.QUEUED, ProcessingStatus.PROCESSING),
        (
            ProcessingStatus.QUEUED,
            ProcessingStatus.RETRYABLE_FAILURE,
        ),
        (
            ProcessingStatus.QUEUED,
            ProcessingStatus.PERMANENT_FAILURE,
        ),
        (ProcessingStatus.PROCESSING, ProcessingStatus.COMPLETED),
        (
            ProcessingStatus.PROCESSING,
            ProcessingStatus.RETRYABLE_FAILURE,
        ),
        (
            ProcessingStatus.PROCESSING,
            ProcessingStatus.PERMANENT_FAILURE,
        ),
        (
            ProcessingStatus.RETRYABLE_FAILURE,
            ProcessingStatus.QUEUED,
        ),
        (
            ProcessingStatus.RETRYABLE_FAILURE,
            ProcessingStatus.PERMANENT_FAILURE,
        ),
    ],
)
def test_allowed_transitions(
    current: ProcessingStatus,
    target: ProcessingStatus,
) -> None:
    assert can_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ProcessingStatus.RECEIVED, ProcessingStatus.COMPLETED),
        (ProcessingStatus.RECEIVED, ProcessingStatus.PROCESSING),
        (ProcessingStatus.QUEUED, ProcessingStatus.COMPLETED),
        (ProcessingStatus.PROCESSING, ProcessingStatus.QUEUED),
        (ProcessingStatus.COMPLETED, ProcessingStatus.QUEUED),
        (
            ProcessingStatus.PERMANENT_FAILURE,
            ProcessingStatus.QUEUED,
        ),
    ],
)
def test_forbidden_transitions(
    current: ProcessingStatus,
    target: ProcessingStatus,
) -> None:
    assert not can_transition(current, target)


@pytest.mark.parametrize("status", list(ProcessingStatus))
def test_same_status_transition_is_not_allowed(
    status: ProcessingStatus,
) -> None:
    assert not can_transition(status, status)
