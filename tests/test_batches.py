"""
Tests for GET /upload-batches

Covers: empty list, correct shape, newest-first ordering.
"""
from tests.conftest import make_upload

PRODUCT_CSV = "product_id,product_name\nABC-001,Blue T-Shirt\n"
SALES_CSV = "product_id,sale_date,quantity,unit_price\nABC-001,2023-01-15,1,14.90\n"


# ---------------------------------------------------------------------------
# GET /upload-batches
# ---------------------------------------------------------------------------
def test_list_batches_empty(client):
    resp = client.get("/upload-batches")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_list_batches_returns_correct_shape(client):
    client.post("/upload/products", files=make_upload(PRODUCT_CSV))
    resp = client.get("/upload-batches")
    body = resp.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert "upload_batches_id" in item
    assert item["file_type"] == "products"
    assert item["filename"] == "test.csv"
    assert item["status"] == "success"
    assert item["rows_accepted"] == 1
    assert item["rows_rejected"] == 0


def test_list_batches_ordered_newest_first(client):
    """Upload products then sales — batches must come back in reverse order."""
    client.post("/upload/products", files=make_upload(PRODUCT_CSV))
    client.post("/upload/sales", files=make_upload(SALES_CSV))

    resp = client.get("/upload-batches")
    items = resp.json()["items"]
    assert len(items) == 2
    # Newest upload (sales) should be first
    assert items[0]["file_type"] == "sales"
    assert items[1]["file_type"] == "products"
