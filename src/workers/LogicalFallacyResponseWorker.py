import asyncio
from multiprocessing.connection import Connection
import threading
import traceback
import uuid
import time
import re

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
    def fol_transformation(self, response, references, messages):
        chains = ["premis_kesimpulan.json", "terms.json", "atomic_formula.json", "fol.json"]
        for chain in chains:
            if chain == "premis_kesimpulan.json":
                prompt = load_prompt_template(chain)
                print(prompt)
                prompt['context']['input_queries']['respons_chatbot'] = response
                prompt = json.dumps(prompt, indent=4)
                messages.append({"role": "user", "content": prompt})
                res = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages
                )
                chain_1 = fix_json_if_incomplete(remove_json_text(res.choices[0].message.content))
                messages.append({"role": "assistant", "content": str(chain_1)})
                # update db
                
                print(f"❇️ Hasil Chain 1: {chain_1}")
                if(chain_1['premis'] == '' or chain_1['kesimpulan'] == ''):
                    print("❌ Tidak ada Logical Fallacy yang ditemukan dalam respons chatbot.")
                    return {
                        "premis": "",
                        "conclusion": "",
                        "terms_premis": "",
                        "terms_kesimpulan": "",
                        "atomic_formula_premis": "",
                        "atomic_formula_kesimpulan": "",
                        "fol": "",
                        "messages": messages,
                        "references": references,
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
                messages.append({"role": "user", "content": prompt})
                res = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages
                )
                
                chain_2 = remove_json_text(res.choices[0].message.content)
                messages.append({"role": "assistant", "content": str(chain_2)})
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
                messages.append({"role": "user", "content": prompt})
                res = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages
                )
                
                chain_3 = remove_json_text(res.choices[0].message.content)
                messages.append({"role": "assistant", "content": str(chain_3)})
                
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
                atomic_formula_premis = data_chain_3['atomic_formula_premis']
                atomic_formula_kesimpulan = data_chain_3['atomic_formula_kesimpulan']
                prompt['context']['input_queries']['respons_chatbot'] = response
                prompt['context']['input_queries']['premis'] = premis
                prompt['context']['input_queries']['kesimpulan'] = kesimpulan
                prompt['context']['input_queries']['term_premis'] = term_premis
                prompt['context']['input_queries']['term_kesimpulan'] = term_kesimpulan
                prompt['context']['input_queries']['atomic_formula_premis'] = atomic_formula_premis
                prompt['context']['input_queries']['atomic_formula_kesimpulan'] = atomic_formula_kesimpulan
                prompt = json.dumps(prompt, indent=4)
                messages.append({"role": "user", "content": prompt})
                res = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages
                )
                
                chain_4 = remove_json_text(res.choices[0].message.content)
                messages.append({"role": "assistant", "content": str(chain_4)})
                
                match = re.search(r'"fol"\s*:\s*"([^"]+)"', chain_4)

                if match:
                    fol = match.group(1)  # Ambil isi dalam tanda kutip
                else:
                    fol = "FOL Tidak ada!"
                    print("Kunci 'fol' tidak ditemukan.")
                print(f"\n\nIni FOL: \n{fol}\n\n")
                print(f"❇️ Hasil Chain 4: {chain_4}")
                print()

        fol_transformation_response = {
            "premis": premis,
            "conclusion": kesimpulan,
            "terms_premis": term_premis,
            "terms_kesimpulan": term_kesimpulan,
            "atomic_formula_premis": atomic_formula_premis,
            "atomic_formula_kesimpulan": atomic_formula_kesimpulan,
            "fol": fol,
            "messages": messages,
            "references": references
        }
        return fol_transformation_response

    def thematic_progression(self,respons_chatbot, messages):
        prompt = load_prompt_template("problems_thematic_progression.json")
        kalimat = respons_chatbot
        prompt['context']['input_queries']['respons_chatbot'] = respons_chatbot 
        prompt = json.dumps(prompt, indent=4)
        messages.append({"role": "user", "content": prompt})
        res = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages
        )
        print()
        problem_tp = remove_json_text(res.choices[0].message.content)
        problem_tp = fix_json_if_incomplete(problem_tp)
        messages.append({"role":"assistant","content":str(problem_tp)})
        return {
            "klausa":problem_tp['klausa'],"pola_tp":problem_tp['pola_tp'],"problems":problem_tp['problems'],"messages":messages}
    
    def modify_response(self,respons_chatbot, counter_example, logical_fallacy, thematic_progression_problems, messages):
        prompt = load_prompt_template("modifikasi.json")
        prompt['context']['relevant_information']['logical_fallacy'] = str(logical_fallacy)  
        prompt['context']['relevant_information']['counterexample'] = str(counter_example)
        prompt['context']['relevant_information']['thematic_progression_problems'] = thematic_progression_problems
        prompt['context']['input_queries']['kalimat'] = respons_chatbot
        prompt = json.dumps(prompt, indent=4)
        messages.append({"role":"user","content":prompt})

        modifikasi_respons = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages
        )
        modifikasi_respons = remove_json_text(modifikasi_respons.choices[0].message.content.strip())
        messages.append({"role":"assistant","content":str(modifikasi_respons)})
        print(f"❇️ Hasil Modifikasi: {modifikasi_respons}")
        modifikasi_respons = {
            "kalimat_asli": fix_json_if_incomplete(modifikasi_respons)['kalimat_asli'],
            "kalimat_modifikasi": fix_json_if_incomplete(modifikasi_respons)['kalimat_modifikasi'],
            "kalimat_keseluruhan": fix_json_if_incomplete(modifikasi_respons)['kalimat_keseluruhan'],
            "messages":messages
        }
        return modifikasi_respons
    def logical_fallacy_response_modification(self,message):
        log("LogicalFallacyResponseWorker/logical_fallacy_response_modification, 📝 Memulai modifikasi prompt logical fallacy.", "info")
        print(json.dumps(message, indent=4))
        if message['data']['fallacy_type'] == "None" or message['data']['fallacy_type'] == None:
            self.sendToOtherWorker(
                        destination=[f"DatabaseInteractionWorker/updateOutputProcess/{message['data']['chat_id']}"],
                        data={
                            "process_name": message["data"]["process_name"],
                            "output": message['data']['prompt']+"\n"+message['data']['references'],
                        },
                        messageId= str(uuid.uuid4())
                    )       
            self.sendToOtherWorker(
                destination=[f"DatabaseInteractionWorker/updateFinalAnswer/{message['data']['chat_id']}"],
                data={
                    "process_name": self.process_name,
                    "output": message['data']['prompt']+"\n"+message['data']['references'],
                },
                messageId= str(uuid.uuid4())
            )  
            log("Loigcal Fallacy Tidak Ditemukan", "warn")
            return 
        progression = self.thematic_progression(respons_chatbot = message['data']['prompt'], messages=message['data']['messages'])
        messages = progression['messages']
        progression = {
            "klausa":progression['klausa'],
            "pola_tp":progression['pola_tp'],
            "problems":progression['problems']
        }
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{message['data']['chat_id']}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Thematic Progression",
                "input": {
                    "conclusion": message['data']['kesimpulan'],
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
            thematic_progression_problems=str(progression),
            messages=messages
        )
        messages = modified_response['messages']
        modified_response = {
            "kalimat_asli": modified_response['kalimat_asli'],
            "kalimat_modifikasi": modified_response['kalimat_modifikasi'],
            "kalimat_keseluruhan": str(modified_response['kalimat_keseluruhan']+"\n"+message['data']['references'])
        }
        
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{message['data']['chat_id']}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Modify Response",
                "input": {
                    "respons_chatbot": message['data']['prompt'],
                    "counter_example": message['data']['interpretasi'],
                    "logical_fallacy": message['data']['fallacy_type'],
                    "thematic_progression_problems": str(progression),
                    },
                "output": modified_response,
            },
            messageId=(str(uuid.uuid4()))
        )
        
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateOutputProcess/{message['data']['chat_id']}"],
            data={
                "process_name": message["data"]["process_name"],
                "output": str(modified_response['kalimat_keseluruhan']),
            },
            messageId= str(uuid.uuid4())
        )       
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateFinalAnswer/{message['data']['chat_id']}"],
            data={
                "process_name": message["data"]["process_name"],
                "output": str(modified_response['kalimat_keseluruhan']) if str(modified_response['kalimat_keseluruhan']) != "" else message['data']['prompt']+"\n"+message['data']['references'],
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
        messages = []
        try:
            # Pola regex: mencari header referensi yang fleksibel
            pattern = r'(.+?)\s*' \
                    r'(?:Daftar\s+Referensi|Referensi)' \
                    r'\s*:?\s*' \
                    r'((?:\[\d+\][^\n]*\n?)+)' \
                    r'(\s*.*$)'

            # Flag re.IGNORECASE untuk tidak sensitif terhadap huruf besar/kecil
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)

            if match:
                response = match.group(1).strip()
                references_list = match.group(2).strip()
                closing = match.group(3).strip()
                
                # Rekonstruksi references dengan penutup
                references = "Referensi:\n" + references_list
                if closing:
                    references += "\n\n" + closing
            else:
                # Fallback: jika tidak menemukan header, coba deteksi dari pola [1] URL
                fallback_pattern = r'(.+?)\s*(\n\[\d+\][^\n]*)+(\s*.*)'
                fallback_match = re.search(fallback_pattern, response, re.DOTALL)
                if fallback_match:
                    response = fallback_match.group(1).strip()
                    references_part = ''.join(re.findall(r'\n\[\d+\][^\n]*', response)).strip()
                    closing = fallback_match.group(3).strip()
                    references = "Referensi:\n" + references_part
                    if closing:
                        references += "\n\n" + closing
                else:
                    response = response.strip()
                    references = ""
        except Exception as e:
            response = response
            references = ""
        
        print(f"\nINI RESPONSE:\n{response}\n")
        print(f"\nINI REFERENCE:\n{references}\n")
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/createNewProgress/{message['data']['chat_id']}"],
            data={
                "process_name": self.process_name,
                "input": response,
                "output": "",
            },
            messageId= str(uuid.uuid4())
        )
        fol_transformation = self.fol_transformation(response, references, messages)
        
       
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
        if fol_transformation['fol'] == "":
            self.sendToOtherWorker(
                destination=[f"DatabaseInteractionWorker/updateOutputProcess/{message['data']['chat_id']}"],
                data={
                    "process_name": message["data"]["process_name"],
                    "output": data['response'],
                },
                messageId= str(uuid.uuid4())
            )       
            self.sendToOtherWorker(
                destination=[f"DatabaseInteractionWorker/updateFinalAnswer/{message['data']['chat_id']}"],
                data={
                    "process_name": self.process_name,
                    "output": data['response'],
                },
                messageId= str(uuid.uuid4())
            )  
            log("Premis atau Kesimpulan tidak Ditemukan", "warn")
            return 
        self.sendToOtherWorker(
            destination=["SMTConverterWorker/smt_file_converter_from_response/"],
            messageId=message.get("messageId"),
            data={
                "fol":fol_transformation['fol'],
                'send_back_destionation': 'LogicalFallacyResponseWorker/onProcessed',
                'type': 'response',
                'prompt': response,
                'references': references,
                'premis':fol_transformation['premis'],
                'kesimpulan':fol_transformation['conclusion'],
                'term_premis':fol_transformation['terms_premis'],
                'terms_kesimpulan':fol_transformation['terms_kesimpulan'],
                'atomic_formula_premis':fol_transformation['atomic_formula_premis'],
                'atomic_formula_kesimpulan':fol_transformation['atomic_formula_kesimpulan'],
                'messages':fol_transformation['messages'],
                'process_name': self.process_name,
                'chat_id': data.get('chat_id', 'unknown_chat_id'),
                'is_eval':False
            }
        )

def main(conn: Connection, config: dict):
    worker = LogicalFallacyResponseWorker()
    worker.run(conn, config)
