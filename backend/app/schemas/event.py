from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any

class EventCreate(BaseModel):
    event_name: str
    session_id: str
    payload: Dict[str, Any] = {}

class EventResponse(BaseModel):
    id: int
    event_name: str
    session_id: str
    payload: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
