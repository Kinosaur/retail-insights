# Retail Insights Engine — Makefile
# ---------------------------------------------------------------
# First time setup (Friend B):
#   1. cp .env.example .env    ← fill in your postgres password
#   2. make install
#   3. make db-create          ← follow the printed instructions
#   4. make migrate
#   5. make run                ← keep this terminal open
#   6. make seed               ← open a NEW terminal, run this
#
# When Person A pushes new data (git pull first, then):
#   make reseed
#
# When Person A pushes a schema change (git pull first, then):
#   make migrate
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
	@echo "Run these two commands in your terminal (replace YOUR_PASSWORD):"
	@echo ""
	@echo "  psql -U postgres -c \"CREATE DATABASE retail_insights;\""
	@echo "  psql -U postgres -c \"CREATE DATABASE retail_insights_test;\""
	@echo ""
	@echo "Then run: make migrate"

migrate:
	.venv/bin/alembic upgrade head
	@echo "✓ Migrations applied. Next: make run"

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
	@echo "Step 1 — wipe the database (run this in your terminal):"
	@echo ""
	@echo "  psql -U postgres -d retail_insights -c \\"
	@echo "  \"TRUNCATE TABLE sales, inventory_snapshots, upload_batches, products RESTART IDENTITY CASCADE;\""
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
	@echo "  make reseed     — instructions to wipe + reload data"
	@echo "  make test       — run all 34 tests"
	@echo "  make lint       — run ruff linter + format check"
	@echo ""
