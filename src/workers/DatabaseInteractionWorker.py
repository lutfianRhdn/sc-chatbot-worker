from multiprocessing.connection import Connection
import os

from pymongo import MongoClient
from bson.objectid import ObjectId

import asyncio
from utils.log import log
from utils.handleMessage import sendMessage
import time

from langchain_openai import AzureOpenAIEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch



from .Worker  import Worker
class DatabaseInteractionWorker(Worker):
  #################
  # dont edit this part
  ################
  _instanceId: str    
  _isBusy: bool = False
  _client: MongoClient 
  _db_name: str 
  def __init__(self, conn: Connection, config: dict):
    self.conn=conn
    self._db_name = config.get("database", "mydatabase") 
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
    self.connect_retrieval()
    if not self._client:
      log("Failed to connect to MongoDB", "error")
    log(f"Connected to MongoDB at {self.connection_string}", "success")
    asyncio.run(self.listen_task())
    self.health_check()

  
  def health_check(self) -> None:
    while True :
      pass
      sendMessage(conn=self.conn,messageId=self._instanceId, status="healthy")
      time.sleep(10)
  
  async def listen_task(self) -> None:
    while True:
      try:
          if self.conn.poll(1):  # Check for messages with 1 second timeout
              message = self.conn.recv()
              dest = [
                  d
                  for d in message["destination"]
                  if d.split("/", 1)[0] == "DatabaseInteractionWorker"
              ]
              # dest = [d for d in message['destination'] if d ='DatabaseInteractionWorker']
              destSplited = dest[0].split('/')
              method = destSplited[1]
              param= destSplited[2]
              instance_method = getattr(self,method)
              print(f"Calling method: {method} with param: {param} and data: {message.get('data', {})}")
              result = instance_method(id=param, data=message.get("data", {}))
              print(f"Received message: {result}")
              sendMessage(
                  conn=self.conn, 
                  status="completed",
                  destination=result["destination"],
                  messageId=message["messageId"],
                  data=convertObjectIdToStr(result.get('data', [])),
              )
      except EOFError:
          log("Connection closed by supervisor",'error')
          break
      except Exception as e:
          log(f"Message loop error: {e}",'error')
          break
  
  #########################################
  # Methods for Database Interaction
  #########################################
  
  def getData(self,id):
    if not self._isBusy:
      self._isBusy =True
      collection= self._db['mycollection']
      data = list(collection.find({"project_id":id}))
      
      self._isBusy= False
      return {"data":data,"destination":["RestApiWorker/onProcessed"]}
  def createNewHistory(self,id,data):
    print(data)
    created = self._db['history'].insert_one({
      "process": [],
      "question": data.get("question", ""),
      "answer": data.get("answer", ""),
      "created_at": data.get("created_at", time.time()),
      "updated_at": data.get("updated_at", time.time())
      
    })
    print(f"New history created with id: {created.inserted_id}")
    return {"data":[{"_id":created.inserted_id}],"destination":["RestApiWorker/onProcessed"]}

    
    
  def createNewProgress(self,id,data):
    process_name = data.get('process_name', '')
    input = data.get('input', '')
    output = data.get('output', '')
    
    print(f"Creating new progress for {process_name} with input: {input} and output: {output}")
    data = self._db['history'].find_one({"_id": ObjectId(id)})
    processed = data.get('process', [])
    processed.append({
      "process_name": process_name,
      "input": input,
      "output": output,
      "sub_process": []
    })
    print(processed,"processed")
    updated = self._db['history'].update_one(
        {"_id": ObjectId(id)},
        {"$set": {
          "process": processed
          }}
    )
    print(f"Updated history with id: {id} to include new progress")
    return {"data":[{"_id":id}],"destination":["RestApiWorker/onProcessed"]}
    # print(f"New progress created for {process_name} with input: {input} and output: {output}")
   

    
  def updateProgress(self,id,data):
      print(f"Updating progress for id: {id} with data: {data}")
      process_name = data.get('process_name', '')
      sub_process_name = data.get('sub_process_name', '')
      input = data.get('input', '')
      output = data.get('output', '')
      message = self._db['history'].find_one({"_id": ObjectId(id)})
      print(f"Found message: {message}")
      process_list = message.get('process', [])

      # Cek apakah proses dengan nama process_name sudah ada
      process_found = False
      for process in process_list:
          if process['process_name'] == process_name:
              print(f"Process {process_name} found, updating sub-process.")
              print(f"Sub-process name: {sub_process_name}, Input: {input}, Output: {output}")
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
      return {"data":[{"_id":id}],"destination":["RestApiWorker/onProcessed"]}
      
  
############### Helper function to convert ObjectId to string in a list of documents
  
  
def convertObjectIdToStr(data: list) -> list:
   res =[]
   for doc in data:
      doc["_id"] = str(doc["_id"])
      res.append(doc)
   return res
# This is the main function that the supervisor calls


def main(conn: Connection, config: dict):
    """Main entry point for the worker process"""
    worker = DatabaseInteractionWorker(conn, config)
    worker.run()