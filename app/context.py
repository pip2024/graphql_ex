"""Per-request GraphQL context.

Strawberry calls `get_context()` once per request and hands the result
to every resolver via `info.context`. This is the idiomatic way to do
dependency injection (db sessions, the current user, request-scoped
caches, dataloaders) instead of resolvers reaching for globals.
"""

from __future__ import annotations

from strawberry.fastapi import BaseContext

from app.data_store import DataStore

# A single shared store for this example. In a real app this would
# typically be a request-scoped DB session instead of a process-wide
# singleton.
_store = DataStore()


class Context(BaseContext):
    """Subclasses strawberry's BaseContext, which FastAPI integration
    requires (it carries the current request/response through too)."""

    def __init__(self, store: DataStore) -> None:
        super().__init__()
        self.store = store


async def get_context() -> Context:
    return Context(store=_store)
