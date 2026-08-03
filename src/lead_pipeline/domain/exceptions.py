"""Domain-specific exceptions."""


class DomainError(Exception):
    """Base exception for domain-rule violations."""


class InvalidStatusTransitionError(DomainError):
    """Raised when a processing-status transition is not permitted."""
