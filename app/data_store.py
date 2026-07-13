"""In-memory 'repository' standing in for a real database.

The point isn't the storage mechanism — it's the shape of the interface
(get_*, list_*, add_*). Swap this class for one backed by SQLAlchemy,
an ORM, or an HTTP client and nothing in schema/ has to change, because
resolvers only ever talk to this interface, never to storage directly.
"""

from __future__ import annotations

from app.models import Author, Book


class DataStore:
    def __init__(self) -> None:
        self._authors: dict[int, Author] = {
            1: Author(id=1, name="Ursula K. Le Guin", country="USA"),
            2: Author(id=2, name="Ted Chiang", country="USA"),
        }
        self._books: dict[int, Book] = {
            1: Book(id=1, title="The Left Hand of Darkness", published_year=1969, author_id=1),
            2: Book(id=2, title="The Dispossessed", published_year=1974, author_id=1),
            3: Book(id=3, title="Exhalation", published_year=2019, author_id=2),
        }
        self._next_book_id = max(self._books) + 1

    def list_books(self) -> list[Book]:
        return list(self._books.values())

    def get_book(self, book_id: int) -> Book | None:
        return self._books.get(book_id)

    def list_authors(self) -> list[Author]:
        return list(self._authors.values())

    def get_author(self, author_id: int) -> Author | None:
        return self._authors.get(author_id)

    def get_authors_by_ids(self, ids: list[int]) -> list[Author | None]:
        """Batch lookup for DataLoader: result order/length must match `ids`."""
        return [self._authors.get(author_id) for author_id in ids]

    def list_books_by_author(self, author_id: int) -> list[Book]:
        return [book for book in self._books.values() if book.author_id == author_id]

    def add_book(self, title: str, published_year: int, author_id: int) -> Book:
        book = Book(
            id=self._next_book_id,
            title=title,
            published_year=published_year,
            author_id=author_id,
        )
        self._books[book.id] = book
        self._next_book_id += 1
        return book
