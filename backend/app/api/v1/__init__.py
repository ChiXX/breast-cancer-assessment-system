from fastapi import APIRouter
from backend.app.api.v1.assessments import router as assessment_router
from backend.app.api.v1.contact_requests import router as contact_router
from backend.app.api.v1.events import router as event_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(assessment_router)
api_v1_router.include_router(contact_router)
api_v1_router.include_router(event_router)
