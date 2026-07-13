"""GraphQL types.

Each type wraps a domain model (`app.models`) via a `from_model`
constructor rather than inheriting from it directly. That keeps the
GraphQL shape (what clients see) free to diverge from the storage
shape (e.g. renaming/hiding fields) without touching `app.models`.
"""

from __future__ import annotations

import strawberry
from strawberry.types import Info

from app.context import Context
from app.models import Author as AuthorModel
from app.models import Book as BookModel


@strawberry.type
class Author:
    id: strawberry.ID
    name: str
    country: str

    @strawberry.field(description="Books written by this author.")
    def books(self, info: Info[Context, None]) -> list[Book]:
        models = info.context.store.list_books_by_author(int(self.id))
        return [Book.from_model(m) for m in models]

    @classmethod
    def from_model(cls, model: AuthorModel) -> Author:
        return cls(id=strawberry.ID(str(model.id)), name=model.name, country=model.country)


@strawberry.type
class Book:
    id: strawberry.ID
    title: str
    published_year: int
    # strawberry.Private fields are ordinary Python attributes that are
    # *not* exposed as GraphQL fields — useful for carrying data a
    # resolver needs (like a foreign key) without leaking it in the schema.
    _author_id: strawberry.Private[int]

    @strawberry.field(description="The author who wrote this book.")
    def author(self, info: Info[Context, None]) -> Author:
        model = info.context.store.get_author(self._author_id)
        if model is None:
            # Data-integrity invariant, not a client-facing error: every
            # stored book always has a valid author_id.
            raise RuntimeError(f"Book {self.id} references missing author {self._author_id}")
        return Author.from_model(model)

    @classmethod
    def from_model(cls, model: BookModel) -> Book:
        return cls(
            id=strawberry.ID(str(model.id)),
            title=model.title,
            published_year=model.published_year,
            _author_id=model.author_id,
        )
