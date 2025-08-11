import strawberry
from typing import List, Optional
from .types import ChatResponse, ChatResponseDataItem, DataItemType, ProcessResponse,PromptResponse,SubProcessType, TopicDataType, TopicQuestionType
import uuid
import threading
from utils.handleMessage import sendMessage, convertMessage


@strawberry.type
class Mutation:
  """GraphQL Mutation root type"""
  
  @strawberry.field
  def chatChatbot(self,projectId:str,prompt:str,info: strawberry.Info)-> ChatResponse:
      """Create a new chat prompt for a given project ID and prompt"""
      worker = info.context.get('worker')
     
      message = worker.sendToOtherWorker(
              destination=["DatabaseInteractionWorker/createNewHistory/"],
              data={
                  "question": prompt,
                  "projectId": projectId
              }
          )
      id = message.get("result", [{}])[0].get("_id", "unknown_id")
      
      sendMessage(
      conn=worker.conn,
      messageId=id,
      status="complated",
      destination=[f"LogicalFallacyPromptWorker/removeLFPrompt/"],
      data={
              "prompt": prompt,
              "id": id,
              "projectId": projectId
          }
      )
      return ChatResponse(
        status="completed",
       data= ChatResponseDataItem(
         chat_id=id,
          prompt=prompt,
          projectId=projectId
       )

    )
    
  @strawberry.field
  def chatResponseLFU(self,response:str,projectId:str,info: strawberry.Info)-> ChatResponse:
      """Create a new chat response for a given project ID and response text"""
      worker = info.context.get('worker')
      
      message = worker.sendToOtherWorker(
          destination=["DatabaseInteractionWorker/createNewHistory/"],
          data={
              "question": response,
              "projectId": projectId
          }
      )
      id = message.get("result", [{}])[0].get("_id", "unknown_id")

      sendMessage(
      conn=worker.conn,
      messageId=id,
      status="complated",
          destination=["LogicalFallacyResponseWorker/removeLFResponse/"],
          data={
              "response":response,
              "chat_id": id
          }
      )
      return ChatResponse(
        status="completed",
       data= ChatResponseDataItem(
         chat_id=id,
          prompt=response,
          projectId=projectId
       )

    )