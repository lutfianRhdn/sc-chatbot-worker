from multiprocessing.connection import Connection
import traceback
import threading
import uuid
import asyncio
import time
import uvicorn
from fastapi import FastAPI, Request
from strawberry.fastapi import GraphQLRouter
from utils.log import log 
from utils.handleMessage import sendMessage, convertMessage
from .Worker import Worker
from graphql.schema import schema

class GraphQLWorker(Worker):
    ###############
    # dont edit this part
    ###############
    conn: Connection
    requests: dict = {}
    instance = None  # Class variable to store the instance
    
    def __init__(self):
        # we'll assign these in run()
        self._port: int = None
        self.requests: dict = {}
        self.app = FastAPI()
        GraphQLWorker.instance = self  # Store instance for context
        
        # Create custom context getter for GraphQL
        async def get_context(request: Request):
            return {"worker": GraphQLWorker.instance}
        
        # Add GraphQL router with context
        graphql_router = GraphQLRouter(schema, context_getter=get_context)
        self.app.include_router(graphql_router, prefix="/graphql")
        
        # Add health check endpoint
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": "GraphQLWorker"}
        
        # Add a root endpoint that provides GraphQL playground
        @self.app.get("/")
        async def root():
            return {"message": "GraphQL Worker is running", "graphql_endpoint": "/graphql"}
        
    def run(self, conn: Connection, port: int):
        # assign here
        GraphQLWorker.conn = conn
        self._port = port
        
        def run_listen_task():
            asyncio.run(self.listen_task())
        threading.Thread(target=run_listen_task, daemon=True).start()

        # Run FastAPI with uvicorn
        uvicorn.run(self.app, host="0.0.0.0", port=self._port, log_level="info")

    async def listen_task(self):
        log("GraphQLWorker is listening for messages...", "info")
        while True:
            try:
                # Change poll(1) to poll(0.1) to reduce blocking time
                if GraphQLWorker.conn.poll(1):  # Shorter timeout
                    message = self.conn.recv()
                    log('Received message in GraphQLWorker', "info")
                    
                    dest = [
                        d
                        for d in message["destination"]
                        if d.split("/", 1)[0] == "GraphQLWorker"
                    ]
                    if dest:
                        destSplited = dest[0].split('/')
                        method = destSplited[1] if len(destSplited) > 1 else "onProcessed"
                        param = destSplited[2] if len(destSplited) > 2 else None
                        
                        instance_method = getattr(self, method, self.onProcessed)
                        instance_method(message)
                
                # Allow other async tasks to run
                await asyncio.sleep(0.01)
            except EOFError:
                break
            except Exception as e:
                log(f"GraphQLWorker listener error: {e}", 'error')
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
        
    def sendToOtherWorker(self, destination: str, data):
        task_id = str(uuid.uuid4())
        evt = threading.Event()
        
        GraphQLWorker.requests[task_id] = {
            "event": evt,
            "response": None
        }
        log(f"Sending request to {destination} with task_id: {task_id}", "info")
        
        sendMessage(
            conn=GraphQLWorker.conn,
            messageId=task_id,
            status="processing",
            destination=destination,
            data=data
        )
        
        if not evt.wait(timeout=30):
            # timeout
            log(f"Request {task_id} to {destination} timed out", "warn")
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

def main(conn: Connection, config: dict):
    worker = GraphQLWorker()
    worker.run(conn, config.get("port", 8000))