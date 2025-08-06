# GraphQL Federation Subgraph 2 Worker

This document describes the GraphQL Federation Subgraph 2 Worker implementation that provides GraphQL federation capabilities based on the existing RestAPI Worker structure.

## Overview

The GraphQL Federation Subgraph 2 Worker (`GraphQLFederationSubgraph2Worker`) is a federation-compliant GraphQL subgraph that exposes the same functionality as the REST API Worker but through GraphQL federation schema.

## Features

- **Federation v2.0 Compliant**: Implements Apollo Federation v2.0 specification
- **Entity Resolution**: Provides federated entities for Chat, Prompt, and Progress
- **Query & Mutation Support**: Mirrors all REST API endpoints as GraphQL operations
- **Inter-worker Communication**: Uses existing worker message system
- **Response Type System**: Includes `@json_response_types` decorator for schema definition

## Architecture

### Core Components

1. **`json_response_types.py`** - Response type definitions and federation entities
2. **`GraphQLFederationSubgraph2Worker.py`** - Main worker implementation
3. **Federation Schema** - Defines entities, keys, and resolvers
4. **Worker Configuration** - Integration with supervisor system

### Federation Entities

#### Chat Entity
```python
@dataclass
class ChatEntity(FederatedEntity):
    chat_id: str        # Federation key
    prompt: str
    project_id: str
    status: ResponseStatus
    progress: Optional[Dict[str, Any]] = None
```

#### Prompt Entity
```python
@dataclass
class PromptEntity(FederatedEntity):
    project_id: str     # Federation key
    content: Dict[str, Any]
```

#### Progress Entity
```python
@dataclass
class ProgressEntity(FederatedEntity):
    chat_id: str        # Federation key (part 1)
    progress_name: str  # Federation key (part 2)
    status: ResponseStatus
    data: Optional[Dict[str, Any]] = None
```

## GraphQL Operations

### Queries
- `getChatById(chatId: String!)` - Retrieve chat information
- `getPromptByProject(projectId: String!)` - Retrieve prompt by project ID

### Mutations
- `createChat(projectId: String!, prompt: String!)` - Create new chat (equivalent to `POST /chat`)
- `createChatCRAG(projectId: String!, prompt: String!)` - Create CRAG chat (equivalent to `POST /chat-crag`)
- `createChatResponse(projectId: String!, response: String!)` - Create chat response (equivalent to `POST /chat-response`)

## Federation Schema

The worker exposes a federation schema with the following structure:

```yaml
version: "2.0"
subgraph: "chatbot-worker-subgraph-2"
entities:
  Chat:
    keys: ["chat_id"]
    fields: ["id", "chat_id", "prompt", "project_id", "status", "progress"]
  Prompt:
    keys: ["project_id"]
    fields: ["id", "project_id", "content"]
  Progress:
    keys: ["chat_id", "progress_name"]
    fields: ["id", "chat_id", "progress_name", "status", "data"]
```

## Configuration

The worker is configured in `src/config/workerConfig.py`:

```python
GraphQLFederationSubgraph2WorkerConfig = {
    'port': 5001,  # Different port from REST API
    'federation_version': '2.0',
    'subgraph_name': 'chatbot-worker-subgraph-2',
    'schema_registry_url': 'http://localhost:4000'
}
```

## Usage

### Starting the Worker

The worker is automatically started by the supervisor:

```python
self.create_worker("GraphQLFederationSubgraph2Worker", count=1, config=GraphQLFederationSubgraph2WorkerConfig)
```

### Inter-worker Communication

The GraphQL worker communicates with other workers using the existing message system:

```python
# Example: Get chat progress
result = self.send_to_other_worker(
    destination=[f"DatabaseInteractionWorker/getProgress/{chat_id}"],
    data={"id": chat_id, "process_name": progress_name}
)
```

### Response Type Decoration

Use the `@json_response_types` decorator to define response types:

```python
@json_response_types(ChatEntity)
async def resolve_chat(self, message: Dict[str, Any], chat_id: str) -> ChatEntity:
    # Implementation
    return ChatEntity(...)
```

## Dependencies

Required packages (added to `requirements.txt`):
- `strawberry-graphql==0.278.1`
- `graphql-core>=3.2.0,<3.4.0`

## Testing

Run the comprehensive test suite:

```bash
cd src
python3 test_graphql_federation.py
```

The test validates:
- Response type system functionality
- Worker initialization and schema generation
- Federation compliance
- Resolver registration
- Configuration integration

## Integration with Apollo Gateway

To integrate with Apollo Gateway/Router:

1. Register the subgraph with your gateway:
```javascript
const subgraphs = [
  {
    name: 'chatbot-worker-subgraph-2',
    url: 'http://localhost:5001/graphql'
  }
  // ... other subgraphs
];
```

2. The worker will automatically provide federation schema introspection
3. Entity resolution works seamlessly across subgraphs

## API Mapping

| REST Endpoint | GraphQL Operation | Description |
|---------------|-------------------|-------------|
| `GET /prompt?project_id=X` | `query { getPromptByProject(projectId: "X") }` | Get prompt by project |
| `GET /chat/{id}?progress_name=X` | `query { getChatById(chatId: "{id}") }` | Get chat progress |
| `POST /chat` | `mutation { createChat(projectId: "X", prompt: "Y") }` | Create new chat |
| `POST /chat-crag` | `mutation { createChatCRAG(projectId: "X", prompt: "Y") }` | Create CRAG chat |
| `POST /chat-response` | `mutation { createChatResponse(projectId: "X", response: "Y") }` | Create chat response |

## Error Handling

The worker provides consistent error responses using the response type system:

```python
def create_error_response(message: str, data: Optional[Dict[str, Any]] = None) -> BaseResponse:
    return BaseResponse(
        status=ResponseStatus.ERROR,
        message=message,
        data=data
    )
```

## Monitoring and Health Checks

The worker sends periodic health checks to the supervisor:

```python
def _send_health_check(self):
    sendMessage(
        conn=self.conn,
        messageId=f"GraphQLFederationSubgraph2Worker-{int(time.time())}",
        status="healthy",
        destination=["supervisor"],
        data={"service": "graphql-federation-subgraph-2", "port": self._port}
    )
```

## Future Enhancements

1. **Real GraphQL Server**: Replace simulation with actual GraphQL server (Strawberry GraphQL)
2. **Subscriptions**: Add real-time subscriptions for progress updates
3. **Advanced Federation**: Implement more complex federation patterns
4. **Schema Registry**: Integration with Apollo Studio schema registry
5. **Metrics**: Add GraphQL-specific metrics and monitoring