from sqlalchemy import Column, DateTime, String, Text, func
from app.db import Base


class AnalysisRun(Base):
    """
    Owned by Person B (analytics & AI).
    Defined here so the schema is in one place and migrations stay clean.
    """
    __tablename__ = "analysis_runs"

    id = Column(String, primary_key=True)              # UUID
    run_type = Column(String, nullable=False)          # e.g. "abc", "forecast", "summary"
    parameters = Column(Text, nullable=True)           # JSON string of inputs
    result = Column(Text, nullable=True)               # JSON string of output / LLM response
    status = Column(String, nullable=False, default="pending")  # pending | done | failed
    created_at = Column(DateTime, server_default=func.now())
