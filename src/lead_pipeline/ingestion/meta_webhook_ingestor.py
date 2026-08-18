"""Orchestrate verified and minimized Meta webhook ingestion."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from lead_pipeline.application.ingest_interaction import IngestInteraction
from lead_pipeline.domain.identifiers import ClientId
from lead_pipeline.ingestion.meta_comment_extractor import (
    extract_comment_interactions,
)
from lead_pipeline.ingestion.webhook_payload import (
    parse_webhook_payload,
    validate_webhook_payload_size,
)
from lead_pipeline.ingestion.webhook_verification import (
    verify_webhook_signature,
)


@dataclass(slots=True)
class MetaWebhookIngestor:
    """Verify, minimize, and ingest authorized Meta webhook events."""

    app_secret: str
    client_id: ClientId
    authorized_business_account_id: str
    max_payload_bytes: int
    ingest_interaction: IngestInteraction
    clock: Callable[[], datetime]

    def ingest(
        self,
        *,
        raw_body: bytes,
        signature: str | None,
    ) -> int:
        """Ingest accepted interactions and return their extracted count."""

        validate_webhook_payload_size(
            raw_body=raw_body,
            max_payload_bytes=self.max_payload_bytes,
        )
        verify_webhook_signature(
            raw_body=raw_body,
            signature=signature,
            app_secret=self.app_secret,
        )
        payload = parse_webhook_payload(
            raw_body=raw_body,
            max_payload_bytes=self.max_payload_bytes,
        )
        interactions = extract_comment_interactions(
            payload=payload,
            client_id=self.client_id,
            authorized_business_account_id=(self.authorized_business_account_id),
            collected_at=self.clock(),
        )

        for interaction in interactions:
            self.ingest_interaction.execute(interaction)

        return len(interactions)
