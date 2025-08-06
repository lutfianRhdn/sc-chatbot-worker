import os
from dotenv import load_dotenv
load_dotenv()

port = int(os.getenv("PORT", 5000))
database={
    "connection_string": os.getenv("DB_CONNECTION_STRING", "mongodb://localhost:27017"),
    "database_name": os.getenv("DB_NAME", "chatbot"),
    "database_tweets": os.getenv("DB_TWEETS", "data_gathering"),
    "mongodb_collection_vector": os.getenv("MONGODB_COLLECTION", "vectorstores"),
    "mongo_vector_search_index_name": os.getenv("MONGO_VECTOR_SEARCH_INDEX_NAME", "index-vectorstores")
}


tavily_api_key = os.getenv("TAVILY_API_KEY", "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")

azure = {
  "endpoint":os.getenv("AZURE_OPENAI_ENDPOINT", "https://crag-skripsi.openai.azure.com/"),
  "api_key": os.getenv("AZURE_OPENAI_API_KEY", "ABCD1234EFGH5678IJKL9012MNOP3456QRST7890UVWX"),
  "deployment_name": {
    "embedding": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING", "text-embedding-3-large"),
    "api": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1"),
    "prompt": os.getenv("AZURE_OPENAI_DEPLOYMENT_PROMPT_NAME", "chatgpt-35-turbo-i")
  },
  "api_version": {
    "embedding": os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION", "2025-01-01-preview"),
    "api": os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
    "prompt": os.getenv("AZURE_OPENAI_API_PROMPT_VERSION", "2024-12-01-preview")
  }
}
rabbit_mq= {
    "url": os.getenv("RABBITMQ_URL", "amqp://admin:admin123@localhost:5672/dev"),
    "consume":{
        "queue": os.getenv("RABBITMQ_CONSUME_QUEUE", "chatbotQueue"),
        "compensation_queue": os.getenv("RABBITMQ_COMPENSATION_QUEUE", "chatbotCompensationQueue")
    },
    "produce":{
        "queue": os.getenv("RABBITMQ_PRODUCE_QUEUE", "topicsQueue"),
        "compensation_queue": os.getenv("RABBITMQ_PRODUCE_COMPENSATION_QUEUE", "topicsCompensationQueue")
    }
}


redis={
    "host": os.getenv("REDIS_URL", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "db": int(os.getenv("REDIS_DB", 0)),
    "username":os.getenv("REDIS_USERNAME", ""),
    "password": os.getenv("REDIS_PASSWORD", "")
}