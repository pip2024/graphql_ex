import pytest

from app.context import Context
from app.data_store import DataStore


@pytest.fixture
def context() -> Context:
    """A fresh, isolated store per test — no shared state between tests."""
    return Context(store=DataStore())
