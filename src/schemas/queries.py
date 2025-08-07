import strawberry
from typing import Optional
from .types import DataItemType,PromptResponse,SubProcessType
import uuid
import threading

@strawberry.type
class Query:
    """GraphQL Query root type"""
    