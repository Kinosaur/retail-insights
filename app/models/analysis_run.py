from sqlalchemy import Column, DateTime, String, Text, func
from app.db import Base


class AnalysisRun(Base):
    """
    Owned by Person B (analytics & AI).
    Defined here so the schema is in one place.

    Caching logic:
    - Before calling the LLM, Person B computes cache_key = hash(metrics_json)
    - If a row with that cache_key already exists and status = "done", return it
    - Otherwise insert a new row, call the LLM, update ai_summary_text + status
    """
    __tablename__ = "analysis_runs"

    analysis_runs_id = Column(String, primary_key=True)         # UUID
    run_type = Column(String, nullable=False)                   # "abc", "forecast", "dead_stock", "summary"
    cache_key = Column(String, nullable=True, index=True)       # hash of metrics_json for cache lookup
    metrics_json = Column(Text, nullable=True)                  # JSON of analytics data fed to LLM
    ai_summary_text = Column(Text, nullable=True)               # plain-English LLM response
    status = Column(String, nullable=False, default="pending")  # pending | done | failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
