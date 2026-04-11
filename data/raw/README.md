# /data/raw — Sample Dataset

These are the raw source files used for development and testing.

| File | Description | Rows |
|---|---|---|
| `uniqlo_sg_products.csv` | Product catalogue — 801 SKUs with name, category, cost and sell price | 801 |
| `sales.csv` | Sales transactions Jan–Dec 2023 | ~54,893 |
| `inventory.csv` | Weekly inventory snapshots Jan–Dec 2023 | ~9,612 |

---

⚠️ **DO NOT EDIT THESE FILES DIRECTLY.**

- These are the original source files. The parser + validator in `app/parsers/` and `app/validators/` reads from these.
- If you need to test with modified data, make a copy with a different filename.
- If you find data quality issues, raise them in a PR comment — do not fix them by hand here.

---

To load this data into the database, use the upload endpoints once the server is running:

```bash
# Start the server
uvicorn app.main:app --reload

# Upload products (done once)
curl -X POST http://localhost:8000/upload/sales \
  -F "file=@data/raw/sales.csv"

curl -X POST http://localhost:8000/upload/inventory \
  -F "file=@data/raw/inventory.csv"
```
