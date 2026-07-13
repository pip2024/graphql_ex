import asyncio

from app.context import Context
from app.schema.schema import schema

ADD_BOOK_MUTATION = """
mutation($input: AddBookInput!) {
  addBook(input: $input) {
    __typename
  }
}
"""


async def test_book_added_subscription_receives_new_book(context: Context) -> None:
    subscription = await schema.subscribe(
        "subscription { bookAdded { title } }", context_value=context
    )

    # Start consuming before publishing, then wait for the subscriber to
    # actually register (the resolver only registers on its first
    # `.__anext__()` step) rather than assume event-loop scheduling order.
    receive_task = asyncio.create_task(subscription.__anext__())
    while context.broadcaster.subscriber_count() == 0:
        await asyncio.sleep(0)

    variables = {"input": {"title": "Ghost Book", "publishedYear": 2024, "authorId": "1"}}
    mutation_result = await schema.execute(
        ADD_BOOK_MUTATION, variable_values=variables, context_value=context
    )
    assert mutation_result.errors is None

    result = await receive_task

    assert result.errors is None
    assert result.data["bookAdded"]["title"] == "Ghost Book"
