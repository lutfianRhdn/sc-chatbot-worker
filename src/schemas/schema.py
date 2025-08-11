import strawberry
from schemas.queries import Query
from schemas.mutations import Mutation

# Create the schema with proper federation support
schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation,
    enable_federation_2=True,
)

# Function to get context for GraphQL execution
def get_context(worker_instance):
    return {"worker": worker_instance}