from fastapi import FastAPI
from backend.app.api.v1 import api_v1_router
from backend.app.database import engine, Base

# Initialize Database
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Breast Cancer Assessment Backend")

app.include_router(api_v1_router)

@app.get("/")
async def root():
    return {"message": "Backend is running"}
