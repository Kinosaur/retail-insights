import pandas as pd


def validate_inventory(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """
    Validate every row in an inventory DataFrame.
    Returns (accepted_rows, error_rows).
    accepted_rows are dicts ready to be passed to InventorySnapshot(**row).
    error_rows follow the UploadError shape: {row, sku_id, reason}.
    """
    accepted: list[dict] = []
    errors: list[dict] = []

    for i, row in df.iterrows():
        row_num = int(i) + 2  # +1 for 0-index, +1 for header row

        # 1. sku_id — strip, uppercase, reject INVALID-* pattern
        raw_sku = str(row.get("sku_id", "")).strip()
        sku_id = raw_sku.upper()
        if not sku_id or sku_id.startswith("INVALID-"):
            errors.append({"row": row_num, "sku_id": sku_id or None, "reason": "missing or invalid SKU"})
            continue

        # 2. quantity_on_hand — must be integer >= 0
        try:
            qty = int(row["quantity_on_hand"])
        except (ValueError, TypeError):
            errors.append({"row": row_num, "sku_id": sku_id, "reason": "quantity_on_hand must be an integer"})
            continue
        if qty < 0:
            errors.append({"row": row_num, "sku_id": sku_id, "reason": "quantity_on_hand cannot be negative"})
            continue

        # 3. snapshot_date — must parse as valid date
        try:
            parsed = pd.to_datetime(row["snapshot_date"])
            if pd.isna(parsed):
                raise ValueError("empty date")
            snapshot_date = parsed.date()
        except Exception:
            errors.append({"row": row_num, "sku_id": sku_id, "reason": "invalid date format"})
            continue

        accepted.append({
            "sku_id": sku_id,
            "quantity_on_hand": qty,
            "snapshot_date": snapshot_date,
        })

    return accepted, errors
