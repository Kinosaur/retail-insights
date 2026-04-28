"""
AI explanation service — Days 13-15.

Gathers all analytics data, checks the analysis_runs cache, and calls
Groq (free tier) to produce a plain-English retail summary if no cached
result exists for the current dataset state.
"""
import hashlib
import json
import os
import uuid
from datetime import date

from groq import Groq
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis_run import AnalysisRun
from app.services.analytics import (
    get_abc,
    get_dead_stock,
    get_overview,
    get_reorder,
    get_top_products,
)

_MODEL = "llama-3.3-70b-versatile"

_SYSTEM = (
    "You are a retail analytics assistant for a small Singapore clothing shop. "
    "You receive analytics data and produce a concise, plain-English business summary. "
    "Always respond with valid JSON only — no markdown, no extra text."
)

_PROMPT = """Here is the analytics data for a Singapore clothing retail store:

OVERVIEW (full year 2025):
- Total revenue: SGD {total_revenue:,.2f}
- Units sold: {total_units:,}
- Average order value: SGD {aov:.2f}
- Unique products sold: {unique_products}

TOP 5 PRODUCTS BY REVENUE (all-time, 2023–2025):
{top_products}

ABC CLASSIFICATION — catalog ranked by all-time revenue contribution:
- A-class (top 80% of total revenue): {a_count} products — core bestsellers
- B-class (next 15%): {b_count} products — regular sellers
- C-class (bottom 5%): {c_count} products — slow movers

DEAD STOCK — products with inventory on hand but no sales in 90+ days:
  Never sold at all: {never_sold_count} products
  Sold before but went stale: {stale_count} products
  Showing worst {dead_shown} examples:
{dead_stock}

REORDER ALERTS — stock below reorder point based on 90-day sales velocity:
  Total products needing reorder: {reorder_count}
  Most urgent (order these first):
{reorder}

Respond with JSON in exactly this format:
{{
  "what_is_working": "2-3 sentences on the strongest performers and positive trends",
  "needs_attention": "2-3 sentences on dead stock, slow movers, and inventory risks",
  "action_this_week": "1-2 concrete, specific actions the shop owner should take this week"
}}"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _gather_metrics(db: Session) -> dict:
    """Call all analytics services and pack results into a single dict."""
    start = date(2025, 1, 1)
    end   = date(2025, 12, 31)

    overview = get_overview(db, start, end)
    top      = get_top_products(db, limit=5, by="revenue")
    abc      = get_abc(db)
    dead     = get_dead_stock(db, days=90)
    reorder  = get_reorder(db, lead_time_days=14, safety_stock_days=7)

    dead_items    = dead["items"]
    never_sold    = [d for d in dead_items if d["days_since_last_sale"] is None]
    stale         = [d for d in dead_items if d["days_since_last_sale"] is not None]

    return {
        "overview":          overview,
        "top_products":      top["items"],
        "abc_summary":       abc["summary"],
        "dead_stock_count":  len(dead_items),
        "never_sold_count":  len(never_sold),
        "stale_count":       len(stale),
        # Show stale first (more urgent — used to sell), then never-sold
        "dead_stock_top3":   (stale + never_sold)[:3],
        "reorder_count":     len(reorder["items"]),
        "reorder_top3":      reorder["items"][:3],
    }


def _dead_stock_line(d: dict) -> str:
    """Format one dead stock row — handle the never-sold case cleanly."""
    qty = d["quantity_on_hand"]
    capital = f", SGD {d['tied_up_capital']:,.2f} tied up" if d["tied_up_capital"] else ""
    if d["days_since_last_sale"] is None:
        return f"  - {d['product_name']} ({qty} units, never sold{capital})"
    return f"  - {d['product_name']} ({qty} units, {d['days_since_last_sale']} days since last sale{capital})"


def _format_prompt(m: dict) -> str:
    ov = m["overview"]

    top_lines = "\n".join(
        f"  {i + 1}. {p['product_name']} — SGD {p['value']:,.2f}"
        for i, p in enumerate(m["top_products"])
    )

    if m["dead_stock_top3"]:
        dead_lines = "\n".join(_dead_stock_line(d) for d in m["dead_stock_top3"])
    else:
        dead_lines = "  None detected"

    if m["reorder_top3"]:
        reorder_lines = "\n".join(
            f"  - {r['product_name']}: {r['quantity_on_hand']} units on hand, "
            f"reorder point {r['reorder_point']}, order {r['recommended_order_qty']} units"
            for r in m["reorder_top3"]
        )
        remainder = m["reorder_count"] - len(m["reorder_top3"])
        if remainder > 0:
            reorder_lines += f"\n  ... and {remainder} more products need reordering"
    else:
        reorder_lines = "  None — all products sufficiently stocked"

    s = m["abc_summary"]
    return _PROMPT.format(
        total_revenue=ov["total_revenue"],
        total_units=ov["total_units_sold"],
        aov=ov["average_order_value"],
        unique_products=ov["unique_products_sold"],
        top_products=top_lines,
        a_count=s["A_count"],
        b_count=s["B_count"],
        c_count=s["C_count"],
        never_sold_count=m["never_sold_count"],
        stale_count=m["stale_count"],
        dead_shown=len(m["dead_stock_top3"]),
        dead_stock=dead_lines,
        reorder_count=m["reorder_count"],
        reorder=reorder_lines,
    )


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def get_explain(db: Session) -> dict:
    """
    Return a plain-English AI summary of the current analytics state.

    Flow:
    1. Gather all analytics data
    2. Hash the data as cache key
    3. Return cached result if one exists
    4. Otherwise call Groq, store result, return it
    """
    metrics     = _gather_metrics(db)
    metrics_str = json.dumps(metrics, default=str, sort_keys=True)
    cache_key   = hashlib.sha256(metrics_str.encode()).hexdigest()

    # Cache hit
    cached = db.execute(
        select(AnalysisRun).where(
            AnalysisRun.cache_key == cache_key,
            AnalysisRun.status == "done",
        )
    ).scalar_one_or_none()

    if cached:
        summary = json.loads(cached.ai_summary_text)
        return {**summary, "cached": True}

    # Cache miss — call Groq
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    prompt = _format_prompt(metrics)

    run = AnalysisRun(
        analysis_runs_id=str(uuid.uuid4()),
        run_type="summary",
        cache_key=cache_key,
        metrics_json=metrics_str,
        status="pending",
    )
    db.add(run)
    db.flush()

    try:
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        text    = response.choices[0].message.content
        summary = json.loads(text)

        # Validate expected keys are present before caching — a bad response
        # committed as "done" would poison every future cache hit.
        required = {"what_is_working", "needs_attention", "action_this_week"}
        missing  = required - summary.keys()
        if missing:
            raise ValueError(f"Groq response missing fields: {missing}")

        run.ai_summary_text = text
        run.status          = "done"
        db.commit()

        return {**summary, "cached": False}

    except Exception:
        run.status = "failed"
        db.commit()
        raise
