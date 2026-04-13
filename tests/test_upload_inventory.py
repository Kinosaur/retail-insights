"""
Tests for POST /upload/inventory

Covers: happy path, missing columns, invalid date, missing quantity.
"""
from tests.conftest import make_upload

PRODUCT_CSV = "product_id,product_name\nABC-001,Blue T-Shirt\nABC-002,Black Jeans\n"

VALID_CSV = """\
product_id,quantity_on_hand,snapshot_date
ABC-001,50,2023-12-31
ABC-002,20,2023-12-31
"""


def _seed_products(client):
    client.post("/upload/products", files=make_upload(PRODUCT_CSV))


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------
def test_upload_inventory_happy_path(client):
    _seed_products(client)
    resp = client.post("/upload/inventory", files=make_upload(VALID_CSV))
    assert resp.status_code == 200
    body = resp.json()
    assert body["file_type"] == "inventory"
    assert body["status"] == "success"
    assert body["rows_accepted"] == 2
    assert body["rows_rejected"] == 0


# ---------------------------------------------------------------------------
# File-level errors (400)
# ---------------------------------------------------------------------------
def test_upload_inventory_missing_required_column(client):
    csv = "product_id,quantity_on_hand\nABC-001,50\n"  # missing snapshot_date
    resp = client.post("/upload/inventory", files=make_upload(csv))
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "MISSING_COLUMNS"


# ---------------------------------------------------------------------------
# Row-level validation
# ---------------------------------------------------------------------------
def test_upload_inventory_invalid_date_rejected(client):
    csv = "product_id,quantity_on_hand,snapshot_date\nABC-001,50,not-a-date\n"
    resp = client.post("/upload/inventory", files=make_upload(csv))
    body = resp.json()
    assert body["rows_rejected"] == 1
    assert "date" in body["errors"][0]["reason"]


def test_upload_inventory_missing_quantity_rejected(client):
    csv = "product_id,quantity_on_hand,snapshot_date\nABC-001,,2023-12-31\n"
    resp = client.post("/upload/inventory", files=make_upload(csv))
    body = resp.json()
    assert body["rows_rejected"] == 1
