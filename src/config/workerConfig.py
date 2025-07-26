
from .env import port, database, tavily_api_key, azure, rabbit_mq


DatabaseInteractionWorkerConfig={
  'connection_string':database['connection_string'],
  'database': database['database_name'],
  "dbTweets": database["database_tweets"],
} 

VectorWorkerConfig={
    "connection_string": database['connection_string'],
    "database": database['database_name'],
    "azure_openai_endpoint": azure['endpoint'],
    "azure_openai_key" : azure['api_key'],
    "azure_openai_deployment_name_embedding": azure['deployment_name']['embedding'],
    "azure_openai_api_version": azure['api_version']['embedding'],
    "mongodb_collection": database['mongodb_collection_vector'],
    "atlas_vector_search_index_name": database['mongo_vector_search_index_name'],
}

PromptRecommendationWorkerConfig={
    "azure_openai_endpoint": azure['endpoint'],
    "azure_openai_api_key" : azure['api_key'],
    "azure_openai_api_version": azure['api_version']['prompt'],
    "azure_openai_model": azure['deployment_name']['prompt'],
    "azure_openai_model_chat": azure['deployment_name']['api'],
    "azure_openai_chat_api_version": azure['api_version']['api'],
    "azure_openai_chat_api_key": azure['api_key'],
    "azure_openai_chat_endpoint": azure['endpoint'],
}

RabbitMQWorkerConfig={
    'connection_string': rabbit_mq['url'],
    'consumeQueue': rabbit_mq['consume']['queue'],
    'consumeCompensationQueue': rabbit_mq['consume']['compensation_queue'],
    'produceQueue': rabbit_mq['produce']['queue'],
    'produceCompensationQueue': rabbit_mq['produce']['compensation_queue']
}

RestApiWorkerConfig={
    'port': port,
}

CRAGWorkerConfig={
    "database": database['database_name'],
    "connection_string": database['connection_string'],
    "index_name": database['mongo_vector_search_index_name'],
    "collection_name": database['mongodb_collection_vector'],
    "tavily_api_key": tavily_api_key,
    "azure_openai_api_key": azure['api_key'],
    "azure_openai_endpoint": azure['endpoint'],
    "azure_openai_deployment_name": azure['deployment_name']['api'],
    "azure_openai_deployment_name_embedding": azure['deployment_name']['embedding'],
    "azure_openai_api_version": azure['api_version']['api'],
    "azure_openai_embedding_api_version": azure['api_version']['embedding'],
}

LogicalFallacyPromptWorkerConfig={
    "azure_openai_api_key": azure['api_key'],
    "azure_openai_endpoint": azure['endpoint'],
    "azure_openai_deployment_name": azure['deployment_name']['api'],
    "azure_openai_api_version": azure['api_version']['api']
}

SMTConverterWorkerConfig={
    "":""
}

CounterExampleCreatorWorkerConfig={
    "azure_openai_api_key": azure['api_key'],
    "azure_openai_endpoint": azure['endpoint'],
    "azure_openai_deployment_name": azure['deployment_name']['api'],
    "azure_openai_api_version": azure['api_version']['api']
}

LogicalFallacyClassificationWorkerConfig={
    "azure_openai_api_key": azure['api_key'],
    "azure_openai_endpoint": azure['endpoint'],
    "azure_openai_deployment_name": azure['deployment_name']['api'],
    "azure_openai_api_version": azure['api_version']['api']
}