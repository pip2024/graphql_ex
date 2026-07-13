import strawberry

from app.schema.mutations import Mutation
from app.schema.queries import Query

schema = strawberry.Schema(query=Query, mutation=Mutation)
