"""
Example GraphQL Federation Schema for Subgraph 2
This file shows what the actual GraphQL schema would look like
when using a real GraphQL server like Strawberry GraphQL.
"""

import strawberry
from typing import List, Optional
from strawberry.federation import key

# This is an example of how the federation schema would be implemented
# with a real GraphQL server (not currently used in the worker)

@strawberry.federation.type(keys=["chatId"])
class Chat:
    chat_id: str = strawberry.federation.field(external=True)
    id: str
    prompt: str
    project_id: str
    status: str
    progress: Optional[str] = None

    @classmethod
    def resolve_reference(cls, chat_id: str):
        # This would be called by the federation gateway
        # when resolving a Chat entity from another subgraph
        return cls(
            id=chat_id,
            chat_id=chat_id,
            prompt="",
            project_id="",
            status="pending"
        )

@strawberry.federation.type(keys=["projectId"])
class Prompt:
    project_id: str = strawberry.federation.field(external=True)
    id: str
    content: str

    @classmethod
    def resolve_reference(cls, project_id: str):
        return cls(
            id=project_id,
            project_id=project_id,
            content=""
        )

@strawberry.federation.type(keys=["chatId", "progressName"])
class Progress:
    chat_id: str = strawberry.federation.field(external=True)
    progress_name: str = strawberry.federation.field(external=True)
    id: str
    status: str
    data: Optional[str] = None

    @classmethod
    def resolve_reference(cls, chat_id: str, progress_name: str):
        return cls(
            id=f"{chat_id}_{progress_name}",
            chat_id=chat_id,
            progress_name=progress_name,
            status="pending"
        )

@strawberry.type
class Query:
    @strawberry.field
    def get_chat_by_id(self, chat_id: str) -> Optional[Chat]:
        # Implementation would call the worker's resolve_chat method
        return Chat(
            id=chat_id,
            chat_id=chat_id,
            prompt="",
            project_id="",
            status="pending"
        )

    @strawberry.field
    def get_prompt_by_project(self, project_id: str) -> Optional[Prompt]:
        # Implementation would call the worker's resolve_prompt method
        return Prompt(
            id=project_id,
            project_id=project_id,
            content=""
        )

@strawberry.input
class CreateChatInput:
    project_id: str
    prompt: str

@strawberry.input
class CreateChatCRAGInput:
    project_id: str
    prompt: str

@strawberry.input
class CreateChatResponseInput:
    project_id: str
    response: str

@strawberry.type
class CreateChatResponse:
    success: bool
    chat_id: str
    message: str

@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_chat(self, input: CreateChatInput) -> CreateChatResponse:
        # Implementation would call the worker's mutation_create_chat method
        return CreateChatResponse(
            success=True,
            chat_id="generated-id",
            message="Chat created successfully"
        )

    @strawberry.mutation
    def create_chat_crag(self, input: CreateChatCRAGInput) -> CreateChatResponse:
        # Implementation would call the worker's mutation_create_chat_crag method
        return CreateChatResponse(
            success=True,
            chat_id="generated-id",
            message="CRAG chat created successfully"
        )

    @strawberry.mutation
    def create_chat_response(self, input: CreateChatResponseInput) -> CreateChatResponse:
        # Implementation would call the worker's mutation_create_chat_response method
        return CreateChatResponse(
            success=True,
            chat_id="generated-id",
            message="Chat response created successfully"
        )

# The schema that would be served by the GraphQL federation subgraph
schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation,
    types=[Chat, Prompt, Progress],
    enable_federation_2=True
)

# Example SDL (Schema Definition Language) that would be generated:
EXAMPLE_SDL = """
extend schema
  @link(url: "https://specs.apollo.dev/federation/v2.0", import: ["@key", "@external"])

type Chat @key(fields: "chatId") {
  chatId: String! @external
  id: String!
  prompt: String!
  projectId: String!
  status: String!
  progress: String
}

type Prompt @key(fields: "projectId") {
  projectId: String! @external
  id: String!
  content: String!
}

type Progress @key(fields: "chatId progressName") {
  chatId: String! @external
  progressName: String! @external
  id: String!
  status: String!
  data: String
}

type Query {
  getChatById(chatId: String!): Chat
  getPromptByProject(projectId: String!): Prompt
}

input CreateChatInput {
  projectId: String!
  prompt: String!
}

input CreateChatCRAGInput {
  projectId: String!
  prompt: String!
}

input CreateChatResponseInput {
  projectId: String!
  response: String!
}

type CreateChatResponse {
  success: Boolean!
  chatId: String!
  message: String!
}

type Mutation {
  createChat(input: CreateChatInput!): CreateChatResponse!
  createChatCRAG(input: CreateChatCRAGInput!): CreateChatResponse!
  createChatResponse(input: CreateChatResponseInput!): CreateChatResponse!
}
"""