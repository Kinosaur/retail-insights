"""
Retail Insights Engine — Synthetic Dataset Generator
Simulates 3 years (2023–2025) of sales and monthly inventory snapshots
for a Singapore Uniqlo store, based on the real product catalog.

Design principles:
- Tier assignment is product-type driven, not random
- Seasonality covers 5 product categories, not just AIRism + cold wear
- Singapore retail calendar is correct per year (CNY, Hari Raya, National Day,
  Deepavali dates shift each year)
- Year-over-year growth: +5% transactions in 2024, +8% in 2025 vs 2023

Usage (from project root):
    python generator/generate_dataset.py
"""
import csv
import random
import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR       = Path(__file__).resolve().parent.parent
INPUT_FILE     = BASE_DIR / "data" / "raw" / "uniqlo_sg_products.csv"
SALES_FILE     = BASE_DIR / "data" / "raw" / "sales.csv"
INVENTORY_FILE = BASE_DIR / "data" / "raw" / "inventory.csv"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DAILY_SALES = 120      # baseline transactions per day for a busy SG Uniqlo
RETURN_RATE      = 0.04     # 4% of transactions are returns
DIRTY_DATA_RATE  = 0.05     # 5% of rows contain intentional data-quality issues
RANDOM_SEED      = 42

YEARS = [2023, 2024, 2025]

# Year-over-year transaction volume multiplier (Uniqlo SG grew)
YOY_GROWTH = {2023: 1.00, 2024: 1.05, 2025: 1.08}


# ---------------------------------------------------------------------------
# Product classification — keyword-based, not random
# ---------------------------------------------------------------------------

def _has(name: str, *keywords: str) -> bool:
    n = name.lower()
    return any(k in n for k in keywords)


def is_airism(name: str) -> bool:
    return "airism" in name.lower()


def is_layering(name: str) -> bool:
    """
    Items Singaporeans buy for air-conditioned offices and overseas travel.
    Includes HEATTECH, fleece, down, jackets, hoodies, sweatshirts, parkas.
    """
    return _has(name,
        "heattech", "fleece", "down", "puffer",
        "jacket", "parka", "blouson", "hoodie", "hooded",
        "sweatshirt", "coat", "vest", "cardigan",
    )


def is_light_wear(name: str) -> bool:
    """
    Items that benefit from Singapore's hot Apr–Sep weather.
    Shorts, linen, tanks, UV protection, sleeveless.
    """
    return _has(name,
        "uv protection", "uv", "linen",
        "tank", "camisole", "sleeveless",
        " shorts",           # space prefix avoids matching "short sleeve"
    )


def is_innerwear(name: str) -> bool:
    """
    Socks, underwear, bras, boxers — consumables, steady year-round.
    """
    return _has(name,
        "sock", "underwear", "boxer", " bra", "bralette",
        "innerwear", "inner", "brief",
    )


def is_kids_or_baby(category: str) -> bool:
    return category in ("Kids", "Baby")


# ---------------------------------------------------------------------------
# Tier scoring — drives A/B/C/dead assignment per product
# Higher score = more likely to be a bestseller
# ---------------------------------------------------------------------------

def is_dead_stock_product(p: dict) -> bool:
    """
    Explicitly marks products that should rarely/never sell in Singapore.
    Dead stock = items that genuinely sit on shelves: wrong climate, wrong
    customer base, or ultra-niche.
    """
    name  = p["product_name"].lower()
    cat   = p["category"]
    price = float(p["sell_price"])

    # Cashmere — too hot in Singapore, luxury price point
    if "cashmere" in name:                      return True
    # Ultra-premium outerwear nobody buys in tropical SG
    if "seamless down" in name:                 return True
    if "trench coat" in name:                   return True
    # Shoes and bags — low volume for Uniqlo vs clothing
    # Note: use specific multi-word terms to avoid "baggy" jeans matching "bag"
    if any(x in name for x in ["shoulder bag", "tote bag", "backpack", "drawstring bag",
                                 "mini bag", "crossbody", "deck shoe", "sneaker shoe"]):
        return True
    # Baby category — very niche customer base (some pass through, most sit)
    if cat == "Baby":                           return True

    return False


def tier_score(p: dict) -> float:
    """
    Score drives A/B/C assignment for non-dead-stock products.
    Higher = more likely to be a bestseller.
    """
    name  = p["product_name"]
    price = float(p["sell_price"])
    score = 0.0

    # ---- Price band (cheaper = higher volume at Uniqlo) ----
    if price < 15:   score += 4
    elif price < 25: score += 3
    elif price < 40: score += 2
    elif price < 60: score += 1
    # $60+: no bonus — premium items land in C-tier naturally

    # ---- Product type bonuses ----
    if is_airism(name):              score += 4   # #1 Singapore hero product
    if is_innerwear(name):           score += 3   # consumable, bought repeatedly
    if _has(name, "heattech"):       score += 2   # year-round (air-con/travel)
    if is_layering(name):            score += 1   # hoodies/jackets for offices
    if is_light_wear(name):          score += 1   # linen/UV/shorts for heat
    if _has(name, "polo"):           score += 0.5
    if _has(name, "graphic", "ut (", " ut "): score += 0.5  # UT graphic tees

    return score


# ---------------------------------------------------------------------------
# Singapore retail calendar — correct dates per year
# ---------------------------------------------------------------------------

# Festive windows: (start, end, multiplier)
# Dates shift each year for lunar/Islamic holidays
FESTIVE_WINDOWS = {
    2023: [
        # Chinese New Year: Jan 22 — 2-week shopping rush before
        (datetime.date(2023, 1, 5),  datetime.date(2023, 1, 21), 3.0),
        # Hari Raya Puasa: Apr 21-22 — Ramadan run-up shopping
        (datetime.date(2023, 4, 10), datetime.date(2023, 4, 22), 2.0),
        # Great Singapore Sale / mid-year
        (datetime.date(2023, 6, 1),  datetime.date(2023, 7, 15), 1.6),
        # National Day long weekend: Aug 9
        (datetime.date(2023, 8, 7),  datetime.date(2023, 8, 10), 1.8),
        # Deepavali: Nov 12 — festive shopping week
        (datetime.date(2023, 11, 6), datetime.date(2023, 11, 12), 1.7),
        # Year-end sale: Dec
        (datetime.date(2023, 12, 1), datetime.date(2023, 12, 31), 2.2),
    ],
    2024: [
        # Chinese New Year: Feb 10
        (datetime.date(2024, 1, 24), datetime.date(2024, 2, 9),  3.0),
        # Hari Raya Puasa: Apr 9-10
        (datetime.date(2024, 3, 25), datetime.date(2024, 4, 10), 2.0),
        # Great Singapore Sale / mid-year
        (datetime.date(2024, 5, 31), datetime.date(2024, 7, 14), 1.6),
        # National Day long weekend: Aug 9
        (datetime.date(2024, 8, 7),  datetime.date(2024, 8, 11), 1.8),
        # Deepavali: Nov 1
        (datetime.date(2024, 10, 26), datetime.date(2024, 11, 1), 1.7),
        # Year-end sale: Dec
        (datetime.date(2024, 12, 1), datetime.date(2024, 12, 31), 2.2),
    ],
    2025: [
        # Chinese New Year: Jan 29
        (datetime.date(2025, 1, 13), datetime.date(2025, 1, 28), 3.0),
        # Hari Raya Puasa: Mar 30-31
        (datetime.date(2025, 3, 17), datetime.date(2025, 3, 31), 2.0),
        # Great Singapore Sale / mid-year
        (datetime.date(2025, 5, 30), datetime.date(2025, 7, 13), 1.6),
        # National Day long weekend: Aug 9
        (datetime.date(2025, 8, 7),  datetime.date(2025, 8, 11), 1.8),
        # Deepavali: Oct 20
        (datetime.date(2025, 10, 14), datetime.date(2025, 10, 20), 1.7),
        # Year-end sale: Dec
        (datetime.date(2025, 12, 1), datetime.date(2025, 12, 31), 2.2),
    ],
}

# Uniqlo campaign days (same pattern each year)
CAMPAIGN_DAYS = {(9, 9), (10, 10), (11, 11), (12, 12)}


def get_day_multiplier(d: datetime.date) -> float:
    mult = 1.0

    # Weekends
    if d.weekday() >= 5:
        mult *= 1.5

    # Festive windows (non-overlapping, checked in order)
    for start, end, m in FESTIVE_WINDOWS.get(d.year, []):
        if start <= d <= end:
            mult *= m
            break

    # Uniqlo campaign days
    if (d.month, d.day) in CAMPAIGN_DAYS:
        mult *= 5.0

    return mult


# ---------------------------------------------------------------------------
# Product seasonality modifier
# ---------------------------------------------------------------------------

def get_product_multiplier(p: dict, d: datetime.date) -> float:
    name = p["product_name"]
    cat  = p["category"]
    m    = d.month

    # AIRism — #1 Singapore hero product, year-round, peak in hot months
    if is_airism(name):
        return 1.5 if 4 <= m <= 9 else 1.2

    # Layering (jackets, hoodies, HEATTECH, fleece, down, coats)
    # Singaporeans buy for air-con offices and overseas travel year-round.
    # Slight boost Oct–Feb (year-end travel + overseas trips).
    if is_layering(name):
        return 1.3 if m in (10, 11, 12, 1, 2) else 0.9

    # Light summer wear (linen, shorts, tanks, UV protection)
    # Peak in hot months; dip in Nov–Jan "cooler" season
    if is_light_wear(name):
        if 4 <= m <= 9:   return 1.3
        if m in (11, 12, 1): return 0.8
        return 1.0

    # Innerwear and socks — steady consumables, tiny festive bump
    if is_innerwear(name):
        return 1.1  # constant — people always need socks

    # Kids: school-season aware
    # Term 1 start (Jan), mid-year holiday shopping (Jun–Jul), year-end (Nov–Dec)
    if is_kids_or_baby(cat):
        if m in (1, 6, 7, 11, 12): return 1.2
        return 0.85

    # Everything else: no special modifier
    return 1.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Reading products from {INPUT_FILE} ...")
    products = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["sell_price"] = float(row["sell_price"])
            products.append(row)
    print(f"Loaded {len(products)} products.")

    # ---- Assign tiers — explicit dead stock, then score-ranked A/B/C ----
    random.seed(RANDOM_SEED)

    # Separate dead stock first (intentional, not random)
    skus_dead  = [p for p in products if is_dead_stock_product(p)]
    sellable   = [p for p in products if not is_dead_stock_product(p)]

    # Sort sellable by score + jitter so same-score products vary naturally
    sellable_scored = sorted(
        sellable,
        key=lambda p: tier_score(p) + random.uniform(0, 0.5),
        reverse=True,
    )

    n       = len(sellable_scored)
    a_limit = int(n * 0.22)   # top 22% of sellable — bestsellers
    b_limit = int(n * 0.55)   # next 33% — regular sellers
                               # remaining 45% — slow movers (C)

    skus_a = sellable_scored[:a_limit]
    skus_b = sellable_scored[a_limit:b_limit]
    skus_c = sellable_scored[b_limit:]

    set_a = {p["product_id"] for p in skus_a}
    set_b = {p["product_id"] for p in skus_b}
    set_c = {p["product_id"] for p in skus_c}

    print(f"Tier A: {len(skus_a)} | Tier B: {len(skus_b)} | "
          f"Tier C: {len(skus_c)} | Dead stock: {len(skus_dead)}")

    def pick_product(d: datetime.date):
        """Weighted bucket selection with product-level seasonality."""
        r = random.random()
        if r < 0.80:   bucket = skus_a
        elif r < 0.95: bucket = skus_b
        else:          bucket = skus_c

        for _ in range(20):
            p  = random.choice(bucket)
            pm = get_product_multiplier(p, d)
            # Normalise against max possible multiplier (1.5 for AIRism peak)
            if random.random() < pm / 1.6:
                return p
        return random.choice(bucket)

    all_sales: list[dict]     = []
    all_inventory: list[dict] = []

    for year in YEARS:
        print(f"\nSimulating {year} ...")
        start_date = datetime.date(year, 1, 1)
        end_date   = datetime.date(year, 12, 31)
        yoy_mult   = YOY_GROWTH[year]

        # Fresh inventory at start of each year
        inventory: dict[str, int] = {}
        for p in skus_a:    inventory[p["product_id"]] = random.randint(150, 250)
        for p in skus_b:    inventory[p["product_id"]] = random.randint(60,  120)
        for p in skus_c:    inventory[p["product_id"]] = random.randint(20,  60)
        for p in skus_dead: inventory[p["product_id"]] = random.randint(30,  80)

        current_date = start_date

        while current_date <= end_date:

            # Monthly inventory snapshot (1st of each month)
            if current_date.day == 1:
                for pid, qty in inventory.items():
                    snap_date_str = current_date.strftime("%Y-%m-%d")
                    qty_str       = str(qty)
                    pid_str       = pid

                    if random.random() < DIRTY_DATA_RATE:
                        dirty_type = random.randint(0, 1)
                        if dirty_type == 0:
                            qty_str = ""
                        else:
                            pid_str = "INVALID-" + pid_str

                    all_inventory.append({
                        "product_id":       pid_str,
                        "quantity_on_hand": qty_str,
                        "snapshot_date":    snap_date_str,
                    })

            # Daily sales
            day_mult    = get_day_multiplier(current_date)
            daily_count = int(BASE_DAILY_SALES * day_mult * yoy_mult * random.uniform(0.85, 1.15))

            for _ in range(daily_count):
                p   = pick_product(current_date)
                pid = p["product_id"]

                is_ret = random.random() < RETURN_RATE
                if is_ret:
                    qty = -random.randint(1, 2)
                else:
                    r = random.random()
                    qty = 1 if r < 0.90 else (2 if r < 0.97 else 3)

                unit_price_f = p["sell_price"]

                if not is_ret:
                    inventory[pid] = inventory.get(pid, 0) - qty

                # Restock when running low
                if inventory.get(pid, 0) < 10:
                    if pid in set_a:   inventory[pid] += random.randint(100, 200)
                    elif pid in set_b: inventory[pid] += random.randint(50,  100)
                    elif pid in set_c: inventory[pid] += random.randint(20,   50)

                date_str  = current_date.strftime("%Y-%m-%d")
                price_str = f"{unit_price_f:.2f}"
                pid_str   = pid
                qty_out   = qty

                # Intentional dirty rows
                if random.random() < DIRTY_DATA_RATE:
                    dirty_type = random.randint(0, 8)
                    if dirty_type == 0:
                        pid_str = ""
                    elif dirty_type == 1:
                        fmt      = random.choice(["%d/%m/%Y", "%b-%d-%Y", "%Y.%m.%d"])
                        date_str = current_date.strftime(fmt)
                    elif dirty_type == 2:
                        qty_out = ""
                    elif dirty_type == 3:
                        sym       = random.choice(["$", "S$", "฿"])
                        price_str = f"{sym}{unit_price_f:.2f}"
                    elif dirty_type == 4:
                        pid_str = "  " + pid_str + " "
                    elif dirty_type == 5:
                        pid_str = pid_str.lower()
                    elif dirty_type == 6:
                        price_str = ""
                    elif dirty_type == 7:
                        date_str = ""
                    elif dirty_type == 8:
                        pid_str = "NEW-12345"

                row_data = {
                    "product_id": pid_str,
                    "sale_date":  date_str,
                    "quantity":   str(qty_out) if qty_out != "" else "",
                    "unit_price": price_str,
                }
                all_sales.append(row_data)

                # Inject exact duplicate rows (~0.5%) to test deduplication
                if random.random() < 0.005:
                    all_sales.append(row_data.copy())

            current_date += datetime.timedelta(days=1)

        print(f"  {year}: daily avg ~{int(BASE_DAILY_SALES * yoy_mult)} transactions")

    print(f"\nTotal: {len(all_sales):,} sales rows, "
          f"{len(all_inventory):,} inventory rows across {len(YEARS)} years.")

    # Write sales CSV
    with open(SALES_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["product_id", "sale_date", "quantity", "unit_price"])
        writer.writeheader()
        writer.writerows(all_sales)
    print(f"Saved → {SALES_FILE}")

    # Write inventory CSV
    with open(INVENTORY_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["product_id", "quantity_on_hand", "snapshot_date"])
        writer.writeheader()
        writer.writerows(all_inventory)
    print(f"Saved → {INVENTORY_FILE}")

    print("\nDone!")


if __name__ == "__main__":
    main()
