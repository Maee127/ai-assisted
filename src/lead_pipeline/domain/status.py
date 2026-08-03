"""Processing-status transition rules."""

from lead_pipeline.domain.enums import ProcessingStatus
from lead_pipeline.domain.exceptions import InvalidStatusTransitionError

_ALLOWED_TRANSITIONS: dict[ProcessingStatus, frozenset[ProcessingStatus]] = {
    ProcessingStatus.RECEIVED: frozenset(
        {
            ProcessingStatus.QUEUED,
            ProcessingStatus.PERMANENT_FAILURE,
        }
    ),
    ProcessingStatus.QUEUED: frozenset(
        {
            ProcessingStatus.PROCESSING,
            ProcessingStatus.RETRYABLE_FAILURE,
            ProcessingStatus.PERMANENT_FAILURE,
        }
    ),
    ProcessingStatus.PROCESSING: frozenset(
        {
            ProcessingStatus.COMPLETED,
            ProcessingStatus.RETRYABLE_FAILURE,
            ProcessingStatus.PERMANENT_FAILURE,
        }
    ),
    ProcessingStatus.RETRYABLE_FAILURE: frozenset(
        {
            ProcessingStatus.QUEUED,
            ProcessingStatus.PERMANENT_FAILURE,
        }
    ),
    ProcessingStatus.COMPLETED: frozenset(),
    ProcessingStatus.PERMANENT_FAILURE: frozenset(),
}


def can_transition(
    current: ProcessingStatus,
    target: ProcessingStatus,
) -> bool:
    """Return whether a processing-status transition is permitted."""

    return target in _ALLOWED_TRANSITIONS[current]


def ensure_transition_allowed(
    current: ProcessingStatus,
    target: ProcessingStatus,
) -> None:
    """Raise when a processing-status transition is not permitted."""

    if not can_transition(current, target):
        raise InvalidStatusTransitionError(
            f"transition from {current.value} to {target.value} is not permitted"
        )
