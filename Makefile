# Retail Insights Engine — Makefile
# ---------------------------------------------------------------
# Database: Neon (cloud PostgreSQL) — shared by Person A and Friend B
#
# First time setup (Friend B):
#   1. cp .env.example .env    ← paste the Neon password from Person A
#   2. make install
#   3. make db-create          ← creates local test DB only (Neon already exists)
#   4. make run                ← keep this terminal open
#   (no seed needed — data already in Neon)
#
# When Person A pushes new data (git pull first, then):
#   → data is already in Neon, just restart server
#
# When Person A pushes a schema change (git pull first, then):
#   → migration already applied to Neon by Person A, just restart server
# ---------------------------------------------------------------

.PHONY: install db-create migrate run seed reseed test lint help

# ---------------------------------------------------------------
# Setup
# ---------------------------------------------------------------

install:
	python -m venv .venv
	.venv/bin/pip install --upgrade pip -q
	.venv/bin/pip install -r requirements.txt
	@echo ""
	@echo "✓ Dependencies installed."
	@echo "  Next: make db-create"

db-create:
	@echo ""
	@echo "Main database lives on Neon (already exists — no action needed)."
	@echo "You only need a local test database for running pytest:"
	@echo ""
	@echo "  psql -U postgres -c \"CREATE DATABASE retail_insights_test;\""
	@echo ""
	@echo "Then run: make run"

migrate:
	@echo "NOTE: Only Person A runs this — it applies to the shared Neon database."
	.venv/bin/alembic upgrade head
	@echo "✓ Migrations applied to Neon."

# ---------------------------------------------------------------
# Run
# ---------------------------------------------------------------

run:
	.venv/bin/uvicorn app.main:app --reload --port 8000

# ---------------------------------------------------------------
# Data
# ---------------------------------------------------------------

seed:
	@echo "Uploading data... (requires 'make run' in another terminal)"
	.venv/bin/python scripts/seed.py

reseed:
	@echo ""
	@echo "⚠  This wipes and reloads ALL data on the shared Neon database."
	@echo "   Tell Friend B before running — his server will see empty tables briefly."
	@echo ""
	@echo "Step 1 — wipe Neon data (run this in your terminal):"
	@echo "  python -c \""
	@echo "  from sqlalchemy import create_engine, text; import os; from dotenv import load_dotenv"
	@echo "  load_dotenv()"
	@echo "  e = create_engine(os.getenv('DATABASE_URL'))"
	@echo "  with e.connect() as c: c.execute(text('TRUNCATE TABLE sales, inventory_snapshots, upload_batches, products RESTART IDENTITY CASCADE')); c.commit()"
	@echo "  \""
	@echo ""
	@echo "Step 2 — reload data:"
	@echo "  make seed"

# ---------------------------------------------------------------
# Dev
# ---------------------------------------------------------------

test:
	.venv/bin/pytest -v

lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .

# ---------------------------------------------------------------
# Help
# ---------------------------------------------------------------

help:
	@echo ""
	@echo "Retail Insights Engine — available commands"
	@echo "-------------------------------------------"
	@echo "  make install    — create venv + install dependencies"
	@echo "  make db-create  — prints DB creation commands to run"
	@echo "  make migrate    — run alembic migrations (create tables)"
	@echo "  make run        — start API server on :8000"
	@echo "  make seed       — upload all CSVs into the database"
	@echo "  make reseed     — wipe Neon data + reload (Person A only)"
	@echo "  make test       — run all 34 tests"
	@echo "  make lint       — run ruff linter + format check"
	@echo ""
