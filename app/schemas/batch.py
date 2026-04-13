from datetime import datetime

from pydantic import BaseModel


class BatchItem(BaseModel):
    upload_batches_id: str
    file_type: str
    filename: str | None
    status: str
    rows_accepted: int | None
    rows_rejected: int | None
    created_at: datetime | None


class BatchListResponse(BaseModel):
    items: list[BatchItem]
