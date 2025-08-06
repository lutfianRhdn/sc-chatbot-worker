# Example GraphQL Queries and Mutations

## Query: Get Prompt
```graphql
query GetPrompt {
  prompt(project_id: "test-project-123") {
    project_id
    prompt
  }
}
```

## Query: Get Chat Progress
```graphql
query GetChatProgress {
  chat_progress(chat_id: "chat-456", progress_name: "logical_fallacy_analysis") {
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

## Mutation: Create CRAG Chat
```graphql
mutation CreateCragChat {
  create_chat_crag(
    project_id: "test-project-123"
    prompt: "What are the benefits of artificial intelligence?"
  ) {
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

## Mutation: Create Logical Fallacy Chat
```graphql
mutation CreateChat {
  create_chat(
    project_id: "test-project-123"
    prompt: "All politicians are corrupt, so we shouldn't trust any government policy."
  ) {
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

## Mutation: Process Chat Response
```graphql
mutation ProcessChatResponse {
  process_chat_response(
    project_id: "test-project-123"
    response: "If you don't agree with this policy, you must hate your country."
  ) {
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

## Schema Introspection Query
```graphql
query IntrospectionQuery {
  __schema {
    queryType {
      name
      fields {
        name
        type {
          name
        }
      }
    }
    mutationType {
      name
      fields {
        name
        type {
          name
        }
      }
    }
  }
}
```

## Federation Service Query
```graphql
query ServiceQuery {
  _service {
    sdl
  }
}
```