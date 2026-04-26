from sqlalchemy import Integer, String, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from backend.app.database import Base

class HistoryDialogue(Base):
    __tablename__ = "history_dialogues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    history_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
