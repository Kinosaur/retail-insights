from pydantic import BaseModel


class UploadError(BaseModel):
    row: int
    sku_id: str | None
    reason: str


class UploadResponse(BaseModel):
    upload_batches_id: str
    file_type: str
    filename: str | None
    status: str
    rows_total: int
    rows_accepted: int
    rows_rejected: int
    errors: list[UploadError]
