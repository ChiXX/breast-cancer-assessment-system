from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.v1 import api_v1_router
from backend.app.database import engine, Base
# Import all models to register them with Base.metadata
from backend.app.models.assessment import Assessment
from backend.app.models.contact_request import ContactRequest
from backend.app.models.event import EventLog
from backend.app.models.history_dialogue import HistoryDialogue

# Initialize Database
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Breast Cancer Assessment Backend")

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)

@app.get("/")
async def root():
    return {"message": "Backend is running"}
