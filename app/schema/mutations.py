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

MIN_PUBLISHED_YEAR = 1
MAX_PUBLISHED_YEAR = 2100


@strawberry.input
class AddBookInput:
    title: str
    published_year: int
    author_id: strawberry.ID


@strawberry.type
class AuthorNotFoundError:
    message: str


@strawberry.type
class InvalidInputError:
    message: str


AddBookResult = Annotated[
    Book | AuthorNotFoundError | InvalidInputError, strawberry.union("AddBookResult")
]


@strawberry.type
class Mutation:
    @strawberry.mutation(description="Add a new book to the catalog.")
    async def add_book(self, info: Info[Context, None], input: AddBookInput) -> AddBookResult:
        title = input.title.strip()
        if not title:
            return InvalidInputError(message="title must not be empty")
        if not MIN_PUBLISHED_YEAR <= input.published_year <= MAX_PUBLISHED_YEAR:
            return InvalidInputError(
                message=(
                    f"publishedYear must be between {MIN_PUBLISHED_YEAR} "
                    f"and {MAX_PUBLISHED_YEAR}"
                )
            )

        try:
            author_id = int(input.author_id)
        except ValueError:
            # Finding: `strawberry.ID` is just a string scalar to GraphQL, so
            # it has no way to enforce "this must be numeric" — a value like
            # authorId: "not-numeric" sails straight past schema validation.
            # Before this fix, `int(input.author_id)` below raised an
            # uncaught ValueError, which surfaced to the client as a bare,
            # unhandled GraphQLError carrying Python's internal exception
            # text — not the typed error a caller would expect, and a minor
            # information leak. Caught here and folded into the same
            # errors-as-data union as every other bad-input case.
            return InvalidInputError(message=f"authorId must be numeric, got {input.author_id!r}")

        store = info.context.store
        if store.get_author(author_id) is None:
            return AuthorNotFoundError(message=f"No author with id {author_id}")

        model = store.add_book(
            title=title,
            published_year=input.published_year,
            author_id=author_id,
        )
        # Notifies any active `bookAdded` subscribers — see app/schema/subscriptions.py.
        await info.context.broadcaster.publish(model)
        return Book.from_model(model)
