# Project Overview — Retail Insights Engine

## What Is This?

The Retail Insights Engine is a backend API that helps small clothing shops understand their business through data. A shop owner uploads their sales and inventory spreadsheets, and the system answers the questions they would otherwise have to do manually in Excel: What is selling? What is sitting dead on shelves? What needs to be reordered before it runs out?

The project also includes an AI layer (powered by Claude) that turns raw numbers into plain-English summaries a shop owner can actually act on.

---

## The Problem It Solves

Small clothing retailers in Singapore typically manage their business with spreadsheets. They face three recurring problems:

1. **No visibility into performance** — They cannot easily tell which products are driving most of their revenue and which are dead weight.
2. **Inventory blind spots** — They discover stockouts only when a customer asks for something that is not there, and they discover overstocks only when they are stuck with unsold items at the end of a season.
3. **Manual and slow** — Generating any insight requires hours of manual work in Excel, so it rarely gets done.

This project automates all of that through a clean API.

---

## Who It Is For

**Primary user:** A small clothing shop owner or operations manager who already collects sales and inventory data in spreadsheets (CSV or Excel) and wants actionable insights without hiring a data analyst.

**Context:** The project is built and demonstrated using synthetic 2023 data modelled on Uniqlo Singapore — 801 real product SKUs, realistic Singapore retail seasonality (Chinese New Year, Hari Raya, National Day, Deepavali, 11.11, year-end sale), and ~50,000 sales transactions.

---

## How It Works

```
Shop owner uploads CSV/Excel files
         ↓
Validation pipeline (row-level cleaning and error reporting)
         ↓
Data stored in PostgreSQL (hosted on Neon cloud, Singapore region)
         ↓
Analytics API answers business questions
         ↓
AI layer (Claude) produces plain-English summaries
```

Every upload goes through a strict validation pipeline before any data is saved. The system tells the user exactly which rows were rejected and why — missing product ID, invalid date, zero quantity, and so on. This means dirty real-world data is handled gracefully rather than silently corrupted.

---

## What The API Can Do

### Data Ingestion (Person A)
| Endpoint | What It Does |
|----------|--------------|
| `POST /upload/products` | Upload a product catalog CSV — new products are inserted, existing ones are updated |
| `POST /upload/sales` | Upload a sales file — validated row by row, returns an error report |
| `POST /upload/inventory` | Upload inventory snapshots — tracks stock levels over time |
| `GET /products` | Browse the full product catalog with category filtering and pagination |
| `GET /products/{id}` | View a single product and its complete sales history |
| `GET /upload-batches` | View all past uploads and their status |

### Analytics (Person B)
| Endpoint | What It Answers |
|----------|-----------------|
| `GET /analytics/overview` | What was total revenue, units sold, and average order value for a period? |
| `GET /analytics/top-products` | What are the top-selling products by revenue, units, or profit margin? |
| `GET /analytics/abc` | Which products are A-class (top 80% of revenue), B-class, or C-class? |
| `GET /analytics/dead-stock` | Which products have not sold recently but still have inventory? |
| `GET /analytics/reorder` | Which products are running low and need to be ordered now? |
| `GET /analytics/forecast` | What is the projected weekly demand for a specific product? |
| `GET /analytics/explain` | Plain-English AI summary of all the above |

---

## Team

| Person | Role | Owns |
|--------|------|------|
| Person A | Data & Ingestion | Database schema, migrations, upload pipeline, validation, ingestion endpoints, tests |
| Person B | Analytics & AI | Analytics endpoints, forecasting, AI explanation layer, caching |

Both engineers connect to the same shared Neon cloud database. Person A manages all schema changes and data loading. Person B reads data only.

---

## Technology

| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python 3.13.0 | Modern async support, strong data ecosystem |
| Framework | FastAPI | Fast, auto-generates interactive API docs |
| Validation | Pydantic v2 | Strict type enforcement on request and response shapes |
| ORM | SQLAlchemy 2.0 | Full control over queries, works well with PostgreSQL |
| Migrations | Alembic | Tracks every schema change with rollback support |
| Database | PostgreSQL (Neon) | Reliable, cloud-hosted, free tier, Singapore region |
| Data processing | Pandas | CSV/Excel parsing and row-level validation |
| AI | Anthropic Claude API | Plain-English summaries of analytics output |
| Testing | pytest | 34 tests covering all upload and GET endpoints |

---

## Data

The system is demonstrated with synthetic 2023 data built to resemble a real Uniqlo Singapore store:

| Table | Rows | Description |
|-------|------|-------------|
| `products` | 801 | Real Uniqlo SG product names and SKUs, with cost and sell prices |
| `sales` | 50,220 | Accepted sales transactions across all of 2023 |
| `inventory_snapshots` | 9,118 | Monthly stock-on-hand snapshots across 12 months |
| `upload_batches` | — | Audit log of every file upload |
| `analysis_runs` | — | Cache for AI-generated summaries |

The dataset includes ~5% intentionally dirty rows (missing IDs, invalid dates, zero quantities) to exercise and demonstrate the validation pipeline.

Seasonality modelled: Chinese New Year (Jan–Feb spike), Hari Raya (Apr), National Day (Aug), Deepavali (Nov), 11.11 campaign (Nov), year-end sale (Dec). AIRism products sell year-round due to Singapore's climate.

---

## Database Design

Five tables, all managed by Alembic migrations:

```
products          ← master catalog, upserted on each upload
sales             ← one row per line item, linked to products and upload_batches
inventory_snapshots ← one row per product per snapshot date
upload_batches    ← audit log of every upload (status, filename, row counts)
analysis_runs     ← cache table for LLM-generated summaries
```

All timestamps are stored in UTC with timezone awareness (`TIMESTAMPTZ`). Sales `is_return` is a boolean column — negative quantities are flagged as returns rather than rejected.

---

## Project Status

Day 9 of 20. Ingestion pipeline and analytics endpoints are complete. Forecasting and AI layer are next.

| Phase | Days | Status |
|-------|------|--------|
| Setup, schema, API contract | 1–2 | ✅ Done |
| Upload pipeline, validation, GET endpoints, tests | 3–5 | ✅ Done |
| Core analytics endpoints | 6–9 | ✅ Done |
| Reorder + forecast | 10–12 | 🔨 Next |
| AI explanation layer | 13–15 | ⏳ Upcoming |
| Polish, README, demo | 16–20 | ⏳ Upcoming |
