"""
Seed script — uploads all 3 raw CSVs into the running API (targets Neon via DATABASE_URL).

Usage:
    python scripts/seed.py            # upload (warns if already loaded)
    python scripts/seed.py --fresh    # shows wipe instructions, then exits

NOTE: This seeds the shared Neon database. Tell Friend B before running --fresh.
Requires the API server to be running:
    make run   (in another terminal)
"""
import argparse
import sys
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

UPLOADS = [
    ("upload/products", DATA_DIR / "uniqlo_sg_products.csv", "products"),
    ("upload/sales",    DATA_DIR / "sales.csv",              "sales"),
    ("upload/inventory",DATA_DIR / "inventory.csv",          "inventory"),
]


def check_server():
    try:
        resp = httpx.get(f"{BASE_URL}/health", timeout=3)
        resp.raise_for_status()
    except Exception:
        print("ERROR: API server is not running.")
        print(f"       Start it with:  make run")
        sys.exit(1)


def check_empty():
    """Return True if products table is already populated."""
    resp = httpx.get(f"{BASE_URL}/products?limit=1")
    return resp.json().get("total", 0) > 0


def wipe_via_api():
    """
    No DELETE /all endpoint exists — wipe runs directly against Neon via SQLAlchemy.
    Warns the user since this affects the shared cloud database.
    """
    print()
    print("  ⚠  --fresh wipes the shared Neon database. Tell Friend B first.")
    print()
    print("  Run this to wipe Neon, then re-run seed.py without --fresh:")
    print()
    print("  python -c \"")
    print("  from sqlalchemy import create_engine, text; import os; from dotenv import load_dotenv")
    print("  load_dotenv()")
    print("  e = create_engine(os.getenv('DATABASE_URL'))")
    print("  with e.connect() as c:")
    print("      c.execute(text('TRUNCATE TABLE sales, inventory_snapshots, upload_batches, products RESTART IDENTITY CASCADE'))")
    print("      c.commit()")
    print("  \"")
    print()
    sys.exit(0)


def upload_file(endpoint: str, filepath: Path, label: str) -> dict:
    print(f"  Uploading {label}...")
    with open(filepath, "rb") as f:
        resp = httpx.post(
            f"{BASE_URL}/{endpoint}",
            files={"file": (filepath.name, f, "text/csv")},
            timeout=120,
        )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true",
                        help="Wipe DB before seeding (shows wipe command)")
    args = parser.parse_args()

    print("Retail Insights — Seed Script")
    print("=" * 40)

    check_server()
    print("✓ Server is running")

    if args.fresh:
        wipe_via_api()

    if check_empty():
        print("⚠  Products table already has data.")
        print("   Run with --fresh to wipe first, or skip to re-upload (upsert).")
        print()

    for endpoint, filepath, label in UPLOADS:
        if not filepath.exists():
            print(f"  ERROR: {filepath} not found")
            sys.exit(1)
        result = upload_file(endpoint, filepath, label)
        accepted = result.get("rows_accepted", "?")
        rejected = result.get("rows_rejected", "?")
        status   = result.get("status", "?")
        print(f"    status={status}  accepted={accepted}  rejected={rejected}")

    print()
    print("Done! Database is loaded.")
    print(f"Browse: {BASE_URL}/docs")


if __name__ == "__main__":
    main()
