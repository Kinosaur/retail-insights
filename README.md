# Retail Insights Engine

> A backend that turns messy retail spreadsheets into actionable insights for small clothing shops.

---

## The Problem

Small clothing shops typically manage inventory and sales in spreadsheets. They have no easy way to know which products drive most of their revenue, which items are sitting dead on shelves, or when to reorder stock before running out. This project automates those answers.

---

## Status

**Day 5 of 20 — Ingestion pipeline complete, analytics in progress.**

| Days | What | Status |
|------|------|--------|
| 1–2 | Setup, schema, API contract | ✅ Done |
| 3–5 | Upload pipeline, validation, GET endpoints, tests | ✅ Done |
| 6–9 | Core analytics endpoints | 🔨 Next |
| 10–12 | Reorder + forecast | ⏳ Upcoming |
| 13–15 | AI explanation layer | ⏳ Upcoming |
| 16–20 | Polish, README, demo | ⏳ Upcoming |

**Current data loaded (Singapore Uniqlo 2023):**
- 801 products
- 50,220 accepted sales rows
- 9,118 inventory snapshots across 12 months

---

## Quickstart

**Prerequisites:** Python 3.11+, PostgreSQL installed locally (for tests only).

The main database runs on [Neon](https://neon.tech) (cloud PostgreSQL, Singapore region) — no local DB setup needed for the app.

```bash
git clone https://github.com/Kinosaur/retail-insights.git
cd retail-insights

cp .env.example .env       # fill in the Neon password (get from Person A)

make install               # create venv + install dependencies
make run                   # start API server on :8000 — data already in Neon
```

API docs: `http://localhost:8000/docs`

---

## Teammate Setup (Friend B)

Same as Quickstart above — 3 commands total. Database lives on Neon so data is already there.

You own the analytics endpoints — everything in `app/routers/analytics.py`, `app/services/analytics.py`, and related schemas.

**You will never need to:**
- Edit the database schema or write migrations (Person A owns this)
- Edit any CSV files or run the generator
- Seed the database (already loaded on Neon)
- Run `alembic upgrade head` (Person A applies migrations to Neon)

**Staying in sync with Person A:**

| Person A does | You do |
|---------------|--------|
| Pushes code changes | `git pull` → restart server |
| Pushes a schema change | `git pull` → restart server (migration already on Neon) |
| Uploads new data to Neon | `git pull` → restart server (data already in Neon) |

Everything syncs through Neon automatically — no local DB management needed.

---

## Architecture

```
retail-insights/
├── app/
│   ├── models/        # SQLAlchemy ORM models (5 tables)
│   ├── schemas/       # Pydantic v2 request/response schemas
│   ├── routers/       # FastAPI route handlers
│   ├── services/      # Business logic
│   ├── parsers/       # CSV / Excel file parsers
│   ├── validators/    # Row-level data cleaning pipeline
│   ├── db.py          # Database session + connection
│   └── main.py        # FastAPI app entry point
├── alembic/           # Database migrations
├── generator/         # Synthetic dataset generator
├── scripts/           # seed.py — loads data via API
├── docs/              # Schema, API contract, blueprint
├── tests/             # pytest test suite (34 tests)
└── data/raw/          # Source CSVs (do not edit directly)
```

---

## API Overview

| Method | Endpoint | Owner | Description |
|--------|----------|-------|-------------|
| POST | `/upload/products` | Person A | Upload product catalog CSV |
| POST | `/upload/sales` | Person A | Upload sales CSV |
| POST | `/upload/inventory` | Person A | Upload inventory CSV |
| GET | `/products` | Person A | Paginated product list with category filter |
| GET | `/products/{product_id}` | Person A | Single product + full sales history |
| GET | `/upload-batches` | Person A | All past uploads with status |
| GET | `/analytics/overview` | Person B | Revenue totals, AOV, units sold |
| GET | `/analytics/top-products` | Person B | Top sellers by revenue / units / margin |
| GET | `/analytics/abc` | Person B | ABC product classification |
| GET | `/analytics/dead-stock` | Person B | Items with no sales in N days |
| GET | `/analytics/reorder` | Person B | Items below reorder point |
| GET | `/analytics/forecast` | Person B | Moving-average forecast for one SKU |
| GET | `/analytics/explain` | Person B | LLM plain-language summary |
| GET | `/health` | — | Health check |

Full contract: [`docs/api.md`](./docs/api.md)

---

## Data Pipeline

Every upload runs through a validation pipeline before touching the database:

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
| Unknown SKU in sales | Auto-create product as UNKNOWN |
| Whitespace in product ID | Trim |
| Lowercase product ID | Normalise to uppercase |

Every upload returns a full validation report with row-level error details.

---

## Dataset

Synthetic 2023 data modelled on Singapore Uniqlo (801 real SKUs). Sales are generated with realistic seasonality: Chinese New Year spike, Hari Raya, National Day, Deepavali, 11.11 campaign, AIRism year-round, year-end sale. ~5% of rows contain intentional dirty data to exercise the validation pipeline.

Raw files are in `data/raw/`. See `data/raw/README.md` — **do not edit directly**.  
To regenerate: `python generator/generate_dataset.py`

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.13 |
| Framework | FastAPI |
| Validation | Pydantic v2 |
| Data processing | Pandas |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| LLM | Anthropic Claude API |
| Testing | pytest |
| Linting | ruff |

---

## Running Tests

```bash
make test
```

34 tests covering all upload endpoints and GET endpoints — happy paths, bad file types, missing columns, invalid dates, NaN prices, duplicates, pagination, 404s, and edge cases.

Tests run against a separate `retail_insights_test` database and are fully isolated (each test gets a clean slate).

---

## Makefile Reference

```bash
make install    # create venv + install dependencies
make db-create  # prints DB creation commands
make migrate    # run Alembic migrations
make run        # start API server on :8000
make seed       # upload all CSVs into database
make reseed     # instructions to wipe + reload data
make test       # run all 34 tests
make lint       # ruff linter + format check
```

---

## Limitations & Honest Caveats

*(Full section to be written on Day 18)*

- SMA forecast is a baseline only — not production forecasting
- Lead time and safety stock are configurable defaults, not real supplier data
- No authentication or multi-tenancy
- Synthetic dataset — results reflect simulated patterns, not a real shop

---

## What We'd Build Next

*(To be filled after MVP)*

---

## Team

- **Person A** — Data & Ingestion: database schema, migrations, file parsers, validation pipeline, upload endpoints, tests
- **Person B** — Analytics & AI: analytics functions, LLM integration, forecasting, caching
