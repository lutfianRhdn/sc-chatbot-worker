import strawberry
from typing import List, Optional
from .types import ChatResponse, ChatResponseDataItem, DataItemType, ProcessResponse,PromptResponse,SubProcessType, TopicDataType, TopicQuestionType
import uuid
import threading
from utils.handleMessage import sendMessage, convertMessage

def _map_subprocess_list(raw) -> List[SubProcessType]:
    if not raw:
        return []
    items: List[SubProcessType] = []
    for it in raw:
        items.append(
            SubProcessType(
                sub_process_name=(
                    it.get("sub_process_name")
                    or it.get("name")
                    or ""  # fallback aman
                ),
                input=it.get("input"),
                output=it.get("output"),
            )
        )
    return items

def _map_data_list(raw) -> List[DataItemType]:
    if not raw:
        return []
    # pastikan iterable list
    raw_list = raw if isinstance(raw, list) else [raw]
    items: List[DataItemType] = []
    for it in raw_list:
        items.append(
            DataItemType(
                input=it.get("input"),
                output=it.get("output"),
                process_name=it.get("process_name"),
                sub_process=_map_subprocess_list(it.get("sub_process")),
            )
        )
    return items


@strawberry.type
class Query:
  """GraphQL Query root type"""
  @strawberry.field
  def prompt(self,projectId:str,prompt:str,info: strawberry.Info)-> ChatResponse:
      """Fetch a prompt response for a given project ID and prompt"""
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
      """Fetch a chat response for a given project ID and response text"""
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
        
      
      
      
      
  @strawberry.field
  def getPrompt(self,projectId:str,info:strawberry.Info) -> PromptResponse: # type: ignore
      """Fetch a prompt response for a given project ID"""
      worker = info.context.get('worker')
      id = projectId
      print(f"Fetching prompt for project ID: {id}")
      cacheDest = [f"CacheWorker/getByKey/{id}"]
      caceData = {"key": id,}
      print(f"Cache destination: {cacheDest}, Cache data: {caceData}")
      result = worker.sendToOtherWorker(
          destination=cacheDest,
          data=caceData
      )
      if len(result["result"]) == 0:
          result = worker.sendToOtherWorker(
              destination=[f"DatabaseInteractionWorker/getPrompt/{projectId}"],
              data={"key": projectId}
          )
          sendMessage(
              conn=worker.conn,
              messageId=str(uuid.uuid4()),
              status="processing",
              destination=['CacheWorker/set/' + projectId ],
              data={
                  "key":f"{projectId}",
                  "value":result['result'],
              }
          )
      print(f"Result from worker: {result}")
      result_data = result["result"][0]
      project_id = result_data["project_id"]
      prompts = result_data["prompts"]

      topic_data_list = []

      for topic_name, question_list in prompts.items():
          questions = [
              TopicQuestionType(
                  pertanyaan=q["pertanyaan"],
                  optimal_prompt=q["optimal_prompt"]
              )
              for q in question_list
          ]
          topic_data = TopicDataType(topic_name=topic_name, questions=questions)
          topic_data_list.append(topic_data)

      return PromptResponse(project_id=project_id, prompt=topic_data_list)

      # prompt = TopicDataType(
      #     topic_name=
      # )
      # return PromptResponse(
      #     project_id=projectId,
      #     prompt=prompt
      # )
  @strawberry.field
  def getStatus(self, chat_id: str, process_name: str, info: strawberry.Info) -> ProcessResponse:
        worker = info.context.get("worker")
        response = worker.sendToOtherWorker(
            destination=[f"DatabaseInteractionWorker/getProgress/{chat_id}"],
            data={"id": chat_id, "process_name": process_name},
        )

        process_result = response.get("result")

        if isinstance(process_result, dict) and "data" in process_result:
            data_items = _map_data_list(process_result.get("data"))
            message = process_result.get("message", response.get("message"))
            status = process_result.get("status", response.get("status"))
        else:
            data_items = _map_data_list(process_result)
            message = response.get("message")
            status = response.get("status")

        return ProcessResponse(
            data=data_items,                  
            message=message or "No message",
            status=status or "unknown",
        )

    #   print(response)
      # if response["status"] == "timeout":
          # return jsonify({"error": "Request timed out"}), 504
      # elif response["status"] == "completed":
      # return jsonify({
      #     "status": "success",
      #     "message": "Progress retrieved successfully",
      #   "data": response["result"]
      #     }), 200
      # else:
      #     return jsonify({"error": "Unknown error"}), 500
      
      # result = self.sendToOtherWorker(
      #     destination=[f"DatabaseInteractionWorker/getStatus/{projectId}"],
      #     data={"process_name": process_name}
      # )
      
      # if not result["result"]:
      #     return DataItemType(
      #         input=None,
      #         output=None,
      #         process_name=process_name,
      #         sub_process=None
      #     )
      
      # data_item = convertMessage(result["result"])
      # return DataItemType(
      #     input=data_item.get("input"),
      #     output=data_item.get("output"),
      #     process_name=data_item.get("process_name"),
      #     sub_process=[SubProcessType(**sub) for sub in data_item.get("sub_process", [])]
      # )