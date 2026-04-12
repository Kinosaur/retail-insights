import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.inventory import InventorySnapshot
from app.models.sale import Sale
from app.models.sku import Sku
from app.models.upload_batch import UploadBatch
from app.parsers.csv_parser import INVENTORY_REQUIRED, SALES_REQUIRED, parse_upload
from app.schemas.upload import UploadError, UploadResponse
from app.validators.inventory import validate_inventory
from app.validators.sales import validate_sales

router = APIRouter(prefix="/upload", tags=["upload"])


def _status(accepted: int, rejected: int) -> str:
    if accepted == 0:
        return "failed"
    if rejected == 0:
        return "success"
    return "partial"


def _ensure_skus_exist(db: Session, sku_ids: list[str]) -> None:
    """Auto-insert any SKU not already in the sku table as UNKNOWN."""
    existing = {
        row.sku_id
        for row in db.query(Sku.sku_id).filter(Sku.sku_id.in_(sku_ids)).all()
    }
    new_skus = [
        Sku(sku_id=sid, sku_name="UNKNOWN", category=None)
        for sid in set(sku_ids)
        if sid not in existing
    ]
    if new_skus:
        db.bulk_save_objects(new_skus)
        db.flush()


@router.post("/sales", response_model=UploadResponse)
async def upload_sales(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    df = await parse_upload(file, SALES_REQUIRED)

    batch_id = str(uuid.uuid4())
    batch = UploadBatch(
        upload_batches_id=batch_id,
        file_type="sales",
        filename=file.filename,
        status="processing",
    )
    db.add(batch)
    db.flush()

    accepted, errors = validate_sales(df)

    if accepted:
        _ensure_skus_exist(db, [r["sku_id"] for r in accepted])
        db.bulk_save_objects([Sale(upload_batches_id=batch_id, **r) for r in accepted])

    batch.rows_accepted = len(accepted)
    batch.rows_rejected = len(errors)
    batch.status = _status(len(accepted), len(errors))
    db.commit()

    return UploadResponse(
        upload_batches_id=batch_id,
        file_type="sales",
        filename=file.filename,
        status=batch.status,
        rows_total=len(accepted) + len(errors),
        rows_accepted=len(accepted),
        rows_rejected=len(errors),
        errors=[UploadError(**e) for e in errors],
    )


@router.post("/inventory", response_model=UploadResponse)
async def upload_inventory(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    df = await parse_upload(file, INVENTORY_REQUIRED)

    batch_id = str(uuid.uuid4())
    batch = UploadBatch(
        upload_batches_id=batch_id,
        file_type="inventory",
        filename=file.filename,
        status="processing",
    )
    db.add(batch)
    db.flush()

    accepted, errors = validate_inventory(df)

    if accepted:
        _ensure_skus_exist(db, [r["sku_id"] for r in accepted])
        db.bulk_save_objects([
            InventorySnapshot(upload_batches_id=batch_id, **r) for r in accepted
        ])

    batch.rows_accepted = len(accepted)
    batch.rows_rejected = len(errors)
    batch.status = _status(len(accepted), len(errors))
    db.commit()

    return UploadResponse(
        upload_batches_id=batch_id,
        file_type="inventory",
        filename=file.filename,
        status=batch.status,
        rows_total=len(accepted) + len(errors),
        rows_accepted=len(accepted),
        rows_rejected=len(errors),
        errors=[UploadError(**e) for e in errors],
    )
