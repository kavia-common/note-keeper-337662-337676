from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.models.notes import (
    DeleteResponse,
    ErrorResponse,
    ListQuery,
    NoteCreateRequest,
    NoteResponse,
    NoteUpdateRequest,
    NotesListResponse,
    NotesSearchResponse,
    SearchQuery,
)
from src.db.sqlite import SQLiteError, get_connection, init_schema
from src.services.notes_service import (
    NoteConflictError,
    NoteNotFoundError,
    NotesServiceError,
    create_note,
    delete_note,
    get_note,
    list_notes,
    search_notes,
    update_note,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notes", tags=["notes"])


def _note_to_response(note) -> NoteResponse:
    return NoteResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def db_conn_dep():
    """
    Dependency that yields a SQLite connection with initialized schema.
    """
    conn = get_connection()
    try:
        init_schema(conn)
        yield conn
    finally:
        conn.close()


def _map_service_error_to_http(e: Exception) -> HTTPException:
    if isinstance(e, NoteNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    if isinstance(e, NoteConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    if isinstance(e, (NotesServiceError, SQLiteError)):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post(
    "",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Note created."},
        400: {"model": ErrorResponse, "description": "Validation error."},
        500: {"model": ErrorResponse, "description": "Server error."},
    },
    summary="Create note",
    description="Create a new note.",
    operation_id="create_note",
)
def create_note_route(payload: NoteCreateRequest, conn=Depends(db_conn_dep)) -> NoteResponse:
    try:
        note = create_note(conn, title=payload.title, content=payload.content)
        return _note_to_response(note)
    except Exception as e:
        raise _map_service_error_to_http(e)


@router.get(
    "",
    response_model=NotesListResponse,
    responses={500: {"model": ErrorResponse}},
    summary="List notes",
    description="List notes ordered by most recently updated.",
    operation_id="list_notes",
)
def list_notes_route(
    limit: int = Query(100, ge=1, le=500, description="Max number of notes to return."),
    offset: int = Query(0, ge=0, description="Pagination offset."),
    conn=Depends(db_conn_dep),
) -> NotesListResponse:
    query = ListQuery(limit=limit, offset=offset)
    try:
        items = list_notes(conn, limit=query.limit, offset=query.offset)
        return NotesListResponse(
            items=[_note_to_response(n) for n in items],
            limit=query.limit,
            offset=query.offset,
        )
    except Exception as e:
        raise _map_service_error_to_http(e)


@router.get(
    "/search",
    response_model=NotesSearchResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Search notes",
    description="Search notes by substring match in title or content (case-insensitive).",
    operation_id="search_notes",
)
def search_notes_route(
    q: str = Query(..., min_length=1, max_length=500, description="Search query."),
    limit: int = Query(50, ge=1, le=500, description="Max number of notes to return."),
    offset: int = Query(0, ge=0, description="Pagination offset."),
    conn=Depends(db_conn_dep),
) -> NotesSearchResponse:
    query = SearchQuery(q=q, limit=limit, offset=offset)
    try:
        items = search_notes(conn, q=query.q, limit=query.limit, offset=query.offset)
        return NotesSearchResponse(
            q=query.q,
            items=[_note_to_response(n) for n in items],
            limit=query.limit,
            offset=query.offset,
        )
    except Exception as e:
        raise _map_service_error_to_http(e)


@router.get(
    "/{note_id}",
    response_model=NoteResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Get note",
    description="Get a note by id.",
    operation_id="get_note",
)
def get_note_route(note_id: str, conn=Depends(db_conn_dep)) -> NoteResponse:
    try:
        note = get_note(conn, note_id=note_id)
        return _note_to_response(note)
    except Exception as e:
        raise _map_service_error_to_http(e)


@router.put(
    "/{note_id}",
    response_model=NoteResponse,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Update note",
    description="Update a note. Partial updates supported by omitting fields.",
    operation_id="update_note",
)
def update_note_route(note_id: str, payload: NoteUpdateRequest, conn=Depends(db_conn_dep)) -> NoteResponse:
    if payload.title is None and payload.content is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'title' or 'content' must be provided.",
        )
    try:
        note = update_note(conn, note_id=note_id, title=payload.title, content=payload.content)
        return _note_to_response(note)
    except Exception as e:
        raise _map_service_error_to_http(e)


@router.delete(
    "/{note_id}",
    response_model=DeleteResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Delete note",
    description="Delete a note by id.",
    operation_id="delete_note",
)
def delete_note_route(note_id: str, conn=Depends(db_conn_dep)) -> DeleteResponse:
    try:
        delete_note(conn, note_id=note_id)
        return DeleteResponse(deleted=True)
    except Exception as e:
        raise _map_service_error_to_http(e)
