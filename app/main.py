from fastapi import FastAPI

from app.db import engine
from app.models import *  # noqa: F401, F403 — ensures all models are registered

app = FastAPI(
    title="Retail Insights Engine",
    description="Data ingestion and analytics backend for retail operations.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
