"""Processing-status transition rules."""

from lead_pipeline.domain.enums import ProcessingStatus

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
