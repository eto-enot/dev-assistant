from typing import List, Optional

from litserve.specs.openai import ChatCompletionChunk
from pydantic import BaseModel


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


class ListFilesResponse(BaseModel):
    content: List[ListFilesResponseItem]


class ChatCompletionChunkType(ChatCompletionChunk):
    type: str = ""


class ReindexProjectRequest(BaseModel):
    work_directory: str


class ReindexProjectResponse(BaseModel):
    pass
