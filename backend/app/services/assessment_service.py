from sqlalchemy.orm import Session
from backend.app.models.assessment import Assessment
from backend.app.models.event import EventLog
from backend.app.services.mcp_service import evaluate_symptoms
from backend.app.schemas.assessment import AssessmentCreate
import json

def create_assessment(db: Session, assessment_in: AssessmentCreate) -> Assessment:
    # 1. Call MCP for evaluation
    mcp_result = evaluate_symptoms(assessment_in.user_input, assessment_in.session_id)
    
    # 2. Create Assessment record
    db_assessment = Assessment(
        session_id=assessment_in.session_id,
        user_input=assessment_in.user_input,
        risk_level=mcp_result["risk_level"],
        advice=mcp_result["advice"],
        evidence=mcp_result["evidence"],
        matched_rule_id=mcp_result["rule_id"],
        contact_team=mcp_result["contact_team"]
    )
    db.add(db_assessment)
    db.commit()
    db.refresh(db_assessment)
    
    # 3. Log event
    event = EventLog(
        event_name="assessment_submitted",
        session_id=assessment_in.session_id,
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
    return db.query(Assessment).filter(Assessment.session_id == session_id).order_by(Assessment.created_at.desc()).all()
