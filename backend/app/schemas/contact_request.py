from pydantic import BaseModel
from datetime import datetime

class ContactRequestCreate(BaseModel):
    assessment_id: int
    session_id: str

class ContactRequestResponse(BaseModel):
    id: int
    assessment_id: int
    session_id: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
