from fastapi import FastAPI

import app.models  # noqa: F401 — registers all models on Base.metadata
from app.routers import batches, products, upload

app = FastAPI(
    title="Retail Insights Engine",
    description="Data ingestion and analytics backend for retail operations.",
    version="0.1.0",
)

app.include_router(upload.router)
app.include_router(products.router)
app.include_router(batches.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
