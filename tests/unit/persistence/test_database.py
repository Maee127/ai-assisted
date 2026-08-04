"""Tests for the SQLAlchemy database foundation."""

from lead_pipeline.persistence.database import NAMING_CONVENTION, Base


def test_base_uses_expected_naming_convention() -> None:
    assert Base.metadata.naming_convention == NAMING_CONVENTION


def test_naming_convention_contains_required_constraint_types() -> None:
    assert NAMING_CONVENTION == {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
