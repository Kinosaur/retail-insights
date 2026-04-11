# Database Schema — Retail Insights Engine

> Single source of truth. Both Person A and Person B must agree before changing anything here.
> Database: SQLite (dev) → PostgreSQL (prod if needed)

---

## Table: `products`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `sku` | TEXT | PRIMARY KEY | e.g. `E483466-000` — always uppercase |
| `name` | TEXT | NOT NULL | Product display name |
| `category` | TEXT | nullable | e.g. `Women`, `Men`, `Unisex` |
| `cost_price` | REAL | nullable | From `uniqlo_sg_products.csv` |
| `sell_price` | REAL | nullable | From `uniqlo_sg_products.csv` |

---

## Table: `upload_batches`

> Created the moment a file is uploaded. Every sales/inventory row references this.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | TEXT | PRIMARY KEY | UUID4, generated at upload time |
| `file_type` | TEXT | NOT NULL | `"sales"` or `"inventory"` |
| `filename` | TEXT | nullable | Original uploaded filename |
| `status` | TEXT | NOT NULL, default `"pending"` | `pending` → `done` or `failed` |
| `rows_accepted` | INTEGER | default 0 | Rows that passed validation |
| `rows_rejected` | INTEGER | default 0 | Rows that failed validation |
| `created_at` | DATETIME | server default now | Auto-set |

---

## Table: `sales`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY autoincrement | |
| `batch_id` | TEXT | FK → `upload_batches.id`, indexed | Which upload this row came from |
| `sku` | TEXT | FK → `products.sku`, indexed | Auto-created if SKU unknown |
| `sale_date` | DATE | NOT NULL, indexed | Format: `YYYY-MM-DD` |
| `quantity` | INTEGER | NOT NULL | Negative = return |
| `unit_price` | REAL | NOT NULL | Must be > 0 |
| `is_return` | INTEGER | default 0 | `1` if quantity < 0 |

---

## Table: `inventory_snapshots`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY autoincrement | |
| `batch_id` | TEXT | FK → `upload_batches.id`, indexed | Which upload this row came from |
| `sku` | TEXT | FK → `products.sku`, indexed | Auto-created if SKU unknown |
| `quantity_on_hand` | INTEGER | NOT NULL | Must be >= 0 |
| `snapshot_date` | DATE | NOT NULL, indexed | Format: `YYYY-MM-DD` |

---

## Table: `analysis_runs`

> Owned by Person B. Defined here so migrations stay in one place.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | TEXT | PRIMARY KEY | UUID4 |
| `run_type` | TEXT | NOT NULL | `"abc"`, `"forecast"`, `"dead_stock"`, `"summary"` |
| `parameters` | TEXT | nullable | JSON string of input parameters |
| `result` | TEXT | nullable | JSON string of output / LLM response |
| `status` | TEXT | NOT NULL, default `"pending"` | `pending` → `done` or `failed` |
| `created_at` | DATETIME | server default now | Auto-set |

---

## Validation Rules (enforced by Person A's pipeline)

### Sales rows
- `sku` — strip whitespace, uppercase; reject if matches `INVALID-*` pattern
- `sale_date` — must parse as valid date; reject if future date
- `quantity` — must be non-zero integer; flag negative as return (`is_return=1`)
- `unit_price` — must be > 0 float; reject if zero or negative
- Duplicates — exact duplicate rows (same sku + date + qty + price) are silently deduplicated

### Inventory rows
- `sku` — strip whitespace, uppercase; reject if matches `INVALID-*` pattern
- `quantity_on_hand` — must be >= 0 integer; reject negatives
- `snapshot_date` — must parse as valid date

### Both
- If `sku` not found in `products` table → auto-insert with `name="UNKNOWN"`, nulls for prices
- Each rejected row is recorded with row number + reason in the upload response

---

## Upload Response Shape (Person B depends on `batch_id`)

```json
{
  "batch_id": "uuid4-string",
  "file_type": "sales",
  "filename": "sales.csv",
  "rows_accepted": 54880,
  "rows_rejected": 13,
  "errors": [
    { "row": 30, "sku": "INVALID-E483002-000", "reason": "invalid SKU format" },
    { "row": 7,  "sku": "E461325-000",         "reason": "negative quantity flagged as return" }
  ]
}
```

> `batch_id` is the key Person B uses to scope all analytics queries.
