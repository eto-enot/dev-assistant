from typing import Optional, TypeAlias

from pydantic import BaseModel, TypeAdapter
from litserve.specs.openai import ChatCompletionChunk

class SetProjectInfoRequest(BaseModel):
    session_id: str
    work_directory: str
    core_info: str
    os: str

class ConfirmToolCallRequest(BaseModel):
    session_id: str
    call_allowed: bool

class ListFilesRequest(BaseModel):
    work_directory: str
    path: Optional[str] = None
    filter: str

class ListFilesResponseItem(BaseModel):
    name: str
    path: str

ListFilesResponseList: TypeAlias = list[ListFilesResponseItem]
ListFilesResponse = TypeAdapter(ListFilesResponseList)

class ChatCompletionChunkType(ChatCompletionChunk):
    type: str = ""
