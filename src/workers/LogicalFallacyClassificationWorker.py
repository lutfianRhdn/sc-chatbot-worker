import json
from multiprocessing.connection import Connection
import os
import threading
from turtle import pd
import uuid
import time
from  utils.log import log 
from utils.handleMessage import sendMessage, convertMessage
from openai import AzureOpenAI
from prompt.logical_fallacy_classification import prompt_klasifikasi_template

import pandas as pd

from .Worker import Worker

class LogicalFallacyClassificationWorker(Worker):
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
        
    def run(self, conn: Connection, config: dict):
        # assign here
        LogicalFallacyClassificationWorker.conn = conn

        #### add your worker initialization code here
        self.client = AzureOpenAI(
            api_key= config["azure_openai_api_key"],
            api_version= config["azure_openai_api_version"],
            azure_endpoint= config["azure_openai_endpoint"]
        )
        self.model_name = config["azure_openai_deployment_name"]
        
        
        
        
        
        
        #### until this part
        # start background threads *before* blocking server
        threading.Thread(target=self.listen_task, daemon=True).start()
        threading.Thread(target=self.health_check, daemon=True).start()

        # asyncio.run(self.listen_task())
        self.health_check()


    def health_check(self):
        """Send a heartbeat every 10s."""
        while True:
            sendMessage(
                conn=LogicalFallacyClassificationWorker.conn,
                messageId="heartbeat",
                status="healthy"
            )
            time.sleep(10)
    def listen_task(self):
        while True:
            try:
                if LogicalFallacyClassificationWorker.conn.poll(1):  # Check for messages with 1 second timeout
                    message = self.conn.recv()
                    dest = [
                        d
                        for d in message["destination"]
                        if d.split("/", 1)[0] == "LogicalFallacyClassificationWorker"
                    ]
                    destSplited = dest[0].split('/')
                    method = destSplited[1]
                    param= destSplited[2]
                    instance_method = getattr(self,method)
                    instance_method(message)
            except EOFError:
                break
            except Exception as e:
              print(e)
              log(f"Listener error: {e}",'error' )
              break

    def sendToOtherWorker(self, destination, messageId: str, data: dict = None) -> None:
      sendMessage(
          conn=LogicalFallacyClassificationWorker.conn,
          destination=destination,
          messageId=messageId,
          status="completed",
          reason="Message sent to other worker successfully.",
          data=data or {}
      )
    ##########################################
    # add your worker methods here
    ##########################################

    def klasifikasi_fallacy(self, premis,prompt, kesimpulan, interpretasi,fallacy_data, message):

        prompt_klasifikasi = prompt_klasifikasi_template.format(
            premis=premis,
            kesimpulan=kesimpulan,
            interpretasi=interpretasi,
            kalimat=prompt,
            fallacy_data = fallacy_data
        )

        response = self.client.chat.completions.create(
            model= self.model_name,
            messages=[{
                "role": "user",
                "content": prompt_klasifikasi
            }],
        )

        llm_response = response.choices[0].message.content.strip()
        parsed = json.loads(llm_response)
        
        # print("Raw response:", parsed)
        self.sendToOtherWorker(
            messageId=message.get("messageId"),
            destination=["LogicalFallacyPromptWorker/logical_fallacy_prompt_modification/"],
            data={
                "premis":premis,
                "kesimpulan":kesimpulan,
                "prompt":prompt,
                "fallacy_type":parsed.get("fallacy_type", "Unknown"),
                "fallacy_location":parsed.get("fallacy_location", {}),
                "feedback":parsed.get("feedback", "Tidak ada feedback."),
                "feedback_intent":message["data"]["feedback"],
                "is_eval":message["data"]["is_eval"],
                "user_intent": message["data"]["user_intent"],
                "eval_iteration" : message["data"]["eval_iteration"],
                "prompt_user" : message["data"]["prompt_user"]
            }
            )        
 
        

    def prepare_classification(self,message)->None:
        premis = message["data"]["premis"]
        kesimpulan = message["data"]["kesimpulan"]
        interpretasi = message["data"]["interpretasi"]
        prompt = message["data"]["prompt"]

        base_path = os.path.dirname(os.path.abspath(__file__))
        fallacy_path = os.path.join(base_path, "../fallacy/fallacy.csv")        

        df = pd.read_csv(fallacy_path, delimiter=';')

        fallacy_data = ""
        for _, row in df.iterrows():
            tipe = row['tipe']
            deskripsi = row['deskripsi']
            contoh = row['contoh']
            fallacy_data += f"- {tipe}: {deskripsi} sebagai contoh: '{contoh}'\n"
        # print(fallacy_data)   
        # print(message) 
        self.klasifikasi_fallacy(premis = premis,
        prompt = prompt,
        kesimpulan = kesimpulan,
        interpretasi = interpretasi,
        fallacy_data = fallacy_data,
        message = message)

        
def main(conn: Connection, config: dict):
    worker = LogicalFallacyClassificationWorker()
    worker.run(conn, config)
