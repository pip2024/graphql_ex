# Subscriptions: bookAdded over WebSocket

Walkthrough of adding the third GraphQL operation type — a `bookAdded`
subscription that pushes to clients whenever `addBook` succeeds — on
top of the existing DataLoader-batched query/mutation setup.

Follows the same flow as the DataLoader note: bottom layer up through
the resolver, then wiring, then tests, then live proof.

## 1. `app/broadcaster.py` — the missing piece Strawberry doesn't provide

Subscriptions need something to notify them when new data shows up.
Strawberry has no built-in pub/sub, so `BookBroadcaster` fills that gap
with the simplest possible mechanism: a list of `asyncio.Queue`s.

```python
async def subscribe(self) -> AsyncGenerator[Book, None]:
    queue: asyncio.Queue[Book] = asyncio.Queue()
    self._subscribers.append(queue)
    try:
        while True:
            yield await queue.get()
    finally:
        self._subscribers.remove(queue)

async def publish(self, book: Book) -> None:
    for queue in self._subscribers:
        await queue.put(book)
```

`subscribe()` hands each caller their own private queue and registers
it, then blocks on `queue.get()` forever, yielding whatever lands
there. `publish()` just pushes into every registered queue. The
`finally` block deregisters the queue when a subscriber disconnects
(the generator gets closed) — without it, disconnected clients would
silently accumulate as dead queues forever.

## 2. `app/context.py` — shared, not per-request

```python
_store = DataStore()
_broadcaster = BookBroadcaster()
```

This is the one deliberate asymmetry versus the `DataLoader` (see
[[dataloader]]): the `DataLoader` is rebuilt fresh on every request
(its cache must never leak between requests), but `_broadcaster` is a
**module-level singleton**, same as `_store`. That's not an oversight —
a subscription connection and the mutation that triggers it are two
*separate* requests entirely. If the broadcaster were rebuilt
per-request, a subscriber's queue would only ever be visible to its own
request, and no mutation from any other connection could ever reach
it. Sharing it is what makes cross-connection notification possible at
all.

## 3. `app/schema/mutations.py` — where a change becomes an event

One line added to `add_book`, right after the book is actually stored:

```python
await info.context.broadcaster.publish(model)
```

This is the moment a plain CRUD write turns into a broadcast event.
Note it publishes the *domain model* (`app.models.Book`), not the
GraphQL type — consistent with the rest of the project's layering,
where `app/models.py` stays GraphQL-agnostic and the `schema/` layer is
responsible for converting to/from it.

## 4. `app/schema/subscriptions.py` — the resolver shape unique to subscriptions

```python
@strawberry.type
class Subscription:
    @strawberry.subscription(description="Fires whenever a new book is added to the catalog.")
    async def book_added(self, info: Info[Context, None]) -> AsyncGenerator[Book, None]:
        async for model in info.context.broadcaster.subscribe():
            yield Book.from_model(model)
```

This is the first resolver in the project that `yield`s instead of
`return`s. A `Query`/`Mutation` resolver runs once and produces one
value; a `@strawberry.subscription` resolver is an async generator — it
stays alive for the life of the connection, producing a new value
every time the underlying `async for` gets one from the broadcaster.
Strawberry treats this operation type differently end-to-end: it's the
trigger for registering a WebSocket route at all.

## 5. `app/schema/schema.py` — one line to complete the trio

```python
schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)
```

Query, Mutation, Subscription — the three GraphQL root operation
types, now all present. Nothing else needed changing in `app/main.py`:
`strawberry.fastapi.GraphQLRouter` inspects the schema and
automatically registers a WebSocket endpoint at the same `/graphql`
path the moment a `subscription=` is present, using the same
`context_getter=get_context` dependency already wired up for HTTP.

## 6. Tests — proving delivery without a real network socket

`tests/test_subscriptions.py` exercises the resolver through
`schema.subscribe(...)` directly (no HTTP/WebSocket involved), but
subscriptions raise a testing wrinkle queries/mutations don't: a
subscription doesn't produce its value until something publishes to
it, and that publish has to happen *after* the subscriber has actually
registered — otherwise the event fires into an empty room.

```python
receive_task = asyncio.create_task(subscription.__anext__())
while context.broadcaster.subscriber_count() == 0:
    await asyncio.sleep(0)

await schema.execute(ADD_BOOK_MUTATION, ...)
result = await receive_task
```

Rather than guessing at event-loop scheduling order (fragile), the
test polls `subscriber_count()` until the registration has actually
happened, *then* fires the mutation. That's why `subscriber_count()`
exists on `BookBroadcaster` at all — it's there specifically to make
this race observable and testable rather than assumed. Ran it 8 times
back-to-back with no flakiness.

## 7. Live verification — the one that isn't just theory

Unit tests calling `schema.subscribe()` directly prove the resolver
logic works, but they never touch
`strawberry.fastapi.GraphQLRouter`'s actual WebSocket handling. So a
throwaway script drove the real thing: started the actual `uvicorn`
server, opened a genuine WebSocket to `/graphql` using the
`graphql-transport-ws` subprotocol, sent the real
`connection_init`/`subscribe` handshake messages, fired `addBook` as an
ordinary HTTP POST from a second connection, and confirmed the
WebSocket received a `next` message carrying the new book — full
stack, not just the schema layer.
