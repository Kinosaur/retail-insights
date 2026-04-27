from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.analytics import (
    ABCResponse,
    DeadStockResponse,
    ForecastResponse,
    OverviewResponse,
    ReorderResponse,
    TopProductsResponse,
)
from app.services.analytics import (
    get_abc,
    get_dead_stock,
    get_forecast,
    get_overview,
    get_reorder,
    get_top_products,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewResponse)
def overview(
    start: date = Query(default=date(2025, 1, 1), description="Start date (inclusive)"),
    end: date = Query(default=date(2025, 12, 31), description="End date (inclusive)"),
    db: Session = Depends(get_db),
) -> OverviewResponse:
    if start > end:
        raise HTTPException(status_code=400, detail="start must not be after end")
    return get_overview(db, start, end)


@router.get("/top-products", response_model=TopProductsResponse)
def top_products(
    limit: int = Query(default=10, ge=1, le=100),
    by: str = Query(default="revenue", pattern="^(revenue|units|margin)$"),
    db: Session = Depends(get_db),
) -> TopProductsResponse:
    return get_top_products(db, limit, by)


@router.get("/abc", response_model=ABCResponse)
def abc(db: Session = Depends(get_db)) -> ABCResponse:
    return get_abc(db)


@router.get("/dead-stock", response_model=DeadStockResponse)
def dead_stock(
    days: int = Query(default=90, ge=1, description="Flag products with no sales in this many days"),
    db: Session = Depends(get_db),
) -> DeadStockResponse:
    return get_dead_stock(db, days)


@router.get("/reorder", response_model=ReorderResponse)
def reorder(
    lead_time_days: int = Query(default=14, ge=1, description="Days from order to delivery"),
    safety_stock_days: int = Query(default=7, ge=0, description="Extra buffer days of stock"),
    db: Session = Depends(get_db),
) -> ReorderResponse:
    return get_reorder(db, lead_time_days, safety_stock_days)


@router.get("/forecast", response_model=ForecastResponse)
def forecast(
    product_id: str = Query(..., description="Product ID to forecast (e.g. E483831-000)"),
    weeks: int = Query(default=4, ge=1, le=12, description="Number of weeks to project forward"),
    db: Session = Depends(get_db),
) -> ForecastResponse:
    result = get_forecast(db, product_id, weeks)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "PRODUCT_NOT_FOUND", "message": f"No product with id '{product_id}'"},
        )
    return result
