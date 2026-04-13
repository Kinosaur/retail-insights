from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.product import ProductDetail, ProductListResponse
from app.services.products import get_product_by_id, get_products

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
def list_products(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ProductListResponse:
    return get_products(db, page=page, limit=limit, category=category)


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
) -> ProductDetail:
    result = get_product_by_id(db, product_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail={"code": "PRODUCT_NOT_FOUND", "message": f"No product with id '{product_id}'"},
        )
    return result
