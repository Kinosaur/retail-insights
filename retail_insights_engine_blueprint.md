# Retail Insights Engine — Detailed Blueprint

A 20-day, 2-person backend project that turns messy retail spreadsheets into clear business insights for a small clothing shop.

---

## 1. Project Goals (be honest about these)

**Primary goal:** Ship a finished, demoable backend in 20 days that an interviewer can run locally and understand in 5 minutes.

**Secondary goal:** Solve a real problem for at least one real shop. If you can find a friend/family clothing business and use their actual (anonymized) data, this project goes from "good" to "memorable."

**What this project proves to interviewers:**
- You can design a clean REST API
- You can model a relational database
- You can validate and clean messy real-world data
- You can implement non-trivial business logic (ABC, reorder points, dead stock)
- You can integrate an LLM in a way that adds real value
- You can scope, plan, and finish a project with a teammate

**What this project is NOT:**
- A production system. Don't pretend it is.
- A real forecasting engine. Moving averages on small-shop data are baselines, not predictions. Say so in the README.
- A replacement for a POS system or ERP.

---

## 2. Tech Stack (locked in)

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Pandas, ecosystem |
| API framework | FastAPI | Auto docs, Pydantic, async-ready |
| Validation | Pydantic v2 | Tight coupling with FastAPI |
| Data processing | Pandas | Standard for tabular work |
| Database | PostgreSQL (via Docker) OR SQLite | Start with SQLite for week 1, migrate to Postgres in week 3 if time allows |
| ORM | SQLAlchemy 2.0 | Industry standard |
| Migrations | Alembic | Shows maturity |
| LLM | Anthropic Claude API or OpenAI | Either works; Claude is cheaper for this volume |
| Testing | pytest | Non-negotiable, see Section 9 |
| Linting | ruff + black | Fast, zero-config |
| Env management | uv or poetry | Pick one on day 1 |

**Explicitly out of scope:** Docker Compose for the whole app, Kafka, Redis, Celery, WebSockets, OCR, auth/users, multi-tenancy, frontend framework. If you finish early, a tiny Streamlit dashboard is acceptable — nothing more.

---

## 3. Database Schema

Five tables. Keep it boring.

**`products`**
- `id` (PK, int)
- `sku` (string, unique, indexed)
- `name` (string)
- `category` (string, indexed)
- `cost_price` (decimal)
- `sell_price` (decimal)
- `created_at`, `updated_at`

**`inventory_snapshots`**
- `id` (PK)
- `product_id` (FK → products)
- `quantity_on_hand` (int)
- `snapshot_date` (date, indexed)
- `upload_batch_id` (FK → upload_batches)

We use snapshots, not a single "current quantity" column, because real shops upload inventory weekly or monthly and you want history.

**`sales`**
- `id` (PK)
- `product_id` (FK → products)
- `sale_date` (date, indexed)
- `quantity` (int)
- `unit_price` (decimal) — price at time of sale, not current price
- `revenue` (decimal, computed and stored = quantity × unit_price)
- `upload_batch_id` (FK → upload_batches)

**`upload_batches`**
- `id` (PK)
- `filename` (string)
- `file_type` (enum: 'sales' | 'inventory')
- `uploaded_at` (timestamp)
- `row_count` (int)
- `error_count` (int)
- `status` (enum: 'pending' | 'success' | 'partial' | 'failed')

This table is gold for interview discussion — it shows you think about observability and idempotency.

**`analysis_runs`** (optional, week 3)
- `id` (PK)
- `run_at` (timestamp)
- `metrics_json` (jsonb) — cached results
- `ai_summary_text` (text)

Cache the LLM output. Calling it on every request is wasteful and slow.

---

## 4. API Contract (design this on Day 3, before coding endpoints)

All responses are JSON. All errors follow a consistent shape:
```json
{ "error": { "code": "INVALID_FILE", "message": "...", "details": {...} } }
```

**Upload endpoints**
- `POST /upload/sales` — multipart file upload, returns `upload_batch_id` and validation summary
- `POST /upload/inventory` — same shape

**Data endpoints** (for debugging and the demo)
- `GET /products` — paginated
- `GET /products/{sku}` — single product with sales history
- `GET /upload-batches` — list of past uploads with status

**Analytics endpoints**
- `GET /analytics/overview?start=&end=` — totals: revenue, units sold, # of SKUs sold, AOV
- `GET /analytics/top-products?limit=10&by=revenue` — top sellers
- `GET /analytics/abc` — A/B/C classification of all products
- `GET /analytics/dead-stock?days=90` — items with no sales in N days
- `GET /analytics/reorder` — items below reorder point
- `GET /analytics/forecast?sku=...&weeks=4` — moving-average forecast for one SKU
- `GET /analytics/explain` — calls the LLM, returns plain-language summary

**Health**
- `GET /health` — returns `{"status": "ok"}`

Write this contract as an OpenAPI spec on Day 3. FastAPI generates it for you, but draft the response shapes in a doc *first* so the two of you agree before writing code.

---

## 5. The Analytics Logic (this is the heart of the project)

### 5.1 Revenue overview
Trivial: `SUM(revenue)` grouped by date range. Also compute units sold, unique SKUs sold, average order value (revenue / number of sale rows).

### 5.2 Top products
`SUM(revenue) GROUP BY product_id ORDER BY revenue DESC LIMIT N`. Also expose `by=units` and `by=margin` (margin = revenue − quantity × cost_price).

### 5.3 ABC classification
Classic Pareto:
1. Sort all products by revenue descending
2. Compute cumulative revenue %
3. **A** = top 80% of revenue, **B** = next 15%, **C** = bottom 5%

Document the thresholds in the README. They're conventional but not universal.

### 5.4 Dead stock
A product is "dead" if it has had **zero sales in the last N days** (default 90) AND `quantity_on_hand > 0` in the latest inventory snapshot. Return SKU, days since last sale, units on hand, and tied-up capital (units × cost_price).

### 5.5 Reorder recommendations
This is where you'll want to think carefully. Simplest defensible version:

```
average_daily_demand = units_sold_last_30_days / 30
lead_time_days = 7  (configurable, default value)
safety_stock = average_daily_demand * 3  (3 days buffer)
reorder_point = (average_daily_demand * lead_time_days) + safety_stock

if quantity_on_hand <= reorder_point:
    flag for reorder
    recommended_order_qty = (average_daily_demand * 30) - quantity_on_hand
```

**Document every assumption.** Lead time and safety stock days should be configurable via query params or a config file. In the README, explicitly say: "These values are defaults; in a real deployment they'd be set per-product based on supplier data."

### 5.6 Forecast
Simple moving average (SMA) over last 4 weeks of weekly sales, projected forward N weeks. Return point estimates only — no confidence intervals, that would be misleading.

**In the README, write a one-paragraph honest disclaimer:** SMA is a baseline. It does not account for seasonality, promotions, or trends. For real forecasting you'd want at minimum a seasonal model (e.g., Holt-Winters) and ideally several months of clean history.

### 5.7 Margin & inventory health (bonus, week 3 if time)
- Gross margin per product
- Inventory turnover ratio: COGS / average inventory value
- Sell-through rate: units sold / units received

---

## 6. The AI Explanation Layer (the part that needs the most thought)

The risk: making this a wrapper around `f"Your top product is {x}"` that pretends to be AI. Don't do that.

**Make the LLM earn its place** by giving it the *full structured analytics output* and asking it to do things templates can't:

1. **Cross-metric pattern detection.** "Your top 5 products are all from one category — that's a concentration risk." "Three of your dead-stock items are from your highest-margin category, suggesting a marketing issue rather than a product problem."

2. **Prioritization.** "Of the 12 reorder flags, these 3 are highest priority because they're A-class items currently below safety stock."

3. **Plain-language framing.** Translate "ABC classification" into "your bestsellers vs. your slow movers" for a non-technical owner.

### Prompt structure
System prompt: define the role (retail analyst), the audience (non-technical small shop owner), the tone (concrete, no jargon, max 200 words), and the output format (3 sections: What's working / What needs attention / What to do this week).

User prompt: a JSON dump of all analytics outputs plus the date range.

**Cache the result** in the `analysis_runs` table keyed by a hash of the input JSON. Don't call the LLM on every request.

### Guardrails
- Never let the LLM invent numbers. If it cites a figure, that figure must appear in the input JSON.
- In the README, show the exact prompt you used — interviewers love this.
- Have a "fallback" mode that produces a templated summary if the LLM call fails. Demoability matters.

---

## 7. Data Cleaning Rules (write these down before coding)

Real spreadsheets are awful. Decide upfront how you handle each case:

| Issue | Rule |
|---|---|
| Missing SKU | Reject row, log to error report |
| Missing quantity | Reject row |
| Missing date | Reject row |
| Missing price | If sales file, reject. If inventory, allow. |
| Negative quantity | Allow (it's a return) — but flag it |
| Duplicate row (same SKU, date, qty, price) | Deduplicate silently |
| Date in wrong format | Try 5 common formats, then reject |
| Currency symbols in price (`$`, `฿`) | Strip and parse |
| New SKU not in products table | Auto-create with name = SKU, category = "uncategorized" |
| Whitespace in SKU | Trim |
| Case differences in SKU (`abc-1` vs `ABC-1`) | Normalize to uppercase |

Every upload returns a validation report:
```json
{
  "batch_id": 42,
  "rows_total": 1500,
  "rows_accepted": 1487,
  "rows_rejected": 13,
  "errors": [
    {"row": 47, "reason": "missing SKU", "raw": {...}},
    ...
  ]
}
```

This validation report is one of the most impressive parts of the project. Don't skip it.

---

## 8. The 20-Day Plan (revised)

I've reorganized your original plan to front-load the riskiest work and leave real time for testing and the README, which is what interviewers actually look at first.

### Days 1–2: Setup & contracts
- Repo, branch protection, README skeleton, ruff/black, pytest config
- Pick env manager, write `pyproject.toml`
- Sketch the database schema in a `schema.md` file
- Draft the API contract in `api.md` — both of you agree before writing endpoints
- **Decide who owns what:** suggested split below
- Find or generate the demo dataset (see Section 10)

### Days 3–5: Database & ingestion
- SQLAlchemy models + Alembic migration
- File parser (CSV + Excel via `pandas.read_excel`)
- Validation pipeline with Pydantic
- `POST /upload/sales` and `POST /upload/inventory` working end-to-end
- Validation report response
- Tests for: happy path, missing columns, malformed dates, duplicates

### Days 6–9: Core analytics
- `/analytics/overview`
- `/analytics/top-products`
- `/analytics/abc`
- `/analytics/dead-stock`
- Tests for each, with a fixed fixture dataset

### Days 10–12: Reorder + forecast
- `/analytics/reorder` with configurable lead time and safety stock
- `/analytics/forecast` with SMA
- Tests
- **Mid-project review:** demo what you have to each other or to a friend. Cut anything that isn't working.

### Days 13–15: AI explanation layer
- Prompt design and iteration (this will take longer than you think)
- `/analytics/explain` endpoint
- Caching in `analysis_runs`
- Fallback templated summary
- Tests with a mocked LLM client

### Days 16–17: Polish & hardening
- Consistent error responses across all endpoints
- Logging (structlog or stdlib)
- Rate limiting on the upload endpoint (slowapi, 1 line)
- Postman collection or Bruno collection in the repo
- Run ruff, fix everything

### Days 18–19: README, demo, recording
- Full README with: problem, solution, architecture diagram, setup, API examples, sample outputs, **honest limitations section**, prompt used for the LLM
- 3-minute Loom or screen recording walking through a fresh `git clone` to working demo
- Sample dataset in `/data` folder
- Architecture diagram (excalidraw is fine)

### Day 20: Buffer
You will need this day. Every project does.

---

## 9. Splitting the Work (2 people)

Decide on Day 1. Suggested split:

**Person A — "Data & Ingestion"**
- Database schema and migrations
- File parsers
- Validation pipeline
- Upload endpoints
- Data fixtures

**Person B — "Analytics & AI"**
- Analytics functions (pure Python, take a DB session, return dicts)
- Analytics endpoints
- Forecast logic
- LLM integration
- Caching

**Shared**
- API contract (Day 2)
- README
- Tests (each person writes tests for their own code, plus one integration test together at the end)

**Daily 10-minute sync.** Not optional. Talk about what's blocking you and what you changed in the shared schema.

**Use a feature-branch workflow.** Both work on `main` is how 20-day projects become 40-day projects.

---

## 10. The Demo Dataset

This is more important than you think. A great project with a synthetic dataset feels fake.

**Best option:** find a real small shop (family, friend, friend-of-friend) that uses spreadsheets. Offer to help them in exchange for using their (anonymized) data. Even 3 months of one shop's data is worth more than any synthetic dataset.

**Second-best option:** use a real public dataset and adapt it. The "Online Retail II" dataset on the UCI Machine Learning Repository is a real UK retailer's transactions and works well for this. Filter to one product category to simulate a clothing shop.

**Worst option (still acceptable):** synthetic data, but make it realistic — include seasonality, a few dead products, a few hot sellers, some returns, some messy rows. Document how you generated it.

Whichever you pick, include the dataset (or a sample) in `/data` so anyone can clone and run.

---

## 11. README Structure (write this on Day 18, not Day 20)

1. **One-sentence pitch** ("A backend that turns messy retail spreadsheets into actionable insights for small clothing shops.")
2. **The problem** (2 paragraphs, concrete)
3. **Demo** — GIF or screenshot of the AI summary output
4. **Architecture diagram**
5. **Quickstart** — `git clone` to running API in under 5 commands
6. **API examples** — curl commands with real responses
7. **The analytics, explained** — what each metric means and how it's computed
8. **The AI layer** — show the actual prompt, show a sample output
9. **Limitations & honest caveats** — *this section will impress people*
10. **What we'd build next** — shows you thought beyond the MVP
11. **Tech stack & why**
12. **Tests** — how to run them, what's covered

---

## 12. What Will Make This Stand Out

In rough order of impact:

1. **A real dataset from a real shop**, even a tiny one
2. **An honest "limitations" section** in the README
3. **The actual LLM prompt published** in the README
4. **A working `git clone` → demo path in under 5 minutes**
5. **Tests, even just 15–20 of them**
6. **A 3-minute demo video**
7. **A clean validation report on upload**
8. **Configurable assumptions** (lead time, safety stock days, dead stock threshold) instead of magic numbers

---

## 13. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| LLM layer feels gimmicky | Make it do cross-metric pattern detection, not just templating |
| Forecast looks wrong | Be honest in README; call it a baseline |
| Two people block each other | Strict module boundaries from Day 1, daily sync |
| Scope creep | Day 12 mid-review; cut anything not working |
| No real data | Spend Day 1 finding real or realistic data |
| Run out of time on README | Write it Day 18, not Day 20 |
| LLM API costs | Cache results; use a cheap model; mock in tests |

---

## 14. Stretch Goals (only if you finish early)

In priority order:
1. A tiny Streamlit or plain-HTML dashboard reading from the API
2. Postgres + Docker Compose
3. A second analysis: customer segments (if your dataset has customer IDs)
4. Export the AI summary as a PDF report
5. Webhook to email the weekly summary

Don't start any of these before Day 18.

---

## Final note

Your original plan was already good. The biggest changes I'd push for are: find a real shop, make the AI layer earn its place, write tests, and budget honest time for the README. Do those four things and this becomes a project you can talk about confidently in interviews for the next two years.

Good luck — and ship it.
