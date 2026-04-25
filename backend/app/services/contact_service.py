from sqlalchemy.orm import Session
from backend.app.models.contact_request import ContactRequest
from backend.app.schemas.contact_request import ContactRequestCreate

def create_contact_request(db: Session, request_in: ContactRequestCreate) -> ContactRequest:
    db_request = ContactRequest(
        assessment_id=request_in.assessment_id,
        session_id=request_in.session_id,
        status="pending"
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request

def get_contact_requests(db: Session, session_id: str):
    return db.query(ContactRequest).filter(ContactRequest.session_id == session_id).all()
