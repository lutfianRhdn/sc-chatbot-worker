from multiprocessing.connection import Connection
import traceback
import threading
import uuid
import time
from flask import Flask, request, jsonify
from strawberry.flask.views import GraphQLView
import strawberry
from utils.log import log 
from utils.handleMessage import sendMessage, convertMessage
from .Worker import Worker
from graphql.types import SubProcessType, DataItemType, RootJSONType, PromptResponse
from graphql.resolvers import Query, Mutation

# Simple GraphQL implementation with Flask and debug-server capabilities
class CustomGraphQLView(GraphQLView):
    # override the instance method called by Strawberry to build context
    def get_context(self, request, response=None):
        # self here is the view instance; we read worker from the view class
        # (set by as_view_with_worker)
        return {"request": request, "worker": getattr(self.__class__, "worker", None), 'response': response}

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

class GraphQLWorker(Worker):
    ###############
    # dont edit this part
    ###############
    conn: Connection
    requests: dict = {}
    
    def __init__(self):
        self.requests: dict = {}
        self.app = Flask(__name__)
        self.schema = strawberry.Schema(
            query=Query,
            mutation=Mutation,
        )
        self.setup_routes()
    
    def setup_routes(self):
        # Add Strawberry GraphQL endpoint with debug capabilities
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
        
        # Add health check endpoint
        @self.app.route('/health')
        def health_check():
            return {"status": "healthy", "service": "GraphQLWorker"}
        
        # Add a root endpoint that provides GraphQL playground
        @self.app.route('/')
        def root():
            return {"message": "GraphQL Worker is running", "graphql_endpoint": "/graphql"}
        
        # Legacy endpoint for backward compatibility
        @self.app.route('/query', methods=['POST'])
        def handle_query():
            """Legacy query handler - redirects to Strawberry"""
            try:
                data = request.get_json()
                query = data.get('query', '')
                variables = data.get('variables', {})
                
                # Execute using Strawberry schema
                context = {"worker": self}
                log.log(f"Executing GraphQL query: {query} with variables: {variables}", 'info')
                result = self.schema.execute_sync(
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
                log.log(f"Error in GraphQL query: {str(e)}", 'error')
                return jsonify({"errors": [{"message": str(e)}]}), 500
        
    def run(self, conn: Connection, port: int):
        # assign here
        GraphQLWorker.conn = conn
        self._port = port
        
        def run_listen_task():
            self.listen_task()
        threading.Thread(target=run_listen_task, daemon=True).start()

        # Run Flask app with debug-server capabilities
        self.app.run(host="0.0.0.0", port=self._port, debug=True, threaded=True)

    def listen_task(self):
        log.log("GraphQLWorker is listening for messages...", "info")
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
                
                # Allow other tasks to run
                time.sleep(0.01)
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