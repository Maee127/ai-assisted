"""Exceptions raised by persistence adapters."""


class PersistenceError(Exception):
    """Base exception for persistence failures."""


class InteractionNotFoundError(PersistenceError):
    """Raised when a requested interaction does not exist."""
