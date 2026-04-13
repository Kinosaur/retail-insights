import math
from datetime import date

from pydantic import BaseModel, field_validator


class ProductItem(BaseModel):
    product_id: str
    product_name: str
    category: str | None
    cost_price: float | None
    sell_price: float | None


class SaleHistoryItem(BaseModel):
    sale_date: date
    quantity: int
    revenue: float

    @field_validator("revenue", mode="before")
    @classmethod
    def coerce_nan(cls, v: object) -> float:
        """PostgreSQL can store NaN as a float; Python's JSON encoder rejects it."""
        if isinstance(v, float) and math.isnan(v):
            return 0.0
        return v


class ProductDetail(ProductItem):
    sales_history: list[SaleHistoryItem]


class ProductListResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: list[ProductItem]
