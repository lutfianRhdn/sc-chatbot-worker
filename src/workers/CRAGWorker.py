from langchain_groq import ChatGroq
import requests
import json
import pandas as pd
import re
import string
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import AzureOpenAIEmbeddings
from langchain_openai import AzureChatOpenAI
from langchain.docstore.document import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools.tavily_search import TavilySearchResults
from typing import List
from typing_extensions import TypedDict
from langchain.schema import Document
from langgraph.graph import END, StateGraph, START
from pprint import pprint
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient
import getpass
import os
from uuid import uuid4
from nltk.tokenize import word_tokenize

from multiprocessing.connection import Connection
import threading
import uuid
import time
from  utils.log import log 
from utils.handleMessage import sendMessage, convertMessage

from .Worker import Worker
from prompt.RetrievalEvaluator import grade_prompt, GradeDocuments
from prompt.LeaderPrompt import leader_prompt
from prompt.SkepticPrompt import skeptic_prompt
from prompt.TrustPrompt import trust_prompt
from prompt.KeywordExtractor import re_write_prompt
from prompt.PromptExtract import prompt_extrac
from prompt.GenerateAnswer import prompt
from utils.state import GraphState

class CRAGWorker(Worker):
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
        CRAGWorker.conn = conn

        #### add your worker initialization code here
        self.conn=conn
        self._db_name = config.get("database", "mydatabase") 
        self.connection_string = config.get("connection_string", "mongodb://localhost:27017/") 
        self.AZURE_OPENAI_API_KEY = config.get("AZURE_OPENAI_API_KEY")
        self.AZURE_OPENAI_ENDPOINT = config.get("AZURE_OPENAI_ENDPOINT")
        self.AZURE_OPENAI_DEPLOYMENT_NAME = config.get("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING = config.get("AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING")
        self.AZURE_OPENAI_API_VERSION = config.get("AZURE_OPENAI_API_VERSION")
        self.TAVILY_API_KEY = config.get("TAVILY_API_KEY")
        os.environ["AZURE_OPENAI_API_KEY"] = self.AZURE_OPENAI_API_KEY
        os.environ["TAVILY_API_KEY"] = self.TAVILY_API_KEY

        self.connect_retrieval()
        self.llm = AzureChatOpenAI(
            azure_endpoint= self.AZURE_OPENAI_ENDPOINT,
            azure_deployment=self.AZURE_OPENAI_DEPLOYMENT_NAME,
            openai_api_version=self.AZURE_OPENAI_API_VERSION,
            temperature=0,
        )
        self.web_search_tool = TavilySearchResults(max_results=5)
        self.rag_chain = prompt | self.llm | StrOutputParser()
        self.keyword_extractor = re_write_prompt | self.llm | StrOutputParser()
        self.leader_chain = leader_prompt | self.llm | StrOutputParser()
        self.extract_chain = prompt_extrac | self.llm | StrOutputParser()
        self.structured_llm_grader = self.llm.with_structured_output(GradeDocuments)
        self.retrieval_grader = grade_prompt | self.structured_llm_grader
        self.skeptic_chain = skeptic_prompt | self.llm | StrOutputParser()
        self.trust_chain = trust_prompt | self.llm | StrOutputParser()
        path_slang = "H:/My Drive/UNIKOM/Skripsi/Code/Socialabs/socialabs-chatbot/kamus/slang.xlsx"
        if not os.path.exists(path_slang):
            print("slang not found, using default path")
        df_slang = pd.read_excel(os.path.abspath(path_slang))
        self.slang_dict = dict(zip(df_slang['slang'], df_slang['formal']))
        workflow = StateGraph(GraphState)

        # Define the nodes
        workflow.add_node("retrieve", self.retrieve)  # retrieve
        workflow.add_node("grade_documents", self.grade_documents)  # grade documents
        workflow.add_node("generate", self.generate)  # generate
        workflow.add_node("transform_query", self.transform_query)  # transform_query
        workflow.add_node("web_search_node", self.web_search)  # web search
        workflow.add_node("knowledge_refinement", self.knowledge_refinement)  # knowledge refinement

        # Build graph
        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            self.decide_to_generate,
            {
                "transform_query": "transform_query",
                "generate": "generate",
            },
        )
        workflow.add_edge("transform_query", "web_search_node")
        workflow.add_edge("web_search_node", "knowledge_refinement")
        workflow.add_edge("knowledge_refinement", "generate")
        workflow.add_edge("generate", END)
        # Compile
        self.app = workflow.compile()
        print("Selesai")


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
                conn=CRAGWorker.conn,
                messageId="heartbeat",
                status="healthy"
            )
            time.sleep(10)
    def listen_task(self):
        while True:
            try:
                if CRAGWorker.conn.poll(1):  # Check for messages with 1 second timeout
                    message = self.conn.recv()
                    dest = [
                        d
                        for d in message["destination"]
                        if d.split("/", 1)[0] == "CRAGWorker"
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
          conn=CRAGWorker.conn,
          destination=destination,
          messageId=messageId,
          status="completed",
          reason="Message sent to other worker successfully.",
          data=data or {}
      )
    ##########################################
    # add your worker methods here
    ##########################################
    # PREPROCESSING
    def casefoldingText(self, text):
        text = text.lower()
        return text

    def cleaningText(self, text):
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

    def tokenizingText(self, text): 
        text = word_tokenize(text)
        return text 
    
    def normalize_text(self, text, slang_dict):
        # Tokenize the text
        # print(text)
        # print(slang_dict)
        tokens = word_tokenize(text)
        
        # Normalize each token using the slang dictionary
        normalized_tokens = [slang_dict.get(token, token) for token in tokens]
        
        # Join the normalized tokens back into a string
        normalized_text = ' '.join(normalized_tokens)
        
        return normalized_text

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)


    def connect_retrieval(self):   
      os.environ["AZURE_OPENAI_API_KEY"] = self.AZURE_OPENAI_API_KEY
      embeddings = AzureOpenAIEmbeddings(
      azure_endpoint=self.AZURE_OPENAI_ENDPOINT,
      azure_deployment=self.AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING,
      openai_api_version=self.AZURE_OPENAI_API_VERSION,
      )
      # initialize MongoDB python client
      client = MongoClient(self.connection_string)

    #   DB_NAME = self._db_name
      DB_NAME = "CRAG"
      COLLECTION_NAME = "CRAG_vectorstores"
      ATLAS_VECTOR_SEARCH_INDEX_NAME = "crag-index-vectorstores"

      MONGODB_COLLECTION = client[DB_NAME][COLLECTION_NAME]

      vector_mongo = MongoDBAtlasVectorSearch(
          collection=MONGODB_COLLECTION,
          embedding=embeddings,
          index_name=ATLAS_VECTOR_SEARCH_INDEX_NAME,
          relevance_score_fn="cosine",
      )

      print(f"Connected to MongoDB Atlas Vector Search at {self.connection_string}")
      # Create vector search index on the collection
      self.vector_mongo = vector_mongo.create_vector_search_index(dimensions=3072)
      self.retriever = vector_mongo.as_retriever()

    def retrieve(self, state):
      """
      Retrieve documents

      Args:
          state (dict): The current graph state

      Returns:
          state (dict): New key added to state, documents, that contains retrieved documents
      """
    #   print("---RETRIEVE---")
      question = state["question"]

      # Retrieval
    #   print(self.retriever)
      documents = self.retriever.get_relevant_documents(question, k=10)
    #   print("===RETRIEVED DOCUMENTS===")
    #   print(documents)
      # print(question)
      return {"documents": documents, "question": question}

    def grade_documents(self, state):
        """
        Determines whether the retrieved documents are relevant to the question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates documents key with only filtered relevant documents
        """

        # print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
        question = state["question"]
        documents = state["documents"]

        # Score each doc
        filtered_docs = []
        web_search = "No"


        # print("===DOCUMENTS TO BE GRADED===")
        # print(documents)
        for d in documents:
            score = self.retrieval_grader.invoke(
                {"question": question, "document": d.page_content}
            )
            grade = score.final_classification
            if grade == "Benar":
                # print("---GRADE: DOCUMENT BENAR---")
                # print(d.page_content)
                filtered_docs.append(d)
            elif grade == "Salah":
                # print("---GRADE: DOCUMENT SALAH---")
                # print(d.page_content)
                web_search = "Yes"
            else:
                # print("---GRADE: DOCUMENT AMBIGU---")
                # print(d.page_content)
                web_search = "Yes"
                filtered_docs.append(d)
                continue
        # print("===FILTERED DOCUMENTS===")
        # print(filtered_docs)
        # print(question)
        # print(web_search)
        # print(grade)
        return {"documents": filtered_docs, "question": question, "web_search": web_search,"grade": grade}

    def transform_query(self, state):
        """
        Transform the query to produce a better question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates question key with a re-phrased question
        """

        # print("---TRANSFORM QUERY---")
        question = state["question"]
        documents = state["documents"]

        # Re-write question
        key_word_result = self.keyword_extractor.invoke({"question": question})
        # print("===KEY WORD RESULT===")
        # print(key_word_result)
        # print(documents)
        # print(question)
        return {"documents": documents, "question": question, "key_word":key_word_result}
    
    def preprocess_text(self, text, slang_dict):
        text = self.casefoldingText(text)
        text = self.cleaningText(text)
        text = self.normalize_text(text, slang_dict)
        tokens = self.tokenizingText(text)
        text = ' '.join(tokens)  # Convert list of tokens back to string
        return text

    def web_search(self, state):
        """
        Web search based on the re-phrased question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates documents key with appended web results
        """

        # print("---WEB SEARCH---")
        question = state["question"]
        documents = state["documents"]
        key_word = state["key_word"]
        # Web search
        docs = self.web_search_tool.invoke({"query": key_word})
        for d in docs:
            # Preprocess text
            d["content"] = self.preprocess_text(d["content"], self.slang_dict)
            # print(d["content"])
            web_result_doc = Document(page_content=d["content"], metadata={"source": d["url"]})
            documents.append(web_result_doc)
        # print("===WEB SEARCH RESULTS===")
        # print(docs)
        # print(web_results)
        # print(documents)
        # print(question)
        # print(key_word)
        return {"documents": documents, "question": question, "key_word": key_word}

    def knowledge_refinement(self, state):
        """
        Knowledge refinement = decompose documents into strip -> filter -> recompose
        Args:
            state (dict): The current graph state
        Returns:
            state (dict): Updates documents key with appended web results
        """
        # print("---KNOWLEDGE REFINEMENT---")
        question = state["question"]
        documents = state["documents"]
        key_word = state["key_word"]


        # decompose
        decomposed_docs = []
        for d in documents:
            # Split dokumen menjadi potongan-potongan kecil 
            text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                chunk_size=256, chunk_overlap=0
            )
            doc_splits = text_splitter.split_documents([d])
            decomposed_docs.extend(doc_splits)
        # print("===DECOMPOSED DOCUMENTS===")
        # print(decomposed_docs)
        # filter
        filtered_docs = []
        for d in decomposed_docs:
            score = self.retrieval_grader.invoke(
                {"question": question, "document": d.page_content}
            )
            grade = score.final_classification
            if grade == "Benar":
                # print("---GRADE: DOCUMENT BENAR---")
                # print(d.page_content)
                filtered_docs.append(d)
            elif grade == "Salah":
                # print("---GRADE: DOCUMENT SALAH---")
                # print(d.page_content)
                continue
            else:
                # print("---GRADE: DOCUMENT AMBIGU---")
                # print(d.page_content)
                filtered_docs.append(d)
                continue
        # print("===FILTERED DOCUMENTS===")
        # print(filtered_docs)
        # recombine
        # Gabungkan isi filtered_docs menjadi satu Document baru
        recombined_content = "\n".join([d.page_content for d in filtered_docs])
        documents = [Document(page_content=recombined_content)]
        # print("===RECOMBINED DOCUMENTS===")
        # print(documents)
        # print(question)
        # print(key_word)
        return {"documents": filtered_docs, "question": question, "key_word": key_word}

    def generate(self, state):
        """
        Generate answer

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
        """
        # print("---GENERATE---")
        question = state["question"]
        documents = state["documents"]

        # gunakan hanya source dan page_content dari dokumen
        documents = [
            Document(
                page_content=doc.page_content,
                metadata={"source": doc.metadata.get("source", "unknown")}
            )
            for doc in documents
        ]

        # Cetak prompt akhir sebelum dikirim ke LLM
        final_prompt = prompt.format(question=question, context=documents)
        # print("==== PROMPT FINAL YANG DIKIRIM ====")
        # # print(final_prompt)
        # print("===================================")

        # RAG generation
        generation = self.rag_chain.invoke({"context": documents, "question": question})
        # print(documents)
        # print(question)
        # print(generation)
        return {"documents": documents, "question": question, "generation": generation}
    
    def decide_to_generate(self, state):
        """
        Determines whether to generate an answer, or re-generate a question.

        Args:
            state (dict): The current graph state

        Returns:
            str: Binary decision for next node to call
        """

        # print("---ASSESS GRADED DOCUMENTS---")
        state["question"]
        web_search = state["web_search"]
        state["documents"]
        grade = state["grade"]


        if web_search == "Yes" and grade == "Salah" :
            # All documents have been filtered check_relevance
            # We will re-generate a new query
            # print(
                # "---DECISION: DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY---"
            # )
            return "transform_query"
        elif web_search == "Yes" and grade == "Ambigu" :
            # All documents have been filtered check_relevance
            # We will re-generate a new query
            # print(
            #     "---DECISION: DOCUMENTS ARE AMBIGUOUS, TRANSFORM QUERY---"
            # )
            return "transform_query"
        else:
            # We have relevant documents, so generate answer
            # print("---DECISION: GENERATE---")
            return "generate"

    def test(self,message)->None:
        """
        Example method to test the worker functionality.
        Replace this with your actual worker methods.
        """
        data = message.get("data", {})
        print(data['prompt'])


        # Run
        inputs = {"question": data['prompt']}
        for output in self.app.stream(inputs):
            for key, value in output.items():
                # Node
                pprint(f"Node '{key}':")
                # Optional: print full state at each node
                # pprint.pprint(value["keys"], indent=2, width=80, depth=None)
            # pprint("\n---\n")

        # Final generation
        print(value["generation"])
        # text = self.casefoldingText("Halo, ini adalah contoh teks untuk diolah.")
        # text = self.cleaningText(text)
        # text = self.tokenizingText(text)
        # path_slang = "H:/My Drive/UNIKOM/Skripsi/Code/Socialabs/socialabs-chatbot/kamus/slang.xlsx"
        # if not os.path.exists(path_slang):
        #     print("slang not found, using default path")

        # df_slang = pd.read_excel(os.path.abspath(path_slang))
        # slang_dict = dict(zip(df_slang['slang'], df_slang['formal']))
        # text = self.normalize_text(' '.join(text), slang_dict)
        # print(text)

        
        





        # process
        # print("Hello World from CRAGWorker!")

        #send back to RestAPI
        self.sendToOtherWorker(
          messageId=message.get("messageId"),
          destination=["RestApiWorker/onProcessed"],
          data=value["generation"]

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
    worker = CRAGWorker()
    worker.run(conn, config)
