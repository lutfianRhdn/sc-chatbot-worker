from email.mime import message
from multiprocessing.connection import Connection
import traceback
from flask import Flask, request, jsonify
from flask_classful import FlaskView, route
import threading
import uuid
import asyncio
import time
from utils.log import log 
from utils.handleMessage import sendMessage, convertMessage
from .Worker import Worker
from flask_cors import CORS
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app)


class RestApiWorker(FlaskView, Worker):
    ###############
    # dont edit this part
    ###############
    route_base = "/"
    conn:Connection
    requests: dict = {}
    def __init__(self):
        # we'll assign these in run()
        self._port: int = None

        self.requests: dict = {}
        
    def run(self, conn: Connection, port: int):
        # assign here
        RestApiWorker.conn = conn
        self._port = port

        RestApiWorker.register(app)
        def run_listen_task():
            asyncio.run(self.listen_task())
        

        # start background threads *before* blocking server
        threading.Thread(target=run_listen_task, daemon=False).start()

        app.run(debug=True, port=6000, use_reloader=False,host="0.0.0.0")
       

            
    async def listen_task(self):
        print("CRAGWorker is listening for messages...")
        while True:
            try:
            # Change poll(1) to poll(0.1) to reduce blocking time
                if RestApiWorker.conn.poll(0.1):  # Shorter timeout
                    message = self.conn.recv()
                    # if(self.isBusy):
                    #     print("CRAGWorker is busy, ignoring message.")
                    #     self.sendToOtherWorker(
                    #         messageId=message.get("messageId"),
                    #         destination=message.get("destination", []),
                    #         data=message.get("data", {}),
                    #         status="failed",
                    #         reason="SERVER_BUSY"
                    #     )
                    #     continue
                    dest = [
                        d
                        for d in message["destination"]
                        if d.split("/", 1)[0] == "RestApiWorker"
                    ]
                    destSplited = dest[0].split('/')
                    method = destSplited[1]
                    param= destSplited[2]
                    instance_method = getattr(self,method)
                    instance_method(message)
                
                # ADD THIS LINE: Allow other async tasks to run
                await asyncio.sleep(0.01)
            except EOFError:
                break
            except Exception as e:
              print(e)
              log(f"Listener error: {e}",'error' )
              break

    def listen_task(self):
        while True:
            try:
                if RestApiWorker.conn.poll(0.1):  # Check for messages with 1 second timeout
                    raw = RestApiWorker.conn.recv()
                    # print(raw)
                    msg = convertMessage(raw)
                    self.onProcessed(raw)
            except EOFError:
                break
            except Exception as e:
                log(f"Listener error: {e}",'error' )
                break

    def onProcessed(self, msg):
        """
        Called when a worker response comes in.
        msg must contain 'messageId' and 'data'.
        """
        task_id = msg.get("messageId")
        entry = RestApiWorker.requests[task_id]
        if not entry:
            return
        entry["response"] = msg.get("data")
        entry["event"].set()
    def sendToOtherWorker(self, destination: str, data):
      task_id = str(uuid.uuid4())
      evt = threading.Event()
      
      RestApiWorker.requests[task_id] = {
          "event": evt,
          "response": None
      }
      print(f"Sending request to {destination} with task_id: {task_id}")
      
      sendMessage(
          conn=RestApiWorker.conn,
          messageId=task_id,
          status="processing",
          destination=destination,
          data=data
      )
      if not evt.wait(timeout=30000):
          # timeout
          return {
              "taskId": task_id,
              "status": "timeout",
              "result": None
          }
      
      # success
      result = RestApiWorker.requests.pop(task_id)["response"]
      return {
          "taskId": task_id,
          "status": "completed",
          "result": result
      }

    ##########################################
    # FLASK ROUTES FUNCTIONS
    ##########################################
    @route('/prompt', methods=['GET'])
    def getPrompt(self):
      projectId = request.args.get('project_id')
      response = self.sendToOtherWorker(
          destination=[f"DatabaseInteractionWorker/getPrompt/{projectId}"],
          data={"projectId": projectId}
      )
    #   print(response)
      if response["status"] == "timeout":
          return jsonify({"error": "Request timed out"}), 504
      elif response["status"] == "completed":
          return jsonify(response["result"]), 200
      else:
          return jsonify({"error": "Unknown error"}), 500
      
      
    @route('/chat/<id>', methods=['GET'])
    def getProgresst(self,id):
      progress_name = request.args.get('progress_name')
      print(f"Getting progress for chat ID: {id} with progress name: {progress_name}")
      response = self.sendToOtherWorker(
          destination=[f"DatabaseInteractionWorker/getProgress/{id}"],
          data={"id": id, "process_name": progress_name}
      )
    #   print(response)
      if response["status"] == "timeout":
          return jsonify({"error": "Request timed out"}), 504
      elif response["status"] == "completed":
          return jsonify({
              "status": "success",
              "message": "Progress retrieved successfully",
            "data": response["result"]
              }), 200
      else:
          return jsonify({"error": "Unknown error"}), 500
      
    @route('/', methods=['GET'])
    def getData(self):
    #   projectId = request.args.get('projectId')
    
      return jsonify({
          "status": "success",
            "message": "RestApiWorker is running",
            
          }), 500

    @route('/chat-crag', methods=['POST'])
    def chatCrag(self):
      
      projectId = request.json.get('projectId')
      prompt = request.json.get('prompt')
      
      message = self.sendToOtherWorker(
            destination=["DatabaseInteractionWorker/createNewHistory/"],
            data={
                "question": prompt,
                "projectId": projectId
            }
        )
      id = message.get("result", [{}])[0].get("_id", "unknown_id")
      print(f"Chat CRAG ID: {id}")
      sendMessage(
        conn=RestApiWorker.conn,
        messageId=id,
        status="complated",
        destination=[f"CRAGWorker/generateAnswer/{id}"],
        data={
                "prompt": prompt,
                "projectId": projectId
            }
      )
      
      if message["status"] == "timeout":
          return jsonify({"error": "Request timed out"}), 504
      elif message["status"] == "completed":
          return jsonify({
              "status": "success create new chat history, the progress updated every completed sub_step processed",
                "data": {
                    "chat_id": id,
                    "prompt": prompt,
                    "projectId": projectId
                }
              }), 200
      else:
          return jsonify({"error": "Unknown error"}), 500
    

    @route('/chat', methods=['POST'])
    def lfu_prompt(self):
        """
        A test route to send a message to another worker.
        """
        projectId = request.json.get('projectId')
        prompt = request.json.get('prompt')
      
        message = self.sendToOtherWorker(
                destination=["DatabaseInteractionWorker/createNewHistory/"],
                data={
                    "question": prompt,
                    "projectId": projectId
                }
            )
        id = message.get("result", [{}])[0].get("_id", "unknown_id")
        
        sendMessage(
        conn=RestApiWorker.conn,
        messageId=id,
        status="complated",
        destination=[f"LogicalFallacyPromptWorker/removeLFPrompt/"],
        data={
                "prompt": prompt,
                "id": id,
                "projectId": projectId
            }
      )
        if message["status"] == "timeout":
          return jsonify({"error": "Request timed out"}), 504
        elif message["status"] == "completed":
          return jsonify({
              "status": "success create new chat history, the progress updated every completed sub_step processed",
                "data": {
                    "chat_id": id,
                    "prompt": prompt,
                    "projectId": projectId
                }
              }), 200
        else:
          return jsonify({"error": "Unknown error"}), 500
      
def main(conn: Connection, config: dict):
    
    worker = RestApiWorker()
    worker.run(conn, config.get("port", 5000))
