from datetime import date

from pydantic import BaseModel


class Period(BaseModel):
    start: date
    end: date


class OverviewResponse(BaseModel):
    period: Period
    total_revenue: float
    total_units_sold: int
    unique_products_sold: int
    average_order_value: float


class TopProductItem(BaseModel):
    product_id: str
    product_name: str
    value: float


class TopProductsResponse(BaseModel):
    by: str
    items: list[TopProductItem]


class ABCItem(BaseModel):
    product_id: str
    product_name: str
    abc_class: str          # "A" | "B" | "C"  (avoids Python reserved word 'class')
    revenue: float
    cumulative_pct: float


class ABCSummary(BaseModel):
    A_count: int
    B_count: int
    C_count: int


class ABCResponse(BaseModel):
    summary: ABCSummary
    items: list[ABCItem]


class DeadStockItem(BaseModel):
    product_id: str
    product_name: str
    days_since_last_sale: int | None    # None = product never sold
    quantity_on_hand: int
    tied_up_capital: float | None       # None = cost_price missing


class DeadStockResponse(BaseModel):
    threshold_days: int
    items: list[DeadStockItem]


class ReorderItem(BaseModel):
    product_id: str
    product_name: str
    quantity_on_hand: int
    reorder_point: int
    recommended_order_qty: int


class ReorderResponse(BaseModel):
    lead_time_days: int
    safety_stock_days: int
    items: list[ReorderItem]


class ForecastWeek(BaseModel):
    week_start: date
    predicted_units: int


class ForecastResponse(BaseModel):
    product_id: str
    product_name: str
    weeks_forecast: int
    forecast: list[ForecastWeek]
    method: str
    disclaimer: str
