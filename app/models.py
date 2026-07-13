"""Plain Python domain models.

These know nothing about GraphQL. Keeping them separate from the
`schema/` package means the schema layer can change (or be replaced
with a different GraphQL library entirely) without touching business
data, and the domain layer can be unit tested with no GraphQL machinery
involved at all.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Author:
    id: int
    name: str
    country: str


@dataclass
class Book:
    id: int
    title: str
    published_year: int
    author_id: int
