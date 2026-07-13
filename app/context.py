"""Per-request GraphQL context.

Strawberry calls `get_context()` once per request and hands the result
to every resolver via `info.context`. This is the idiomatic way to do
dependency injection (db sessions, the current user, request-scoped
caches, dataloaders) instead of resolvers reaching for globals.
"""

from __future__ import annotations

from strawberry.dataloader import DataLoader
from strawberry.fastapi import BaseContext

from app.data_store import DataStore
from app.models import Author

# A single shared store for this example. In a real app this would
# typically be a request-scoped DB session instead of a process-wide
# singleton.
_store = DataStore()


async def _load_authors(ids: list[int]) -> list[Author | None]:
    return _store.get_authors_by_ids(ids)


class Context(BaseContext):
    """Subclasses strawberry's BaseContext, which FastAPI integration
    requires (it carries the current request/response through too)."""

    def __init__(self, store: DataStore, author_loader: DataLoader[int, Author | None]) -> None:
        super().__init__()
        self.store = store
        self.author_loader = author_loader


async def get_context() -> Context:
    # A fresh DataLoader per request: its cache and batching window must
    # not leak across requests, unlike `_store`, which is stateless data
    # and safe to share.
    return Context(store=_store, author_loader=DataLoader(load_fn=_load_authors))
