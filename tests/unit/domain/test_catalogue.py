"""Tests for client-owned catalogue items."""

import pytest

from lead_pipeline.domain.catalogue import CatalogueItem
from lead_pipeline.domain.identifiers import CatalogueItemId, ClientId


def build_item(**overrides: object) -> CatalogueItem:
    values: dict[str, object] = {
        "catalogue_item_id": CatalogueItemId("item-1"),
        "client_id": ClientId("client-1"),
        "name": "  Vitamin C Serum  ",
        "category": "  Serums  ",
        "description": "  Brightening serum for dull-looking skin.  ",
    }
    values.update(overrides)

    return CatalogueItem(**values)  # type: ignore[arg-type]


def test_catalogue_item_normalizes_text_fields() -> None:
    item = build_item()

    assert item.name == "Vitamin C Serum"
    assert item.category == "Serums"
    assert item.description == "Brightening serum for dull-looking skin."


@pytest.mark.parametrize(
    ("field_name", "message"),
    [
        ("name", "name must not be empty"),
        ("category", "category must not be empty"),
        ("description", "description must not be empty"),
    ],
)
def test_catalogue_item_rejects_blank_required_text(
    field_name: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_item(**{field_name: "   "})


def test_catalogue_item_preserves_client_boundary() -> None:
    item = build_item()

    assert item.client_id == ClientId("client-1")
    assert item.catalogue_item_id == CatalogueItemId("item-1")


def test_catalogue_item_is_immutable() -> None:
    item = build_item()

    with pytest.raises(AttributeError):
        item.name = "Changed"  # type: ignore[misc]
