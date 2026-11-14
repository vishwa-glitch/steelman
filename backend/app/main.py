"""Steelman API. Step 1: only a health check."""

from fastapi import FastAPI

app = FastAPI(title="Steelman API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
