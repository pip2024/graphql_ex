"""In-memory pub/sub backing the `bookAdded` subscription.

A subscriber is just an `asyncio.Queue`: `subscribe()` registers one and
yields whatever arrives on it; `publish()` fans a new item out to every
registered queue. This is enough to demonstrate the GraphQL subscription
contract in a single process. A real deployment running multiple server
processes would back this with something shared across processes instead
(Redis pub/sub, a message queue, a DB change stream), since this
in-memory list only sees subscribers connected to the same process.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from app.models import Book


class BookBroadcaster:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[Book]] = []

    def subscriber_count(self) -> int:
        return len(self._subscribers)

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
