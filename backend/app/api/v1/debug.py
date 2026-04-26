from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db, Base, engine

# Ensure all models are loaded
from backend.app.models.assessment import Assessment
from backend.app.models.contact_request import ContactRequest
from backend.app.models.event import EventLog
from backend.app.models.history_dialogue import HistoryDialogue
import os

router = APIRouter(prefix="/debug")

def check_debug():
    if os.getenv("DEBUG") != "True":
        raise HTTPException(status_code=404, detail="Not Found")

def get_assessments_data(db: Session):
    return [
        {
            "id": a.id,
            "session_id": a.session_id,
            "user_input": a.user_input,
            "risk_level": a.risk_level,
            "advice": a.advice,
            "contact_team": a.contact_team,
            "created_at": a.created_at.isoformat() if a.created_at else None
        } for a in db.query(Assessment).all()
    ]

def get_contact_requests_data(db: Session):
    return [
        {
            "id": c.id,
            "assessment_id": c.assessment_id,
            "session_id": c.session_id,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None
        } for c in db.query(ContactRequest).all()
    ]

def get_events_data(db: Session):
    return [
        {
            "id": e.id,
            "event_name": e.event_name,
            "session_id": e.session_id,
            "payload": e.payload,
            "created_at": e.created_at.isoformat() if e.created_at else None
        } for e in db.query(EventLog).all()
    ]

def get_history_dialogues_data(db: Session):
    return [
        {
            "id": h.id,
            "session_id": h.session_id,
            "history_json": h.history_json,
            "created_at": h.created_at.isoformat() if h.created_at else None
        } for h in db.query(HistoryDialogue).all()
    ]

@router.get("/db/dump", dependencies=[Depends(check_debug)])
def dump_db(db: Session = Depends(get_db)):
    return {
        "assessments": get_assessments_data(db),
        "contact_requests": get_contact_requests_data(db),
        "event_logs": get_events_data(db),
        "history_dialogues": get_history_dialogues_data(db)
    }

@router.get("/db/assessments", dependencies=[Depends(check_debug)])
def get_all_assessments(db: Session = Depends(get_db)):
    return get_assessments_data(db)

@router.get("/db/contact-requests", dependencies=[Depends(check_debug)])
def get_all_contact_requests(db: Session = Depends(get_db)):
    return get_contact_requests_data(db)

@router.get("/db/events", dependencies=[Depends(check_debug)])
def get_all_events(db: Session = Depends(get_db)):
    return get_events_data(db)

@router.get("/db/history-dialogues", dependencies=[Depends(check_debug)])
def get_all_history_dialogues(db: Session = Depends(get_db)):
    return get_history_dialogues_data(db)

@router.post("/db/reset", dependencies=[Depends(check_debug)])
def reset_db(db: Session = Depends(get_db)):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return {"status": "ok", "message": "Database dropped and recreated successfully"}
