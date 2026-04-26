from fastapi import APIRouter, Depends, HTTPException
import traceback
from sqlalchemy.orm import Session
from typing import List, Dict
from backend.app.database import get_db
from backend.app.schemas.assessment import AssessmentCreate, AssessmentResponse, AssessmentSave
from backend.app.services import assessment_service

router = APIRouter(prefix="/assessments", tags=["assessments"])

@router.post("", response_model=AssessmentResponse, status_code=200)
def create_assessment(assessment_in: AssessmentCreate, db: Session = Depends(get_db)):
    """
    Evaluate symptoms without saving to database.
    """
    try:
        return assessment_service.evaluate_assessment(db, assessment_in)
    except Exception as e:
        traceback.print_exc()
        error_str = str(e)
        if "httpx" in error_str.lower() or "connection" in error_str.lower():
            raise HTTPException(status_code=502, detail=f"MCP Connection Error: {error_str}")
        raise HTTPException(status_code=500, detail=f"Internal Error: {error_str}")

@router.post("/save", response_model=AssessmentResponse, status_code=201)
def save_assessment(save_in: AssessmentSave, db: Session = Depends(get_db)):
    """
    Save final assessment and full conversation history.
    """
    try:
        return assessment_service.save_assessment_and_history(db, save_in)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Save Error: {str(e)}")

@router.get("/{assessment_id}", response_model=AssessmentResponse)
def read_assessment(assessment_id: int, db: Session = Depends(get_db)):
    db_assessment = assessment_service.get_assessment(db, assessment_id)
    if db_assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return db_assessment

@router.get("", response_model=List[Dict[str, str]])
def read_history(session_id: str, db: Session = Depends(get_db)):
    """
    Get full conversation history for a session.
    """
    return assessment_service.get_history(db, session_id)
