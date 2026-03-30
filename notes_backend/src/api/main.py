from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.notes import router as notes_router

openapi_tags = [
    {
        "name": "health",
        "description": "Health and service status endpoints.",
    },
    {
        "name": "notes",
        "description": "CRUD and search operations for notes.",
    },
]

app = FastAPI(
    title="Notes Backend API",
    description=(
        "REST API for a minimal notes app.\n\n"
        "Core resources:\n"
        "- Notes: create, list, get, update, delete\n"
        "- Search: substring search over title/content\n\n"
        "This backend uses SQLite for persistence and is structured with a small "
        "service layer to be cloud-sync-ready in the future."
    ),
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# Basic logging configuration suitable for container logs.
logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"], summary="Health check", operation_id="health_check")
def health_check():
    """Health check endpoint used for deployment/runtime verification."""
    return {"message": "Healthy"}


app.include_router(notes_router)
