# graphql-ex

A minimal but "real-shaped" GraphQL API in Python, built with
[Strawberry](https://strawberry.rocks/) (code-first, type-hint-driven)
and served over [FastAPI](https://fastapi.tiangolo.com/). The domain is
a tiny book catalog: `Author` → `Book`.

## Why this structure

```
app/
  models.py         # plain dataclasses — the domain, no GraphQL awareness
  data_store.py      # in-memory "repository" standing in for a real DB
  broadcaster.py      # in-memory pub/sub backing the bookAdded subscription
  context.py            # per-request context (dependency injection point)
  schema/
    types.py              # GraphQL types, each wrapping a domain model
    queries.py             # Query root
    mutations.py            # Mutation root
    subscriptions.py         # Subscription root
    schema.py                 # combines Query + Mutation + Subscription
  main.py                      # FastAPI app, mounts the schema at /graphql
tests/                          # tests execute the schema directly — no HTTP needed
scripts/export_schema.py         # writes schema.graphql (see "Exporting the schema")
```

The core idea worth taking away: **the domain model, the storage
layer, and the GraphQL layer are three separate concerns.** A resolver
never touches storage directly — it goes through `info.context.store`.
This is what lets you swap the in-memory store for a real database, or
swap Strawberry for a different library, without a rewrite.

## Avoiding N+1 with a DataLoader

Querying `{ books { author { name } } }` resolves `Book.author` once
per book returned. Calling the store directly there means one lookup
per book — fine here, but on a real database that's one query per row
(the classic GraphQL N+1 problem). `Book.author`
(`app/schema/types.py`) instead calls `info.context.author_loader.load(...)`,
a `strawberry.dataloader.DataLoader` (created per-request in
`app/context.py`) that collects every author id requested during one
tick of the event loop and fetches them in a single batched call to
`DataStore.get_authors_by_ids`. This is why the resolver is `async def`
— `DataLoader.load()` is awaitable, and batching only works across
concurrently-awaited calls.

## Subscriptions

The third GraphQL operation type, alongside Query and Mutation: instead
of one request/response, a client opens a persistent WebSocket
connection and receives a stream of values over time.
`Subscription.book_added` (`app/schema/subscriptions.py`) is an async
generator resolver — it `yield`s a `Book` every time one gets added,
rather than `return`ing once. It's fed by `app/broadcaster.py`, a
small in-memory pub/sub (a list of `asyncio.Queue`s); `Mutation.add_book`
publishes to it right after adding a book. A real, multi-process
deployment would back this with something shared across processes
instead — Redis pub/sub, a message queue, a DB change stream — since
this in-memory version only sees subscribers connected to the same
process.

`strawberry.fastapi.GraphQLRouter` (already mounted in `app/main.py`)
registers the WebSocket endpoint automatically at the same `/graphql`
path — no extra wiring needed. Try it in the GraphiQL UI: open two
browser tabs at http://127.0.0.1:8000/graphql, run this in the first...

```graphql
subscription {
  bookAdded {
    title
    publishedYear
  }
}
```

...then run the `addBook` mutation (see below) in the second tab and
watch the first tab receive the new book immediately.

## Running it

This project uses [uv](https://docs.astral.sh/uv/) to manage the
virtual environment and dependencies. Install it once (`pip install uv`
or see the [install docs](https://docs.astral.sh/uv/getting-started/installation/)),
then:

```bash
uv sync --extra dev

uv run uvicorn app.main:app --reload
```

`uv sync` creates and populates `.venv` automatically from
`pyproject.toml` — no manual activation step needed, since `uv run`
executes commands inside that environment for you.

Open http://127.0.0.1:8000/graphql — Strawberry serves an interactive
GraphiQL UI there. Try:

```graphql
query {
  books {
    title
    author {
      name
      country
    }
  }
}
```

```graphql
mutation {
  addBook(input: { title: "Ghost Book", publishedYear: 2024, authorId: "1" }) {
    __typename
    ... on Book {
      title
    }
    ... on AuthorNotFoundError {
      message
    }
  }
}
```

Try `authorId: "999"` in that mutation to see the typed-error branch —
see the "errors as data" note in `app/schema/mutations.py` for why it's
modeled as a union instead of a raised exception.

## Running the tests

```bash
uv run pytest
```

Tests call `schema.execute(...)` (or, for the subscription test,
`schema.subscribe(...)`) directly with a GraphQL query string — no HTTP
server or test client needed, which keeps them fast and makes them a
good place to learn how a resolver behaves in isolation.

## Coding style / lint

```bash
uv run ruff check .
uv run ruff format .
```

## Exporting the schema for another team

A GraphQL schema is a contract. Once other teams build against it —
generating a typed client, wiring up a gateway, feeding a schema
registry, or just reading it to know what's available — you want a
plain `.graphql` SDL file they can consume without running your Python
code. Strawberry can produce that file two ways:

**1. CLI (simplest, good for local/manual use):**

```bash
uv run strawberry export-schema app.schema.schema:schema > schema.graphql
```

**2. Script (`scripts/export_schema.py`, good for CI):**

```bash
uv run python scripts/export_schema.py
```

Both produce the same SDL, e.g.:

```graphql
type Author {
  id: ID!
  name: String!
  country: String!
  books: [Book!]!
}

type Book {
  id: ID!
  title: String!
  publishedYear: Int!
  author: Author!
}
...
```

Typical uses for that file once you have it:

- **Commit it to the repo** (or a dedicated `schema/` repo) so a
  frontend team can review changes in a PR diff without running your
  service.
- **Publish it to a schema registry** (e.g. Apollo GraphOS, a WunderGraph
  registry, or an internal one) so consumers always resolve the latest
  contract.
- **Feed it to client codegen** — e.g. `graphql-codegen` for a
  TypeScript frontend, generating fully-typed query hooks from your
  schema plus their `.graphql` query documents.
- **Diff it in CI** between commits to catch breaking changes (removed
  fields, changed types) before they ship — tools like
  `graphql-inspector` do this directly against two SDL files.

Because the script (option 2) is just Python, it's easy to extend —
e.g. add a step that runs `graphql-inspector diff` against the
previous `schema.graphql` and fails CI on a breaking change.
