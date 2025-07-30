import asyncio
from multiprocessing.connection import Connection
import threading
import uuid
import time
from utils.loadPromptTemplate import load_prompt_template
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
    async def listen_task(self):
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
                    await asyncio.sleep(0.1)  # Add a small delay to prevent busy-waiting
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

        if not isinstance(model, str) or not model.strip():
            print("interpretasi_counterexample, ❌ Counterexample tidak valid atau kosong.")
        
        if 'prompt_interpretation_template' not in globals():
            print("interpretasi_counterexample, ❌ Template interpretasi tidak ditemukan.")
        try:
            if( message['data']['type'] =='prompt'):
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
            else: 
                prompt = load_prompt_template("interpretasi_counter_example.json")
                prompt['context']['relevant_information']['respons_chatbot'] = prompt_pengguna
                prompt['context']['relevant_information']['premis'] = premis
                prompt['context']['relevant_information']['kesimpulan'] = kesimpulan
                prompt['context']['relevant_information']['terms_premis'] = terms_premis
                prompt['context']['relevant_information']['terms_kesimpulan'] = terms_kesimpulan
                prompt['context']['relevant_information']['atomic_formula'] = predikat
                prompt['context']['relevant_information']['fol'] = fol
                prompt['context']['input_queries']['hasil_smt_solver'] = model

                filled_prompt = json.dumps(prompt, indent=4)
            log("interpretasi_counterexample, 📝 Mengirim prompt ke LLM untuk interpretasi counterexample.", "info")
            # Panggil LLM
            response = self.client.chat.completions.create(
                model= self.model_name,
                messages=[
                    {"role": "system", "content": "Anda adalah pakar logika formal dan reasoning."},
                    {"role": "user", "content": filled_prompt}
                ]
            )
            hasil = response.choices[0].message.content.strip()
            print("interpretasi_counterexample, 📝 Hasil dari LLM:", hasil)
            try:
                if hasil.startswith("```json"):
                    hasil = hasil.replace("```json","")
                    hasil = hasil.replace("```","")
                result_json = json.loads(hasil)
                print("interpretasi_counterexample, 📝 Hasil JSON yang di-parse:", result_json)
                    
                message['data']['interpretasi']= result_json["interpretasi_counter_example"] if "interpretasi_counter_example" in result_json else result_json["interpretasi_counterexample"]
                log("interpretasi_counterexample, ✅ Interpretasi counterexample berhasil dibuat.", "info")
                if message['data']['is_eval'] == False:
                    self.sendToOtherWorker(
                            destination=[f"DatabaseInteractionWorker/updateProgress/{message['data']['chat_id']}"],
                            data={
                                "process_name": message["data"]["process_name"],
                                "sub_process_name": "Counterexample Interpretation",
                                "input": {
                                    "model": model,
                                    "prompt": prompt_pengguna,
                                    "premis": premis,
                                    "kesimpulan": kesimpulan,
                                    "terms_premis": terms_premis,
                                    "terms_kesimpulan": terms_kesimpulan,
                                    "predikat": predikat,
                                    "fol": fol,
                                    },
                                "output": message['data']['interpretasi'],
                            },
                            messageId=(str(uuid.uuid4()))
                        )
                self.sendToOtherWorker(
                        messageId=message.get("messageId"),
                        destination=["LogicalFallacyClassificationWorker/prepare_classification/"],
                        data=message['data']
                        )

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
