import io

import pandas as pd
from fastapi import HTTPException, UploadFile

SALES_REQUIRED = {"sku_id", "sale_date", "quantity", "unit_price"}
INVENTORY_REQUIRED = {"sku_id", "quantity_on_hand", "snapshot_date"}

# Columns that arrive with different names in the raw CSVs
_COLUMN_ALIASES = {
    "sku": "sku_id",       # uniqlo_sg_products.csv uses "sku"
    "name": "sku_name",    # uniqlo_sg_products.csv uses "name"
}

_ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower() for c in df.columns]
    return df.rename(columns=_COLUMN_ALIASES)


async def parse_upload(file: UploadFile, required_columns: set[str]) -> pd.DataFrame:
    filename = file.filename or ""
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": f"File must be .csv or .xlsx — got: '{ext or 'no extension'}'",
            },
        )

    contents = await file.read()

    try:
        if ext == ".csv":
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "UNREADABLE_FILE", "message": f"Could not read file: {exc}"},
        )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail={"code": "EMPTY_FILE", "message": "File has no data rows"},
        )

    df = _normalise_columns(df)

    missing = required_columns - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_COLUMNS",
                "message": f"Required columns not found: {sorted(missing)}",
            },
        )

    return df
