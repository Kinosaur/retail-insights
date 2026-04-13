"""
Retail Insights Engine — Synthetic Dataset Generator
Simulates one year (2023) of sales and monthly inventory snapshots
for a Singapore Uniqlo store, based on the real product catalog.

Usage (from project root):
    python generator/generate_dataset.py
"""
import csv
import random
import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — always relative to this file so it works from any working directory
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE  = BASE_DIR / "data" / "raw" / "uniqlo_sg_products.csv"
SALES_FILE  = BASE_DIR / "data" / "raw" / "sales.csv"
INVENTORY_FILE = BASE_DIR / "data" / "raw" / "inventory.csv"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DAILY_SALES = 120       # baseline transactions per day for a busy SG Uniqlo
RETURN_RATE      = 0.04      # 4 % of transactions are returns
DIRTY_DATA_RATE  = 0.05      # 5 % of rows contain intentional data-quality issues
START_DATE = datetime.date(2023, 1, 1)
END_DATE   = datetime.date(2023, 12, 31)

RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Product classification helpers
# ---------------------------------------------------------------------------
def is_cold_wear(name: str) -> bool:
    """Heattech, fleece, down etc. — popular in SG mainly for air-con + travel."""
    name = name.lower()
    return any(x in name for x in ["heattech", "fleece", "down", "puffer", "coat"])


def is_airism(name: str) -> bool:
    """AIRism — Uniqlo's #1 seller in tropical Singapore."""
    return "airism" in name.lower()


# ---------------------------------------------------------------------------
# Singapore retail calendar 2023
# ---------------------------------------------------------------------------
def get_day_multiplier(date: datetime.date) -> float:
    multiplier = 1.0

    # --- Weekends ---
    if date.weekday() >= 5:
        multiplier *= 1.5

    # --- Chinese New Year (Jan 22, 2023) — spike in the fortnight before ---
    if datetime.date(2023, 1, 5) <= date <= datetime.date(2023, 1, 21):
        multiplier *= 3.0

    # --- Hari Raya Puasa 2023: Apr 21-22 — shopping rush in Ramadan run-up ---
    elif datetime.date(2023, 4, 10) <= date <= datetime.date(2023, 4, 22):
        multiplier *= 2.0

    # --- Singapore Great Sale / mid-year payday ---
    elif datetime.date(2023, 6, 1) <= date <= datetime.date(2023, 7, 15):
        multiplier *= 1.6

    # --- National Day long weekend (Aug 9) ---
    elif datetime.date(2023, 8, 7) <= date <= datetime.date(2023, 8, 10):
        multiplier *= 1.8

    # --- Deepavali 2023: Nov 12 — golden week of Indian festive shopping ---
    elif datetime.date(2023, 11, 6) <= date <= datetime.date(2023, 11, 12):
        multiplier *= 1.7

    # --- Christmas & year-end sale ---
    elif datetime.date(2023, 12, 1) <= date <= datetime.date(2023, 12, 31):
        multiplier *= 2.2

    # --- Uniqlo double-digit campaign days ---
    if (date.month, date.day) in [(9, 9), (10, 10), (11, 11), (12, 12)]:
        multiplier *= 5.0

    return multiplier


# ---------------------------------------------------------------------------
# Season modifier per product × date
# ---------------------------------------------------------------------------
def get_product_multiplier(product_name: str, date: datetime.date) -> float:
    """
    Singapore is tropical (28-32 °C year-round).
    - AIRism: boosted all year, peak Apr-Sep (hotter months).
    - Cold wear (Heattech, fleece, down): people buy for air-con offices and
      overseas travel — steady year-round, slight boost Oct-Feb.
    """
    if is_airism(product_name):
        if 4 <= date.month <= 9:
            return 1.4   # peak heat season
        return 1.1

    if is_cold_wear(product_name):
        # Never suppressed — Singaporeans wear Heattech under blazers daily
        if date.month in [10, 11, 12, 1, 2]:
            return 1.3   # slight boost when people holiday abroad
        return 0.9       # still sells, just a touch slower

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

    random.seed(RANDOM_SEED)
    random.shuffle(products)

    total   = len(products)
    a_limit = int(total * 0.20)   # top 20 % — bestsellers
    b_limit = int(total * 0.50)   # next 30 % — regular sellers
    c_limit = int(total * 0.90)   # next 40 % — slow movers

    skus_a    = products[:a_limit]
    skus_b    = products[a_limit:b_limit]
    skus_c    = products[b_limit:c_limit]
    skus_dead = products[c_limit:]          # bottom 10 % — near-dead stock

    # Initial inventory levels
    inventory: dict[str, int] = {}
    for p in skus_a:    inventory[p["product_id"]] = random.randint(100, 250)
    for p in skus_b:    inventory[p["product_id"]] = random.randint(50, 100)
    for p in skus_c:    inventory[p["product_id"]] = random.randint(20, 50)
    for p in skus_dead: inventory[p["product_id"]] = random.randint(30, 80)

    # Fast-lookup sets for restock logic
    set_a    = {p["product_id"] for p in skus_a}
    set_b    = {p["product_id"] for p in skus_b}
    set_c    = {p["product_id"] for p in skus_c}

    def pick_product(date: datetime.date):
        """Weighted bucket selection with product-level seasonality."""
        r = random.random()
        if r < 0.80:   bucket = skus_a
        elif r < 0.95: bucket = skus_b
        else:          bucket = skus_c

        for _ in range(20):          # max retries to avoid infinite loop
            p = random.choice(bucket)
            pm = get_product_multiplier(p["product_name"], date)
            if random.random() < pm / 1.5:   # normalised acceptance
                return p
        return random.choice(bucket)  # fallback

    sales_data: list[dict] = []
    inventory_snapshots: list[dict] = []

    current_date = START_DATE
    print("Simulating days...")

    while current_date <= END_DATE:

        # Monthly inventory snapshot (1st of each month)
        if current_date.day == 1:
            for pid, qty in inventory.items():
                snap_date_str = current_date.strftime("%Y-%m-%d")
                qty_str       = str(qty)
                pid_str       = pid

                # Intentional dirty rows in inventory
                if random.random() < DIRTY_DATA_RATE:
                    dirty_type = random.randint(0, 1)
                    if dirty_type == 0:
                        qty_str = ""              # missing quantity
                    else:
                        pid_str = "INVALID-" + pid_str   # bad product_id

                inventory_snapshots.append({
                    "product_id":       pid_str,
                    "quantity_on_hand": qty_str,
                    "snapshot_date":    snap_date_str,
                })

        # Daily sales simulation
        day_mult    = get_day_multiplier(current_date)
        daily_count = int(BASE_DAILY_SALES * day_mult * random.uniform(0.85, 1.15))

        for _ in range(daily_count):
            p   = pick_product(current_date)
            pid = p["product_id"]

            # Returns vs normal sales
            is_return = random.random() < RETURN_RATE
            if is_return:
                qty = -random.randint(1, 2)
            else:
                r = random.random()
                if r < 0.90:   qty = 1
                elif r < 0.97: qty = 2
                else:          qty = 3

            unit_price_f = p["sell_price"]

            # Update inventory
            if not is_return:
                inventory[pid] = inventory.get(pid, 0) - qty

            # Restock when running low
            if inventory.get(pid, 0) < 10:
                if pid in set_a:   inventory[pid] = inventory.get(pid, 0) + random.randint(100, 200)
                elif pid in set_b: inventory[pid] = inventory.get(pid, 0) + random.randint(50, 100)
                elif pid in set_c: inventory[pid] = inventory.get(pid, 0) + random.randint(20, 50)

            # Format clean values
            date_str  = current_date.strftime("%Y-%m-%d")
            price_str = f"{unit_price_f:.2f}"
            pid_str   = pid

            # Intentional dirty rows in sales (mirrors blueprint Section 7)
            if random.random() < DIRTY_DATA_RATE:
                dirty_type = random.randint(0, 8)
                if dirty_type == 0:
                    pid_str = ""                       # missing product_id
                elif dirty_type == 1:
                    fmt = random.choice(["%d/%m/%Y", "%b-%d-%Y", "%Y.%m.%d"])
                    date_str = current_date.strftime(fmt)   # wrong date format
                elif dirty_type == 2:
                    qty = ""                           # missing quantity
                elif dirty_type == 3:
                    sym = random.choice(["$", "S$", "฿"])
                    price_str = f"{sym}{unit_price_f:.2f}"  # currency symbol in price
                elif dirty_type == 4:
                    pid_str = "  " + pid_str + " "    # whitespace around product_id
                elif dirty_type == 5:
                    pid_str = pid_str.lower()          # lowercase product_id
                elif dirty_type == 6:
                    price_str = ""                     # missing price
                elif dirty_type == 7:
                    date_str = ""                      # missing date
                elif dirty_type == 8:
                    pid_str = "NEW-12345"              # unknown SKU (blueprint auto-create rule)

            row_data = {
                "product_id": pid_str,
                "sale_date":  date_str,
                "quantity":   str(qty) if qty != "" else "",
                "unit_price": price_str,
            }
            sales_data.append(row_data)

            # Inject exact duplicate rows (~0.5 %) to test deduplication
            if random.random() < 0.005:
                sales_data.append(row_data.copy())

        current_date += datetime.timedelta(days=1)

    print(f"Generated {len(sales_data):,} sales rows "
          f"and {len(inventory_snapshots):,} inventory snapshot rows.")

    # Write sales CSV
    with open(SALES_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["product_id", "sale_date", "quantity", "unit_price"])
        writer.writeheader()
        writer.writerows(sales_data)
    print(f"Saved → {SALES_FILE}")

    # Write inventory CSV
    with open(INVENTORY_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["product_id", "quantity_on_hand", "snapshot_date"])
        writer.writeheader()
        writer.writerows(inventory_snapshots)
    print(f"Saved → {INVENTORY_FILE}")

    print("Done!")


if __name__ == "__main__":
    main()
