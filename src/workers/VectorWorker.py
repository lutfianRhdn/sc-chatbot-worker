import asyncio
from multiprocessing.connection import Connection
import os
import threading
import uuid
import time
from  utils.log import log 
from utils.handleMessage import sendMessage, convertMessage
from langchain.schema import Document

import re
import string
from nltk.tokenize import word_tokenize
from langchain_openai import AzureOpenAIEmbeddings
import pandas as pd
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_mongodb import MongoDBAtlasVectorSearch
from uuid import uuid4
from pymongo import MongoClient

import traceback
import nltk
# check if nltk data is downloaded, if not download it
nltk.download('punkt_tab')

from .Worker import Worker

class VectorWorker(Worker):
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
        VectorWorker.conn = conn

        #### add your worker initialization code here
        
        # print(config)
        self.embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=config['azure_openai_endpoint'],
            azure_deployment=config['azure_openai_deployment_name_embedding'],
            openai_api_version=config['azure_openai_api_version'],
            azure_ad_token=config['azure_openai_key'],
        )
        client = MongoClient(config['connection_string'])
        MONGODB_COLLECTION = client[config['database']][config['mongodb_collection']]

        self.vector_mongo = MongoDBAtlasVectorSearch(
                collection=MONGODB_COLLECTION,
                embedding=self.embeddings,
                index_name=config['atlas_vector_search_index_name'],
                relevance_score_fn="cosine",
            )
        self.vector_mongo.create_vector_search_index(dimensions=3072)
        print("VectorWorker initialized with MongoDB Atlas Vector Search and Azure OpenAI embeddings.")
        
        #### until this part
        # start background threads *before* blocking server
        # threading.Thread(target=self.listen_task, daemon=True).start()

        asyncio.run(self.listen_task())
    async def listen_task(self):
        while True:
            try:
                if VectorWorker.conn.poll(1):  # Check for messages with 1 second timeout
                    message = self.conn.recv()
                    dest = [
                        d
                        for d in message["destination"]
                        if d.split("/", 1)[0] == "VectorWorker"
                    ]
                    destSplited = dest[0].split('/')
                    method = destSplited[1]
                    param= destSplited[2]
                    instance_method = getattr(self,method)
                    instance_method(data=message['data'],id=param, message=message)
                    asyncio.sleep(0.1)  # Add a small sleep to prevent busy waiting
            except EOFError:
                break
            except Exception as e:
              print(e)
              log(f"Listener error: {e}",'error' )
              break
    # def onProcessed(self, msg: dict):
    #     """
    #     Called when a worker response comes in.
    #     msg must contain 'messageId' and 'data'.
    #     """
    #     task_id = msg.get("messageId")
    #     entry = VectorWorker.requests[task_id]
    #     if not entry:
    #         return
    #     entry["response"] = msg.get("data")
    #     entry["event"].set()
    def sendToOtherWorker(self, destination, messageId: str, data: dict = None) -> None:
      sendMessage(
          conn=VectorWorker.conn,
          destination=destination,
          messageId=messageId,
          status="completed",
          reason="Message sent to other worker successfully.",
          data=data or {}
      )
    ##########################################
    # add your worker methods here
    ##########################################
   
        # return {"status": "success", "data": "This is a test response."}
    def casefoldingText(self,text):
        text = text.lower()
        return text
    def cleaningText(self,text):
        text = re.sub(r'²', '', text)  # Menghapus simbol kuadrat
        text = re.sub(r'@\S+', '', text)  # Menghapus seluruh mention
        text = re.sub(r'#\S+', '', text)  # Menghapus hashtag
        text = re.sub(r'RT[\s]', '', text) # remove RT
        text = re.sub(r"http\S+", '', text) # remove link
        # text = re.sub(r'[0-9]+', '', text) # remove numbers
        text = re.sub(r'[^\w\s]', '', text) # Menghapus karakter non-alfanumerik kecuali spasi
        text = re.sub('\s+',' ',text) # remove multiple whitespace
        text = re.sub(r"\b[a-zA-Z]\b", "", text) #remove single char
        text = text.replace('\\t'," ").replace('\\n'," ").replace('\\u'," ").replace('\\',"") # remove tab, new line, ans back slice
        text = text.encode('ascii', 'replace').decode('ascii') # remove non ASCII (emoticon, chinese word, .etc)
        text = text.replace('\n', ' ') # replace new line into space
        text = text.translate(str.maketrans('', '', string.punctuation)) # remove all punctuations
        text = text.strip(' ') # remove characters space from both left and right text
        return text
    def tokenizingText(self,text): 
        text = word_tokenize(text)
        return text
    def normalize_text(self,text, slang_dict):
        # Tokenize the text
        tokens = word_tokenize(text)
        
        # Normalize each token using the slang dictionary
        normalized_tokens = [slang_dict.get(token, token) for token in tokens]
        
        # Join the normalized tokens back into a string
        normalized_text = ' '.join(normalized_tokens)
        
        return normalized_text
    def runCreating(self,id,data,message)->None:
        """
        Example method to test the worker functionality.
        Replace this with your actual worker methods.
        """
        projectId = data.get("projectId", "")
        keyword = data.get("keyword", "")
        start_date = data.get("start_date", "")
        end_date = data.get("end_date", "")


        #send back to RestAPI
        self.sendToOtherWorker(
          messageId=message.get("messageId"),
          destination=[f"DatabaseInteractionWorker/getTweets/{projectId}"],
          data={
                "keyword": keyword,
                "start_date": start_date,
                "end_date": end_date
          }
          )
        log("Test method called", "info")
    def createVector(self,data,id,message):
        try:
            # print(message)
            projectId = id
            documents = data # {}
            print("Creating vector for project:", projectId, "with size:", len(documents))
            documents = [
                {
                    "full_text": doc.get("full_text", ""),
                    "tweet_url": doc.get("tweet_url", "")
                } for doc in documents if isinstance(doc, dict)
            ]
            
            print("Number of documents to process:", len(documents))
            # df['casefolded_text'] = df['full_text'].apply(casefoldingText)
            
            documents = [
                {
                    "full_text": self.casefoldingText(doc.get("full_text", "")),
                    "tweet_url": doc.get("tweet_url", "")
                } for doc in documents
            ]
            print("Casefolding completed. Number of documents:", len(documents))
            # df['cleaned_text'] = df['casefolded_text'].apply(cleaningText)
            documents = [
                {
                    "full_text": self.cleaningText(doc.get("full_text", "")),
                    "tweet_url": doc.get("tweet_url", "")
                } for doc in documents
            ]
            print("Cleaning completed. Number of documents:", len(documents))
            base_dir = os.path.dirname(os.path.abspath(__file__))  # path ke file ini
            path_slang = os.path.join(base_dir, "../../kamus/slang.xlsx")
            if not os.path.exists(path_slang):
                print("slang not found, using default path")
            print("Loading slang dictionary from:", path_slang)
            df_slang = pd.read_excel(path_slang)
            print("Slang dictionary loaded with", len(df_slang), "entries.")
            slang_dict = dict(zip(df_slang['slang'], df_slang['formal']))
            print("Slang dictionary created with", len(slang_dict), "entries.")
            
            # Apply normalization (this should happen before tokenization)
            documents = [
                {
                    "full_text": self.normalize_text(doc.get("full_text", ""), slang_dict),
                    "tweet_url": doc.get("tweet_url", "")
                } for doc in documents
            ]
            print("Normalization completed. Number of documents:", len(documents))
            
            # Apply final casefolding
            documents = [
                {
                    "full_text": self.casefoldingText(doc.get("full_text", "")),
                    "tweet_url": doc.get("tweet_url", "")
                } for doc in documents
            ]
            print("Final casefolding completed. Number of documents:", len(documents))
            # Create documents for vector store (keep as strings, don't tokenize yet)
            docs_list = [
                Document(
                    page_content=doc.get("full_text", ""),
                    metadata={
                        "source": doc.get("tweet_url", ""),
                    }
                ) for doc in documents if isinstance(doc, dict)
            ]
            print("Documents created for vector store. Number of documents:", len(docs_list))
            
            # text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                # chunk_size=256, chunk_overlap=0
            # )
            # doc_splits = text_splitter.split_documents(docs_list)

            self.insertVector(docs_list)
        except Exception as  e :
            traceback.print_exc()
            log(f"Error in createVector: {e}", "error")
            # self.sendToOtherWorker(
            #     messageId=message.get("messageId"),``
            #     destination=[f"DatabaseInteractionWorker/insertVectorError/{projectId}"],
            #     data={"error": str(e)}
            # )
            return
    def insertVector(self,doc):
        print("Inserting vectors into MongoDB Atlas Vector Search...")
        uuids = [str(uuid4()) for _ in range(len(doc))]
        self.vector_mongo.add_documents(documents=doc, ids=uuids)
        print("Vectors inserted successfully.")
def main(conn: Connection, config: dict):
    worker = VectorWorker()
    worker.run(conn, config)
