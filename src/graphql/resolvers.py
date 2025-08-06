import strawberry
from strawberry.federation import Schema
from typing import List, Optional
from .types import SubProcessType, DataItemType, RootJSONType, PromptResponse

# Context will be injected by the GraphQLWorker to provide access to sendToOtherWorker
@strawberry.type
class Query:
    """GraphQL Query root for the sc-chatbot-worker subgraph"""
    
    @strawberry.field
    def prompt(self, info, project_id: str) -> Optional[PromptResponse]:
        """Get prompt by project ID"""
        worker = info.context.get("worker")
        if not worker:
            return PromptResponse(project_id=project_id, prompt={"error": "Worker not available"})
            
        # First try cache
        cache_result = worker.sendToOtherWorker(
            destination=[f"CacheWorker/getByKey/{project_id}"],
            data={"project_id": project_id}
        )
        
        if cache_result["status"] == "completed" and cache_result["result"]:
            return PromptResponse(project_id=project_id, prompt=cache_result["result"])
        
        # If not in cache, get from database
        db_result = worker.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/getPrompt/{project_id}"],
            data={"key": project_id}
        )
        
        if db_result["status"] == "completed":
            # Cache the result
            worker.sendToOtherWorker(
                destination=['CacheWorker/set/' + project_id],
                data={
                    "key": project_id,
                    "value": db_result['result'],
                }
            )
            return PromptResponse(project_id=project_id, prompt=db_result["result"])
            
        return PromptResponse(project_id=project_id, prompt={"error": "Prompt not found"})
    
    @strawberry.field 
    def chat_progress(self, info, chat_id: str, progress_name: Optional[str] = None) -> Optional[RootJSONType]:
        """Get chat progress by ID and optional progress name"""
        worker = info.context.get("worker")
        if not worker:
            return RootJSONType(data=[], message="Worker not available", status="error")
            
        response = worker.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/getProgress/{chat_id}"],
            data={"id": chat_id, "process_name": progress_name}
        )
        
        if response["status"] == "timeout":
            return RootJSONType(data=[], message="Request timed out", status="timeout")
        elif response["status"] == "completed":
            # Convert response to our GraphQL types
            data_items = []
            if isinstance(response["result"], list):
                for item in response["result"]:
                    # Convert each item to DataItemType
                    sub_processes = []
                    if item.get("sub_process"):
                        for sp in item["sub_process"]:
                            sub_processes.append(SubProcessType(
                                sub_process_name=sp.get("sub_process_name", ""),
                                input=sp.get("input"),
                                output=sp.get("output")
                            ))
                    
                    data_items.append(DataItemType(
                        input=item.get("input"),
                        output=item.get("output"),
                        process_name=item.get("process_name"),
                        sub_process=sub_processes if sub_processes else None
                    ))
            
            return RootJSONType(
                data=data_items,
                message="Progress retrieved successfully",
                status="success"
            )
        else:
            return RootJSONType(data=[], message="Unknown error", status="error")

@strawberry.type
class Mutation:
    """GraphQL Mutation root for the sc-chatbot-worker subgraph"""
    
    @strawberry.field
    def create_chat_crag(self, info, project_id: str, prompt: str) -> Optional[RootJSONType]:
        """Create a new CRAG chat session"""
        worker = info.context.get("worker")
        if not worker:
            return RootJSONType(data=[], message="Worker not available", status="error")
            
        # Create new history
        message = worker.sendToOtherWorker(
            destination=["DatabaseInteractionWorker/createNewHistory/"],
            data={
                "question": prompt,
                "projectId": project_id
            }
        )
        
        if message["status"] == "completed":
            chat_id = message.get("result", [{}])[0].get("_id", "unknown_id")
            
            # Start CRAG processing
            worker.sendToOtherWorker(
                destination=[f"CRAGWorker/generateAnswer/{chat_id}"],
                data={
                    "prompt": prompt,
                    "projectId": project_id
                }
            )
            
            return RootJSONType(
                data=[DataItemType(
                    input=prompt,
                    process_name="crag_chat_creation",
                    output={
                        "chat_id": chat_id,
                        "prompt": prompt,
                        "projectId": project_id
                    }
                )],
                message="Success create new chat history, the progress updated every completed sub_step processed",
                status="success"
            )
        else:
            return RootJSONType(data=[], message="Failed to create chat", status="error")
    
    @strawberry.field
    def create_chat(self, info, project_id: str, prompt: str) -> Optional[RootJSONType]:
        """Create a new chat session with logical fallacy processing"""
        worker = info.context.get("worker")
        if not worker:
            return RootJSONType(data=[], message="Worker not available", status="error")
            
        # Create new history
        message = worker.sendToOtherWorker(
            destination=["DatabaseInteractionWorker/createNewHistory/"],
            data={
                "question": prompt,
                "projectId": project_id
            }
        )
        
        if message["status"] == "completed":
            chat_id = message.get("result", [{}])[0].get("_id", "unknown_id")
            
            # Start logical fallacy prompt processing
            worker.sendToOtherWorker(
                destination=[f"LogicalFallacyPromptWorker/removeLFPrompt/"],
                data={
                    "prompt": prompt,
                    "id": chat_id,
                    "projectId": project_id
                }
            )
            
            return RootJSONType(
                data=[DataItemType(
                    input=prompt,
                    process_name="logical_fallacy_chat_creation",
                    output={
                        "chat_id": chat_id,
                        "prompt": prompt,
                        "projectId": project_id
                    }
                )],
                message="Success create new chat history, the progress updated every completed sub_step processed",
                status="success"
            )
        else:
            return RootJSONType(data=[], message="Failed to create chat", status="error")
        
    @strawberry.field
    def process_chat_response(self, info, project_id: str, response: str) -> Optional[RootJSONType]:
        """Process a chat response for logical fallacy analysis"""
        worker = info.context.get("worker")
        if not worker:
            return RootJSONType(data=[], message="Worker not available", status="error")
            
        # Create new history for response
        message = worker.sendToOtherWorker(
            destination=["DatabaseInteractionWorker/createNewHistory/"],
            data={
                "question": response,
                "projectId": project_id
            }
        )
        
        if message["status"] == "completed":
            chat_id = message.get("result", [{}])[0].get("_id", "unknown_id")
            
            # Start logical fallacy response processing
            worker.sendToOtherWorker(
                destination=["LogicalFallacyResponseWorker/removeLFResponse/"],
                data={
                    "response": response,
                    "chat_id": chat_id
                }
            )
            
            return RootJSONType(
                data=[DataItemType(
                    input=response,
                    process_name="logical_fallacy_response_processing", 
                    output={
                        "chat_id": chat_id,
                        "response": response
                    }
                )],
                message="Success create new chat history, the progress updated every completed sub_step processed",
                status="success"
            )
        else:
            return RootJSONType(data=[], message="Failed to process response", status="error")

# Create the federated schema
schema = Schema(
    query=Query,
    mutation=Mutation,
    enable_federation_2=True
)