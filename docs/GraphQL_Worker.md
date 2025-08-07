# GraphQL Worker Documentation

## Overview

The GraphQL Worker provides a GraphQL Federation 2 subgraph interface for the sc-chatbot-worker system. It exposes the same functionality as the REST API but through GraphQL queries and mutations.

## Endpoints

- GraphQL Playground: `http://localhost:8000/graphql`
- Health Check: `http://localhost:8000/health`

## Schema Types

### SubProcessType
```graphql
type SubProcessType {
  sub_process_name: String!
  input: JSON
  output: JSON
}
```

### DataItemType
```graphql
type DataItemType {
  input: JSON
  output: JSON
  process_name: String
  sub_process: [SubProcessType]
}
```

### RootJSONType
```graphql
type RootJSONType {
  data: [DataItemType!]!
  message: String
  status: String
}
```

### PromptResponse
```graphql
type PromptResponse {
  project_id: String
  prompt: JSON
}
```

## Queries

### Get Prompt by Project ID
```graphql
query GetPrompt($projectId: String!) {
  prompt(project_id: $projectId) {
    project_id
    prompt
  }
}
```

Variables:
```json
{
  "projectId": "your-project-id-here"
}
```

### Get Chat Progress
```graphql
query GetChatProgress($chatId: String!, $progressName: String) {
  chat_progress(chat_id: $chatId, progress_name: $progressName) {
    data {
      input
      output
      process_name
      sub_process {
        sub_process_name
        input
        output
      }
    }
    message
    status
  }
}
```

Variables:
```json
{
  "chatId": "your-chat-id-here",
  "progressName": "optional-progress-name"
}
```

## Mutations

### Create CRAG Chat
```graphql
mutation CreateCragChat($projectId: String!, $prompt: String!) {
  create_chat_crag(project_id: $projectId, prompt: $prompt) {
    data {
      input
      output
      process_name
      sub_process {
        sub_process_name
        input
        output
      }
    }
    message
    status
  }
}
```

Variables:
```json
{
  "projectId": "your-project-id",
  "prompt": "Your question here"
}
```

### Create Logical Fallacy Chat
```graphql
mutation CreateChat($projectId: String!, $prompt: String!) {
  create_chat(project_id: $projectId, prompt: $prompt) {
    data {
      input
      output
      process_name
      sub_process {
        sub_process_name
        input
        output
      }
    }
    message
    status
  }
}
```

Variables:
```json
{
  "projectId": "your-project-id",
  "prompt": "Your prompt to analyze for logical fallacies"
}
```

### Process Chat Response
```graphql
mutation ProcessChatResponse($projectId: String!, $response: String!) {
  process_chat_response(project_id: $projectId, response: $response) {
    data {
      input
      output
      process_name
      sub_process {
        sub_process_name
        input
        output
      }
    }
    message
    status
  }
}
```

Variables:
```json
{
  "projectId": "your-project-id",
  "response": "Response to analyze for logical fallacies"
}
```

## Federation 2 Support

This GraphQL worker implements GraphQL Federation 2 subgraph specification, making it compatible with Apollo Gateway and other federation-aware GraphQL gateways.

## Configuration

The GraphQL worker is configured in `src/config/workerConfig.py`:

```python
GraphQLWorkerConfig = {
    'port': 8000,  # Different port from REST API
}
```

## Integration with Existing Workers

The GraphQL worker integrates seamlessly with the existing worker system:

- **CacheWorker**: For caching prompts
- **DatabaseInteractionWorker**: For data persistence
- **CRAGWorker**: For CRAG chat processing
- **LogicalFallacyPromptWorker**: For logical fallacy analysis of prompts
- **LogicalFallacyResponseWorker**: For logical fallacy analysis of responses

All GraphQL resolvers use the same inter-worker communication mechanism as the REST API, ensuring consistent behavior across both interfaces.