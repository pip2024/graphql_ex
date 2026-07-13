from __future__ import annotations

import strawberry
from strawberry.types import Info

from app.context import Context
from app.schema.types import Author, Book


@strawberry.type
class Query:
    @strawberry.field(description="Every book in the catalog.")
    def books(self, info: Info[Context, None]) -> list[Book]:
        return [Book.from_model(m) for m in info.context.store.list_books()]

    @strawberry.field(description="A single book by id, or null if it doesn't exist.")
    def book(self, info: Info[Context, None], id: strawberry.ID) -> Book | None:
        model = info.context.store.get_book(int(id))
        return Book.from_model(model) if model else None

    @strawberry.field(description="Every author.")
    def authors(self, info: Info[Context, None]) -> list[Author]:
        return [Author.from_model(m) for m in info.context.store.list_authors()]

    @strawberry.field(description="A single author by id, or null if they don't exist.")
    def author(self, info: Info[Context, None], id: strawberry.ID) -> Author | None:
        model = info.context.store.get_author(int(id))
        return Author.from_model(model) if model else None
