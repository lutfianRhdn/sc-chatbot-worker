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
from typing import List, final
from typing_extensions import TypedDict
from langchain.schema import Document
from langgraph.graph import END, StateGraph, START
from pprint import pprint
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient
import os
from uuid import uuid4
from nltk.tokenize import word_tokenize
import traceback
from multiprocessing.connection import Connection
import threading
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
    process_name: str = "Reduce information hallucinations by applying CRAG."
    def __init__(self):
        # we'll assign these in run()
        self._port: int = None

        self.requests: dict = {}
        
    def run(self, conn: Connection, config: dict):
        try:
            # assign here
            CRAGWorker.conn = conn
            
# CRAGWorkerConfig={
#     "database": database.database_name,
#     "connection_string": database.connection_string,
#     "index_name": database.mongo_vector_search_index_name,
#     "collection_name": database.mongodb_collection_vector,
#     "TAVILY_API_KEY": tavily_api_key,
#     "azure_openai_api_key": azure.api_key,
#     "azure_openai_endpoint": azure.endpoint,
#     "azure_openai_deployment_name": azure.deployment_name.api,
#     "azure_openai_deployment_name_embedding": azure.deployment_name.embedding,
#     "azure_openai_api_version": azure.api_version.api,
#     "azure_openai_embedding_api_version": azure.api_version.embedding,
# }

            #### add your worker initialization code here
            self.conn=conn
            self._db_name = config.get("database", "mydatabase") 
            self.search_index_name = config.get("index_name",  "index-vectorstores")
            self.collection_name = config.get("collection_name", "vectorstores")
            
            self.connection_string = config.get("connection_string", "mongodb://localhost:27017/") 
            os.environ["AZURE_OPENAI_API_KEY"] = config['azure_openai_api_key']
            os.environ["TAVILY_API_KEY"] = config['tavily_api_key']

            self.llm = AzureChatOpenAI(
                azure_endpoint= config['azure_openai_endpoint'],
                azure_deployment=config['azure_openai_deployment_name'],
                openai_api_version=config['azure_openai_api_version'],
                temperature=0,
            )
            self.embeddings = AzureOpenAIEmbeddings(
                azure_endpoint= config['azure_openai_endpoint'],
                azure_deployment=config['azure_openai_deployment_name_embedding'],
                openai_api_version= config['azure_openai_embedding_api_version'],
            )
            self.connect_retrieval()
            
            self.web_search_tool = TavilySearchResults(max_results=5)
            self.rag_chain = prompt | self.llm | StrOutputParser()
            self.keyword_extractor = re_write_prompt | self.llm | StrOutputParser()
            self.leader_chain = leader_prompt | self.llm | StrOutputParser()
            self.extract_chain = prompt_extrac | self.llm | StrOutputParser()
            self.structured_llm_grader = self.llm.with_structured_output(GradeDocuments)
            self.retrieval_grader = grade_prompt | self.structured_llm_grader
            self.skeptic_chain = skeptic_prompt | self.llm | StrOutputParser()
            self.trust_chain = trust_prompt | self.llm | StrOutputParser()
            base_dir = os.path.dirname(os.path.abspath(__file__))  # path ke file ini
            path_slang = os.path.join(base_dir, "../../kamus/slang.xlsx")
            if not os.path.exists(path_slang):
                print("slang not found, using default path")
            df_slang = pd.read_excel(path_slang)
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


            # Define the workflow for CRAG evaluation
            workflow_evaluasi = StateGraph(GraphState)

            workflow_evaluasi.add_node("s0", self.initial_answer_node)
            workflow_evaluasi.add_node("s1", self.get_evidence_node)
            workflow_evaluasi.add_node("s2", self.skeptic_node)
            workflow_evaluasi.add_node("s3", self.trust_node)
            workflow_evaluasi.add_node("increment_round", self.increment_round_node)
            workflow_evaluasi.add_node("s4", self.leader_node)

            # Add edges
            workflow_evaluasi.add_edge(START, "s0")
            workflow_evaluasi.add_edge("s0", "s1")
            workflow_evaluasi.add_edge("s1", "s2")
            workflow_evaluasi.add_edge("s2", "s3")

            # After trust node, check if we should continue or end based on new logic
            workflow_evaluasi.add_conditional_edges(
                "s3",
                self.should_continue_debate,
                {
                    "continue_debate": "increment_round",  # Increment round and go back to skeptic
                    "end_debate": "s4"                     # Go to leader node to end
                }
            )

            # After incrementing round, go back to skeptic for next round
            workflow_evaluasi.add_edge("increment_round", "s2")
            workflow_evaluasi.add_edge("s4", END)

            self.app_evaluasi = workflow_evaluasi.compile()
            print('CRAGWorker initialized successfully.')

            #### until this part
            # start background threads *before* blocking server
            threading.Thread(target=self.listen_task, daemon=True).start()
            threading.Thread(target=self.health_check, daemon=True).start()

            # asyncio.run(self.listen_task())
            self.health_check()
        except Exception as e:
            traceback.print_exc()
            print(e)
            log(f"Failed to connect to CRAGWorker: {e}", "error")

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
                    instance_method(id = param,mId = message.get("messageId"), data = message.get("data", {}))
            except EOFError:
                break
            except Exception as e:
              print(e)
              log(f"Listener error: {e}",'error' )
              break

    def sendToOtherWorker(self, messageId,destination, data: dict = None) -> None:
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
      try:
        
        # initialize MongoDB python client
        client = MongoClient(self.connection_string)

        DB_NAME = self._db_name
        COLLECTION_NAME = self.collection_name = "vectorstores"
        ATLAS_VECTOR_SEARCH_INDEX_NAME = self.search_index_name = "vector_search_index"

        MONGODB_COLLECTION = client[DB_NAME][COLLECTION_NAME]

        vector_mongo = MongoDBAtlasVectorSearch(
            collection=MONGODB_COLLECTION,
            embedding=self.embeddings,
            index_name=ATLAS_VECTOR_SEARCH_INDEX_NAME,
            relevance_score_fn="cosine",
        )

        print(f"Connected to MongoDB Atlas Vector Search at {self.connection_string}")
        # Create vector search index on the collection
        self.vector_mongo = vector_mongo.create_vector_search_index(dimensions=3072)
        self.retriever = vector_mongo.as_retriever()
        print("MongoDB Atlas Vector Search initialized successfully.")
      except Exception as e:
        traceback.print_exc()
        print(f"Error connecting to MongoDB Atlas Vector Search: {e}")
        log(f"Error connecting to MongoDB Atlas Vector Search: {e}", "error")
        raise e

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
      page_content = [doc.page_content for doc in documents]
      result_retrieve = {"documents": page_content, "number_of_documents": len(page_content)}
      self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{self.id}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Retrieval",
                "input": question,
                "output": result_retrieve
            },
            messageId=(str(uuid4()))
      )
      # print(result_retrieve)
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
        result_grade = []
        for d in documents:
            score = self.retrieval_grader.invoke(
                {"question": question, "document": d.page_content}
            )
            grade = score.final_classification
            if grade == "Benar":
                # print("---GRADE: DOCUMENT BENAR---")
                # print(d.page_content)
                result_grade.append({"document": d.page_content, "grade": "Benar"})
                filtered_docs.append(d)
            elif grade == "Salah":
                # print("---GRADE: DOCUMENT SALAH---")
                # print(d.page_content)
                result_grade.append({"document": d.page_content, "grade": "Salah"})
                web_search = "Yes"
            else:
                # print("---GRADE: DOCUMENT AMBIGU---")
                # print(d.page_content)
                result_grade.append({"document": d.page_content, "grade": "Ambigu"})
                web_search = "Yes"
                filtered_docs.append(d)
                continue
        # print("===FILTERED DOCUMENTS===")
        # print(filtered_docs)
        # print(question)
        # print(web_search)
        # print(grade)
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{self.id}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Retrieval Evaluation",
                "input": question,
                "output": result_grade,
            },
            messageId=(str(uuid4()))
        )
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

        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{self.id}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Keyword Extraction",
                "input": question,
                "output": key_word_result,
            },
            messageId=(str(uuid4()))
        )
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
            serialized_docs = [
                {"content": doc.page_content, "source": doc.metadata['source']}
                for doc in documents
            ]
        # print("===WEB SEARCH RESULTS===")
        # print(docs)
        # print(web_results)
        # print(documents)
        # print(question)
        # print(key_word)
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{self.id}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Knowledge Searching",
                "input": key_word,
                "output": serialized_docs,
            },
            messageId=(str(uuid4()))
        )
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
        result_kl = []
        for d in decomposed_docs:
            score = self.retrieval_grader.invoke(
                {"question": question, "document": d.page_content}
            )
            grade = score.final_classification
            if grade == "Benar":
                # print("---GRADE: DOCUMENT BENAR---")
                # print(d.page_content)
                result_kl.append({"document": d.page_content, "grade": grade})
                filtered_docs.append(d)
            elif grade == "Salah":
                # print("---GRADE: DOCUMENT SALAH---")
                # print(d.page_content)
                result_kl.append({"document": d.page_content, "grade": grade})
                continue
            else:
                # print("---GRADE: DOCUMENT AMBIGU---")
                # print(d.page_content)
                result_kl.append({"document": d.page_content, "grade": grade})
                filtered_docs.append(d)
                continue
        # print("===FILTERED DOCUMENTS===")
        # print(filtered_docs)
        # recombine
        # Gabungkan isi filtered_docs menjadi satu Document baru
        # recombined_content = "\n".join([d.page_content for d in filtered_docs])
        # documents = [Document(page_content=recombined_content)]
        # print("===RECOMBINED DOCUMENTS===")
        # print(documents)
        # print(question)
        # print(key_word)
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{self.id}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Knowledge Refinement",
                "input": [doc.page_content for doc in documents],
                "output": {
                    "Decompose": [doc.page_content for doc in decomposed_docs],
                    "Filter": result_kl,
                    "Recompose": [doc.page_content for doc in filtered_docs]
                }
            },
            messageId=(str(uuid4()))
        )
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

        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{self.id}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Generation",
                "input": question,
                "output": generation,
            },
            messageId=(str(uuid4()))
        )
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
        

    def initial_answer_node(self, state):
        """
        Create the initial node of the graph.
        """
        # print("=== Initial Answer Node ===")
        claim = state["claim"]
        # Show the prompt that will be sent
        prompt_vars = {"input": claim}
        # print("=== Prompt Initial Answer Node===")
        # print(prompt_extrac.format(**prompt_vars))
        text = self.extract_chain.invoke(prompt_vars)
        # print(text)
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{self.id}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Claim Detection",
                "input": claim,
                "output": text,
            },
            messageId=(str(uuid4()))
        )
        return {"claim": text, "round_count": 1}
    
    def get_evidence_node(self, state):
        """
        Create the evidence node of the graph.
        """
        # print("=== Evidence Node ===")
        claim = state["claim"]
        question = state["question"]
        evidence = state["evidence"]

        serialized_evidence = [{"content": doc.page_content, "source": doc.metadata['source']} for doc in evidence]

        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{self.id}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Evidence Retrieval",
                "input": claim,
                "output": serialized_evidence,
            },
            messageId=(str(uuid4()))
        )
        
        return {"claim": claim, "evidence": evidence, "round_count": state.get("round_count", 1)}

    def skeptic_node(self, state):
        """
        Create the skeptic node of the graph.
        """
        round_count = state.get("round_count", 1)
        # print(f"=== Skeptic Node - Round {round_count} ===")
        evidence = state["evidence"]
        claim = state["claim"]
        previous_opinion = state.get("previous_opinion", "")

        prompt_vars = {"claim": claim, "evidence": evidence, "previous_opinion": previous_opinion}
        # print("=== Prompt Skeptic Node===")
        # print(skeptic_prompt.format(**prompt_vars))
        text = self.skeptic_chain.invoke(prompt_vars)
        # print(text)
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{self.id}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Skeptic Evaluation",
                "input": previous_opinion,
                "output": text,
            },
            messageId=(str(uuid4()))
        )
        
        if previous_opinion:
            previous_opinion = previous_opinion + "," + text
        else:
            previous_opinion = text

        
        return {"claim": claim, "evidence": evidence, "previous_opinion": previous_opinion, "round_count": round_count}
    
    def trust_node(self, state):
        """
        Create the trust node of the graph.
        """
        round_count = state.get("round_count", 1)
        # print(f"=== Trust Node - Round {round_count} ===")
        evidence = state["evidence"]
        claim = state["claim"]
        previous_opinion = state.get("previous_opinion", "")
        
        prompt_vars = {"claim": claim, "evidence": evidence, "previous_opinion": previous_opinion}
        # print("=== Prompt Trust Node===")
        # print(trust_prompt.format(**prompt_vars))
        
        text = self.trust_chain.invoke(prompt_vars)
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{self.id}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Trust Evaluation",
                "input": previous_opinion,
                "output": text,
            },
            messageId=(str(uuid4()))
        )
        if previous_opinion:
            previous_opinion = previous_opinion + "," + text
        else:
            previous_opinion = text
        # print(text)

        return {"claim": claim, "evidence": evidence, "previous_opinion": previous_opinion, "round_count": round_count}
    
    def increment_round_node(self, state):
        """
        Increment the round counter after both agents have spoken.
        """
        round_count = state.get("round_count", 1)
        new_round_count = round_count + 1
        # print(f"=== Completed Round {round_count}, Moving to Round {new_round_count} ===")
        
        return {
            "claim": state["claim"], 
            "evidence": state["evidence"], 
            "previous_opinion": state["previous_opinion"],
            "round_count": new_round_count
        }
    
    def leader_node(self, state):
        """
        Create the leader node of the graph.
        """
        # print("=== Leader Node - Final Decision ===")
        evidence = state["evidence"]
        claim = state["claim"]
        previous_opinion = state["previous_opinion"]
        
        prompt_vars = {"claim": claim, "evidence": evidence, "previous_opinion": previous_opinion}
        # print("=== Prompt Leader Node===")
        # print(leader_prompt.format(**prompt_vars))

        text = self.leader_chain.invoke(prompt_vars)
        # print(text)
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateProgress/{self.id}"],
            data={
                "process_name": self.process_name,
                "sub_process_name": "Leader Evaluation",
                "input": previous_opinion,
                "output": text,
            },
            messageId=(str(uuid4()))
        )
        return {"claim": claim, "evidence": evidence, "previous_opinion": previous_opinion}

    def extract_factuality_from_opinion(self, opinion_text):
        """
        Extract factuality value from opinion text that contains JSON-like structure.
        """
        try:
            # Remove extra whitespace and clean the text
            opinion_text = opinion_text.strip()
            
            # Method 1: Try to find the complete JSON structure
            # Look for { at start and } at end, handling nested braces
            start = opinion_text.find('{')
            if start != -1:
                brace_count = 0
                for i in range(start, len(opinion_text)):
                    if opinion_text[i] == '{':
                        brace_count += 1
                    elif opinion_text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = opinion_text[start:i+1]
                            try:
                                parsed = json.loads(json_str)
                                if "factuality" in parsed:
                                    return parsed["factuality"]
                            except:
                                pass
                            break
            
            # Method 2: Simple string search for factuality value
            if '"factuality": true' in opinion_text.lower():
                return True
            elif '"factuality": false' in opinion_text.lower():
                return False
            elif '"factuality":true' in opinion_text.lower():
                return True
            elif '"factuality":false' in opinion_text.lower():
                return False
                
            return None
        except Exception as e:
            print(f"Error extracting factuality: {e}")
            return None
        
    def check_factuality_consensus(self, previous_opinion, round_count):
        """
        Check if there's consensus on factuality between skeptic and trust agents.
        Returns True if both agree on factuality value, False otherwise.
        """
        if not previous_opinion or round_count < 2:
            return False
        
        # Instead of splitting by comma (which is unreliable due to commas in JSON),
        # let's find individual JSON objects
        json_objects = []
        
        # Find all complete JSON objects in the string
        i = 0
        while i < len(previous_opinion):
            start = previous_opinion.find('{', i)
            if start == -1:
                break
                
            brace_count = 0
            end = -1
            for j in range(start, len(previous_opinion)):
                if previous_opinion[j] == '{':
                    brace_count += 1
                elif previous_opinion[j] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = j
                        break
            
            if end != -1:
                json_str = previous_opinion[start:end+1]
                json_objects.append(json_str)
                i = end + 1
            else:
                break
        
        # print(f"Found {len(json_objects)} JSON objects")
        
        # For round 2, we need at least 4 objects (skeptic1, trust1, skeptic2, trust2)
        # For round 3, we need at least 6 objects
        expected_objects = round_count * 2
        
        if len(json_objects) < expected_objects:
            # print(f"Not enough JSON objects yet. Expected: {expected_objects}, Got: {len(json_objects)}")
            return False
        
        # Get the last two JSON objects (current round's skeptic and trust)
        current_round_objects = json_objects[-2:]
        
        factuality_values = []
        for i, json_obj in enumerate(current_round_objects):
            factuality = self.extract_factuality_from_opinion(json_obj)
            # print(f"JSON object {i+1}: {json_obj[:100]}...")
            # print(f"Extracted factuality: {factuality}")
            if factuality is not None:
                factuality_values.append(factuality)
        
        # Check if we have factuality values from both agents and they agree
        if len(factuality_values) == 2 and factuality_values[0] == factuality_values[1]:
            # print(f"Consensus found: both agents agree on factuality = {factuality_values[0]}")
            return True
        
        # print("No consensus found")
        return False
    
    def should_continue_debate(self, state):
        """
        Determine if the debate should continue based on:
        1. Minimum 2 rounds
        2. Maximum 3 rounds 
        3. Consensus on factuality between skeptic and trust agents
        """
        round_count = state.get("round_count", 1)
        previous_opinion = state.get("previous_opinion", "")
        
        # print(f"=== Checking debate continuation - Round {round_count} ===")
        # print(f"Previous opinions length: {len(previous_opinion.split(',')) if previous_opinion else 0}")
        
        # Must complete at least 2 rounds
        if round_count < 2:
            # print("Continue: Minimum 2 rounds not reached")
            return "continue_debate"
        
        # Maximum 3 rounds
        if round_count >= 3:
            # print("End: Maximum 3 rounds reached")
            return "end_debate"
        
        # Check for factuality consensus (only after round 2 or higher)
        if round_count >= 2:
            has_consensus = self.check_factuality_consensus(previous_opinion, round_count)
            if has_consensus:
                # print("End: Factuality consensus reached between skeptic and trust")
                return "end_debate"
            else:
                # print("Continue: No factuality consensus yet")
                return "continue_debate"
        
        return "continue_debate"

    def generateAnswer(self,id, data, mId)->None:
        """
        Example method to generateAnswer the worker functionality.
        Replace this with your actual worker methods.
        """
        # print(data['prompt'])
        self.id = id
        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/createNewProgress/{id}"],
            data={
                "process_name": self.process_name,
                "input": data['prompt'],
                "output": "",
            },
            messageId= str(uuid4())
        )


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
        final_response = value["generation"]
        # print(value["generation"])
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

        
        



        self.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/updateOutputProcess/{id}"],
            data={
                "process_name": self.process_name,
                "output": value["generation"],
            },
            messageId= str(uuid4())
        )


        input_evaluasi = {
            "claim": value["generation"],
            "evidence": value["documents"],
            "question": value["question"]
        }

        for output in self.app_evaluasi.stream(input_evaluasi):
            for key, value in output.items():
                # Node
                pprint(f"Node '{key}':")
                # Optional: print full state at each node
                # pprint.pprint(value["keys"], indent=2, width=80, depth=None)
            pprint("\n---\n")


        #send back to RestAPI
        self.sendToOtherWorker(
          messageId=mId,
          destination=["RestApiWorker/onProcessed"],
          data= final_response

          )
        
      #   sendMessage(
      #     status="completed",
      #     reason="Test method executed successfully.",
      #     destination=["supervisor"],
      #     data={"message": "This is a test response."}
      # )
        # log("Test method called", "info")
        # return {"status": "success", "data": "This is a test response."}

def main(conn: Connection, config: dict):
    worker = CRAGWorker()
    worker.run(conn, config)
