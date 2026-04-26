from sqlalchemy.orm import Session
from datetime import datetime
from backend.app.models.assessment import Assessment
from backend.app.models.event import EventLog
from backend.app.models.history_dialogue import HistoryDialogue
from backend.app.services.mcp_service import evaluate_symptoms, store_memory
from backend.app.schemas.assessment import AssessmentCreate, AssessmentResponse, AssessmentSave
import json

def evaluate_assessment(db: Session, assessment_in: AssessmentCreate) -> AssessmentResponse:
    # 1. Fetch history for context (can still use old assessments if history_dialogues is empty)
    if assessment_in.history is not None:
        history = assessment_in.history
    else:
        # Try to get from history_dialogues first
        latest_history = db.query(HistoryDialogue).filter(
            HistoryDialogue.session_id == assessment_in.session_id
        ).order_by(HistoryDialogue.created_at.desc()).first()
        
        if latest_history:
            history = latest_history.history_json
        else:
            # Fallback to old assessments
            previous_assessments = db.query(Assessment).filter(
                Assessment.session_id == assessment_in.session_id
            ).order_by(Assessment.created_at.asc()).all()
            
            history = []
            for past in previous_assessments:
                history.append({"role": "user", "content": past.user_input})
                history.append({"role": "assistant", "content": past.display_text or past.advice})

    # 2. Call MCP for evaluation
    mcp_result = evaluate_symptoms(assessment_in.user_input, assessment_in.session_id, history=history)
    
    # 3. Return response without saving to DB yet
    return AssessmentResponse(
        session_id=assessment_in.session_id,
        user_input=assessment_in.user_input,
        risk_level=mcp_result["risk_level"],
        action_required=mcp_result.get("action_required"),
        ctcae_grade=mcp_result.get("ctcae_grade"),
        advice=mcp_result["advice"],
        evidence=mcp_result["evidence"],
        matched_rule_id=mcp_result["rule_id"],
        contact_team=mcp_result["contact_team"],
        display_text=mcp_result.get("display_text", ""),
        version="v1.0.0",
        created_at=datetime.utcnow()
    )

def save_assessment_and_history(db: Session, save_in: AssessmentSave) -> Assessment:
    # 1. Create Assessment record
    db_assessment = Assessment(
        session_id=save_in.session_id,
        user_input=save_in.assessment.user_input,
        risk_level=save_in.assessment.risk_level,
        action_required=save_in.assessment.action_required,
        ctcae_grade=save_in.assessment.ctcae_grade,
        advice=save_in.assessment.advice,
        evidence=save_in.assessment.evidence,
        matched_rule_id=save_in.assessment.matched_rule_id,
        contact_team=save_in.assessment.contact_team,
        display_text=save_in.assessment.display_text
    )
    db.add(db_assessment)
    db.commit()
    db.refresh(db_assessment)
    
    # 2. Save full history
    db_history = HistoryDialogue(
        session_id=save_in.session_id,
        history_json=save_in.history
    )
    db.add(db_history)
    db.commit()

    # 3. Trigger MCP memory storage
    try:
        store_memory(save_in.session_id, save_in.history)
    except Exception as e:
        print(f"Error triggering MCP memory storage: {e}")
    
    # 4. Log event
    event = EventLog(
        event_name="assessment_finished",
        session_id=save_in.session_id,
        payload={
            "assessment_id": db_assessment.id,
            "risk_level": db_assessment.risk_level,
            "rule_id": db_assessment.matched_rule_id
        }
    )
    db.add(event)
    db.commit()
    
    return db_assessment

def get_assessment(db: Session, assessment_id: int) -> Assessment:
    return db.query(Assessment).filter(Assessment.id == assessment_id).first()

def get_history(db: Session, session_id: str):
    latest_history = db.query(HistoryDialogue).filter(
        HistoryDialogue.session_id == session_id
    ).order_by(HistoryDialogue.created_at.desc()).first()
    
    if latest_history:
        return latest_history.history_json
    
    # Fallback to old assessments if no history_dialogues found
    previous_assessments = db.query(Assessment).filter(
        Assessment.session_id == session_id
    ).order_by(Assessment.created_at.asc()).all()
    
    history = []
    for past in previous_assessments:
        history.append({"role": "user", "content": past.user_input})
        history.append({"role": "assistant", "content": past.display_text or past.advice})
    return history
