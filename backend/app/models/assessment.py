from sqlalchemy import Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from backend.app.database import Base

class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_input: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    advice: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    matched_rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    contact_team: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
