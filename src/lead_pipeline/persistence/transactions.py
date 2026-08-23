"""SQLAlchemy transaction-factory contracts."""

from contextlib import AbstractContextManager
from typing import Protocol

from sqlalchemy.orm import Session


class SessionTransactionFactory(Protocol):
    """Create request-scoped SQLAlchemy transaction contexts."""

    def begin(self) -> AbstractContextManager[Session]:
        """Return a context that commits or rolls back one transaction."""

        ...
