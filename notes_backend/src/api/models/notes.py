from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class NoteBase(BaseModel):
    """Base fields for note models."""

    title: str = Field(..., min_length=1, max_length=200, description="Note title.")
    content: str = Field(..., min_length=1, description="Note body content.")


class NoteCreateRequest(NoteBase):
    """Request body for creating a note."""
    pass


class NoteUpdateRequest(BaseModel):
    """Request body for updating a note (partial update supported)."""

    title: str | None = Field(None, min_length=1, max_length=200, description="New title.")
    content: str | None = Field(None, min_length=1, description="New content.")


class NoteResponse(NoteBase):
    """Response model representing a note."""

    id: str = Field(..., description="Note ID (UUID).")
    created_at: str = Field(..., description="Creation timestamp (ISO-8601, UTC).")
    updated_at: str = Field(..., description="Last update timestamp (ISO-8601, UTC).")


class NotesListResponse(BaseModel):
    """Response model for listing notes."""
    items: list[NoteResponse] = Field(..., description="Notes list.")
    limit: int = Field(..., ge=1, le=500, description="Applied limit.")
    offset: int = Field(..., ge=0, description="Applied offset.")


class NotesSearchResponse(NotesListResponse):
    """Response model for searching notes."""
    q: str = Field(..., min_length=1, description="Search query string.")


class ErrorResponse(BaseModel):
    """Standard error response payload."""
    detail: str = Field(..., description="Human-readable error message.")


class DeleteResponse(BaseModel):
    """Response payload for delete operations."""
    deleted: bool = Field(..., description="Whether the note was deleted.")


class SearchQuery(BaseModel):
    """Validated search query parameters."""

    q: str = Field(..., min_length=1, max_length=500, description="Search query string.")
    limit: int = Field(50, ge=1, le=500, description="Max number of results to return.")
    offset: int = Field(0, ge=0, description="Pagination offset.")

    @field_validator("q")
    @classmethod
    def strip_and_validate_q(cls, v: str) -> str:
        v2 = v.strip()
        if not v2:
            raise ValueError("Search query must not be empty.")
        return v2


class ListQuery(BaseModel):
    """Validated list query parameters."""

    limit: int = Field(100, ge=1, le=500, description="Max number of notes to return.")
    offset: int = Field(0, ge=0, description="Pagination offset.")
