from app.context import Context
from app.schema.schema import schema

ADD_BOOK_MUTATION = """
mutation($input: AddBookInput!) {
  addBook(input: $input) {
    __typename
    ... on Book {
      title
    }
    ... on AuthorNotFoundError {
      message
    }
    ... on InvalidInputError {
      message
    }
  }
}
"""


async def test_add_book_success(context: Context) -> None:
    variables = {
        "input": {"title": "Stories of Your Life", "publishedYear": 2002, "authorId": "2"}
    }

    result = await schema.execute(
        ADD_BOOK_MUTATION, variable_values=variables, context_value=context
    )

    assert result.errors is None
    assert result.data["addBook"]["__typename"] == "Book"
    assert result.data["addBook"]["title"] == "Stories of Your Life"


async def test_add_book_with_unknown_author_returns_typed_error(context: Context) -> None:
    variables = {"input": {"title": "Ghost Book", "publishedYear": 2024, "authorId": "999"}}

    result = await schema.execute(
        ADD_BOOK_MUTATION, variable_values=variables, context_value=context
    )

    assert result.errors is None
    assert result.data["addBook"]["__typename"] == "AuthorNotFoundError"


async def test_add_book_with_empty_title_returns_invalid_input_error(context: Context) -> None:
    variables = {"input": {"title": "   ", "publishedYear": 2024, "authorId": "1"}}

    result = await schema.execute(
        ADD_BOOK_MUTATION, variable_values=variables, context_value=context
    )

    assert result.errors is None
    assert result.data["addBook"]["__typename"] == "InvalidInputError"


async def test_add_book_with_out_of_range_published_year_returns_invalid_input_error(
    context: Context,
) -> None:
    variables = {"input": {"title": "Ghost Book", "publishedYear": 3000, "authorId": "1"}}

    result = await schema.execute(
        ADD_BOOK_MUTATION, variable_values=variables, context_value=context
    )

    assert result.errors is None
    assert result.data["addBook"]["__typename"] == "InvalidInputError"


async def test_add_book_with_non_numeric_author_id_returns_invalid_input_error(
    context: Context,
) -> None:
    variables = {
        "input": {"title": "Ghost Book", "publishedYear": 2024, "authorId": "not-numeric"}
    }

    result = await schema.execute(
        ADD_BOOK_MUTATION, variable_values=variables, context_value=context
    )

    assert result.errors is None
    assert result.data["addBook"]["__typename"] == "InvalidInputError"
