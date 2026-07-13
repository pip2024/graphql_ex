# DataLoader: avoiding N+1 in Book.author

Walkthrough of how `app/schema/types.py`'s `Book.author` resolver was
converted from a direct store call to a batched `strawberry.dataloader.DataLoader`
lookup — the fix for the classic GraphQL N+1 problem.

Follows the shape of one request through the system — bottom layer
(data) up through the resolver, then how the tests had to adapt.

## 1. `app/data_store.py` — a batch-shaped lookup

Added one method next to the existing single-item `get_author`:

```python
def get_authors_by_ids(self, ids: list[int]) -> list[Author | None]:
    """Batch lookup for DataLoader: result order/length must match `ids`."""
    return [self._authors.get(author_id) for author_id in ids]
```

This exists because `DataLoader` has a strict contract: whatever function
you give it must take a list of keys and return a list of results **the
same length, in the same order** — including `None` for keys that don't
exist (missing keys can't just be silently dropped, or the alignment
breaks). This method is that batch-shaped version of `get_author`.

## 2. `app/context.py` — building the loader per-request

Two pieces changed here.

**A module-level batch function**, `_load_authors`, is the actual
function the `DataLoader` will call. It's `async` because `DataLoader`
requires an awaitable, even though the underlying lookup
(`_store.get_authors_by_ids`) is plain sync code.

**`Context` grew an `author_loader` field**, and `get_context()`
constructs a *brand-new* `DataLoader` on every single request:

```python
async def get_context() -> Context:
    return Context(store=_store, author_loader=DataLoader(load_fn=_load_authors))
```

This is the detail most worth internalizing: `_store` is a shared
module-level singleton (fine — it's just data), but the `DataLoader` is
**not** shared. A `DataLoader` caches every key it's ever loaded for as
long as it's alive. If it were a singleton like `_store`, request A's
cached results would silently leak into request B. So it's built fresh,
scoped to exactly one request's lifetime.

## 3. `app/schema/types.py` — the resolver that actually uses it

`Book.author` changed from calling the store directly to going through
the loader:

```python
async def author(self, info: Info[Context, None]) -> Author:
    model = await info.context.author_loader.load(self._author_id)
    if model is None:
        raise RuntimeError(...)
    return Author.from_model(model)
```

Two things had to change together here: the method became `async def`
(required, since `.load()` returns an awaitable), and the body calls
`.load(self._author_id)` instead of
`info.context.store.get_author(self._author_id)`.

The payoff: if a query resolves multiple books in the same request
(`{ books { author { name } } }`), each `Book.author` call queues its
`author_id` onto the loader instead of immediately hitting the store.
Once the event loop reaches the next tick with no more synchronous work
queued, `DataLoader` fires **one** call to `_load_authors` with *all*
the collected ids at once, then distributes the results back to each
waiting `.load()` call. That's the batching. It also caches within that
window — verified live: two books by the same author (Ursula K. Le
Guin, id 1) only triggered one underlying lookup for that id, not two.

## 4. Tests — the ripple effect of making one resolver async

This is the part that touched the most files, and it's a good
illustration of a general rule: **once any resolver in the graph is
async, the whole execution becomes async**, even if most of your
resolvers are still plain sync functions.

- `tests/conftest.py`: the `context` fixture now also builds a
  `DataLoader` bound to its own isolated `DataStore`, mirroring
  `get_context()`'s pattern but scoped per-test instead of per-request.
- `tests/test_queries.py` / `tests/test_mutations.py`: every test
  became `async def`, and `schema.execute_sync(...)` became
  `await schema.execute(...)`. `execute_sync` flatly can't run a query
  that touches an async resolver — it only works when the whole
  resolver tree is synchronous.

## 5. `pyproject.toml` — making the async tests runnable

Two additions to support step 4: `pytest-asyncio` as a dev dependency,
and

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

`asyncio_mode = "auto"` tells `pytest-asyncio` to treat every
`async def test_...` as a test to run on an event loop automatically —
without this, you'd need `@pytest.mark.asyncio` stacked on top of every
single test function.

## 6. `README.md` — documenting the *why*

Added a short "Avoiding N+1 with a DataLoader" section between the
architecture overview and the run instructions, so someone reading
top-to-bottom hits the concept before they hit the code that
implements it.

## The thread connecting all of it

Data layer needs a batch-shaped method → context needs to own a
per-request loader instance built from that method → the resolver
needs to be async to call it → everything that executes that resolver
(real requests via FastAPI, and tests via `schema.execute`) needs to be
async-aware too.
