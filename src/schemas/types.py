import strawberry
from typing import List, Optional
from strawberry.scalars import JSON
from dataclasses import dataclass

# Untuk sub-process yang muncul berulang dan punya struktur mirip
@strawberry.type
class SubProcessType:
    sub_process_name: str
    input: Optional[JSON] = None   # kadang string, kadang object, kadang null
    output: Optional[JSON] = None  # fleksibel -> pakai JSON scalar

# Item utama di dalam array "data"
@strawberry.type
class DataItemType:
    input: Optional[JSON] = None
    output: Optional[JSON] = None
    process_name: Optional[str] = None
    # sub_process adalah list dari SubProcessType (jika ada)
    sub_process: Optional[List[SubProcessType]] = None

# Root object yang membungkus "data" dan metadata
@strawberry.type
class ProcessResponse:
    data: List[DataItemType]
    message: Optional[str] = None
    status: Optional[str] = None


@strawberry.type
class ChatResponseDataItem:
    chat_id: str
    prompt: str
    projectId: str
@strawberry.type
class ChatResponse:
    status: str
    data: ChatResponseDataItem

@strawberry.type
class TopicQuestionType:
    optimal_prompt: str
    pertanyaan: str

@strawberry.type
class TopicDataType:
    topic_name: str
    questions: List[TopicQuestionType]
@strawberry.type
class PromptResponse:
    project_id: str
    prompt: List[TopicDataType]
