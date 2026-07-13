from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from app.context import get_context
from app.schema.schema import schema

graphql_app: GraphQLRouter = GraphQLRouter(schema, context_getter=get_context)

app = FastAPI(title="GraphQL Example")
app.include_router(graphql_app, prefix="/graphql")


@app.get("/")
def root() -> dict[str, str]:
    return {"graphql": "/graphql"}
