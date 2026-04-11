# API Contract — Retail Insights Engine

> This document must be agreed upon by Person A and Person B before writing any endpoint code.
> Last updated: Day 2

---

## General Rules

- All responses are JSON
- All errors follow this shape:
```json
{ "error": { "code": "ERROR_CODE", "message": "human readable", "details": {} } }
```
- Dates always in `YYYY-MM-DD` format
- All endpoints return HTTP 200 on success unless noted

---

## Person A Endpoints (Data & Ingestion)

### `POST /upload/sales`
Upload a sales CSV or Excel file.

**Request:** `multipart/form-data`
| Field | Type | Required |
|---|---|---|
| `file` | file | ✅ |

**Response `200`:**
```json
{
  "upload_batches_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_type": "sales",
  "filename": "sales_jan2023.csv",
  "status": "partial",
  "rows_total": 1500,
  "rows_accepted": 1487,
  "rows_rejected": 13,
  "errors": [
    { "row": 47, "sku_id": null, "reason": "missing SKU" },
    { "row": 103, "sku_id": "E461325-000", "reason": "negative quantity flagged as return" }
  ]
}
```

**Error codes:**
| Code | HTTP | Meaning |
|---|---|---|
| `INVALID_FILE_TYPE` | 400 | File is not CSV or Excel |
| `EMPTY_FILE` | 400 | File has no rows |
| `MISSING_COLUMNS` | 400 | Required columns not found |

---

### `POST /upload/inventory`
Upload an inventory snapshot CSV or Excel file.

**Request:** `multipart/form-data`
| Field | Type | Required |
|---|---|---|
| `file` | file | ✅ |

**Response `200`:** Same shape as `/upload/sales` with `"file_type": "inventory"`

---

### `GET /products`
Paginated list of all products.

**Query params:**
| Param | Default | Notes |
|---|---|---|
| `page` | 1 | |
| `limit` | 50 | Max 200 |
| `category` | — | Filter by category |

**Response `200`:**
```json
{
  "total": 801,
  "page": 1,
  "limit": 50,
  "items": [
    {
      "sku_id": "E483466-000",
      "sku_name": "Linen V Neck T",
      "category": "Women",
      "cost_price": 15.96,
      "sell_price": 39.90
    }
  ]
}
```

---

### `GET /products/{sku_id}`
Single product detail with sales history.

**Response `200`:**
```json
{
  "sku_id": "E483466-000",
  "sku_name": "Linen V Neck T",
  "category": "Women",
  "cost_price": 15.96,
  "sell_price": 39.90,
  "sales_history": [
    { "sale_date": "2023-01-01", "quantity": 2, "revenue": 79.80 }
  ]
}
```

**Error codes:**
| Code | HTTP | Meaning |
|---|---|---|
| `PRODUCT_NOT_FOUND` | 404 | sku_id does not exist |

---

### `GET /upload-batches`
List of all past upload batches.

**Response `200`:**
```json
{
  "items": [
    {
      "upload_batches_id": "550e8400-e29b-41d4-a716-446655440000",
      "file_type": "sales",
      "filename": "sales_jan2023.csv",
      "status": "success",
      "rows_accepted": 1487,
      "rows_rejected": 13,
      "created_at": "2023-01-01T10:00:00"
    }
  ]
}
```

---

## Person B Endpoints (Analytics & AI)

> Person B owns these. Shapes agreed here, implementation is Person B's.

### `GET /analytics/overview`
**Query params:** `start` (date), `end` (date)

**Response `200`:**
```json
{
  "period": { "start": "2023-01-01", "end": "2023-12-31" },
  "total_revenue": 125430.50,
  "total_units_sold": 8921,
  "unique_skus_sold": 412,
  "average_order_value": 14.06
}
```

---

### `GET /analytics/top-products`
**Query params:** `limit` (default 10), `by` (`revenue` | `units` | `margin`)

**Response `200`:**
```json
{
  "by": "revenue",
  "items": [
    { "sku_id": "E483466-000", "sku_name": "Linen V Neck T", "value": 4280.70 }
  ]
}
```

---

### `GET /analytics/abc`
**Response `200`:**
```json
{
  "summary": { "A_count": 82, "B_count": 120, "C_count": 599 },
  "items": [
    {
      "sku_id": "E483466-000",
      "sku_name": "Linen V Neck T",
      "class": "A",
      "revenue": 4280.70,
      "cumulative_pct": 12.3
    }
  ]
}
```

---

### `GET /analytics/dead-stock`
**Query params:** `days` (default 90)

**Response `200`:**
```json
{
  "threshold_days": 90,
  "items": [
    {
      "sku_id": "E483466-000",
      "sku_name": "Linen V Neck T",
      "days_since_last_sale": 120,
      "quantity_on_hand": 45,
      "tied_up_capital": 718.20
    }
  ]
}
```

---

### `GET /analytics/reorder`
**Query params:** `lead_time_days` (default 7), `safety_stock_days` (default 3)

**Response `200`:**
```json
{
  "lead_time_days": 7,
  "safety_stock_days": 3,
  "items": [
    {
      "sku_id": "E483466-000",
      "sku_name": "Linen V Neck T",
      "quantity_on_hand": 5,
      "reorder_point": 18,
      "recommended_order_qty": 55
    }
  ]
}
```

---

### `GET /analytics/forecast`
**Query params:** `sku_id` (required), `weeks` (default 4)

**Response `200`:**
```json
{
  "sku_id": "E483466-000",
  "sku_name": "Linen V Neck T",
  "weeks_forecast": 4,
  "forecast": [
    { "week_start": "2024-01-01", "predicted_units": 12 },
    { "week_start": "2024-01-08", "predicted_units": 11 }
  ],
  "method": "simple_moving_average",
  "disclaimer": "SMA baseline only. Does not account for seasonality or trends."
}
```

---

### `GET /analytics/explain`
Calls LLM with full analytics output. Result cached in `analysis_runs` table.

**Response `200`:**
```json
{
  "analysis_runs_id": "uuid4-string",
  "cached": false,
  "summary": {
    "whats_working": "...",
    "needs_attention": "...",
    "action_this_week": "..."
  },
  "generated_at": "2023-12-01T10:00:00"
}
```

---

### `GET /health`
**Response `200`:** `{ "status": "ok" }`

---

## Shared Rules

- `upload_batches_id` is always a UUID4 string — Person B uses this to scope analytics queries
- Auto-created SKUs (unknown at upload time) get `category = "uncategorized"`, `sku_name = sku_id`
- Status values for `upload_batches`: `pending` | `success` | `partial` | `failed`
- `partial` = some rows accepted, some rejected
- `success` = all rows accepted
- `failed` = zero rows accepted (file was completely invalid)
