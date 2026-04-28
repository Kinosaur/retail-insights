import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.inventory import InventorySnapshot
from app.models.product import Product
from app.models.sale import Sale
from app.models.upload_batch import UploadBatch
from app.parsers.csv_parser import (
    INVENTORY_REQUIRED,
    PRODUCTS_REQUIRED,
    SALES_REQUIRED,
    parse_upload,
)
from app.schemas.upload import UploadError, UploadResponse
from app.validators.inventory import validate_inventory
from app.validators.products import validate_products
from app.validators.sales import validate_sales

router = APIRouter(prefix="/upload", tags=["upload"])


def _status(accepted: int, rejected: int) -> str:
    if accepted == 0:
        return "failed"
    if rejected == 0:
        return "success"
    return "partial"


_INSERT_CHUNK = 5_000  # max rows per flush to stay within psycopg3 param limits


def _ensure_products_exist(db: Session, product_ids: list[str]) -> None:
    """Auto-insert any product not already in the products table as UNKNOWN."""
    if not product_ids:
        return
    # Fetch ALL existing product_ids without an IN filter — avoids the
    # 65535-parameter PostgreSQL limit when product_ids has thousands of entries.
    existing = {row.product_id for row in db.query(Product.product_id).all()}
    new_products = [
        Product(product_id=pid, product_name="UNKNOWN", category=None)
        for pid in set(product_ids)
        if pid not in existing
    ]
    if new_products:
        db.add_all(new_products)
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
        filename=file.filename or "unnamed",
        status="processing",
    )
    db.add(batch)
    db.flush()

    accepted, errors = validate_sales(df)

    if accepted:
        _ensure_products_exist(db, [r["product_id"] for r in accepted])
        for i in range(0, len(accepted), _INSERT_CHUNK):
            db.add_all(
                [
                    Sale(upload_batches_id=batch_id, **r)
                    for r in accepted[i : i + _INSERT_CHUNK]
                ]
            )
            db.flush()

    batch.rows_accepted = len(accepted)
    batch.rows_rejected = len(errors)
    batch.status = _status(len(accepted), len(errors))
    db.commit()

    return UploadResponse(
        upload_batches_id=batch_id,
        file_type="sales",
        filename=file.filename or "unnamed",
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
        filename=file.filename or "unnamed",
        status="processing",
    )
    db.add(batch)
    db.flush()

    accepted, errors = validate_inventory(df)

    if accepted:
        _ensure_products_exist(db, [r["product_id"] for r in accepted])
        for i in range(0, len(accepted), _INSERT_CHUNK):
            db.add_all(
                [
                    InventorySnapshot(upload_batches_id=batch_id, **r)
                    for r in accepted[i : i + _INSERT_CHUNK]
                ]
            )
            db.flush()

    batch.rows_accepted = len(accepted)
    batch.rows_rejected = len(errors)
    batch.status = _status(len(accepted), len(errors))
    db.commit()

    return UploadResponse(
        upload_batches_id=batch_id,
        file_type="inventory",
        filename=file.filename or "unnamed",
        status=batch.status,
        rows_total=len(accepted) + len(errors),
        rows_accepted=len(accepted),
        rows_rejected=len(errors),
        errors=[UploadError(**e) for e in errors],
    )


@router.post("/products", response_model=UploadResponse)
async def upload_products(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """
    Load or refresh the product catalog (upsert).
    Existing products are updated; new ones are inserted.
    """
    df = await parse_upload(file, PRODUCTS_REQUIRED)

    batch_id = str(uuid.uuid4())
    batch = UploadBatch(
        upload_batches_id=batch_id,
        file_type="products",
        filename=file.filename or "unnamed",
        status="processing",
    )
    db.add(batch)
    db.flush()

    accepted, errors = validate_products(df)

    if accepted:
        stmt = pg_insert(Product).values(accepted)
        stmt = stmt.on_conflict_do_update(
            index_elements=["product_id"],
            set_={
                "product_name": stmt.excluded.product_name,
                "category": stmt.excluded.category,
                "cost_price": stmt.excluded.cost_price,
                "sell_price": stmt.excluded.sell_price,
                "updated_at": func.now(),  # onupdate= doesn't fire on pg_insert upserts
            },
        )
        db.execute(stmt)

    batch.rows_accepted = len(accepted)
    batch.rows_rejected = len(errors)
    batch.status = _status(len(accepted), len(errors))
    db.commit()

    return UploadResponse(
        upload_batches_id=batch_id,
        file_type="products",
        filename=file.filename or "unnamed",
        status=batch.status,
        rows_total=len(accepted) + len(errors),
        rows_accepted=len(accepted),
        rows_rejected=len(errors),
        errors=[UploadError(**e) for e in errors],
    )
