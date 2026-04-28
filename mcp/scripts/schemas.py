from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from mcp.agents.schemas import RiskLevel

class EvaluateRequest(BaseModel):
    user_input: str
    session_id: str
    history: Optional[List[Dict[str, Any]]] = []

class EvaluateResponse(BaseModel):
    risk_level: RiskLevel
    action_required: Optional[str] = None
    ctcae_grade: Optional[str] = None
    advice: str
    contact_team: bool
    evidence: str
    rule_id: str
    display_text: str = ""
    id: Optional[int] = None # For DB reference if needed

class MemoryItem(BaseModel):
    clue: str
    summary: str
    learned: bool

class MemoryStoreRequest(BaseModel):
    session_id: str
    history: List[Dict[str, Any]]

class SessionResponse(BaseModel):
    memories: List[MemoryItem]

class KnowledgeLearnResponse(BaseModel):
    status: str
