"""Domain model for client-owned catalogue items."""

from dataclasses import dataclass

from lead_pipeline.domain.identifiers import CatalogueItemId, ClientId


@dataclass(frozen=True, slots=True)
class CatalogueItem:
    """One searchable item within an isolated client catalogue."""

    catalogue_item_id: CatalogueItemId
    client_id: ClientId
    name: str
    category: str
    description: str

    def __post_init__(self) -> None:
        normalized_name = self.name.strip()
        normalized_category = self.category.strip()
        normalized_description = self.description.strip()

        if not normalized_name:
            raise ValueError("name must not be empty")

        if not normalized_category:
            raise ValueError("category must not be empty")

        if not normalized_description:
            raise ValueError("description must not be empty")

        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "category", normalized_category)
        object.__setattr__(self, "description", normalized_description)


@dataclass(frozen=True, slots=True)
class CatalogueContext:
    """Immutable catalogue evidence for one client classification."""

    client_id: ClientId
    items: tuple[CatalogueItem, ...] = ()

    def __post_init__(self) -> None:
        normalized_items = tuple(self.items)

        if any(item.client_id != self.client_id for item in normalized_items):
            raise ValueError("catalogue items must belong to the context client")

        object.__setattr__(self, "items", normalized_items)
