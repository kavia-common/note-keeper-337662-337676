from __future__ import annotations

import logging
import os

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

# Prefer explicit origin allow-list for credentialed requests.
# In hosted environments, set NOTES_CORS_ALLOW_ORIGINS to the frontend URL (comma-separated list).
_cors_allow_origins_env = os.getenv("NOTES_CORS_ALLOW_ORIGINS", "").strip()
_cors_allow_origins = (
    [o.strip() for o in _cors_allow_origins_env.split(",") if o.strip()]
    if _cors_allow_origins_env
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins,
    # Browsers disallow `Access-Control-Allow-Origin: *` with credentials.
    # Only enable credentials when we are not using wildcard origins.
    allow_credentials=("*" not in _cors_allow_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"], summary="Health check", operation_id="health_check")
def health_check():
    """Health check endpoint used for deployment/runtime verification."""
    return {"message": "Healthy"}


app.include_router(notes_router)
