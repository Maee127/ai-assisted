"""Persistence interfaces used by the application layer."""

from datetime import datetime
from typing import Protocol

from lead_pipeline.domain.catalogue import CatalogueItem
from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.enums import ProcessingStatus
from lead_pipeline.domain.identifiers import ClientId, InstagramEventId
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.domain.unresolved import UnresolvedRecord


class InteractionRepository(Protocol):
    """Persistence boundary for authorized Instagram interactions."""

    def add(self, interaction: InstagramInteraction) -> None:
        """Persist an interaction idempotently."""

        ...

    def get_by_event_id(
        self,
        event_id: InstagramEventId,
    ) -> InstagramInteraction | None:
        """Return an interaction by its stable event identifier."""

        ...


class ClassificationRepository(Protocol):
    """Persistence boundary for versioned classification results."""

    def add(
        self,
        *,
        source_event_id: InstagramEventId,
        client_id: ClientId,
        result: ClassificationResult,
        created_at: datetime,
    ) -> str:
        """Persist a classification and return its generated identifier."""

        ...


class UnresolvedRecordRepository(Protocol):
    """Persistence boundary for double-uncertain classifications."""

    def add(
        self,
        *,
        record: UnresolvedRecord,
        primary_classification_id: str,
        stronger_classification_id: str,
    ) -> str:
        """Persist an unresolved record and return its identifier."""

        ...


class InteractionStatusRepository(Protocol):
    """Persistence boundary for interaction lifecycle transitions."""

    def transition_status(
        self,
        *,
        event_id: InstagramEventId,
        target: ProcessingStatus,
    ) -> None:
        """Apply one permitted processing-status transition."""

        ...


class CatalogueRepository(Protocol):
    """Persistence and retrieval boundary for client-owned catalogues."""

    def upsert(self, item: CatalogueItem) -> None:
        """Insert or update one item inside its client boundary."""

        ...

    def search(
        self,
        *,
        client_id: ClientId,
        query: str,
        limit: int = 5,
    ) -> tuple[CatalogueItem, ...]:
        """Return relevant items only from the specified client catalogue."""

        ...
