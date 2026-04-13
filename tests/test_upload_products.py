"""
Tests for POST /upload/products

Covers: happy path, missing columns, bad file type, missing product_id,
missing product_name, duplicate product_id in same file, upsert behaviour.
"""
from tests.conftest import make_upload


VALID_CSV = """\
product_id,product_name,category,cost_price,sell_price
ABC-001,Blue T-Shirt,Tops,5.00,14.90
ABC-002,Black Jeans,Bottoms,12.00,39.90
ABC-003,White Hoodie,Outerwear,18.00,59.90
"""


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------
def test_upload_products_happy_path(client):
    resp = client.post("/upload/products", files=make_upload(VALID_CSV))
    assert resp.status_code == 200
    body = resp.json()
    assert body["file_type"] == "products"
    assert body["status"] == "success"
    assert body["rows_accepted"] == 3
    assert body["rows_rejected"] == 0
    assert body["errors"] == []


# ---------------------------------------------------------------------------
# File-level errors (400)
# ---------------------------------------------------------------------------
def test_upload_products_invalid_file_type(client):
    resp = client.post(
        "/upload/products",
        files={"file": ("catalog.txt", b"some data", "text/plain")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_FILE_TYPE"


def test_upload_products_missing_required_column(client):
    csv = "product_id,category\nABC-001,Tops\n"
    resp = client.post("/upload/products", files=make_upload(csv))
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "MISSING_COLUMNS"


def test_upload_products_empty_file(client):
    resp = client.post("/upload/products", files=make_upload("product_id,product_name\n"))
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "EMPTY_FILE"


# ---------------------------------------------------------------------------
# Row-level validation
# ---------------------------------------------------------------------------
def test_upload_products_missing_product_id_rejected(client):
    csv = "product_id,product_name\n,Blue T-Shirt\nABC-002,Black Jeans\n"
    resp = client.post("/upload/products", files=make_upload(csv))
    body = resp.json()
    assert body["rows_accepted"] == 1
    assert body["rows_rejected"] == 1
    assert body["errors"][0]["reason"] == "missing product ID"


def test_upload_products_missing_product_name_rejected(client):
    csv = "product_id,product_name\nABC-001,\nABC-002,Black Jeans\n"
    resp = client.post("/upload/products", files=make_upload(csv))
    body = resp.json()
    assert body["rows_accepted"] == 1
    assert body["rows_rejected"] == 1
    assert body["errors"][0]["reason"] == "missing product name"


def test_upload_products_duplicate_id_in_file_deduped(client):
    """Same product_id twice in one file — first row wins, second silently dropped."""
    csv = (
        "product_id,product_name\n"
        "ABC-001,First Name\n"
        "ABC-001,Second Name\n"
    )
    resp = client.post("/upload/products", files=make_upload(csv))
    body = resp.json()
    # Only 1 accepted — duplicate is silently dropped (not an error row)
    assert body["rows_accepted"] == 1
    assert body["rows_rejected"] == 0


# ---------------------------------------------------------------------------
# Upsert: re-uploading the catalog updates existing rows
# ---------------------------------------------------------------------------
def test_upload_products_upsert_updates_existing(client):
    # First upload
    csv_v1 = "product_id,product_name,sell_price\nABC-001,Original Name,14.90\n"
    client.post("/upload/products", files=make_upload(csv_v1))

    # Second upload with updated name and price
    csv_v2 = "product_id,product_name,sell_price\nABC-001,Updated Name,19.90\n"
    resp = client.post("/upload/products", files=make_upload(csv_v2))
    assert resp.status_code == 200
    assert resp.json()["rows_accepted"] == 1

    # Verify the update was applied via GET /products
    product = client.get("/products/ABC-001").json()
    assert product["product_name"] == "Updated Name"
    assert product["sell_price"] == 19.90
