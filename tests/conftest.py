import pytest
from strawberry.dataloader import DataLoader

from app.context import Context
from app.data_store import DataStore
from app.models import Author


@pytest.fixture
def context() -> Context:
    """A fresh, isolated store (and loader) per test — no shared state between tests."""
    store = DataStore()

    async def load_authors(ids: list[int]) -> list[Author | None]:
        return store.get_authors_by_ids(ids)

    return Context(store=store, author_loader=DataLoader(load_fn=load_authors))
