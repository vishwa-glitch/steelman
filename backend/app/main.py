"""Steelman API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import get_settings, router

app = FastAPI(title="Steelman API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().cors_origins),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
