"""Mutations.

`add_book` demonstrates the "errors as data" pattern: instead of
raising a Python exception (which GraphQL turns into a top-level
`errors` array and a `null` result — hard for clients to branch on),
expected failure cases are modeled as part of the return type via a
union. Clients query `__typename` to see which case they got. Reserve
raised exceptions for truly unexpected failures (bugs, infra errors).
"""

from __future__ import annotations

from typing import Annotated

import strawberry
from strawberry.types import Info

from app.context import Context
from app.schema.types import Book


@strawberry.input
class AddBookInput:
    title: str
    published_year: int
    author_id: strawberry.ID


@strawberry.type
class AuthorNotFoundError:
    message: str


AddBookResult = Annotated[Book | AuthorNotFoundError, strawberry.union("AddBookResult")]


@strawberry.type
class Mutation:
    @strawberry.mutation(description="Add a new book to the catalog.")
    async def add_book(self, info: Info[Context, None], input: AddBookInput) -> AddBookResult:
        store = info.context.store
        if store.get_author(int(input.author_id)) is None:
            return AuthorNotFoundError(message=f"No author with id {input.author_id}")

        model = store.add_book(
            title=input.title,
            published_year=input.published_year,
            author_id=int(input.author_id),
        )
        # Notifies any active `bookAdded` subscribers — see app/schema/subscriptions.py.
        await info.context.broadcaster.publish(model)
        return Book.from_model(model)
