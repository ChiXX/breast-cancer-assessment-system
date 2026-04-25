from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.event import EventLog
from backend.app.schemas.event import EventCreate, EventResponse

router = APIRouter(prefix="/events", tags=["events"])

@router.post("", response_model=EventResponse, status_code=201)
def create_event(event_in: EventCreate, db: Session = Depends(get_db)):
    db_event = EventLog(
        event_name=event_in.event_name,
        session_id=event_in.session_id,
        payload=event_in.payload
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event
