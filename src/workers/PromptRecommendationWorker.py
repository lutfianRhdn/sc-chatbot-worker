import asyncio
from multiprocessing.connection import Connection
import os
import re
import threading
import uuid
import time

from langchain_openai import AzureOpenAI,AzureChatOpenAI
import traceback
import pandas as pd
from  utils.log import log 
from utils.handleMessage import sendMessage, convertMessage
from langchain.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser



from .Worker import Worker

class PromptRecommendationWorker(Worker):
    ###############
    # dont edit this part
    ###############
    route_base = "/"
    conn:Connection
    requests: dict = {}
    def __init__(self):
        # we'll assign these in run()
        self._port: int = None
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.requests: dict = {}
        
    def run(self, conn: Connection, config:dict):
        # assign here
        PromptRecommendationWorker.conn = conn

        #### add your worker initialization code here
        
        # AZURE_OPENAI_MODEL_CHAT
        self.llm = AzureOpenAI(
            azure_endpoint=config['azure_openai_endpoint'],
            deployment_name=config['azure_openai_model'], 
            temperature=0,
            api_key=config['azure_openai_api_key'],
            openai_api_version=config['azure_openai_api_version']
            )
        self.llmChat = AzureChatOpenAI(
            azure_endpoint=config['azure_openai_chat_endpoint'],
            deployment_name=config['azure_openai_model_chat'],
            openai_api_version=config['azure_openai_chat_api_version'],
            temperature=0,
            api_key=config['azure_openai_chat_api_key']
            )
        
        with open(os.path.join(os.path.dirname(__file__), '../prompt', 'format_context_prompt.txt'), 'r') as file:
            self.format_context_prompt = file.read()
        with open(os.path.join(self.base_dir, '..', 'prompt', 'get_category_prompt.txt'), 'r') as file:
            self.get_category_prompt = file.read()
        with open(os.path.join(self.base_dir, '..', 'prompt', 'optimal_prompt.txt'), 'r') as file:
            self.optimal_prompt = file.read()
            
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        #### until this part
        # start background threads *before* blocking server
        print("PromptRecommendationWorker started successfully.")
        asyncio.run(self.listen_task())
    async def listen_task(self):
        while True:
            try:
                if PromptRecommendationWorker.conn.poll(1):  # Check for messages with 1 second timeout
                    message = self.conn.recv()
                    dest = [
                        d
                        for d in message["destination"]
                        if d.split("/", 1)[0] == "PromptRecommendationWorker"
                    ]
                    # print(f"[*] Received message: {message}")
                    destSplited = dest[0].split('/')
                    method = destSplited[1]
                    param= destSplited[2]
                    instance_method = getattr(self,method)
                    instance_method(id=param,data = message['data'],message=message)
                    asyncio.sleep(0.1)  # Sleep to prevent busy waiting
            except EOFError:
                break
            except Exception as e:
              print(e)
              log(f"Listener error: {e}",'error' )
              break

    def sendToOtherWorker(self, destination, messageId: str, data: dict = None) -> None:
      sendMessage(
          conn=PromptRecommendationWorker.conn,
          destination=destination,
          messageId=messageId,
          status="completed",
          reason="Message sent to other worker successfully.",
          data=data or {}
      )
    ##########################################
    # add your worker methods here
    ##########################################
    
    
    
    ###########################################
    # prepos
    ##########################################
    
    
    
    
    def format_context(self,topics):
        context = [f"{i}. {topic}" for i, topic in enumerate(topics, 1)]
       
        prompt_template = PromptTemplate.from_template(self.format_context_prompt)

        chain = prompt_template | self.llm | StrOutputParser() 
        formatted_context = chain.invoke({"input": context})
        return formatted_context
    
    def preprocess_documents(self,tweets):
        documents = pd.DataFrame(tweets)
        documents = documents[['full_text', 'tweet_url']]
        documents = documents.drop_duplicates(subset=['full_text'])
        documents['full_text'] = documents['full_text'].apply(self.normalize_text)
        return documents
    
    def normalize_text(self,text):
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r"\.\s*,", "", text)
        text = text.replace("..", ".")
        text = text.replace(". .", ".")
        text = text.replace("\n", "")
        return text.strip()
    def save_to_csv(self,data, filename):
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
    
    # def get_context(self):
    #     return self.format_context()

    def get_csv_path(self,keyword):
        return os.path.join(os.path.dirname(__file__), '..', 'data', f'{keyword}.csv')

    
    #########################
    # main function
    ########################
    def get_category(self, context):
        system = "You are an AI assistant that helps determine what category a topic falls into"

        
        template = ChatPromptTemplate.from_messages([
            ("system", system),
            ("human", self.get_category_prompt)
        ])
        
        runnable = template | self.llm | StrOutputParser()
        
        category = runnable.invoke({
            "list_topics": context
        })
        
        return category

    def get_optimal_prompt(self, category, context):
     

        # llm = AzureChatOpenAI(deployment_name='classroom-4o',openai_api_version='2024-12-01-preview', temperature=0)

        template_3 = ChatPromptTemplate.from_template(self.optimal_prompt)

        runnable_3 = template_3 | self.llmChat | JsonOutputParser()

        optimal_prompt = runnable_3.invoke({
            "category": category,
            "list_topics": context
        })

        return optimal_prompt
    
    def run_preprocessing(self,keyword,topics,tweets):
        print(f"[*] Running preprocessing for keyword: {keyword} and topics: {topics}")
        preprocessed_documents = self.preprocess_documents(tweets)
        print(f"[*] Preprocessed documents: {preprocessed_documents.shape[0]} rows")
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', f'{keyword}.csv')
        print(f"[*] Saving preprocessed documents to: {csv_path}")
        self.save_to_csv(preprocessed_documents, csv_path)
        print(f"[*] Preprocessed documents saved successfully.")
        formatted_context = self.format_context(topics)
        return formatted_context
        
        
    
    def generatePrompt(self,id,message,data):
        m_id= message['messageId']
        project_id = data['projectId']
        keyword = data['keyword']
        topics= data['topics']
        start_date = data['start_date']
        end_date = data['end_date']
        
        self.sendToOtherWorker(
          messageId=m_id,
          destination=[f"DatabaseInteractionWorker/getTweets/{project_id}"],
          data={
                "keyword": keyword,
                "start_date": start_date,
                "end_date": end_date
          }
          )
        self.topics = topics
        self.keyword = keyword
        self.project_id = project_id



    def onTweetComing(self,id,message,data):
        try:
            print(f"[*] Received tweets for id: {id}")
            
            preprocessed_data = self.run_preprocessing(self.keyword,self.topics,tweets=data)
            print(f"[*] Preprocessed data for keyword: {self.keyword} and topics: {self.topics}")
            category = self.get_category(preprocessed_data)
            print(f"[*] Category determined: {category}")
            prompts = self.get_optimal_prompt(category=category,context=preprocessed_data)
            print(f"[*] Optimal prompt generated: {prompts}")
            print(f"[*] Sending prompts to DatabaseInteractionWorker/createNewPrompt")
            self.sendToOtherWorker(
                messageId=message['messageId'],
                destination=['DatabaseInteractionWorker/createNewPrompt/'],
                data={
                    "prompts":prompts,
                    "project_id":id   
                }
            )
            print(f"[*] Prompts sent successfully for id: {id}")
        except Exception as e:
            traceback.print_exc()
            log(f"Error in onTweetComing: {e}", "error")
        # self.tweets={
        #     "messageId":id,
        #     "data":data
        #     }
        # self.evt.set()
    
    # def test(self,message)->None:
    #     """
    #     Example method to test the worker functionality.
    #     Replace this with your actual worker methods.
    #     """
    #     data = message.get("data", {})


    #     # process


    #     #send back to RestAPI
    #     self.sendToOtherWorker(
    #       messageId=message.get("messageId"),
    #       destination=["RestApiWorker/onProcessed"],
    #       data=data
    #       )
    #   #   sendMessage(
    #   #     status="completed",
    #   #     reason="Test method executed successfully.",
    #   #     destination=["supervisor"],
    #   #     data={"message": "This is a test response."}
    #   # )
    #     log("Test method called", "info")
        # return {"status": "success", "data": "This is a test response."}

def main(conn: Connection, config: dict):
    worker = PromptRecommendationWorker()
    worker.run(conn, config)
