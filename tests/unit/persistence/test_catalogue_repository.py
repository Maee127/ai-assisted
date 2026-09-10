"""Tests for the SQLAlchemy catalogue repository."""

from typing import cast
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from lead_pipeline.domain.catalogue import CatalogueItem
from lead_pipeline.domain.identifiers import CatalogueItemId, ClientId
from lead_pipeline.persistence.models import CatalogueItemRow
from lead_pipeline.persistence.sqlalchemy_repositories import (
    SqlAlchemyCatalogueRepository,
)


def build_item(
    *,
    client_id: str = "client-1",
    item_id: str = "item-1",
    name: str = "Vitamin C Serum",
    category: str = "Serums",
    description: str = "Brightening serum for dull-looking skin.",
) -> CatalogueItem:
    return CatalogueItem(
        catalogue_item_id=CatalogueItemId(item_id),
        client_id=ClientId(client_id),
        name=name,
        category=category,
        description=description,
    )


def build_row() -> CatalogueItemRow:
    return CatalogueItemRow(
        client_id="client-1",
        catalogue_item_id="item-1",
        name="Vitamin C Serum",
        category="Serums",
        description="Brightening serum for dull-looking skin.",
    )


def test_upsert_adds_new_catalogue_item() -> None:
    session = Mock(spec=Session)
    session.get.return_value = None
    repository = SqlAlchemyCatalogueRepository(session=session)

    repository.upsert(build_item())

    session.get.assert_called_once_with(
        CatalogueItemRow,
        ("client-1", "item-1"),
    )
    session.add.assert_called_once()

    row = cast(CatalogueItemRow, session.add.call_args.args[0])

    assert row.client_id == "client-1"
    assert row.catalogue_item_id == "item-1"
    assert row.name == "Vitamin C Serum"
    assert row.category == "Serums"
    assert row.description == "Brightening serum for dull-looking skin."
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_upsert_updates_existing_catalogue_item() -> None:
    session = Mock(spec=Session)
    row = build_row()
    session.get.return_value = row
    repository = SqlAlchemyCatalogueRepository(session=session)

    repository.upsert(
        build_item(
            name="Updated Serum",
            category="Treatments",
            description="Updated description.",
        )
    )

    assert row.name == "Updated Serum"
    assert row.category == "Treatments"
    assert row.description == "Updated description."
    session.add.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_search_maps_rows_to_domain_items() -> None:
    session = Mock(spec=Session)
    session.scalars.return_value.all.return_value = [build_row()]
    repository = SqlAlchemyCatalogueRepository(session=session)

    items = repository.search(
        client_id=ClientId("client-1"),
        query="vitamin serum",
    )

    assert items == (build_item(),)
    session.scalars.assert_called_once()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_search_statement_contains_client_boundary() -> None:
    session = Mock(spec=Session)
    session.scalars.return_value.all.return_value = []
    repository = SqlAlchemyCatalogueRepository(session=session)

    repository.search(
        client_id=ClientId("client-1"),
        query="serum",
    )

    statement = session.scalars.call_args.args[0]
    compiled = statement.compile()

    assert "client-1" in compiled.params.values()


@pytest.mark.parametrize(
    "query",
    ["", "   ", "\t", "\n", "---", "😍"],
)
def test_search_without_terms_returns_empty_result(query: str) -> None:
    session = Mock(spec=Session)
    repository = SqlAlchemyCatalogueRepository(session=session)

    items = repository.search(
        client_id=ClientId("client-1"),
        query=query,
    )

    assert items == ()
    session.scalars.assert_not_called()


@pytest.mark.parametrize("limit", [0, -1, 21])
def test_search_rejects_limit_outside_range(limit: int) -> None:
    session = Mock(spec=Session)
    repository = SqlAlchemyCatalogueRepository(session=session)

    with pytest.raises(ValueError, match="limit must be between 1 and 20"):
        repository.search(
            client_id=ClientId("client-1"),
            query="serum",
            limit=limit,
        )

    session.scalars.assert_not_called()
