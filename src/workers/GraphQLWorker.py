from multiprocessing.connection import Connection
import traceback
import threading
import uuid
import asyncio
import time
from utils.log import log 
from utils.handleMessage import sendMessage, convertMessage
from .Worker import Worker
from urllib.parse import urlparse
import strawberry
from schemas.queries import Query, Mutation
from strawberry.asgi import GraphQL
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
import uvicorn

# Create the federated schema with enable_federation_2=True as requested
schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation,
    enable_federation_2=True
)

# Global variable to store worker instance for context
_worker_instance = None

# Create the GraphQL app
graphql_app = GraphQL(schema)

# Create the main app with CORS middleware
app = Starlette()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_route("/graphql", graphql_app)
app.add_websocket_route("/graphql", graphql_app)


class GraphQLWorker(Worker):
    ###############
    # dont edit this part
    ###############
    conn: Connection
    requests: dict = {}
    
    def __init__(self):
        # we'll assign these in run()
        self._port: int = None
        self.requests: dict = {}
        
    def run(self, conn: Connection, port: int):
        # assign here
        GraphQLWorker.conn = conn
        self._port = port
        
        def run_listen_task():
            asyncio.run(self.listen_task())
        threading.Thread(target=run_listen_task, daemon=True).start()

        # Patch the resolvers to have access to this worker instance
        self._patch_resolvers()
        
        # Start the ASGI server
        uvicorn.run(app, host="0.0.0.0", port=self._port)

    def _patch_resolvers(self):
        """Patch the resolver methods to have access to this worker instance"""
        # Import and set the worker instance in the queries module
        from schemas.queries import set_worker_instance
        set_worker_instance(self)
        
    async def listen_task(self):
        print("GraphQLWorker is listening for messages...")
        while True:
            try:
                # Change poll(1) to poll(0.1) to reduce blocking time
                if GraphQLWorker.conn.poll(1):  # Shorter timeout
                    message = self.conn.recv()
                    print('received message')
                    dest = [
                        d
                        for d in message["destination"]
                        if d.split("/", 1)[0] == "GraphQLWorker"
                    ]
                    destSplited = dest[0].split('/')
                    method = destSplited[1]
                    param = destSplited[2] if len(destSplited) > 2 else None
                    instance_method = getattr(self, method)
                    instance_method(message)
                
                # ADD THIS LINE: Allow other async tasks to run
                await asyncio.sleep(0.01)
            except EOFError:
                break
            except Exception as e:
                print(e)
                log(f"Listener error: {e}", 'error')
                break

    def onProcessed(self, msg):
        """
        Called when a worker response comes in.
        msg must contain 'messageId' and 'data'.
        """
        task_id = msg.get("messageId")
        entry = GraphQLWorker.requests.get(task_id)
        if not entry:
            return
        entry["response"] = msg.get("data")
        entry["event"].set()
        
    def sendToOtherWorker(self, destination: list[str], data):
        task_id = str(uuid.uuid4())
        evt = threading.Event()
        
        GraphQLWorker.requests[task_id] = {
            "event": evt,
            "response": None
        }
        print(f"Sending request to {destination} with task_id: {task_id}")
        
        sendMessage(
            conn=GraphQLWorker.conn,
            messageId=task_id,
            status="processing",
            destination=destination,
            data=data
        )
        if not evt.wait(timeout=30):
            # timeout
            return {
                "taskId": task_id,
                "status": "timeout",
                "result": None
            }
        
        # success
        result = GraphQLWorker.requests.pop(task_id)["response"]
        return {
            "taskId": task_id,
            "status": "completed",
            "result": result
        }

    ##########################################
    # GraphQL Resolver Implementation Methods
    ##########################################
    def get_prompt_impl(self, project_id: str):
        """Implementation for getPrompt resolver"""
        result = self.sendToOtherWorker(
            destination=[f"CacheWorker/getByKey/{project_id}"],
            data={"project_id": project_id}
        )
        print(result)
        if len(result["result"]) == 0:
            result = self.sendToOtherWorker(
                destination=[f"DatabaseInteractionWorker/getPrompt/{project_id}"],
                data={"key": project_id}
            )
            sendMessage(
                conn=GraphQLWorker.conn,
                messageId=str(uuid.uuid4()),
                status="processing",
                destination=['CacheWorker/set/' + project_id],
                data={
                    "key": f"{project_id}",
                    "value": result['result'],
                }
            )
        return result

    def get_progress_impl(self, chat_id: str, progress_name: str = None):
        """Implementation for getProgress resolver"""
        print(f"Getting progress for chat ID: {chat_id} with progress name: {progress_name}")
        response = self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/getProgress/{chat_id}"],
            data={"id": chat_id, "process_name": progress_name}
        )
        return response

    def chat_crag_impl(self, project_id: str, prompt: str):
        """Implementation for chatCrag resolver"""
        message = self.sendToOtherWorker(
            destination=["DatabaseInteractionWorker/createNewHistory/"],
            data={
                "question": prompt,
                "projectId": project_id
            }
        )
        id = message.get("result", [{}])[0].get("_id", "unknown_id")
        print(f"Chat CRAG ID: {id}")
        sendMessage(
            conn=GraphQLWorker.conn,
            messageId=id,
            status="completed",
            destination=[f"CRAGWorker/generateAnswer/{id}"],
            data={
                "prompt": prompt,
                "projectId": project_id
            }
        )
        return {
            "status": "success",
            "message": "success create new chat history, the progress updated every completed sub_step processed",
            "data": {
                "chat_id": id,
                "prompt": prompt,
                "projectId": project_id
            }
        }

    def chat_prompt_impl(self, project_id: str, prompt: str):
        """Implementation for lfu_prompt resolver"""
        message = self.sendToOtherWorker(
            destination=["DatabaseInteractionWorker/createNewHistory/"],
            data={
                "question": prompt,
                "projectId": project_id
            }
        )
        id = message.get("result", [{}])[0].get("_id", "unknown_id")
        
        sendMessage(
            conn=GraphQLWorker.conn,
            messageId=id,
            status="completed",
            destination=[f"LogicalFallacyPromptWorker/removeLFPrompt/"],
            data={
                "prompt": prompt,
                "id": id,
                "projectId": project_id
            }
        )
        return {
            "status": "success",
            "message": "success create new chat history, the progress updated every completed sub_step processed",
            "data": {
                "chat_id": id,
                "prompt": prompt,
                "projectId": project_id
            }
        }

    def chat_response_impl(self, project_id: str, response: str):
        """Implementation for lfu_response resolver"""
        message = self.sendToOtherWorker(
            destination=["DatabaseInteractionWorker/createNewHistory/"],
            data={
                "question": response,
                "projectId": project_id
            }
        )
        id = message.get("result", [{}])[0].get("_id", "unknown_id")

        sendMessage(
            conn=GraphQLWorker.conn,
            messageId=id,
            status="completed",
            destination=["LogicalFallacyResponseWorker/removeLFResponse/"],
            data={
                "response": response,
                "chat_id": id
            }
        )
        return {
            "status": "success",
            "message": "success create new chat history, the progress updated every completed sub_step processed",
            "data": {
                "response": response,
            }
        }


def main(conn: Connection, config: dict):
    worker = GraphQLWorker()
    worker.run(conn, config.get("port", 8000))