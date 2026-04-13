from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.upload_batch import UploadBatch
from app.schemas.batch import BatchItem, BatchListResponse

router = APIRouter(prefix="/upload-batches", tags=["upload-batches"])


@router.get("", response_model=BatchListResponse)
def list_batches(db: Session = Depends(get_db)) -> BatchListResponse:
    rows = (
        db.query(UploadBatch)
        .order_by(UploadBatch.created_at.desc())
        .all()
    )
    return BatchListResponse(
        items=[
            BatchItem(
                upload_batches_id=b.upload_batches_id,
                file_type=b.file_type,
                filename=b.filename,
                status=b.status,
                rows_accepted=b.rows_accepted,
                rows_rejected=b.rows_rejected,
                created_at=b.created_at,
            )
            for b in rows
        ]
    )
