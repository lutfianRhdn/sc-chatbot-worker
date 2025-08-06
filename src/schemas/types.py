import strawberry
from typing import Optional, List
import json


@strawberry.type
class PromptResult:
    task_id: str
    status: str
    result: Optional[str] = None  # JSON string instead of dict


@strawberry.type
class ProgressData:
    id: str
    status: str
    message: str
    data: Optional[str] = None  # JSON string instead of dict


@strawberry.type
class ChatResult:
    status: str
    message: str
    data: Optional[str] = None  # JSON string instead of dict


@strawberry.type
class HealthStatus:
    status: str
    message: str


@strawberry.input
class ChatInput:
    project_id: str
    prompt: str


@strawberry.input
class ChatResponseInput:
    project_id: str
    response: str