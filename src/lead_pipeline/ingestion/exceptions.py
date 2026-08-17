"""Exceptions raised by ingestion adapters."""


class IngestionError(Exception):
    """Base exception for ingestion failures."""


class WebhookVerificationError(IngestionError):
    """Base exception for webhook verification failures."""


class InvalidCallbackVerificationError(WebhookVerificationError):
    """Raised when Meta callback verification fails."""


class InvalidWebhookSignatureError(WebhookVerificationError):
    """Raised when a webhook request signature is invalid."""


class WebhookPayloadError(IngestionError):
    """Base exception for invalid webhook request bodies."""


class InvalidWebhookPayloadError(WebhookPayloadError):
    """Raised when a webhook body is not a valid JSON object."""


class WebhookPayloadTooLargeError(WebhookPayloadError):
    """Raised when a webhook body exceeds the configured limit."""


class UnauthorizedWebhookAccountError(IngestionError):
    """Raised when an event belongs to another Instagram account."""
