# Database Schema — Retail Insights Engine

> Single source of truth. Both Person A and Person B must agree before changing anything here.
> Database: PostgreSQL

---

## Table: `products`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `product_id` | TEXT | PRIMARY KEY | e.g. `E483466-000` — always uppercase |
| `product_name` | TEXT | NOT NULL | Product display name |
| `category` | TEXT | nullable, **indexed** | e.g. `Women`, `Men`, `Unisex` |
| `cost_price` | REAL | nullable | From `uniqlo_sg_products.csv` |
| `sell_price` | REAL | nullable | From `uniqlo_sg_products.csv` |
| `created_at` | DATETIME | server default now | Auto-set |
| `updated_at` | DATETIME | server default now, on update now | Auto-set |

---

## Table: `upload_batches`

> Created the moment a file is uploaded. Every sales/inventory row references this.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `upload_batches_id` | TEXT | PRIMARY KEY | UUID4, generated at upload time |
| `file_type` | TEXT | NOT NULL | `"sales"` or `"inventory"` |
| `filename` | TEXT | nullable | Original uploaded filename |
| `status` | TEXT | NOT NULL, default `"pending"` | `pending` → `success` / `partial` / `failed` |
| `rows_accepted` | INTEGER | default 0 | Rows that passed validation |
| `rows_rejected` | INTEGER | default 0 | Rows that failed validation |
| `created_at` | DATETIME | server default now | Auto-set |

---

## Table: `sales`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `sale_id` | INTEGER | PRIMARY KEY autoincrement | |
| `upload_batches_id` | TEXT | FK → `upload_batches.upload_batches_id`, indexed | Which upload this row came from |
| `product_id` | TEXT | FK → `products.product_id`, indexed | Auto-created if product unknown |
| `sale_date` | DATE | NOT NULL, indexed | Format: `YYYY-MM-DD` |
| `quantity` | INTEGER | NOT NULL | Negative = return |
| `unit_price` | REAL | NOT NULL | Must be > 0 |
| `revenue` | REAL | NOT NULL | Stored = quantity × unit_price. Required for analytics. |
| `is_return` | INTEGER | default 0 | `1` if quantity < 0 |

---

## Table: `inventory_snapshots`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `inventory_snapshots_id` | INTEGER | PRIMARY KEY autoincrement | |
| `upload_batches_id` | TEXT | FK → `upload_batches.upload_batches_id`, indexed | Which upload this row came from |
| `product_id` | TEXT | FK → `products.product_id`, indexed | Auto-created if product unknown |
| `quantity_on_hand` | INTEGER | NOT NULL | Must be >= 0 |
| `snapshot_date` | DATE | NOT NULL, indexed | Format: `YYYY-MM-DD` |

---

## Table: `analysis_runs`

> Owned by Person B. Defined here so the schema is in one place.
> Caching: before calling the LLM, compute `cache_key = hash(metrics_json)`. If a row with that key exists and `status = "done"`, return it. Don't call the LLM again.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `analysis_runs_id` | TEXT | PRIMARY KEY | UUID4 |
| `run_type` | TEXT | NOT NULL | `"abc"`, `"forecast"`, `"dead_stock"`, `"summary"` |
| `cache_key` | TEXT | nullable, **indexed** | Hash of `metrics_json` — used to skip duplicate LLM calls |
| `metrics_json` | TEXT | nullable | JSON of all analytics data fed into the LLM |
| `ai_summary_text` | TEXT | nullable | Plain-English LLM response (the 3-section summary) |
| `status` | TEXT | NOT NULL, default `"pending"` | `pending` → `done` / `failed` |
| `created_at` | DATETIME | server default now | Auto-set |

---

## Validation Rules (enforced by Person A's pipeline)

### Sales rows
- `product_id` — strip whitespace, uppercase; reject if matches `INVALID-*` pattern
- `sale_date` — must parse as valid date; reject if future date
- `quantity` — must be non-zero integer; flag negative as return (`is_return=1`)
- `unit_price` — must be > 0 float; reject if zero or negative
- `revenue` — computed and stored as `quantity × unit_price`
- Duplicates — exact duplicate rows (same product_id + date + qty + price) are silently deduplicated

### Inventory rows
- `product_id` — strip whitespace, uppercase; reject if matches `INVALID-*` pattern
- `quantity_on_hand` — must be >= 0 integer; reject negatives
- `snapshot_date` — must parse as valid date

### Both
- If `product_id` not found in `products` table → auto-insert with `product_name="UNKNOWN"`, nulls for prices
- Each rejected row is recorded with row number + reason in the upload response

---

## Upload Response Shape (Person B depends on `upload_batches_id`)

```json
{
  "upload_batches_id": "uuid4-string",
  "file_type": "sales",
  "filename": "sales.csv",
  "status": "partial",
  "rows_accepted": 54880,
  "rows_rejected": 13,
  "errors": [
    { "row": 30, "product_id": "INVALID-E483002-000", "reason": "invalid product ID format" },
    { "row": 7,  "product_id": "E461325-000",         "reason": "negative quantity flagged as return" }
  ]
}
```

> `upload_batches_id` is the key Person B uses to scope all analytics queries.
