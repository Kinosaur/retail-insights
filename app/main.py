from fastapi import FastAPI

import app.models  # noqa: F401 — registers all models on Base.metadata

app = FastAPI(
    title="Retail Insights Engine",
    description="Data ingestion and analytics backend for retail operations.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
