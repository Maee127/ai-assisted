"""Concrete SQLAlchemy persistence adapters."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session

from lead_pipeline.domain.catalogue import CatalogueItem
from lead_pipeline.domain.classification import ClassificationResult
from lead_pipeline.domain.enums import ProcessingStatus, SourceType
from lead_pipeline.domain.identifiers import (
    CatalogueItemId,
    ClientId,
    InstagramEventId,
    InstagramMediaId,
    InstagramUserId,
)
from lead_pipeline.domain.interactions import InstagramInteraction
from lead_pipeline.domain.status import ensure_transition_allowed
from lead_pipeline.domain.unresolved import UnresolvedRecord
from lead_pipeline.persistence.exceptions import InteractionNotFoundError
from lead_pipeline.persistence.models import (
    CatalogueItemRow,
    ClassificationRow,
    InteractionRow,
    UnresolvedRecordRow,
)

_CATALOGUE_TERM_PATTERN = re.compile(r"[a-z0-9]+")


def _catalogue_search_terms(query: str) -> tuple[str, ...]:
    normalized_query = query.strip().casefold()

    if not normalized_query:
        raise ValueError("query must not be empty")

    terms = tuple(dict.fromkeys(_CATALOGUE_TERM_PATTERN.findall(normalized_query)))

    if not terms:
        raise ValueError("query must contain searchable text")

    return terms


@dataclass(slots=True)
class SqlAlchemyCatalogueRepository:
    """Persist and retrieve items within one client catalogue."""

    session: Session

    def upsert(self, item: CatalogueItem) -> None:
        """Stage an insert or update without owning the transaction."""

        identity = (
            item.client_id.value,
            item.catalogue_item_id.value,
        )
        row = self.session.get(CatalogueItemRow, identity)

        if row is None:
            self.session.add(
                CatalogueItemRow(
                    client_id=item.client_id.value,
                    catalogue_item_id=item.catalogue_item_id.value,
                    name=item.name,
                    category=item.category,
                    description=item.description,
                )
            )
            return

        row.name = item.name
        row.category = item.category
        row.description = item.description

    def search(
        self,
        *,
        client_id: ClientId,
        query: str,
        limit: int = 5,
    ) -> tuple[CatalogueItem, ...]:
        """Return ranked lexical matches from only one client."""

        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")

        terms = _catalogue_search_terms(query)
        patterns = tuple(f"%{term}%" for term in terms)

        name_match = or_(
            *(CatalogueItemRow.name.ilike(pattern) for pattern in patterns)
        )
        category_match = or_(
            *(CatalogueItemRow.category.ilike(pattern) for pattern in patterns)
        )
        description_match = or_(
            *(CatalogueItemRow.description.ilike(pattern) for pattern in patterns)
        )

        relevance = (
            case((name_match, 3), else_=0)
            + case((category_match, 2), else_=0)
            + case((description_match, 1), else_=0)
        )

        statement = (
            select(CatalogueItemRow)
            .where(
                CatalogueItemRow.client_id == client_id.value,
                or_(name_match, category_match, description_match),
            )
            .order_by(
                relevance.desc(),
                CatalogueItemRow.name.asc(),
                CatalogueItemRow.catalogue_item_id.asc(),
            )
            .limit(limit)
        )

        rows = self.session.scalars(statement).all()

        return tuple(
            CatalogueItem(
                catalogue_item_id=CatalogueItemId(row.catalogue_item_id),
                client_id=ClientId(row.client_id),
                name=row.name,
                category=row.category,
                description=row.description,
            )
            for row in rows
        )


@dataclass(slots=True)
class SqlAlchemyInteractionRepository:
    """Persist interactions through an existing SQLAlchemy transaction."""

    session: Session

    def add(self, interaction: InstagramInteraction) -> None:
        """Stage an interaction unless its stable event ID already exists."""

        event_id = interaction.event_id.value

        if self.session.get(InteractionRow, event_id) is not None:
            return

        self.session.add(
            InteractionRow(
                event_id=event_id,
                client_id=interaction.client_id.value,
                user_id=interaction.user_id.value,
                media_id=interaction.media_id.value,
                source_type=interaction.source_type.value,
                text=interaction.text,
                source_timestamp=interaction.source_timestamp,
                collected_at=interaction.collected_at,
                processing_status=interaction.status.value,
                username=interaction.username,
            )
        )

    def get_by_event_id(
        self,
        event_id: InstagramEventId,
    ) -> InstagramInteraction | None:
        """Return an interaction by its stable event identifier."""

        row = self.session.get(
            InteractionRow,
            event_id.value,
        )

        if row is None:
            return None

        return InstagramInteraction(
            event_id=InstagramEventId(row.event_id),
            client_id=ClientId(row.client_id),
            user_id=InstagramUserId(row.user_id),
            media_id=InstagramMediaId(row.media_id),
            source_type=SourceType(row.source_type),
            text=row.text,
            source_timestamp=row.source_timestamp,
            collected_at=row.collected_at,
            status=ProcessingStatus(row.processing_status),
            username=row.username,
        )

    def transition_status(
        self,
        *,
        event_id: InstagramEventId,
        target: ProcessingStatus,
    ) -> None:
        """Apply one validated lifecycle transition."""

        row = self.session.get(
            InteractionRow,
            event_id.value,
        )

        if row is None:
            raise InteractionNotFoundError("interaction was not found")

        current = ProcessingStatus(row.processing_status)
        ensure_transition_allowed(current, target)
        row.processing_status = target.value


@dataclass(slots=True)
class SqlAlchemyClassificationRepository:
    """Persist versioned classifications in an existing transaction."""

    session: Session
    id_factory: Callable[[], UUID] = uuid4

    def add(
        self,
        *,
        source_event_id: InstagramEventId,
        client_id: ClientId,
        result: ClassificationResult,
        created_at: datetime,
    ) -> str:
        """Stage a classification and return its generated identifier."""

        if created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")

        classification_id = str(self.id_factory())

        self.session.add(
            ClassificationRow(
                classification_id=classification_id,
                source_event_id=source_event_id.value,
                client_id=client_id.value,
                label=result.label.value,
                confidence=result.confidence,
                reason=result.reason,
                model_name=result.model_name,
                model_version=result.model_version,
                prompt_version=result.prompt_version,
                created_at=created_at,
            )
        )

        return classification_id


@dataclass(slots=True)
class SqlAlchemyUnresolvedRecordRepository:
    """Persist unresolved outcomes in an existing transaction."""

    session: Session
    id_factory: Callable[[], UUID] = uuid4

    def add(
        self,
        *,
        record: UnresolvedRecord,
        primary_classification_id: str,
        stronger_classification_id: str,
    ) -> str:
        """Stage an unresolved record and return its generated identifier."""

        primary_id = primary_classification_id.strip()
        stronger_id = stronger_classification_id.strip()

        if not primary_id:
            raise ValueError("primary_classification_id must not be empty")

        if not stronger_id:
            raise ValueError("stronger_classification_id must not be empty")

        unresolved_id = str(self.id_factory())

        self.session.add(
            UnresolvedRecordRow(
                unresolved_id=unresolved_id,
                client_id=record.client_id.value,
                user_id=record.user_id.value,
                source_event_id=record.source_event_id.value,
                primary_classification_id=primary_id,
                stronger_classification_id=stronger_id,
                created_at=record.created_at,
            )
        )

        return unresolved_id
