import asyncio
from multiprocessing.connection import Connection
import threading
import uuid
import time
from  utils.log import log 
from utils.handleMessage import sendMessage, convertMessage
from openai import AzureOpenAI
import json
from .Worker import Worker
from prompt.counterexample_interpretation import prompt_interpretation_template

class CounterExampleCreatorWorker(Worker):
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
        CounterExampleCreatorWorker.conn = conn

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
    def listen_task(self):
        while True:
            try:
                if CounterExampleCreatorWorker.conn.poll(1):  # Check for messages with 1 second timeout
                    message = self.conn.recv()
                    dest = [
                        d
                        for d in message["destination"]
                        if d.split("/", 1)[0] == "CounterExampleCreatorWorker"
                    ]
                    destSplited = dest[0].split('/')
                    method = destSplited[1]
                    param= destSplited[2]
                    instance_method = getattr(self,method)
                    instance_method(message)
                    asyncio.sleep(0.1)  # Add a small delay to prevent busy-waiting
            except EOFError:
                break
            except Exception as e:
              print(e)
              log(f"Listener error: {e}",'error' )
              break

    def sendToOtherWorker(self, destination, messageId: str, data: dict = None) -> None:
      sendMessage(
          conn=CounterExampleCreatorWorker.conn,
          destination=destination,
          messageId=messageId,
          status="completed",
          reason="Message sent to other worker successfully.",
          data=data or {}
      )
    ##########################################
    # add your worker methods here
    ##########################################

    def interpretasi_counterexample(self, message):
        model = message["data"]['model']
        prompt_pengguna = message["data"]['prompt']
        premis = message["data"]['premis']
        kesimpulan = message["data"]['kesimpulan']
        terms_premis = message["data"]['term_premis']
        terms_kesimpulan = message["data"]['terms_kesimpulan']
        predikat = message["data"]['predikat']
        fol = message["data"]['fol']
        # print(message)
        if not isinstance(model, str) or not model.strip():
            print("interpretasi_counterexample, ❌ Counterexample tidak valid atau kosong.")
        
        if 'prompt_interpretation_template' not in globals():
            print("interpretasi_counterexample, ❌ Template interpretasi tidak ditemukan.")

        try:
            # Isi prompt dengan data

            filled_prompt = prompt_interpretation_template.format(
                kalimat=prompt_pengguna,
                premis=json.dumps(premis),
                kesimpulan=kesimpulan,
                terms_premis=json.dumps(terms_premis),
                terms_kesimpulan=json.dumps(terms_kesimpulan),
                predikat=json.dumps(predikat),
                fol=fol.replace('"', '\\"'),
                counterexample=model.replace('"', '\\"')
            )

            # Panggil LLM
            response = self.client.chat.completions.create(
                model= self.model_name,
                messages=[
                    {"role": "system", "content": "Anda adalah pakar logika formal dan reasoning."},
                    {"role": "user", "content": filled_prompt}
                ]
            )
            hasil = response.choices[0].message.content.strip()
            try:
                if hasil.startswith("```json"):
                    hasil = hasil.replace("```json","")
                    hasil = hasil.replace("```","")
                result_json = json.loads(hasil)
                # print(hasil)
                if message['data']['is_eval'] == False:
                    self.sendToOtherWorker(
                        destination=[f"DatabaseInteractionWorker/updateProgress/{message['data']['chat_id']}"],
                        data={
                            "process_name": message["data"]["process_name"],
                            "sub_process_name": "Counterexample Interpretation",
                            "input": {
                                "prompt" : prompt_pengguna,
                                "premis" : json.dumps(premis),
                                "kesimpulan" : kesimpulan,
                                "terms_premis" : json.dumps(terms_premis),
                                "terms_kesimpulan" : json.dumps(terms_kesimpulan),
                                "predikat" : json.dumps(predikat),
                                "fol" : fol.replace('"', '\\"'),
                                "model" : model
                            },
                            "output": result_json["interpretasi_counterexample"],
                        },
                        messageId=(str(uuid.uuid4()))
                    )
                    
                self.sendToOtherWorker(
                        messageId=message.get("messageId"),
                        destination=["LogicalFallacyClassificationWorker/prepare_classification/"],
                        data={
                            "interpretasi":result_json["interpretasi_counterexample"],
                            "premis":premis,
                            "kesimpulan":kesimpulan,
                            "prompt":prompt_pengguna,
                            "feedback": message["data"]["feedback"],
                            "is_eval": message["data"]["is_eval"],
                            "user_intent": message["data"]["user_intent"],
                            "eval_iteration" : message["data"]["eval_iteration"],
                            "prompt_user" : message["data"]["prompt_user"],
                            "chat_id" : message["data"]["chat_id"],
                            "process_name" : message["data"]["process_name"],
                            "latest_intent" : message["data"]["latest_intent"]
                        }
                        )

                return result_json
            except json.JSONDecodeError:
                print("❌ Gagal parsing JSON. Isi respon:\n", hasil)
                return {
                    "error": "Failed to parse LLM response as JSON",
                    "raw_response": hasil,
                    "fallacy_type": "Unknown",
                    "explanation": f"Error dalam klasifikasi: {str(hasil)}"
                }
            
        except Exception as e:
            return {"interpretasi_counterexample": f"❌ Terjadi kesalahan internal: {str(e)}"}


    def test(self,message)->None:
        """
        Example method to test the worker functionality.
        Replace this with your actual worker methods.
        """
        data = message.get("data", {})


        # process


        #send back to RestAPI
        self.sendToOtherWorker(
          messageId=message.get("messageId"),
          destination=["RestApiWorker/onProcessed"],
          data=data
          )
      #   sendMessage(
      #     status="completed",
      #     reason="Test method executed successfully.",
      #     destination=["supervisor"],
      #     data={"message": "This is a test response."}
      # )
        log("Test method called", "info")
        # return {"status": "success", "data": "This is a test response."}

def main(conn: Connection, config: dict):
    worker = CounterExampleCreatorWorker()
    worker.run(conn, config)
