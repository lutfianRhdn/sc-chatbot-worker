"""
JSON Response Types for GraphQL Federation Subgraph
This module defines the response type decorators and schemas used by the GraphQL federation worker.
"""
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

# Decorator for defining JSON response types
def json_response_types(*response_types):
    """
    Decorator to define JSON response types for GraphQL resolvers.
    This helps in schema generation and type validation.
    """
    def decorator(func):
        func._response_types = response_types
        return func
    return decorator

# Status enums
class ResponseStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class MessageStatus(Enum):
    HEALTHY = "healthy"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# Base response types that match the existing REST API structure
@dataclass
class BaseResponse:
    """Base response structure for all GraphQL responses"""
    status: ResponseStatus
    message: str
    data: Optional[Dict[str, Any]] = None

@dataclass
class WorkerResponse:
    """Response structure for worker-to-worker communication"""
    taskId: str
    status: ResponseStatus
    result: Optional[Dict[str, Any]] = None

@dataclass
class PromptResponse:
    """Response for prompt-related operations"""
    status: ResponseStatus
    message: str
    data: Optional[Dict[str, Any]] = None

@dataclass
class ChatResponse:
    """Response for chat operations"""
    status: ResponseStatus
    message: str
    data: Dict[str, Any]

@dataclass
class ProgressResponse:
    """Response for progress tracking"""
    status: ResponseStatus
    message: str
    data: Optional[Dict[str, Any]] = None

@dataclass
class CRAGResponse:
    """Response for CRAG (Chat Retrieval Augmented Generation) operations"""
    status: ResponseStatus
    message: str
    data: Dict[str, Any]

@dataclass
class LogicalFallacyResponse:
    """Response for logical fallacy analysis"""
    status: ResponseStatus
    message: str
    data: Optional[Dict[str, Any]] = None

# GraphQL-specific types for federation
@dataclass
class EntityKey:
    """Entity key for GraphQL federation"""
    field: str
    value: str

@dataclass
class FederatedEntity:
    """Base federated entity structure"""
    id: str
    _service: str = "chatbot-worker-subgraph-2"

# Federation-specific response types
@dataclass  
class ChatEntity(FederatedEntity):
    """Chat entity for GraphQL federation"""
    chat_id: str = ""
    prompt: str = ""
    project_id: str = ""
    status: ResponseStatus = ResponseStatus.SUCCESS
    progress: Optional[Dict[str, Any]] = None

@dataclass
class PromptEntity(FederatedEntity):
    """Prompt entity for GraphQL federation"""
    project_id: str = ""
    content: Dict[str, Any] = None

    def __post_init__(self):
        if self.content is None:
            self.content = {}

@dataclass
class ProgressEntity(FederatedEntity):
    """Progress entity for GraphQL federation"""
    chat_id: str = ""
    progress_name: str = ""
    status: ResponseStatus = ResponseStatus.SUCCESS
    data: Optional[Dict[str, Any]] = None

# Helper functions for response creation
def create_success_response(message: str, data: Optional[Dict[str, Any]] = None) -> BaseResponse:
    """Create a success response"""
    return BaseResponse(
        status=ResponseStatus.SUCCESS,
        message=message,
        data=data
    )

def create_error_response(message: str, data: Optional[Dict[str, Any]] = None) -> BaseResponse:
    """Create an error response"""
    return BaseResponse(
        status=ResponseStatus.ERROR,
        message=message,
        data=data
    )

def create_processing_response(message: str, data: Optional[Dict[str, Any]] = None) -> BaseResponse:
    """Create a processing response"""
    return BaseResponse(
        status=ResponseStatus.PROCESSING,
        message=message,
        data=data
    )

# Type mappings for GraphQL schema generation
RESPONSE_TYPE_MAPPINGS = {
    'prompt': PromptResponse,
    'chat': ChatResponse,
    'progress': ProgressResponse,
    'crag': CRAGResponse,
    'logical_fallacy': LogicalFallacyResponse,
    'base': BaseResponse
}

# Federation entity mappings
FEDERATED_ENTITY_MAPPINGS = {
    'Chat': ChatEntity,
    'Prompt': PromptEntity,
    'Progress': ProgressEntity
}