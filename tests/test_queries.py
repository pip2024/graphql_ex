from app.context import Context
from app.schema.schema import schema


async def test_books_query(context: Context) -> None:
    result = await schema.execute("{ books { title } }", context_value=context)

    assert result.errors is None
    assert {"title": "The Left Hand of Darkness"} in result.data["books"]


async def test_book_by_id_includes_nested_author(context: Context) -> None:
    query = "query($id: ID!) { book(id: $id) { title author { name } } }"

    result = await schema.execute(query, variable_values={"id": "1"}, context_value=context)

    assert result.errors is None
    assert result.data["book"]["title"] == "The Left Hand of Darkness"
    assert result.data["book"]["author"]["name"] == "Ursula K. Le Guin"


async def test_unknown_book_returns_null_not_an_error(context: Context) -> None:
    query = "query($id: ID!) { book(id: $id) { title } }"

    result = await schema.execute(query, variable_values={"id": "999"}, context_value=context)

    assert result.errors is None
    assert result.data["book"] is None
