# Retail Insights Engine

> A backend that turns messy retail spreadsheets into actionable insights for small clothing shops.

---

## The Problem

Small clothing shops typically manage inventory and sales in spreadsheets. They have no easy way to know which products drive most of their revenue, which items are sitting dead on shelves, or when to reorder stock before running out. This project automates those answers.

## Status

🚧 **In development** — Day 1-2 of a 20-day build.

---

## Quickstart

**Prerequisites:** PostgreSQL must be running locally with a database named `retail_insights`.

```bash
git clone https://github.com/Kinosaur/retail-insights.git
cd retail-insights

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and fill in your DATABASE_URL

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

API docs available at: `http://localhost:8000/docs`

---

## Architecture

```
retail-insights/
├── app/
│   ├── models/       # SQLAlchemy ORM models (5 tables)
│   ├── schemas/      # Pydantic v2 validation schemas
│   ├── routers/      # FastAPI route handlers
│   ├── services/     # Business logic
│   ├── parsers/      # CSV / Excel file parsers
│   ├── validators/   # Data cleaning pipeline
│   ├── db.py         # Database session + connection setup
│   └── main.py       # FastAPI app entry point
├── alembic/          # Database migrations
├── docs/             # Schema, API contract, blueprint
├── tests/            # pytest test suite
└── data/raw/         # Sample dataset (do not edit)
```

---

## API Overview

| Method | Endpoint | Owner | Description |
|---|---|---|---|
| POST | `/upload/sales` | Person A | Upload a sales CSV/Excel file |
| POST | `/upload/inventory` | Person A | Upload an inventory CSV/Excel file |
| GET | `/products` | Person A | Paginated product list |
| GET | `/products/{product_id}` | Person A | Single product + sales history |
| GET | `/upload-batches` | Person A | List of past uploads with status |
| GET | `/analytics/overview` | Person B | Revenue totals, AOV, units sold |
| GET | `/analytics/top-products` | Person B | Top sellers by revenue/units/margin |
| GET | `/analytics/abc` | Person B | ABC product classification |
| GET | `/analytics/dead-stock` | Person B | Items with no sales in N days |
| GET | `/analytics/reorder` | Person B | Items below reorder point |
| GET | `/analytics/forecast` | Person B | SMA forecast for one SKU |
| GET | `/analytics/explain` | Person B | LLM-generated plain-language summary |
| GET | `/health` | — | Health check |

Full contract: see [`docs/api.md`](./docs/api.md)

---

## Dataset

Uses Uniqlo Singapore product data (801 SKUs) with sales and inventory history across 2023.
Raw files are in `data/raw/`. See `data/raw/README.md` — do not edit directly.

---

## Tech Stack

| Layer | Choice |
|---|---|
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
source .venv/bin/activate
pytest
```

---

## Limitations & Honest Caveats

*(To be written on Day 18)*

- SMA forecast is a baseline only — not production forecasting
- Lead time and safety stock are configurable defaults, not real supplier data
- No authentication or multi-tenancy

---

## What We'd Build Next

*(To be filled after MVP)*

---

## Team

- **Person A** (Data & Ingestion) — database schema, file parsers, validation pipeline, upload endpoints
- **Person B** (Analytics & AI) — analytics functions, LLM integration, forecasting
