import ast
import asyncio
import json
from multiprocessing.connection import Connection
import os
import threading
import traceback
import uuid
import time

import pandas as pd
from  utils.log import log 
from utils.handleMessage import sendMessage, convertMessage
from prompt.prompt_fol_extraction import prompt_fol_template
from prompt.semantic_intent import prompt_intent_template
from prompt.thematic_progression import prompt_progression_template
from prompt.prompt_modification import prompt_modification_template
from openai import AzureOpenAI
from .Worker import Worker
from prompt.semantic_intent_relation import prompt_intent_relationship_template

class LogicalFallacyPromptWorker(Worker):
    ###############
    # dont edit this part
    ###############
    route_base = "/"
    conn:Connection
    process_name: str = "Handling Logical Fallacy on User Prompt"
    requests: dict = {}
    def __init__(self):
        # we'll assign these in run()
        self._port: int = None

        self.requests: dict = {}
        
    def run(self, conn: Connection, config: dict):
        # assign here
        LogicalFallacyPromptWorker.conn = conn

        #### add your worker initialization code here
        self.client = AzureOpenAI(
            api_key= config["azure_openai_api_key"],
            api_version= config["azure_openai_api_version"],
            azure_endpoint= config["azure_openai_endpoint"]
        )
        self.model_name = config["azure_openai_deployment_name"]
        
        
        log("Logical Fallacy Prompt Worker initialized with model: " + self.model_name, 'info')
        
        
        #### until this part
        # start background threads *before* blocking server

        asyncio.run(self.listen_task())

    async def listen_task(self):
        while True:
            try:
                if LogicalFallacyPromptWorker.conn.poll(1):  # Check for messages with 1 second timeout
                    message = self.conn.recv()
                    dest = [
                        d
                        for d in message["destination"]
                        if d.split("/", 1)[0] == "LogicalFallacyPromptWorker"
                    ]
                    destSplited = dest[0].split('/')
                    method = destSplited[1]
                    param= destSplited[2]
                    instance_method = getattr(self,method)
                    instance_method(message)
                    await asyncio.sleep(0.1)  # Allow other tasks to run
            except EOFError:
                break
            except Exception as e:
              print(e)
              log(f"Listener error: {e}",'error' )
              break

    def sendToOtherWorker(self, destination, messageId: str, data: dict = None) -> None:
      sendMessage(
          conn=LogicalFallacyPromptWorker.conn,
          destination=destination,
          messageId=messageId,
          status="completed",
          reason="Message sent to other worker successfully.",
          data=data or {}
      )
    ##########################################
    # add your worker methods here
    ##########################################
    def transformasi_prompt_ke_fol(self, prompt_pengguna: str):
        prompt_fol = prompt_fol_template.format(kalimat=prompt_pengguna)

        response = self.client.chat.completions.create(
            model= self.model_name,
            messages=[
                {"role": "system", "content": "Anda adalah pakar logika formal."},
                {"role": "user", "content": prompt_fol}
            ],
            temperature=0.3,
            max_tokens=1500
        )

        llm_response = response.choices[0].message.content.strip()

        # Bersihkan karakter Unicode dan escape
        def fix_unicode(text):
            if isinstance(text, str):
                try:
                    # coba deteksi jika ada karakter aneh, tapi jika tidak bisa decode, tetapkan saja
                    return text.encode('utf-8').decode('utf-8')
                except UnicodeDecodeError:
                    return text
            elif isinstance(text, list):
                return [fix_unicode(t) for t in text]
            elif isinstance(text, dict):
                return {k: fix_unicode(v) for k, v in text.items()}
            return text


        # # Coba parse JSON atau literal_eval jika perlu
        try:
            data = json.loads(llm_response)
        except json.JSONDecodeError:
            try:
                data = ast.literal_eval(llm_response)
            except Exception as e:
                print("Gagal parsing LLM response:", e)
                return {"error": str(e), "raw": llm_response}

        kalimat = fix_unicode(data.get("kalimat"))
        premis = fix_unicode((data.get("premis", "")))
        kesimpulan = fix_unicode((data.get("kesimpulan", "")))
        terms_premis = fix_unicode((data.get("terms_premis", [])))
        terms_kesimpulan = fix_unicode((data.get("terms_kesimpulan", [])))
        atomic_premis = fix_unicode((data.get("atomic_formula_premis", [])))
        atomic_kesimpulan = fix_unicode((data.get("atomic_formula_kesimpulan", [])))
        predikat = fix_unicode((data.get("predikat", [])))
        fol = fix_unicode((data.get("fol", "")))

        return {
            "kalimat": kalimat,
            "premis": premis,
            "kesimpulan": kesimpulan,
            "terms_premis": terms_premis,
            "terms_kesimpulan": terms_kesimpulan,
            "atomic_formula_premis": atomic_premis,
            "atomic_formula_kesimpulan": atomic_kesimpulan,
            "predikat": predikat,
            "fol": fol
        }

    def intent(self, prompt_pengguna):
        prompt_intent = prompt_intent_template.format(
            kalimat=prompt_pengguna
        )
        response = self.client.chat.completions.create(
            model= self.model_name,
            messages=[{
                "role": "user",
                "content": prompt_intent
            }]
        )

        # Ambil hasil teks dari response
        semantic_intent = response.choices[0].message.content.strip()
        return semantic_intent

    def progression(self, prompt_pengguna):
        prompt_progression = prompt_progression_template.format(
            kalimat=prompt_pengguna
        )
        response = self.client.chat.completions.create(
            model= self.model_name,
            messages=[{
                "role": "user",
                "content": prompt_progression
            }]
        )

        # Ambil hasil teks dari response
        prompt_progression = response.choices[0].message.content.strip()
        return prompt_progression

    def modification(self, prompt_pengguna, premis, kesimpulan, intent, fallacy_type_data, fallacy_location, feedback, masalah_thematic_progression):
        try:
            # print(prompt_pengguna)
            # print("========================")
            # print(premis)
            # print("========================")
            # print(kesimpulan)
            # print("========================")
            # print(intent)
            # print("========================")
            # print(fallacy_type_data)
            # print("========================")
            # print(fallacy_location)
            # print("========================")
            # print(feedback)
            # print("========================")
            # print(masalah_thematic_progression)
            # print("========================")
            prompt_modification = prompt_modification_template.format(
                kalimat=prompt_pengguna,
                premis = premis,
                kesimpulan = kesimpulan,
                intent = intent,
                fallacy_type_data = fallacy_type_data,
                fallacy_location = fallacy_location,
                feedback = feedback,
                masalah_thematic_progression = masalah_thematic_progression
            )        

            response = self.client.chat.completions.create(
                model= self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt_modification
                    }
                ]
            )

            hasil_modifikasi = response.choices[0].message.content
            return hasil_modifikasi
        except Exception as e:
            traceback.print_exc()
            print(e)        

    def logical_fallacy_prompt_modification(self, message):
        try:
            prompt_pengguna = message["data"]["prompt"]
            premis = message["data"]["premis"]    
            kesimpulan = message["data"]["kesimpulan"]    
            fallacy_type = message["data"]["fallacy_type"]    
            fallacy_location = message["data"]["fallacy_location"]    
            feedback = message["data"]["feedback"]
            
            feedback_intent = message["data"]["feedback_intent"]
            is_eval = message["data"]["is_eval"]
            user_intent = message["data"]["user_intent"]
            prompt_user = message["data"]["prompt_user"]
            latest_intent = message["data"]["latest_intent"]

            eval_iteration = message["data"]["eval_iteration"]      
            # print(eval_iteration, fallacy_type)
            # print(feedback_intent)
            
            if eval_iteration == 3 or (fallacy_type == None and feedback_intent == None):
                self.final_prompt_logical_fallacy(text=prompt_pengguna,
                                    message=message,
                                    intent_relation='entailment' if feedback_intent == None else 'no entailment',
                                    user_intent=user_intent,
                                    modified_intent=latest_intent,
                                    fallacy_type=fallacy_type)
                return
            
            intent = self.intent(prompt_pengguna)
            if message['data']['is_eval'] == False:
                self.sendToOtherWorker(
                    destination=[f"DatabaseInteractionWorker/updateProgress/{message['data']['chat_id']}"],
                    data={
                        "process_name": message["data"]["process_name"],
                        "sub_process_name": "Anlysis Semantic Intent",
                        "input": prompt_pengguna,
                        "output": intent,
                    },
                    messageId=(str(uuid.uuid4()))
                )

            progression = self.progression(prompt_pengguna)
            if message['data']['is_eval'] == False:
                self.sendToOtherWorker(
                    destination=[f"DatabaseInteractionWorker/updateProgress/{message['data']['chat_id']}"],
                    data={
                        "process_name": message["data"]["process_name"],
                        "sub_process_name": "Analysis and Identification Thematic Progression Problem",
                        "input": prompt_pengguna,
                        "output": json.loads(progression)["masalah_thematic_progression"],
                    },
                    messageId=(str(uuid.uuid4()))
                )
                        
            base_path = os.path.dirname(os.path.abspath(__file__))
            fallacy_path = os.path.join(base_path, "../fallacy/fallacy.csv")        

            df = pd.read_csv(fallacy_path, delimiter=';')

            fallacy_type_data = ""

            # Loop untuk cari fallacy yang sesuai dengan fallacy_type
            for _, row in df.iterrows():
                tipe = row['tipe']
                deskripsi = row['deskripsi']
                contoh = row['contoh']
                
                # Cek kecocokan (bisa case-insensitive)
                if tipe.strip().lower() == fallacy_type.strip().lower():
                    fallacy_type_data += f"- {tipe} adalah {deskripsi}"
            thematic_progression = json.loads(progression)["masalah_thematic_progression"]
            final_prompt = self.modification(prompt_pengguna=prompt_pengguna,
            premis = premis,
            kesimpulan=kesimpulan,
            intent=intent,
            fallacy_type_data=fallacy_type_data,
            fallacy_location=fallacy_location,
            feedback = feedback_intent if feedback_intent is not None else feedback,
            masalah_thematic_progression=thematic_progression[0] if len(thematic_progression)>0 else "")
            # print(final_prompt)
            final_prompt_parsed = json.loads(final_prompt)["modified_sentence"]

            if message['data']['is_eval'] == False:
                self.sendToOtherWorker(
                    destination=[f"DatabaseInteractionWorker/updateProgress/{message['data']['chat_id']}"],
                    data={
                        "process_name": message["data"]["process_name"],
                        "sub_process_name": "Prompt Modification",
                        "input": {
                            "prompt_pengguna" : prompt_pengguna,
                            "premis" :  premis,
                            "kesimpulan" : kesimpulan,
                            "intent" : intent,
                            "fallacy_type_data" : fallacy_type_data,
                            "fallacy_location" : fallacy_location,
                            "feedback" :  feedback,
                            "masalah_thematic_progression" : thematic_progression[0] if len(thematic_progression)>0 else ""
                        },
                        "output": final_prompt_parsed,
                    },
                    messageId=(str(uuid.uuid4()))
                )
            
            
            modified_intent = self.intent(final_prompt_parsed)
            # print(modified_intent)
            intent_relation = self.intent_relationship(prompt_pengguna = prompt_user if prompt_user is not None else prompt_pengguna,
            prompt_modifikasi=final_prompt_parsed,
            semantic_intent_prompt= intent,
            semantic_intent_modif=modified_intent)
            # print(intent_relation)
            feedback_intent = intent_relation["feedback_intent"]
            is_eval = False
            log(f"iteration: {eval_iteration},user intent:{user_intent if user_intent is not None else intent},modified_intent:{modified_intent},logical_fallacy:{fallacy_type},intent_relation{intent_relation['relationship']}")

            if intent_relation["relationship"] == "no entailment" and fallacy_type != None:
                is_eval=True
                self.prepare_fol_transformation(prompt = final_prompt_parsed,
                prompt_user =  prompt_user if prompt_user is not None else prompt_pengguna,
                feedback_intent=feedback_intent,
                is_eval=is_eval,
                user_intent=user_intent if user_intent is not None else intent,
                eval_iteration=eval_iteration+1, message = message,
                latest_intent = modified_intent
                )

                return

            self.final_prompt_logical_fallacy(text=final_prompt_parsed,
                                              message=message,
                                              intent_relation=intent_relation["relationship"],
                                              user_intent=user_intent if user_intent is not None else intent,
                                              modified_intent=modified_intent,
                                              fallacy_type=fallacy_type)
        
        except Exception as e:
            traceback.print_exc()
            print(e)

    def intent_relationship(self, prompt_pengguna, prompt_modifikasi, semantic_intent_prompt, semantic_intent_modif):
        prompt_intent_relationship = prompt_intent_relationship_template.format(
            prompt_pengguna=prompt_pengguna,
            prompt_modifikasi=prompt_modifikasi,
            semantic_intent_prompt=semantic_intent_prompt,
            semantic_intent_modif=semantic_intent_modif
        )

        response = self.client.chat.completions.create(
            model= self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": prompt_intent_relationship
                }
            ],
            max_tokens=500
        )

        # Ambil hasil teks dari response
        semantic_intent_relationship = response.choices[0].message.content.strip()
        
        # Optional: coba parse ke JSON
        try:
            parsed_result = json.loads(semantic_intent_relationship)
        except:
            parsed_result = {"raw_response": semantic_intent_relationship}
        
        return parsed_result
    
    def final_prompt_logical_fallacy(self, text, message, intent_relation, fallacy_type, user_intent, modified_intent):
        chat_id = message['data']['chat_id']
        log("success remove logical fallacy from prompt on chatId : "+chat_id,'success')
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{chat_id}"],
            data={
                "process_name": message["data"]["process_name"],
                "sub_process_name": "Evaluation",
                "input": {
                    "intent_relation": str(intent_relation),
                    "fallacy_type": fallacy_type or "",
                    "user_intent": str(user_intent),
                    "modified_intent": str(modified_intent),
                },
                "output": text,
            },
            messageId=(str(uuid.uuid4()))
        )
        
        log("Sukses remove logical fallacy dari prompt")
        # print(text)

        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateOutputProcess/{chat_id}"],
            data={
                "process_name": message["data"]["process_name"],
                "output": text,
            },
            messageId= str(uuid.uuid4())
        )        
        self.sendToOtherWorker(
            messageId= message['messageId'],
            destination=[f"CRAGWorker/generateAnswer/{chat_id}"],
            data={
                "projectId": "1",
                "prompt": text
            }
        )        
    def prepare_fol_transformation(self,
        prompt,
        message,
        feedback_intent=None,
        is_eval = False,
        user_intent = None,
        eval_iteration = 0,
        prompt_user = None,
        chat_id = None,
        process_name = "",
        latest_intent = None):

        # print(prompt)
        transformasi_fol = self.transformasi_prompt_ke_fol(prompt)
        
        fol = transformasi_fol.get("fol", "FOL tidak ditemukan")
        premis = transformasi_fol.get("premis", "Premis tidak ditemukan")
        kesimpulan = transformasi_fol.get("kesimpulan", "Kesimpulan tidak ditemukan")
        term_premis = transformasi_fol.get("term_premis", "term premis tidak ditemukan")
        terms_kesimpulan = transformasi_fol.get("terms_kesimpulan", "term kesimpulan tidak ditemukan")
        atomic_formula_premis = transformasi_fol.get("atomic_formula_premis", "atomic formula premis tidak ditemukan")
        atomic_formula_kesimpulan = transformasi_fol.get("atomic_formula_kesimpulan", "atomic formula kesimpulan tidak ditemukan")
        predikat = transformasi_fol.get("predikat", "predikat tidak ditemukan")
        # self.sendToOtherWorker(
        #     destination=[f"DatabaseInteractionWorker/updateOutputProcess/{chat_id}"],
        #     data={
        #         "process_name": process_name,
                # "output": {
                #     "fol": fol,
                #     "premis": premis,
                #     "kesimpulan": kesimpulan,
                #     "term_premis": term_premis,
                #     "term_premis": term_premis,
                #     "atomic_formula_premis": atomic_formula_premis,
                #     "atomic_formula_kesimpulan": atomic_formula_kesimpulan,
                #     "predikat": predikat,
                # },
        #     },
        #     messageId= str(uuid.uuid4())
        # )
        if is_eval == False:
            self.sendToOtherWorker(
                destination=[f"DatabaseInteractionWorker/updateProgress/{chat_id}"],
                data={
                    "process_name": process_name,
                    "sub_process_name": "FOL Extraction",
                    "input": prompt,
                    "output": {
                        "fol": fol,
                        "premis": premis,
                        "kesimpulan": kesimpulan,
                        "term_premis": term_premis,
                        "term_premis": term_premis,
                        "atomic_formula_premis": atomic_formula_premis,
                        "atomic_formula_kesimpulan": atomic_formula_kesimpulan,
                        "predikat": predikat,
                    },
                },
                messageId=(str(uuid.uuid4()))
            )
        
        # print("transformasi fol", transformasi_fol)
        # print("fol", fol)
        # print("premis", premis)
        # print("kesimpulan", kesimpulan)
        self.sendToOtherWorker(
          messageId=message.get("messageId"),
          destination=["SMTConverterWorker/fol_to_smtlib/"],
          data={
              "fol":fol,
              "premis":premis,
              "kesimpulan":kesimpulan,
              "prompt":prompt,
              "premis":premis,
              "kesimpulan":kesimpulan,
              "terms_kesimpulan":terms_kesimpulan,
              "term_premis":term_premis,
              "atomic_formula_premis":atomic_formula_premis,
              "atomic_formula_kesimpulan":atomic_formula_kesimpulan,
              "predikat":predikat,
              "feedback":feedback_intent,
              "user_intent" : user_intent,
              "is_eval" : is_eval,
              "eval_iteration" : eval_iteration,
              "prompt_user" : prompt_user,
              "chat_id" : chat_id or message['data']['chat_id'],
              "process_name" : process_name or message['data']['process_name'],
              "latest_intent":latest_intent
          }
          )


    def removeLFPrompt(self,message)->None:
        """
        Example method to test the worker functionality.
        Replace this with your actual worker methods.
        """
        data = message.get("data", {})
        prompt = data["prompt"]
        id=data["id"]

        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/createNewProgress/{id}"],
            data={
                "process_name": self.process_name,
                "input": data['prompt'],
                "output": "",
            },
            messageId= str(uuid.uuid4())
        )

        self.prepare_fol_transformation(prompt=prompt, message=message, chat_id = id, process_name = self.process_name)
    

def main(conn: Connection, config: dict):
    worker = LogicalFallacyPromptWorker()
    worker.run(conn, config)
