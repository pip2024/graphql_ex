"""Subscriptions.

The third GraphQL operation type alongside Query and Mutation: instead
of a single request/response, a client opens a persistent connection
(WebSocket, handled automatically by `strawberry.fastapi.GraphQLRouter`)
and receives a stream of values over time. A subscription resolver is
an async generator — it `yield`s a value each time there's something
new to send, rather than `return`ing once.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import strawberry
from strawberry.types import Info

from app.context import Context
from app.schema.types import Book


@strawberry.type
class Subscription:
    @strawberry.subscription(description="Fires whenever a new book is added to the catalog.")
    async def book_added(self, info: Info[Context, None]) -> AsyncGenerator[Book, None]:
        async for model in info.context.broadcaster.subscribe():
            yield Book.from_model(model)
