import strawberry
from typing import Optional
import json
from .types import PromptResult, ProgressData, ChatResult, HealthStatus, ChatInput, ChatResponseInput

# Global worker instance reference
_worker_instance = None

def set_worker_instance(worker):
    """Set the global worker instance"""
    global _worker_instance
    _worker_instance = worker

def get_worker_instance():
    """Get the global worker instance"""
    return _worker_instance


@strawberry.type
class Query:
    @strawberry.field
    def get_prompt(self, project_id: str) -> PromptResult:
        """Get prompt by project ID"""
        worker = get_worker_instance()
        if worker:
            result = worker.get_prompt_impl(project_id)
            return PromptResult(
                task_id=result.get("taskId", ""),
                status=result.get("status", ""),
                result=json.dumps(result.get("result")) if result.get("result") else None
            )
        return PromptResult(task_id="", status="error", result=None)
    
    @strawberry.field
    def get_progress(self, chat_id: str, progress_name: Optional[str] = None) -> ProgressData:
        """Get progress for a chat session"""
        worker = get_worker_instance()
        if worker:
            response = worker.get_progress_impl(chat_id, progress_name)
            if response["status"] == "timeout":
                return ProgressData(id=chat_id, status="error", message="Request timed out", data=None)
            elif response["status"] == "completed":
                return ProgressData(
                    id=chat_id,
                    status="success",
                    message="Progress retrieved successfully",
                    data=json.dumps(response["result"]) if response["result"] else None
                )
            else:
                return ProgressData(id=chat_id, status="error", message="Unknown error", data=None)
        return ProgressData(id=chat_id, status="error", message="Worker not available", data=None)
    
    @strawberry.field
    def health_check(self) -> HealthStatus:
        """Health check endpoint"""
        return HealthStatus(status="success", message="GraphQLWorker is running")


@strawberry.type
class Mutation:
    @strawberry.mutation
    def chat_crag(self, input: ChatInput) -> ChatResult:
        """Start a CRAG chat session"""
        worker = get_worker_instance()
        if worker:
            result = worker.chat_crag_impl(input.project_id, input.prompt)
            return ChatResult(
                status=result.get("status", ""),
                message=result.get("message", ""),
                data=json.dumps(result.get("data")) if result.get("data") else None
            )
        return ChatResult(status="error", message="Worker not available", data=None)
    
    @strawberry.mutation
    def chat_prompt(self, input: ChatInput) -> ChatResult:
        """Process logical fallacy prompt"""
        worker = get_worker_instance()
        if worker:
            result = worker.chat_prompt_impl(input.project_id, input.prompt)
            return ChatResult(
                status=result.get("status", ""),
                message=result.get("message", ""),
                data=json.dumps(result.get("data")) if result.get("data") else None
            )
        return ChatResult(status="error", message="Worker not available", data=None)
    
    @strawberry.mutation
    def chat_response(self, input: ChatResponseInput) -> ChatResult:
        """Process logical fallacy response"""
        worker = get_worker_instance()
        if worker:
            result = worker.chat_response_impl(input.project_id, input.response)
            return ChatResult(
                status=result.get("status", ""),
                message=result.get("message", ""),
                data=json.dumps(result.get("data")) if result.get("data") else None
            )
        return ChatResult(status="error", message="Worker not available", data=None)