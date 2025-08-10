from multiprocessing.connection import Connection
from flask import Flask, request, jsonify
import threading
import uuid
import asyncio
import time
import json
import utils.log as log
from utils.handleMessage import sendMessage, convertMessage
from strawberry.flask.views import GraphQLView
from schemas.schema import schema
import strawberry
from schemas.queries import Query


# Simple GraphQL-like implementation without external dependencies
app = Flask(__name__)
class CustomGraphQLView(GraphQLView):
    # override the instance method called by Strawberry to build context
    def get_context(self, request,response=None):
        # self here is the view instance; we read worker from the view class
        # (set by as_view_with_worker)
        return {"request": request, "worker": getattr(self.__class__, "worker", None),'response':response}

    @classmethod
    def as_view_with_worker(cls, name, worker, **kwargs):
        """
        Attach the worker to the view class and return the view function.
        Do NOT pass get_context or worker into as_view(...) kwargs.
        """
        # Attach worker to the view class (so instances can access it)
        cls.worker = worker
        # Create and return the Flask view function
        return super().as_view(name, **kwargs)
class GraphQLWorker:
    requests: dict = {}
    def __init__(self):
        self.app = Flask(__name__)
        self.schema = strawberry.federation.Schema(
            query=Query,
            enable_federation_2=True,
        )
        self.setup_routes()
    
    def setup_routes(self):
        # Add Strawberry GraphQL endpoint
        self.app.add_url_rule(
            '/graphql',
            view_func=CustomGraphQLView.as_view_with_worker(
                'graphql',
                worker=self,
                schema=self.schema,
                graphiql=True
            ),
            methods=['GET', 'POST']
        )
        
        # Legacy endpoint for backward compatibility
        self.app.route('/query', methods=['POST'])(self.handle_query)
    
    def handle_query(self):
        """Legacy query handler - redirects to Strawberry"""
        try:
            data = request.get_json()
            query = data.get('query', '')
            variables = data.get('variables', {})
            
            # Execute using Strawberry schema
            context = {"worker": self}
            log.log(f"Executing GraphQL query: {query} with variables: {variables}", 'info')
            result = schema.execute_sync(
                query=query,
                variable_values=variables,
                context_value=context
            )
            
            # Format response
            response_data = {"data": result.data}
            if result.errors:
                response_data["errors"] = [{"message": str(error)} for error in result.errors]
                
            return jsonify(response_data), 200
            
        except Exception as e:
            log.log(f"GraphQL error: {e}", 'error')
            return jsonify({
                "errors": [{"message": str(e)}]
            }), 500

    def run(self, conn: Connection, port: int):
        # assign here
        GraphQLWorker.conn = conn
        self._port = port
        def run_listen_task():
            asyncio.run(self.listen_task())
        threading.Thread(target=run_listen_task, daemon=True).start()

        # Start Flask server
        self.app.run(debug=True, port=self._port, use_reloader=False, host="0.0.0.0")
    
    async def listen_task(self):
        while True:
            try:
                if GraphQLWorker.conn.poll(1):  # Check for messages with 1 second timeout
                    print("[GRAPHQLWORKER]Listening for messages...")
                    
                    raw = GraphQLWorker.conn.recv()
                    msg = convertMessage(raw)
                    self.onProcessed(raw)
                    await asyncio.sleep(0.1)  # Yield control to the event loop
            except EOFError:
                break
            except Exception as e:
                log.log(f"Listener error: {e}", 'error')
                break
    
    def onProcessed(self, msg: dict):
        """
        Called when a worker response comes in.
        msg must contain 'messageId' and 'data'.
        """
        task_id = msg.get("messageId")
        print(f"Received response for task_id: {task_id} with ")
        
        entry = GraphQLWorker.requests.get(task_id)
        if not entry:
            return
        entry["response"] = msg.get("data")
        entry["event"].set()
    
    def sendToOtherWorker(self, destination: list, data: dict):
        """Send synchronous message to other worker and wait for response"""
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
        
        if not evt.wait(timeout=10):
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
    
    def send_message_async(self, destination: list, data: dict):
        """Send asynchronous message to other worker (fire and forget)"""
        task_id = str(uuid.uuid4())
        
        sendMessage(
            conn=GraphQLWorker.conn,
            messageId=task_id,
            status="processing",
            destination=destination,
            data=data
        )

def main(conn: Connection, config: dict):
    worker = GraphQLWorker()
    worker.run(conn, config.get("port", 8000))