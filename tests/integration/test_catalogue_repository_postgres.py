"""PostgreSQL integration test for tenant-isolated catalogue retrieval."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker

from lead_pipeline.domain.catalogue import CatalogueItem
from lead_pipeline.domain.identifiers import CatalogueItemId, ClientId
from lead_pipeline.persistence.models import CatalogueItemRow
from lead_pipeline.persistence.sqlalchemy_repositories import (
    SqlAlchemyCatalogueRepository,
)


def get_test_database_url() -> str:
    """Return the opt-in integration database URL."""

    database_url = os.environ.get("TEST_DATABASE_URL")

    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    return database_url


def test_catalogue_search_is_ranked_and_isolated_by_client() -> None:
    database_url = get_test_database_url()
    test_id = str(uuid4())
    first_client = ClientId(f"catalogue-client-a-{test_id}")
    second_client = ClientId(f"catalogue-client-b-{test_id}")
    shared_item_id = CatalogueItemId(f"shared-item-{test_id}")

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )
    session_factory: sessionmaker[Session] = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    first_client_name_match = CatalogueItem(
        catalogue_item_id=shared_item_id,
        client_id=first_client,
        name="Vitamin C Serum",
        category="Serums",
        description="Brightening treatment for dull-looking skin.",
    )
    first_client_category_match = CatalogueItem(
        catalogue_item_id=CatalogueItemId(f"category-item-{test_id}"),
        client_id=first_client,
        name="Daily Moisturizer",
        category="Vitamin Care",
        description="Daily hydration for dry-looking skin.",
    )
    second_client_private_item = CatalogueItem(
        catalogue_item_id=shared_item_id,
        client_id=second_client,
        name="Private Vitamin C Serum",
        category="Serums",
        description="This item belongs only to the second client.",
    )

    try:
        with session_factory.begin() as session:
            repository = SqlAlchemyCatalogueRepository(session=session)
            repository.upsert(first_client_name_match)
            repository.upsert(first_client_category_match)
            repository.upsert(second_client_private_item)

        with Session(engine) as session:
            repository = SqlAlchemyCatalogueRepository(session=session)

            first_client_results = repository.search(
                client_id=first_client,
                query="vitamin",
                limit=20,
            )
            top_result = repository.search(
                client_id=first_client,
                query="vitamin",
                limit=1,
            )
            second_client_results = repository.search(
                client_id=second_client,
                query="vitamin",
                limit=20,
            )

        assert first_client_results == (
            first_client_name_match,
            first_client_category_match,
        )
        assert top_result == (first_client_name_match,)
        assert second_client_results == (second_client_private_item,)
        assert all(item.client_id == first_client for item in first_client_results)
    finally:
        with session_factory.begin() as session:
            session.execute(
                delete(CatalogueItemRow).where(
                    CatalogueItemRow.client_id.in_(
                        [
                            first_client.value,
                            second_client.value,
                        ]
                    )
                )
            )

        engine.dispose()
