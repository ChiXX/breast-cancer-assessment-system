from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.app.database import get_db
from backend.app.schemas.contact_request import ContactRequestCreate, ContactRequestResponse
from backend.app.services import contact_service

router = APIRouter(prefix="/contact-requests", tags=["contact-requests"])

@router.post("", response_model=ContactRequestResponse, status_code=201)
def create_contact_request(request_in: ContactRequestCreate, db: Session = Depends(get_db)):
    return contact_service.create_contact_request(db, request_in)

@router.get("", response_model=List[ContactRequestResponse])
def read_contact_requests(session_id: str, db: Session = Depends(get_db)):
    return contact_service.get_contact_requests(db, session_id)
