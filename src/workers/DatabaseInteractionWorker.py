import json
from multiprocessing.connection import Connection
import os

from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import traceback
import asyncio
from utils.log import log
from utils.handleMessage import sendMessage
import time




from .Worker  import Worker
class DatabaseInteractionWorker(Worker):
  #################
  # dont edit this part
  ################
  _instanceId: str    
  isBusy: bool = False
  _client: MongoClient 
  _db_name: str 
  conn: Connection
  def __init__(self, conn: Connection, config: dict):
    DatabaseInteractionWorker.conn=conn
    self._db_name = config.get("database", "mydatabase") 
    self._dbTweets = config.get("dbTweets", "dataGathering")
    self.connection_string = config.get("connection_string", "mongodb://localhost:27017/") 
    self.AZURE_OPENAI_API_KEY = config.get("AZURE_OPENAI_API_KEY")
    self.AZURE_OPENAI_ENDPOINT = config.get("AZURE_OPENAI_ENDPOINT")
    self.AZURE_OPENAI_DEPLOYMENT_NAME = config.get("AZURE_OPENAI_DEPLOYMENT_NAME")
    self.AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING = config.get("AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING")
    self.AZURE_OPENAI_API_VERSION = config.get("AZURE_OPENAI_API_VERSION")
  def run(self) -> None:
    self._instanceId = "DatabaseInteractionWorker"
    self._client = MongoClient(self.connection_string)
    self._db= self._client[self._db_name]
    self._dbTweets = self._client[self._dbTweets]
    if not self._client:
      log("Failed to connect to MongoDB", "error")
    self._client.server_info()  # This will raise an exception if the connection fails
    log(f"Connected to MongoDB at {self.connection_string}", "success")
    async def run_background_tasks():
      try:
          # Run both health_check and listen_task concurrently
          await asyncio.gather(
              self.listen_task()
          )
      except Exception as e:
          traceback.print_exc()
          print(e)
          log(f"Failed to run background tasks: {e}", "error")

                # Start the async tasks
    asyncio.run(run_background_tasks())

  
  async def listen_task(self):
      print("DatabaseInteractionWorker is listening for messages...")
      while True:
        try:
        # Change poll(1) to poll(0.1) to reduce blocking time
          if DatabaseInteractionWorker.conn.poll(0.1):  # Shorter timeout
            message = self.conn.recv()
            if(self.isBusy):
                print("DatabaseInteractionWorker is busy, ignoring message.")
                self.sendToOtherWorker(
                    messageId=message.get("messageId"),
                    destination=message.get("destination", []),
                    data=message.get("data", {}),
                    status="failed",
                    reason="SERVER_BUSY"
                )
                continue
            self.isBusy =True
            dest = [
                d
                for d in message["destination"]
                if d.split("/", 1)[0] == "DatabaseInteractionWorker"
            ]
            destSplited = dest[0].split('/')
            method = destSplited[1]
            param= destSplited[2]
            instance_method = getattr(self,method)
            result = instance_method(id = param, data = message.get("data", {}))
              
            sendMessage(
                conn=self.conn, 
                status="completed",
                destination=result["destination"],
                messageId=message["messageId"],
                data=convertObjectIdToStr(result.get('data', [])),
            )
            self.isBusy = False
      
        except EOFError:
            log("Connection closed by supervisor",'error')
            break
        except Exception as e:
            traceback.print_exc()
            print(e)
            log(f"Message loop error: {e}",'error')
            break
        await asyncio.sleep(0.1)  # Sleep to prevent busy-waiting
  
  #########################################
  # Methods for Database Interaction
  #########################################
  
  def getPrompt(self,id,data):
    prompts = self._db['prompts'].find({"project_id":id})
    print(prompts)
    return {"data":list(prompts),"destination":[f"RestApiWorker/onProcessed/"]}
  
  def getTweets(self, id,data):
    if not self._isBusy:
      try:
        self._isBusy = True
      
        start_date = data.get("start_date", "")
        end_date = data.get("end_date", "")
        keyword = data.get("keyword", "")

        collection = self._dbTweets['tweets']
        # Query
        # print(keyword.replace(' ','|'),"keyword")
        match_stage = {
              '$match': {
                  'full_text': {'$regex': keyword.replace(' ','|'), '$options': 'i'}
              }
          }
          
        pipeline = [match_stage]

          # Add date filtering if both start_date and end_date are provided
        if start_date and end_date:
          start_datetime = datetime.strptime(f"{start_date} 00:00:00 +0000", "%Y-%m-%d %H:%M:%S %z")
          end_datetime = datetime.strptime(f"{end_date} 23:59:59 +0000", "%Y-%m-%d %H:%M:%S %z")
          # print(f"Filtering tweets from {start_datetime} to {end_datetime}")
          
          add_fields_stage = {
              '$addFields': {
                  'parsed_date': {'$toDate': '$created_at'}
              }
          }
          match_date_stage = {
              '$match': {
                  'parsed_date': {'$gte': start_datetime, '$lte': end_datetime}
              }
          }

          pipeline.extend([add_fields_stage, match_date_stage])
          
          # Project stage to include only specific fields
        project_stage = {
              '$project': {
                  '_id' : 1,
                  'full_text': 1,
                  'username': 1,
                  'in_reply_to_screen_name': 1,
                  'tweet_url': 1
              }
          }
        pipeline.append(project_stage)
          # Execute the aggregation pipeline
        cursor = collection.aggregate(pipeline)
        
          # return list(cursor)

        self._isBusy = False
        # print(list(cursor))
        return {"data": list(cursor), "destination": [
          f"VectorWorker/createVector/{id}"
          f"PromptRecommendationWorker/onTweetComing/{id}"
          ]}
      except Exception as e:
        traceback.print_exc()
        log(f"Error in getTweets: {e}", "error")
  
  def getData(self,id):
    if not self._isBusy:
      self._isBusy =True
      collection= self._db['mycollection']
      data = list(collection.find({"project_id":id}))
      
      self._isBusy= False
      return {"data":data,"destination":["RestApiWorker/onProcessed"]}
  def createNewHistory(self,id,data):
    created = self._db['history'].insert_one({
      "process": [],
      "question": data.get("question", ""),
      "answer": data.get("answer", ""),
      "created_at": data.get("created_at", time.time()),
      "updated_at": data.get("updated_at", time.time())
      
    })
    print(f"New history created with id: {created.inserted_id}")
    return {"data":[{"_id":created.inserted_id}],"destination":["RestApiWorker/onProcessed/"]}

    
  def getProgress(self,id,data):
    # print(f"Fetching progress for id: {id}")
    process_name = data['process_name'] if 'process_name' in data else ''
    # print(f"Process name: {process_name}")
    query = {"_id": ObjectId(id)}
    if process_name:
      query['process.process_name'] = process_name
    # print(f"Query: {query}")
    message = self._db['history'].find_one(query)
    # print(f"Found message: {message}")
    if not message:
      print(f"No message found with id: {id}")
      return {"data": [], "destination": ["RestApiWorker/onProcessed/"]}
    process_list = message.get('process', [])
    # print(f"Process list: {process_list}")
    if process_name:
      process_list = [p for p in process_list if p['process_name'] == process_name]
      # print(f"Filtered process list: {process_list}")
    if not process_list:
      print(f"No process found with name: {process_name}")
    return {"data": list(process_list), "destination": ["RestApiWorker/onProcessed/"]}
  
  
  def createNewProgress(self,id,data):
    process_name = data.get('process_name', '')
    input = data.get('input', '')
    output = data.get('output', '')
    
    # print(f"Creating new progress for {process_name} with input: {input} and output: {output}")
    data = self._db['history'].find_one({"_id": ObjectId(id)})
    processed = data.get('process', [])
    processed.append({
      "process_name": process_name,
      "input": input,
      "output": output,
      "sub_process": []
    })
    updated = self._db['history'].update_one(
        {"_id": ObjectId(id)},
        {"$set": {
          "process": processed
          }}
    )
    print(f"Updated history with id: {id} to include new progress")
    return {"data":[{"_id":id}],"destination":["supervisor"]}
    # print(f"New progress created for {process_name} with input: {input} and output: {output}")
   
  def updateOutputProcess(self,id,data):
      # print(f"Updating output for id: {id} with data: {data}")
      process_name = data.get('process_name', '')
      output = data.get('output', '')

      updated = self._db['history'].update_one(
          {"_id": ObjectId(id), "process.process_name": process_name},
          {"$set": {
              "process.$.output": output,
              "updated_at": time.time()
          }}
      )
      return {"data":[{"_id":id}],"destination":["supervisor"]}

      
    
  def updateFinalAnswer(self,id,data):
      # print(f"Updating output for id: {id} with data: {data}")
      output = data.get('output', '')

      updated = self._db['history'].update_one(
          {"_id": ObjectId(id)},
          {"$set": {
              "answer": output,
              "updated_at": time.time()
          }}
      )
      return {"data":[{"_id":id}],"destination":["supervisor"]}

      
  def updateProgress(self,id,data):
      # print(f"Updating progress for id: {id} with data: {data}")
      process_name = data.get('process_name', '')
      sub_process_name = data.get('sub_process_name', '')
      input = data.get('input', '')
      output = data.get('output', '')
      message = self._db['history'].find_one({"_id": ObjectId(id)})
      # print(f"Found message: {message}")
      process_list = message.get('process', [])

      # Cek apakah proses dengan nama process_name sudah ada
      process_found = False
      for process in process_list:
          if process['process_name'] == process_name:
              # print(f"Sub-process name: {sub_process_name}, Input: {input}, Output: {output}")
              process['sub_process'].append({
                  "sub_process_name": sub_process_name,
                  "input": input,
                  "output": output
              })
              process_found = True
              break

      # Jika belum ada, buat entri baru
      if not process_found:
          process_list.append({
              "process_name": process_name,
              "sub_process": [{
                  "sub_process_name": sub_process_name,
                  "input": input,
                  "output": output
              }]
          })

      # Simpan kembali ke MongoDB
      self._db['history'].update_one(
          {"_id": ObjectId(id)},
          {"$set": {
              "process": process_list
          }}
      )
      return {"data":[{"_id":id}],"destination":["supervisor"]}



  def createNewPrompt(self,id,data):
    try:
      # print(f"Creating new prompt  with data: {data}")
      created = self._db['prompts'].insert_one(data)
      print(f"New prompt created with id: {created.inserted_id}")
      return {"data":[{"_id":created.inserted_id}],"destination":["supervisor"]}
    except Exception as e:
      traceback.print_exc()
      log(f"Error in createNewPrompt: {e}", "error")
      return {"data": [], "destination": ["supervisor"]}
############### Helper function to convert ObjectId to string in a list of documents
  
  
def convertObjectIdToStr(data: list) -> list:
   res =[]
   for doc in data:
    if("_id" in doc and isinstance(doc["_id"], ObjectId)):
      doc["_id"] = str(doc["_id"])
    res.append(doc)
   return res
# This is the main function that the supervisor calls


def main(conn: Connection, config: dict):
    """Main entry point for the worker process"""
    worker = DatabaseInteractionWorker(conn, config)
    worker.run()