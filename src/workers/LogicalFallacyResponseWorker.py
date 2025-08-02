import asyncio
from multiprocessing.connection import Connection
import threading
import traceback
import uuid
import time

from openai import AzureOpenAI
from utils.loadPromptTemplate import fix_json_if_incomplete, load_prompt_template, remove_json_text
from  utils.log import log 
from utils.handleMessage import sendMessage, convertMessage
# from utils.get_counter_example import get_counter_example
import json
from flask import Flask, request, jsonify
from .Worker import Worker

class LogicalFallacyResponseWorker(Worker):
    ###############
    # dont edit this part
    ###############
    route_base = "/"
    conn:Connection
    requests: dict = {}
    process_name ="Handling Logical Fallacy on Response Chatbot"
    def __init__(self):
        # we'll assign these in run()
        self._port: int = None

        self.requests: dict = {}
        
    def run(self, conn: Connection, config):
        # assign here
        try:
            LogicalFallacyResponseWorker.conn = conn

            #### add your worker initialization code here
            
            
            print(config)
            self.client = AzureOpenAI(
                azure_endpoint = config['azure_openai_endpoint'],
                api_key=config['azure_openai_api_key'],  
                api_version=config['azure_openai_api_version']
                )
            self.model_name = config['azure_openai_deployment_name']

            
            log("LogicalFallacyResponseWorker initialized successfully", "info")
            asyncio.run(self.listen_task())
        except Exception as e:
            log(f"Error in LogicalFallacyResponseWorker run method: {e}", 'error')
            traceback.print_exc()



    async def listen_task(self):
        while True:
            try:
                if LogicalFallacyResponseWorker.conn.poll(1):  # Check for messages with 1 second timeout
                    message = self.conn.recv()
                    dest = [
                        d
                        for d in message["destination"]
                        if d.split("/", 1)[0] == "LogicalFallacyResponseWorker"
                    ]
                    destSplited = dest[0].split('/')
                    method = destSplited[1]
                    param= destSplited[2]
                    instance_method = getattr(self,method)
                    instance_method(message)
                    await asyncio.sleep(0.01)  # Allow other async tasks to run
            except EOFError:
                break
            except Exception as e:
              print(e)
              log(f"Listener error: {e}",'error' )
              break

    def sendToOtherWorker(self, destination, messageId: str, data: dict = None) -> None:
      sendMessage(
          conn=LogicalFallacyResponseWorker.conn,
          destination=destination,
          messageId=messageId,
          status="completed",
          reason="Message sent to other worker successfully.",
          data=data or {}
      )
    ##########################################
    # add your worker methods here
    ##########################################
    def fol_transformation(self, response):
        chains = ["premis_kesimpulan.json", "terms.json", "atomic_formula.json", "fol.json"]
        for chain in chains:
            if chain == "premis_kesimpulan.json":
                prompt = load_prompt_template(chain)
                prompt['context']['input_queries']['respons_chatbot'] = response
                prompt = json.dumps(prompt, indent=4)
                res = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                )
                chain_1 = fix_json_if_incomplete(remove_json_text(res.choices[0].message.content))
                # update db
                
                print(f"❇️ Hasil Chain 1: {chain_1}")
                if(chain_1['premis'] == '' or chain_1['kesimpulan'] == ''):
                    print("❌ Tidak ada Logical Fallacy yang ditemukan dalam respons chatbot.")
                    return {
                        "premis": "",
                        "conclusion": "",
                        "terms_premis": "",
                        "terms_kesimpulan": "",
                        "atomic_formula": "",
                        "fol": ""
                    }
                print() 
            elif chain == "terms.json":
                prompt = load_prompt_template(chain)
                data = chain_1
                premis = data['premis']
                kesimpulan = data['kesimpulan']
                prompt['context']['input_queries']['premis'] = premis
                prompt['context']['input_queries']['kesimpulan'] = kesimpulan
                prompt = json.dumps(prompt, indent=4)
                res = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                )
                chain_2 = remove_json_text(res.choices[0].message.content)
                
                print(f"❇️ Hasil Chain 2: {chain_2}")
                print()
            elif chain == "atomic_formula.json":
                prompt = load_prompt_template(chain)
                data = fix_json_if_incomplete(chain_2)
                term_premis = data['terms_premis']
                term_kesimpulan = data['terms_kesimpulan']
                prompt['context']['input_queries']['premis'] = premis
                prompt['context']['input_queries']['kesimpulan'] = kesimpulan
                prompt['context']['input_queries']['term_premis'] = term_premis
                prompt['context']['input_queries']['term_kesimpulan'] = term_kesimpulan
                prompt = json.dumps(prompt, indent=4)
                res =  self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                )
                chain_3 = remove_json_text(res.choices[0].message.content)
                
                print(f"❇️ Hasil Chain 3: {chain_3}")
                print()
            elif chain == "fol.json":
                prompt = load_prompt_template(chain)
                data_chain_1 = chain_1
                data_chain_2 = fix_json_if_incomplete(chain_2)
                data_chain_3 = fix_json_if_incomplete(chain_3)
                premis = data_chain_1['premis']
                kesimpulan = data_chain_1['kesimpulan']
                term_premis = data_chain_2['terms_premis']
                term_kesimpulan = data_chain_2['terms_kesimpulan']
                atomic_formula = data_chain_3['atomic_formula']
                prompt['context']['input_queries']['respons_chatbot'] = response
                prompt['context']['input_queries']['premis'] = premis
                prompt['context']['input_queries']['kesimpulan'] = kesimpulan
                prompt['context']['input_queries']['term_premis'] = term_premis
                prompt['context']['input_queries']['term_kesimpulan'] = term_kesimpulan
                prompt['context']['input_queries']['atomic_formula'] = atomic_formula
                prompt = json.dumps(prompt, indent=4)
                res =  self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                )
                chain_4 = remove_json_text(res.choices[0].message.content)
                
                fol = fix_json_if_incomplete(chain_4)
                print(fol)
                fol = fol['fol']
                print(f"❇️ Hasil Chain 4: {chain_4}")
                print()

        fol_transformation_response = {
            "premis": premis,
            "conclusion": kesimpulan,
            "terms_premis": term_premis,
            "terms_kesimpulan": term_kesimpulan,
            "atomic_formula": atomic_formula,
            "fol": fol,
        }
        return fol_transformation_response

    def thematic_progression(self,premise, conclusion):
        prompt = load_prompt_template("theme_rheme.json")
        kalimat = ' '.join(premise) + ' ' + conclusion
        prompt['context']['input_queries']['kalimat'] = kalimat 
        prompt = json.dumps(prompt, indent=4)
        res = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )
        print()
        pola_tp = remove_json_text(res.choices[0].message.content)
        
        pola_tp = fix_json_if_incomplete(pola_tp)

        prompt = load_prompt_template("problems_thematic_progression.json")
        prompt['context']['input_queries']['kalimat'] = kalimat
        prompt['context']['input_queries']['identifikasi_theme_rheme'] = pola_tp['identifikasi_theme_rheme']
        prompt['context']['input_queries']['identifikasi_jenis_thematic_progression'] = pola_tp['identifikasi_jenis_thematic_progression']
        prompt = json.dumps(prompt, indent=4)
        res = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )
        res_parsed = remove_json_text(res.choices[0].message.content)

        return {"jenis_masalah_thematic_progression":pola_tp['identifikasi_jenis_thematic_progression'],"identifikasi_masalah_thematic_progression":fix_json_if_incomplete(res_parsed)['identifikasi_masalah_thematic_progression']}
    
    def modify_response(self,respons_chatbot, counter_example, logical_fallacy, thematic_progression_problems):
        prompt = load_prompt_template("modifikasi.json")
        prompt['context']['relevant_information']['logical_fallacy'] = str(logical_fallacy)  
        prompt['context']['relevant_information']['counterexample'] = str(counter_example)
        prompt['context']['input_queries']['thematic_progression_problems'] = thematic_progression_problems
        prompt['context']['input_queries']['respons_chatbot'] = respons_chatbot
        prompt = json.dumps(prompt, indent=4)
        modifikasi_respons = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )
        
        modifikasi_respons = remove_json_text(modifikasi_respons.choices[0].message.content)
        print(f"❇️ Hasil Modifikasi: {modifikasi_respons}")
        print(f"prompt yang digunakan: {prompt}")
        modifikasi_respons = {
            "kalimat_asli": fix_json_if_incomplete(modifikasi_respons)['kalimat_asli'],
            "kalimat_modifikasi": fix_json_if_incomplete(modifikasi_respons)['kalimat_modifikasi'],
            "kalimat_keseluruhan": fix_json_if_incomplete(modifikasi_respons)['kalimat_keseluruhan']
        }
        return modifikasi_respons
    def logical_fallacy_response_modification(self,message):
        log("LogicalFallacyResponseWorker/logical_fallacy_response_modification, 📝 Memulai modifikasi prompt logical fallacy.", "info")
        print(json.dumps(message, indent=4))
        
        progression = self.thematic_progression(premis=message['data']['premis'], kesimpulan=message['data']['kesimpulan'])
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{message['data']['chat_id']}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Thematic Progression",
                "input": {
                    "conclution": message['data']['kesimpulan'],
                    "premis": message['data']['premis'],
                    },
                "output": progression,
            },
            messageId=(str(uuid.uuid4()))
        )
        print(f"🧮 Hasil Identifikasi TP: {progression}")
        print(json.dumps(message, indent=4))
        print(json.dumps(progression, indent=4))
        modified_response = self.modify_response(
            respons_chatbot=message['data']['prompt'],
            counter_example=message['data']['interpretasi'],
            logical_fallacy=message['data']['fallacy_type'],
            thematic_progression_problems=progression['identifikasi_masalah_thematic_progression']
        )
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{message['data']['chat_id']}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Modify Response",
                "input": {
                    "respons_chatbot": message['data']['prompt'],
                    "counter_example": message['data']['interpretasi'],
                    "logical_fallacy": message['data']['fallacy_type'],
                    "thematic_progression_problems": progression['identifikasi_masalah_thematic_progression'],
                    },
                "output": modified_response,
            },
            messageId=(str(uuid.uuid4()))
        )
        
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateOutputProcess/{message['data']['chat_id']}"],
            data={
                "process_name": message["data"]["process_name"],
                "output": modified_response['kalimat_keseluruhan'],
            },
            messageId= str(uuid.uuid4())
        )       
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateFinalAnswer/{message['data']['chat_id']}"],
            data={
                "process_name": message["data"]["process_name"],
                "output": modified_response['kalimat_keseluruhan'],
            },
            messageId= str(uuid.uuid4())
        )       
        
        print(f"📝 Hasil Modifikasi Respons Chatbot: {modified_response}")
        
        
    def removeLFResponse(self,message)->None:
        """
        Example method to test the worker functionality.
        Replace this with your actual worker methods.
        """
        data = message.get("data", {})
        response = data['response']
        fol_transformation = self.fol_transformation(response)
        self.sendToOtherWorker(
                destination=[f"DatabaseInteractionWorker/updateProgress/{message['data']['chat_id']}"],
                data={
                    "process_name": self.process_name,
                    "sub_process_name": "FOL Extraction",
                    "input": response,
                    "output": fol_transformation,
                },
                messageId=(str(uuid.uuid4()))
            )
        self.sendToOtherWorker(
            destination=["SMTConverterWorker/smt_file_converter_from_response/"],
            messageId=message.get("messageId"),
            data={
                "fol":fol_transformation['fol'],
                'send_back_destionation': 'LogicalFallacyResponseWorker/onProcessed',
                'type': 'response',
                'prompt': response,
                'premis':fol_transformation['premis'],
                'kesimpulan':fol_transformation['conclusion'],
                'term_premis':fol_transformation['terms_premis'],
                'terms_kesimpulan':fol_transformation['terms_kesimpulan'],
                'predikat':fol_transformation['atomic_formula'],
                'process_name': self.process_name,
                'chat_id': data.get('chat_id', 'unknown_chat_id'),
                'is_eval':False
            }
        )

def main(conn: Connection, config: dict):
    worker = LogicalFallacyResponseWorker()
    worker.run(conn, config)
