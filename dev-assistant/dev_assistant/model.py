from pydantic import BaseModel
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
    filter: str

class ListFilesResponse(BaseModel):
    name: str
    path: str

class ChatCompletionChunkType(ChatCompletionChunk):
    type: str = ""
