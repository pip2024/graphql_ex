"""Per-request GraphQL context.

Strawberry calls `get_context()` once per request and hands the result
to every resolver via `info.context`. This is the idiomatic way to do
dependency injection (db sessions, the current user, request-scoped
caches, dataloaders) instead of resolvers reaching for globals.
"""

from __future__ import annotations

from strawberry.dataloader import DataLoader
from strawberry.fastapi import BaseContext

from app.broadcaster import BookBroadcaster
from app.data_store import DataStore
from app.models import Author

# Shared across requests: `_store` is stateless data, and `_broadcaster`
# must stay the same instance across connections for a subscriber in one
# request to see a mutation published from another.
_store = DataStore()
_broadcaster = BookBroadcaster()


async def _load_authors(ids: list[int]) -> list[Author | None]:
    return _store.get_authors_by_ids(ids)


class Context(BaseContext):
    """Subclasses strawberry's BaseContext, which FastAPI integration
    requires (it carries the current request/response through too)."""

    def __init__(
        self,
        store: DataStore,
        author_loader: DataLoader[int, Author | None],
        broadcaster: BookBroadcaster,
    ) -> None:
        super().__init__()
        self.store = store
        self.author_loader = author_loader
        self.broadcaster = broadcaster


async def get_context() -> Context:
    # A fresh DataLoader per request: its cache and batching window must
    # not leak across requests, unlike `_store`/`_broadcaster`, which are
    # shared on purpose (see above).
    return Context(
        store=_store,
        author_loader=DataLoader(load_fn=_load_authors),
        broadcaster=_broadcaster,
    )
