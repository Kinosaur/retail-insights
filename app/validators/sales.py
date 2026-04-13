import math
from datetime import date

import pandas as pd


def validate_sales(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """
    Validate every row in a sales DataFrame.
    Returns (accepted_rows, error_rows).
    accepted_rows are dicts ready to be passed to Sale(**row).
    error_rows follow the UploadError shape: {row, product_id, reason}.
    """
    accepted: list[dict] = []
    errors: list[dict] = []
    seen: set[tuple] = set()  # duplicate detection
    today = date.today()

    for i, row in df.iterrows():
        row_num = int(i) + 2  # +1 for 0-index, +1 for header row

        # 1. product_id — strip, uppercase, reject INVALID-* pattern
        raw_id = str(row.get("product_id", "")).strip()
        product_id = raw_id.upper()
        if not product_id or product_id.startswith("INVALID-"):
            errors.append({"row": row_num, "product_id": product_id or None, "reason": "missing or invalid product ID"})
            continue

        # 2. sale_date — must parse, must not be future
        try:
            parsed = pd.to_datetime(row["sale_date"])
            if pd.isna(parsed):
                raise ValueError("empty date")
            sale_date = parsed.date()
        except Exception:
            errors.append({"row": row_num, "product_id": product_id, "reason": "invalid date format"})
            continue
        if sale_date > today:
            errors.append({"row": row_num, "product_id": product_id, "reason": "future date not allowed"})
            continue

        # 3. quantity — non-zero integer
        try:
            quantity = int(row["quantity"])
        except (ValueError, TypeError):
            errors.append({"row": row_num, "product_id": product_id, "reason": "quantity must be an integer"})
            continue
        if quantity == 0:
            errors.append({"row": row_num, "product_id": product_id, "reason": "quantity cannot be zero"})
            continue

        # 4. unit_price — must be a real number > 0 (NaN passes <= 0 check, so guard explicitly)
        try:
            unit_price = float(row["unit_price"])
            if math.isnan(unit_price):
                raise ValueError("NaN")
        except (ValueError, TypeError):
            errors.append({"row": row_num, "product_id": product_id, "reason": "unit_price must be a number"})
            continue
        if unit_price <= 0:
            errors.append({"row": row_num, "product_id": product_id, "reason": "unit_price must be > 0"})
            continue

        # 5. duplicate — same product_id + date + qty + price → silently skip
        dedup_key = (product_id, sale_date, quantity, unit_price)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # 6. compute revenue, flag returns
        accepted.append({
            "product_id": product_id,
            "sale_date": sale_date,
            "quantity": quantity,
            "unit_price": unit_price,
            "revenue": round(quantity * unit_price, 4),
            "is_return": 1 if quantity < 0 else 0,
        })

    return accepted, errors
