from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AssessmentCreate(BaseModel):
    user_input: str
    session_id: str

class AssessmentResponse(BaseModel):
    id: int
    session_id: str
    user_input: str
    risk_level: str
    advice: str
    evidence: str
    matched_rule_id: str
    contact_team: bool
    version: str
    created_at: datetime

    class Config:
        from_attributes = True
