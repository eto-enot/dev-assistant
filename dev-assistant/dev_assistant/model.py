from pydantic import BaseModel

class SetProjectInfoRequest(BaseModel):
    session_id: str
    work_directory: str
    core_info: str

class ConfirmToolCallRequest(BaseModel):
    session_id: str
    call_allowed: bool