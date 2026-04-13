"""
Tests for POST /upload/sales

Covers: happy path, missing columns, bad file type, missing product_id,
invalid date, future date, NaN unit_price, duplicate rows, returns flagged.
"""
from tests.conftest import make_upload

# Pre-seed a product so FK constraint is satisfied for happy-path tests
PRODUCT_CSV = "product_id,product_name\nABC-001,Blue T-Shirt\nABC-002,Black Jeans\n"

VALID_CSV = """\
product_id,sale_date,quantity,unit_price
ABC-001,2023-01-15,2,14.90
ABC-002,2023-01-16,1,39.90
ABC-001,2023-02-01,3,14.90
"""


def _seed_products(client):
    client.post("/upload/products", files=make_upload(PRODUCT_CSV))


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------
def test_upload_sales_happy_path(client):
    _seed_products(client)
    resp = client.post("/upload/sales", files=make_upload(VALID_CSV))
    assert resp.status_code == 200
    body = resp.json()
    assert body["file_type"] == "sales"
    assert body["status"] == "success"
    assert body["rows_accepted"] == 3
    assert body["rows_rejected"] == 0


# ---------------------------------------------------------------------------
# File-level errors (400)
# ---------------------------------------------------------------------------
def test_upload_sales_invalid_file_type(client):
    resp = client.post(
        "/upload/sales",
        files={"file": ("sales.json", b"{}", "application/json")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_FILE_TYPE"


def test_upload_sales_missing_required_column(client):
    csv = "product_id,sale_date,quantity\nABC-001,2023-01-15,2\n"  # missing unit_price
    resp = client.post("/upload/sales", files=make_upload(csv))
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "MISSING_COLUMNS"


# ---------------------------------------------------------------------------
# Row-level validation
# ---------------------------------------------------------------------------
def test_upload_sales_missing_product_id_rejected(client):
    csv = "product_id,sale_date,quantity,unit_price\n,2023-01-15,2,14.90\nABC-001,2023-01-16,1,14.90\n"
    resp = client.post("/upload/sales", files=make_upload(csv))
    body = resp.json()
    assert body["rows_accepted"] == 1
    assert body["rows_rejected"] == 1
    assert "product ID" in body["errors"][0]["reason"]


def test_upload_sales_invalid_date_rejected(client):
    csv = "product_id,sale_date,quantity,unit_price\nABC-001,not-a-date,2,14.90\n"
    resp = client.post("/upload/sales", files=make_upload(csv))
    body = resp.json()
    assert body["rows_accepted"] == 0
    assert body["rows_rejected"] == 1
    assert "date" in body["errors"][0]["reason"]


def test_upload_sales_future_date_rejected(client):
    csv = "product_id,sale_date,quantity,unit_price\nABC-001,2099-12-31,2,14.90\n"
    resp = client.post("/upload/sales", files=make_upload(csv))
    body = resp.json()
    assert body["rows_rejected"] == 1
    assert "future" in body["errors"][0]["reason"]


def test_upload_sales_nan_unit_price_rejected(client):
    """NaN unit_price must be rejected — not silently stored in the DB."""
    csv = "product_id,sale_date,quantity,unit_price\nABC-001,2023-01-15,2,\n"
    resp = client.post("/upload/sales", files=make_upload(csv))
    body = resp.json()
    assert body["rows_rejected"] == 1
    assert "unit_price" in body["errors"][0]["reason"]


def test_upload_sales_duplicate_row_deduplicated(client):
    """Exact duplicate (same product_id + date + qty + price) appears once in DB."""
    csv = (
        "product_id,sale_date,quantity,unit_price\n"
        "ABC-001,2023-01-15,2,14.90\n"
        "ABC-001,2023-01-15,2,14.90\n"  # exact duplicate
    )
    resp = client.post("/upload/sales", files=make_upload(csv))
    body = resp.json()
    assert body["rows_accepted"] == 1
    assert body["rows_rejected"] == 0


def test_upload_sales_negative_quantity_is_return(client):
    """Negative quantity is accepted and flagged as a return (is_return=1)."""
    _seed_products(client)
    csv = "product_id,sale_date,quantity,unit_price\nABC-001,2023-01-15,-1,14.90\n"
    resp = client.post("/upload/sales", files=make_upload(csv))
    body = resp.json()
    assert body["rows_accepted"] == 1
    assert body["rows_rejected"] == 0
