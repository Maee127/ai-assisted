"""Domain enumerations for the lead intelligence pipeline."""

from enum import StrEnum


class SourceType(StrEnum):
    """Supported Instagram interaction sources."""

    POST_COMMENT = "POST_COMMENT"
    REEL_COMMENT = "REEL_COMMENT"
    MENTION = "MENTION"


class ClassificationLabel(StrEnum):
    """Permitted top-level classification outcomes."""

    SALES_LEAD = "SALES_LEAD"
    CUSTOMER_CARE = "CUSTOMER_CARE"
    IRRELEVANT = "IRRELEVANT"
    SPAM = "SPAM"
    UNCERTAIN = "UNCERTAIN"


class InterestType(StrEnum):
    """How a beauty-related interest was identified."""

    EXPLICIT = "EXPLICIT"
    INFERRED = "INFERRED"


class ProcessingStatus(StrEnum):
    """High-level lifecycle states for an accepted interaction."""

    RECEIVED = "RECEIVED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"
