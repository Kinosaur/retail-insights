from datetime import date, timedelta

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.models.inventory import InventorySnapshot
from app.models.product import Product
from app.models.sale import Sale


def _data_reference_date(db: Session) -> date:
    """
    Use the latest sale date in the dataset as the reference point for relative
    calculations (dead-stock age, reorder lookback).  This keeps the analytics
    meaningful for historical datasets that don't extend to today.
    """
    result = db.execute(select(func.max(Sale.sale_date))).scalar()
    return result or date.today()


def _latest_inventory_sq():
    """Subquery: most-recent quantity_on_hand per product."""
    max_date_sq = (
        select(
            InventorySnapshot.product_id,
            func.max(InventorySnapshot.snapshot_date).label("max_date"),
        )
        .group_by(InventorySnapshot.product_id)
        .subquery()
    )
    return (
        select(
            InventorySnapshot.product_id,
            InventorySnapshot.quantity_on_hand,
        )
        .join(
            max_date_sq,
            (InventorySnapshot.product_id == max_date_sq.c.product_id)
            & (InventorySnapshot.snapshot_date == max_date_sq.c.max_date),
        )
        .subquery()
    )


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

def get_overview(db: Session, start: date, end: date) -> dict:
    row = db.execute(
        select(
            func.coalesce(func.sum(Sale.revenue), 0.0).label("total_revenue"),
            func.coalesce(func.sum(Sale.quantity), 0).label("total_units"),
            func.coalesce(func.count(Sale.sale_id), 0).label("total_transactions"),
            func.coalesce(func.count(Sale.product_id.distinct()), 0).label("unique_products"),
        ).where(
            Sale.is_return == False,  # noqa: E712
            Sale.sale_date >= start,
            Sale.sale_date <= end,
        )
    ).one()

    total_revenue = float(row.total_revenue)
    total_units = int(row.total_units)
    total_transactions = int(row.total_transactions)
    unique_products = int(row.unique_products)
    aov = round(total_revenue / total_transactions, 2) if total_transactions > 0 else 0.0

    return {
        "period": {"start": start, "end": end},
        "total_revenue": round(total_revenue, 2),
        "total_units_sold": total_units,
        "unique_products_sold": unique_products,
        "average_order_value": aov,
    }


# ---------------------------------------------------------------------------
# Top products
# ---------------------------------------------------------------------------

def get_top_products(db: Session, limit: int, by: str) -> dict:
    if by == "units":
        value_expr = func.sum(Sale.quantity)
    elif by == "margin":
        value_expr = func.sum((Product.sell_price - Product.cost_price) * Sale.quantity)
    else:
        value_expr = func.sum(Sale.revenue)

    filters = [Sale.is_return == False, Product.product_name != "UNKNOWN"]  # noqa: E712
    if by == "margin":
        filters += [Product.cost_price.is_not(None), Product.sell_price.is_not(None)]

    rows = db.execute(
        select(
            Sale.product_id,
            Product.product_name,
            value_expr.label("value"),
        )
        .join(Product, Sale.product_id == Product.product_id)
        .where(*filters)
        .group_by(Sale.product_id, Product.product_name)
        .order_by(value_expr.desc())
        .limit(limit)
    ).all()

    return {
        "by": by,
        "items": [
            {
                "product_id": r.product_id,
                "product_name": r.product_name,
                "value": round(float(r.value or 0.0), 2),
            }
            for r in rows
        ],
    }


# ---------------------------------------------------------------------------
# ABC classification
# ---------------------------------------------------------------------------

def get_abc(db: Session) -> dict:
    rows = db.execute(
        select(
            Sale.product_id,
            Product.product_name,
            func.sum(Sale.revenue).label("revenue"),
        )
        .join(Product, Sale.product_id == Product.product_id)
        .where(Sale.is_return == False, Product.product_name != "UNKNOWN")  # noqa: E712
        .group_by(Sale.product_id, Product.product_name)
        .order_by(func.sum(Sale.revenue).desc())
    ).all()

    total = float(sum(r.revenue for r in rows)) or 1.0  # guard zero-data case

    cumulative = 0.0
    items = []
    for r in rows:
        cumulative += float(r.revenue)
        pct = round(cumulative / total * 100, 1)
        abc_class = "A" if pct <= 80.0 else ("B" if pct <= 95.0 else "C")
        items.append({
            "product_id": r.product_id,
            "product_name": r.product_name,
            "abc_class": abc_class,
            "revenue": round(float(r.revenue), 2),
            "cumulative_pct": pct,
        })

    summary = {
        "A_count": sum(1 for i in items if i["abc_class"] == "A"),
        "B_count": sum(1 for i in items if i["abc_class"] == "B"),
        "C_count": sum(1 for i in items if i["abc_class"] == "C"),
    }
    return {"summary": summary, "items": items}


# ---------------------------------------------------------------------------
# Dead stock
# ---------------------------------------------------------------------------

def get_dead_stock(db: Session, days: int) -> dict:
    ref_date = _data_reference_date(db)
    cutoff = ref_date - timedelta(days=days)
    inv_sq = _latest_inventory_sq()

    last_sale_sq = (
        select(
            Sale.product_id,
            func.max(Sale.sale_date).label("last_sale_date"),
        )
        .where(Sale.is_return == False)  # noqa: E712
        .group_by(Sale.product_id)
        .subquery()
    )

    rows = db.execute(
        select(
            Product.product_id,
            Product.product_name,
            Product.cost_price,
            last_sale_sq.c.last_sale_date,
            inv_sq.c.quantity_on_hand,
        )
        .join(inv_sq, Product.product_id == inv_sq.c.product_id)
        .join(last_sale_sq, Product.product_id == last_sale_sq.c.product_id, isouter=True)
        .where(
            Product.product_name != "UNKNOWN",
            inv_sq.c.quantity_on_hand > 0,
            (last_sale_sq.c.last_sale_date < cutoff)
            | (last_sale_sq.c.last_sale_date.is_(None)),
        )
        .order_by(last_sale_sq.c.last_sale_date.asc().nullsfirst())
    ).all()

    items = []
    for r in rows:
        qty = r.quantity_on_hand
        days_since = (ref_date - r.last_sale_date).days if r.last_sale_date else None
        capital = round(qty * r.cost_price, 2) if r.cost_price else None
        items.append({
            "product_id": r.product_id,
            "product_name": r.product_name,
            "days_since_last_sale": days_since,
            "quantity_on_hand": qty,
            "tied_up_capital": capital,
        })

    return {"threshold_days": days, "items": items}


# ---------------------------------------------------------------------------
# Reorder alerts
# ---------------------------------------------------------------------------

def get_reorder(db: Session, lead_time_days: int, safety_stock_days: int) -> dict:
    ref_date = _data_reference_date(db)
    lookback_start = ref_date - timedelta(days=90)
    inv_sq = _latest_inventory_sq()

    # Daily sales rate over the 90 days before the reference date
    daily_rate_sq = (
        select(
            Sale.product_id,
            (func.sum(Sale.quantity) / 90.0).label("daily_rate"),
        )
        .where(
            Sale.is_return == False,  # noqa: E712
            Sale.sale_date >= lookback_start,
            Sale.sale_date <= ref_date,
        )
        .group_by(Sale.product_id)
        .subquery()
    )

    reorder_days = lead_time_days + safety_stock_days

    rows = db.execute(
        select(
            Product.product_id,
            Product.product_name,
            inv_sq.c.quantity_on_hand,
            daily_rate_sq.c.daily_rate,
        )
        .join(inv_sq, Product.product_id == inv_sq.c.product_id)
        .join(daily_rate_sq, Product.product_id == daily_rate_sq.c.product_id)
        .where(
            Product.product_name != "UNKNOWN",
            inv_sq.c.quantity_on_hand < daily_rate_sq.c.daily_rate * reorder_days,
        )
        .order_by(inv_sq.c.quantity_on_hand.asc())
    ).all()

    items = []
    for r in rows:
        daily_rate = float(r.daily_rate)
        reorder_point = max(1, int(daily_rate * reorder_days))
        # Recommend stock to cover 30 days of projected demand
        recommended = max(0, int(daily_rate * 30) - r.quantity_on_hand)
        items.append({
            "product_id": r.product_id,
            "product_name": r.product_name,
            "quantity_on_hand": r.quantity_on_hand,
            "reorder_point": reorder_point,
            "recommended_order_qty": recommended,
        })

    return {"lead_time_days": lead_time_days, "safety_stock_days": safety_stock_days, "items": items}


# ---------------------------------------------------------------------------
# Forecast (Simple Moving Average)
# ---------------------------------------------------------------------------

_SMA_WINDOW = 8  # number of historical weeks used to compute the average
_DISCLAIMER = "SMA baseline only. Does not account for seasonality or trends."


def get_forecast(db: Session, product_id: str, weeks: int) -> dict | None:
    pid = product_id.upper()

    product = db.execute(
        select(Product).where(Product.product_id == pid)
    ).scalar_one_or_none()
    if not product:
        return None

    # Weekly sales totals — date_trunc gives the Monday of each ISO week
    week_expr = cast(func.date_trunc("week", Sale.sale_date), Date)
    rows = db.execute(
        select(
            week_expr.label("week_start"),
            func.sum(Sale.quantity).label("units"),
        )
        .where(Sale.product_id == pid, Sale.is_return == False)  # noqa: E712
        .group_by(week_expr)
        .order_by(week_expr)
    ).all()

    if not rows:
        return {
            "product_id": product.product_id,
            "product_name": product.product_name,
            "weeks_forecast": weeks,
            "forecast": [],
            "method": "simple_moving_average",
            "disclaimer": "No sales history found for this product — forecast unavailable.",
        }

    # SMA over the last _SMA_WINDOW weeks (or fewer if not enough history)
    window = rows[-_SMA_WINDOW:]
    avg_units = sum(int(r.units) for r in window) / len(window)
    predicted = max(0, round(avg_units))

    # Project forward from the last recorded week
    last_week: date = rows[-1].week_start
    forecast = [
        {
            "week_start": last_week + timedelta(weeks=i),
            "predicted_units": predicted,
        }
        for i in range(1, weeks + 1)
    ]

    return {
        "product_id": product.product_id,
        "product_name": product.product_name,
        "weeks_forecast": weeks,
        "forecast": forecast,
        "method": "simple_moving_average",
        "disclaimer": _DISCLAIMER,
    }
