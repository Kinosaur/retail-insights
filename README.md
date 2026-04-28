# Retail Insights Engine

> A backend API that turns messy retail spreadsheets into actionable business insights — with an AI layer that explains what to do next.

---

## What It Does

Small clothing shops track sales and inventory in spreadsheets but have no easy way to act on that data. This project automates the most common retail intelligence questions:

- Which products drive most of the revenue?
- What is sitting dead on shelves?
- What needs to be reordered before it runs out?
- What should the shop owner actually do this week?

Upload your CSVs, hit the API, get answers. The last endpoint (`/analytics/explain`) calls an LLM and returns a plain-English summary any non-technical person can read.

---

## Quickstart

**You will need:**
- Python 3.13 — [python.org](https://python.org)
- A PostgreSQL database — free Neon cloud account at [neon.tech](https://neon.tech) (recommended, no local install needed), or a local PostgreSQL instance
- A free Groq API key — [console.groq.com](https://console.groq.com) (for the AI explanation endpoint)

### 1 — Clone and install

**Mac / Linux**
```bash
git clone https://github.com/Kinosaur/retail-insights.git
cd retail-insights
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows**
```bat
git clone https://github.com/Kinosaur/retail-insights.git
cd retail-insights
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2 — Configure environment

```bash
cp .env.example .env      # Mac / Linux
copy .env.example .env    # Windows
```

Open `.env` and fill in two values:

```
DATABASE_URL=postgresql+psycopg://your_user:your_password@your_host/your_db
GROQ_API_KEY=gsk_your_key_here
```

If using Neon: copy the **pooler connection string** from your Neon dashboard and paste it as `DATABASE_URL`. Make sure it starts with `postgresql+psycopg://`.

### 3 — Create the database tables

```bash
alembic upgrade head
```

### 4 — Start the server

**Mac / Linux**
```bash
uvicorn app.main:app --reload
```

**Windows**
```bat
python -m uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 5 — Load the sample data

In a second terminal (with the server still running):

**Mac / Linux**
```bash
source .venv/bin/activate
python scripts/seed.py
```

**Windows**
```bat
.venv\Scripts\activate
python scripts/seed.py
```

This uploads 801 products, ~155,000 sales rows, and 27,000 inventory snapshots. On a Neon free-tier database this takes around 5–10 minutes — let it run.

### 6 — Try it

Open `http://localhost:8000/docs` and try these endpoints:

| Endpoint | What to expect |
|----------|----------------|
| `GET /analytics/overview` | 2025 revenue summary |
| `GET /analytics/top-products` | Top 10 products by revenue |
| `GET /analytics/dead-stock` | Items with no sales in 90+ days |
| `GET /analytics/reorder` | Products running low on stock |
| `GET /analytics/explain` | Plain-English AI summary of everything above |

---

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload/products` | Upload product catalog CSV |
| `POST` | `/upload/sales` | Upload sales CSV — validated row by row |
| `POST` | `/upload/inventory` | Upload inventory CSV |
| `GET` | `/products` | Paginated product list with category filter |
| `GET` | `/products/{product_id}` | Single product with full sales history |
| `GET` | `/upload-batches` | All past uploads with status and row counts |
| `GET` | `/analytics/overview` | Total revenue, units sold, AOV for any date range |
| `GET` | `/analytics/top-products` | Top sellers ranked by revenue, units, or margin |
| `GET` | `/analytics/abc` | ABC classification — A (top 80% revenue), B, C |
| `GET` | `/analytics/dead-stock` | Products with inventory but no sales in N days |
| `GET` | `/analytics/reorder` | Products below reorder point based on sales velocity |
| `GET` | `/analytics/forecast` | 8-week moving average demand forecast for one SKU |
| `GET` | `/analytics/explain` | LLM plain-English summary with action recommendation |
| `GET` | `/health` | Health check |

Full contract: [`docs/api.md`](./docs/api.md)

---

## Data Pipeline

Every upload is validated row by row before anything is saved. The API returns a report of exactly which rows were accepted, rejected, and why.

| Issue | Rule |
|-------|------|
| Missing product ID | Reject row |
| Missing quantity | Reject row |
| Missing date | Reject row |
| Missing price (sales) | Reject row |
| Negative quantity | Accept — flagged as return |
| Duplicate row | Deduplicate silently |
| Wrong date format | Try common formats, then reject |
| Currency symbols (`$`, `S$`, `฿`) | Strip and parse |
| Unknown product ID in sales | Auto-create product as UNKNOWN |
| Whitespace in product ID | Trim |
| Lowercase product ID | Normalise to uppercase |

---

## Dataset

The sample data (`data/raw/`) is synthetic 2023–2025 data modelled on Singapore Uniqlo — 801 real product SKUs with realistic seasonality: Chinese New Year (date shifts each year), Hari Raya, National Day (Aug 9), Deepavali, 11.11 campaign, AIRism year-round, year-end sale. Year-over-year growth is baked in (+5% in 2024, +8% in 2025). About 5% of rows contain intentional dirty data to demonstrate the validation pipeline.

| Table | Rows | Description |
|-------|------|-------------|
| `products` | 801 | Product names, categories, cost and sell prices |
| `sales` | 155,090 | Accepted transactions across 3 years |
| `inventory_snapshots` | 27,403 | Monthly stock-on-hand across 36 months |

To regenerate the raw CSVs: `python generator/generate_dataset.py`

---

## Architecture

```
retail-insights/
├── app/
│   ├── models/        # SQLAlchemy ORM models (5 tables)
│   ├── schemas/       # Pydantic v2 request/response schemas
│   ├── routers/       # FastAPI route handlers
│   ├── services/      # Business logic and query layer
│   ├── parsers/       # CSV / Excel file parsers
│   ├── validators/    # Row-level data cleaning pipeline
│   ├── db.py          # Database session and connection
│   └── main.py        # FastAPI app entry point
├── alembic/           # Database migrations
├── generator/         # Synthetic dataset generator
├── scripts/           # seed.py — loads sample data via the API
├── docs/              # API contract, project overview, MVP scope
├── tests/             # pytest test suite (34 tests)
└── data/raw/          # Source CSVs — do not edit directly
```

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.13 |
| Framework | FastAPI |
| Validation | Pydantic v2 |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Database | PostgreSQL |
| Data processing | Pandas |
| LLM | Groq API — llama-3.3-70b-versatile (free tier) |
| Testing | pytest |

---

## Running Tests

Requires a local PostgreSQL instance. Tests run against a separate database and never touch your main database.

**1. Create the test database** (one time only):
```bash
createdb retail_insights_test
```

**2. Add `TEST_DATABASE_URL` to your `.env`:**
```
TEST_DATABASE_URL=postgresql+psycopg://postgres:yourpassword@localhost:5432/retail_insights_test
```

**3. Run:**
```bash
pytest
```

The test suite creates and drops all tables automatically. 34 tests covering upload endpoints, GET endpoints, validation edge cases, pagination, 404s, and duplicate handling.

---

## Limitations

- **SMA forecast is a baseline** — the 8-week moving average does not account for seasonality, trends, or promotions. Treat it as directional, not predictive.
- **Lead time and safety stock are defaults** — 14-day lead time and 7-day safety stock are reasonable starting points but should be adjusted to real supplier agreements via query params.
- **No transaction grouping** — each sales row is one line item. True basket-level AOV and "frequently bought together" analysis require adding a receipt/order ID to the schema.
- **No authentication** — any request to the server is accepted. Not suitable for production without adding auth.
- **Synthetic dataset** — results reflect simulated patterns, not a real shop's performance.

---

## What We'd Build Next

- **Frontend dashboard** — a UI so shop owners don't need to use Swagger
- **Better forecasting** — replace SMA with a model that handles seasonality (Prophet or exponential smoothing)
- **Transaction grouping** — add a receipt/order ID for basket analysis and true AOV
- **Authentication** — API keys or JWT for multi-tenant use
- **Year-over-year comparison** — `GET /analytics/overview?compare=true` for same-period last year
- **Reorder webhook** — push a notification when a product crosses its reorder point

---

## Team

- **Person A** — Data & Ingestion: database schema, migrations, file parsers, validation pipeline, upload endpoints, tests
- **Person B** — Analytics & AI: analytics service layer, forecasting, AI explanation, caching
