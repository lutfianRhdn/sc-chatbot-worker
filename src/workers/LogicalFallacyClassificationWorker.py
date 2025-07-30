import asyncio
import json
from multiprocessing.connection import Connection
import os
import threading
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

        asyncio.run(self.listen_task())

    async def listen_task(self):
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
                    await asyncio.sleep(0.1)  # Add a small delay to prevent busy-waiting
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
        
        if message['data']['is_eval'] == False:
            self.sendToOtherWorker(
                destination=[f"DatabaseInteractionWorker/updateProgress/{message['data']['chat_id']}"],
                data={
                    "process_name": message["data"]["process_name"],
                    "sub_process_name": "Logical fallacy Classification",
                    "input": {
                        "premis" :premis,
                        "kesimpulan" :kesimpulan,
                        "interpretasi" :interpretasi,
                        "kalimat" :prompt,
                        "fallacy_data" : fallacy_data                    
                    },
                    "output": {
                        "fallacy_type":parsed.get("fallacy_type", "Unknown"),
                        "fallacy_location":parsed.get("fallacy_location", {}),
                        "feedback":parsed.get("feedback", "Tidak ada feedback."),
                    },
                },
                messageId=(str(uuid.uuid4()))
            )
        message['data']['fallacy_type'] = parsed.get("fallacy_type", "Unknown")
        message['data']['fallacy_location'] = parsed.get("fallacy_location", {})
        message['data']['feedback'] = parsed.get("feedback", "Tidak ada feedback.")
        self.sendToOtherWorker(
            messageId=message.get("messageId"),
            destination=["LogicalFallacyPromptWorker/logical_fallacy_prompt_modification/" if message['data']['type'] == 'prompt' else "LogicalFallacyResponseWorker/logical_fallacy_prompt_modification/"], 
            data=message['data']
            )        
 
        

    def prepare_classification(self,message)->None:
        premis = message["data"]["premis"]
        kesimpulan = message["data"]["kesimpulan"]
        interpretasi = message["data"]["interpretasi"]
        prompt = message["data"]["prompt"]
        log("prepare_classification, 📝 Memulai klasifikasi logical fallacy.", "info")

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
