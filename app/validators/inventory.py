import pandas as pd


def validate_inventory(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """
    Validate every row in an inventory DataFrame.
    Returns (accepted_rows, error_rows).
    accepted_rows are dicts ready to be passed to InventorySnapshot(**row).
    error_rows follow the UploadError shape: {row, product_id, reason}.
    """
    accepted: list[dict] = []
    errors: list[dict] = []

    for i, row in df.iterrows():
        row_num = int(i) + 2  # +1 for 0-index, +1 for header row

        # 1. product_id — strip, uppercase, reject INVALID-* pattern
        #    pandas stores empty cells as float NaN; str(NaN) == "nan" which is truthy.
        raw_id_val = row.get("product_id", "")
        raw_id = "" if pd.isna(raw_id_val) else str(raw_id_val).strip()
        product_id = raw_id.upper()
        if not product_id or product_id.startswith("INVALID-"):
            errors.append({"row": row_num, "product_id": product_id or None, "reason": "missing or invalid product ID"})
            continue

        # 2. quantity_on_hand — must be integer >= 0
        try:
            qty = int(row["quantity_on_hand"])
        except (ValueError, TypeError):
            errors.append({"row": row_num, "product_id": product_id, "reason": "quantity_on_hand must be an integer"})
            continue
        if qty < 0:
            errors.append({"row": row_num, "product_id": product_id, "reason": "quantity_on_hand cannot be negative"})
            continue

        # 3. snapshot_date — must parse as valid date
        try:
            parsed = pd.to_datetime(row["snapshot_date"])
            if pd.isna(parsed):
                raise ValueError("empty date")
            snapshot_date = parsed.date()
        except (ValueError, TypeError, OverflowError):
            errors.append({"row": row_num, "product_id": product_id, "reason": "invalid date format"})
            continue

        accepted.append({
            "product_id": product_id,
            "quantity_on_hand": qty,
            "snapshot_date": snapshot_date,
        })

    return accepted, errors
