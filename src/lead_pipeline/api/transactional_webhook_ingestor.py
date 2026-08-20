"""Transactional composition for Meta webhook ingestion."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy.orm import Session

from lead_pipeline.application.ingest_interaction import IngestInteraction
from lead_pipeline.domain.identifiers import ClientId
from lead_pipeline.ingestion.meta_webhook_ingestor import MetaWebhookIngestor
from lead_pipeline.persistence.sqlalchemy_repositories import (
    SqlAlchemyInteractionRepository,
)


class SessionTransactionFactory(Protocol):
    """Create request-scoped SQLAlchemy transaction contexts."""

    def begin(self) -> AbstractContextManager[Session]:
        """Return a context that commits or rolls back one transaction."""

        ...


@dataclass(slots=True)
class TransactionalMetaWebhookIngestor:
    """Persist one verified webhook delivery in one transaction."""

    session_factory: SessionTransactionFactory
    app_secret: str
    client_id: ClientId
    authorized_business_account_id: str
    max_payload_bytes: int
    clock: Callable[[], datetime]

    def ingest(
        self,
        *,
        raw_body: bytes,
        signature: str | None,
    ) -> int:
        """Verify, extract, and atomically persist one delivery."""

        with self.session_factory.begin() as session:
            repository = SqlAlchemyInteractionRepository(
                session=session,
            )
            use_case = IngestInteraction(
                repository=repository,
            )
            ingestor = MetaWebhookIngestor(
                app_secret=self.app_secret,
                client_id=self.client_id,
                authorized_business_account_id=(self.authorized_business_account_id),
                max_payload_bytes=self.max_payload_bytes,
                ingest_interaction=use_case,
                clock=self.clock,
            )

            return ingestor.ingest(
                raw_body=raw_body,
                signature=signature,
            )
