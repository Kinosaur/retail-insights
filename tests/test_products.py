"""
Tests for GET /products and GET /products/{product_id}

Covers: empty DB, pagination, category filter, sales history, 404.
"""
from tests.conftest import make_upload

PRODUCT_CSV = """\
product_id,product_name,category,cost_price,sell_price
ABC-001,Blue T-Shirt,Tops,5.00,14.90
ABC-002,Black Jeans,Bottoms,12.00,39.90
ABC-003,White Hoodie,Tops,18.00,59.90
"""

SALES_CSV = """\
product_id,sale_date,quantity,unit_price
ABC-001,2023-01-15,2,14.90
ABC-001,2023-02-01,1,14.90
"""


def _seed_products(client):
    client.post("/upload/products", files=make_upload(PRODUCT_CSV))


def _seed_sales(client):
    client.post("/upload/sales", files=make_upload(SALES_CSV))


# ---------------------------------------------------------------------------
# GET /products
# ---------------------------------------------------------------------------
def test_list_products_empty_db(client):
    resp = client.get("/products")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_list_products_returns_all(client):
    _seed_products(client)
    resp = client.get("/products")
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


def test_list_products_pagination(client):
    _seed_products(client)
    resp = client.get("/products?page=1&limit=2")
    body = resp.json()
    assert body["total"] == 3   # total is always the full count
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["limit"] == 2


def test_list_products_category_filter(client):
    _seed_products(client)
    resp = client.get("/products?category=Tops")
    body = resp.json()
    assert body["total"] == 2
    assert all(item["category"] == "Tops" for item in body["items"])


def test_list_products_category_filter_no_match(client):
    _seed_products(client)
    resp = client.get("/products?category=DoesNotExist")
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


# ---------------------------------------------------------------------------
# GET /products/{product_id}
# ---------------------------------------------------------------------------
def test_get_product_returns_correct_fields(client):
    _seed_products(client)
    resp = client.get("/products/ABC-001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["product_id"] == "ABC-001"
    assert body["product_name"] == "Blue T-Shirt"
    assert body["category"] == "Tops"
    assert body["cost_price"] == 5.00
    assert body["sell_price"] == 14.90
    assert "sales_history" in body


def test_get_product_lowercase_id_normalised(client):
    """product_id lookup should be case-insensitive — service uppercases it."""
    _seed_products(client)
    resp = client.get("/products/abc-001")
    assert resp.status_code == 200
    assert resp.json()["product_id"] == "ABC-001"


def test_get_product_with_sales_history(client):
    _seed_products(client)
    _seed_sales(client)
    resp = client.get("/products/ABC-001")
    body = resp.json()
    assert len(body["sales_history"]) == 2
    # History is ordered by sale_date ascending
    assert body["sales_history"][0]["sale_date"] == "2023-01-15"
    assert body["sales_history"][0]["quantity"] == 2
    assert body["sales_history"][0]["revenue"] == 29.80


def test_get_product_no_sales_returns_empty_history(client):
    _seed_products(client)
    resp = client.get("/products/ABC-002")
    body = resp.json()
    assert body["sales_history"] == []


def test_get_product_not_found(client):
    resp = client.get("/products/DOESNOTEXIST")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "PRODUCT_NOT_FOUND"
