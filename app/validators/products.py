import pandas as pd


def validate_products(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """
    Validate every row in a products catalog DataFrame.
    Returns (accepted_rows, error_rows).
    accepted_rows are dicts ready for pg_insert(Product).values(...).
    """
    accepted: list[dict] = []
    errors: list[dict] = []
    seen: set[str] = set()

    for i, row in df.iterrows():
        row_num = int(i) + 2

        # 1. product_id — required, strip, uppercase
        #    pandas stores empty cells as float NaN; str(NaN) == "nan" which is truthy,
        #    so we must check pd.isna() before stringifying.
        raw_id_val = row.get("product_id", "")
        raw_id = "" if pd.isna(raw_id_val) else str(raw_id_val).strip()
        product_id = raw_id.upper()
        if not product_id:
            errors.append({"row": row_num, "product_id": None, "reason": "missing product ID"})
            continue

        # 2. product_name — required
        raw_name_val = row.get("product_name", "")
        product_name = "" if pd.isna(raw_name_val) else str(raw_name_val).strip()
        if not product_name:
            errors.append({"row": row_num, "product_id": product_id, "reason": "missing product name"})
            continue

        # 3. duplicate product_id in same file → keep first
        if product_id in seen:
            continue
        seen.add(product_id)

        # 4. optional fields — None if blank/missing
        def _float_or_none(val) -> float | None:
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        accepted.append({
            "product_id": product_id,
            "product_name": product_name,
            "category": str(row.get("category", "")).strip() or None,
            "cost_price": _float_or_none(row.get("cost_price")),
            "sell_price": _float_or_none(row.get("sell_price")),
        })

    return accepted, errors
