import strawberry
from typing import List, Optional
from strawberry.scalars import JSON

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
class RootJSONType:
    data: List[DataItemType]
    message: Optional[str] = None
    status: Optional[str] = None

# Response type for prompt queries (using strawberry.type only for Python 3.10 compatibility)
@strawberry.type
class PromptResponse:
    project_id: Optional[str] = None
    prompt: Optional[JSON] = None