"""Exceptions raised by ingestion adapters."""


class IngestionError(Exception):
    """Base exception for ingestion failures."""


class WebhookVerificationError(IngestionError):
    """Base exception for webhook verification failures."""


class InvalidCallbackVerificationError(WebhookVerificationError):
    """Raised when Meta callback verification fails."""


class InvalidWebhookSignatureError(WebhookVerificationError):
    """Raised when a webhook request signature is invalid."""
