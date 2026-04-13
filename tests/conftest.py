"""
Shared fixtures for the Retail Insights Engine test suite.

Uses a dedicated local `retail_insights_test` PostgreSQL database — never Neon.
Tests wipe all tables between runs so they must NEVER point at the shared cloud DB.

Requires TEST_DATABASE_URL in your .env file:
    TEST_DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/retail_insights_test
"""
import os
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — registers all models with Base
from app.db import Base, get_db
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is not set.\n"
        "Add it to your .env file:\n"
        "  TEST_DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/retail_insights_test\n"
        "Never point TEST_DATABASE_URL at Neon — tests wipe all tables between runs."
    )

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Session-scoped: create all tables once, drop after the whole run
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def create_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Function-scoped: wipe all rows between tests
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.connect() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE sales, inventory_snapshots, upload_batches, products"
                " RESTART IDENTITY CASCADE"
            )
        )
        conn.commit()


# ---------------------------------------------------------------------------
# TestClient with get_db overridden to use the test database
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------
def make_upload(content: str, filename: str = "test.csv"):
    """Return the `files` dict expected by TestClient.post()."""
    return {"file": (filename, BytesIO(content.encode("utf-8")), "text/csv")}
