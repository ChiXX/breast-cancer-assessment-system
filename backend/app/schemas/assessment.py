from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

class AssessmentCreate(BaseModel):
    user_input: str
    session_id: str
    history: Optional[List[Dict[str, Any]]] = None

class AssessmentResponse(BaseModel):
    id: Optional[int] = None
    session_id: str
    user_input: str
    risk_level: str
    action_required: Optional[str] = None
    ctcae_grade: Optional[str] = None
    advice: str
    evidence: str
    matched_rule_id: str
    display_text: Optional[str] = None
    contact_team: bool
    version: str
    created_at: datetime

    class Config:
        from_attributes = True

class AssessmentSave(BaseModel):
    session_id: str
    assessment: AssessmentResponse
    history: List[Dict[str, Any]]

class HistoryDialogueResponse(BaseModel):
    id: int
    session_id: str
    history_json: List[Dict[str, str]]
    created_at: datetime

    class Config:
        from_attributes = True
