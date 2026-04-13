from sqlalchemy import Column, DateTime, Integer, String, func
from app.db import Base


class UploadBatch(Base):
    __tablename__ = "upload_batches"

    upload_batches_id = Column(String, primary_key=True)   # UUID, set at upload time
    file_type = Column(String, nullable=False)             # "sales" or "inventory"
    filename = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending | success | partial | failed
    rows_accepted = Column(Integer, default=0)
    rows_rejected = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
