from pydantic import BaseModel

class SetWorkDirectoryRequest(BaseModel):
    session_id: str
    dir: str
