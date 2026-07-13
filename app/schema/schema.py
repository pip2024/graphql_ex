import strawberry

from app.schema.mutations import Mutation
from app.schema.queries import Query
from app.schema.subscriptions import Subscription

schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)
