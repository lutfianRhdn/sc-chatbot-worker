# GraphQL Worker Documentation

## Overview
The GraphQL Worker provides a GraphQL API interface similar to the REST API Worker, using the strawberry library with federation 2 enabled.

## Configuration
The GraphQL Worker runs on port 8000 by default (configurable in `config/workerConfig.py`).

```python
GraphQLWorkerConfig = {
    'port': 8000,  # Different port from REST API
}
```

## Schema Structure
The GraphQL schema is created with federation 2 enabled as requested:

```python
import strawberry
from schemas.queries import Query

schema = strawberry.federation.Schema(
    query=Query,
    enable_federation_2=True
)
```

## Available Operations

### Queries
- `healthCheck`: Returns health status of the GraphQL Worker
- `getPrompt(projectId: String!)`: Get prompt by project ID (mirrors `/prompt` REST endpoint)
- `getProgress(chatId: String!, progressName: String)`: Get progress for a chat session (mirrors `/chat/<id>` REST endpoint)

### Mutations
- `chatCrag(input: ChatInput!)`: Start a CRAG chat session (mirrors `/chat-crag` REST endpoint)
- `chatPrompt(input: ChatInput!)`: Process logical fallacy prompt (mirrors `/chat` REST endpoint)
- `chatResponse(input: ChatResponseInput!)`: Process logical fallacy response (mirrors `/chat-respons` REST endpoint)

### Input Types
```graphql
input ChatInput {
  projectId: String!
  prompt: String!
}

input ChatResponseInput {
  projectId: String!
  response: String!
}
```

### Return Types
```graphql
type HealthStatus {
  status: String!
  message: String!
}

type PromptResult {
  taskId: String!
  status: String!
  result: String  # JSON string
}

type ProgressData {
  id: String!
  status: String!
  message: String!
  data: String  # JSON string
}

type ChatResult {
  status: String!
  message: String!
  data: String  # JSON string
}
```

## Example Queries

### Health Check
```graphql
query {
  healthCheck {
    status
    message
  }
}
```

### Get Prompt
```graphql
query GetPrompt($projectId: String!) {
  getPrompt(projectId: $projectId) {
    taskId
    status
    result
  }
}
```

### Chat CRAG
```graphql
mutation ChatCrag($input: ChatInput!) {
  chatCrag(input: $input) {
    status
    message
    data
  }
}
```

## Accessing the GraphQL API

### Development
When running locally, the GraphQL endpoint is available at:
- **GraphQL endpoint**: `http://localhost:8000/graphql`
- **GraphiQL interface**: `http://localhost:8000/graphql` (accessible via browser)

### Federation 2 Features
The schema includes federation 2 features:
- `_Service` type for schema introspection
- `scalar _Any` for federation support
- Compatible with Apollo Federation v2

## Inter-Worker Communication
The GraphQL Worker communicates with other workers using the same message-passing system as the REST API Worker:
- `CacheWorker` for caching
- `DatabaseInteractionWorker` for database operations
- `CRAGWorker` for CRAG processing
- `LogicalFallacyPromptWorker` and `LogicalFallacyResponseWorker` for logical fallacy processing

## Starting the Worker
The GraphQL Worker is automatically started by the supervisor when you run:

```bash
python src/supervisor.py
```

It will be available alongside the REST API Worker on a different port (8000 vs 5000).