from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.app.database import get_db
from backend.app.schemas.assessment import AssessmentCreate, AssessmentResponse
from backend.app.services import assessment_service

router = APIRouter(prefix="/assessments", tags=["assessments"])

@router.post("", response_model=AssessmentResponse, status_code=201)
def create_assessment(assessment_in: AssessmentCreate, db: Session = Depends(get_db)):
    try:
        return assessment_service.create_assessment(db, assessment_in)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"MCP Error: {str(e)}")

@router.get("/{assessment_id}", response_model=AssessmentResponse)
def read_assessment(assessment_id: int, db: Session = Depends(get_db)):
    db_assessment = assessment_service.get_assessment(db, assessment_id)
    if db_assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return db_assessment

@router.get("", response_model=List[AssessmentResponse])
def read_history(session_id: str, db: Session = Depends(get_db)):
    return assessment_service.get_history(db, session_id)
