"""
Notes service layer.

This module defines the canonical flow(s) for notes operations. API routes should call
these functions rather than embedding SQL inline.

Error contract:
- Raises NoteNotFoundError when a note id does not exist.
- Raises NoteConflictError when trying to create an existing note id (shouldn't happen
  with UUID ids, but explicit for completeness).
- Raises NotesServiceError for other service-level failures.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.db.sqlite import execute, fetchall, fetchone

logger = logging.getLogger(__name__)


class NotesServiceError(Exception):
    """Base error for notes service operations."""


class NoteNotFoundError(NotesServiceError):
    """Raised when a note is not found."""


class NoteConflictError(NotesServiceError):
    """Raised when a note cannot be created due to conflict."""


@dataclass(frozen=True)
class NoteRecord:
    """In-memory representation of a note row."""

    id: str
    title: str
    content: str
    created_at: str
    updated_at: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _row_to_note(row: sqlite3.Row) -> NoteRecord:
    return NoteRecord(
        id=row["id"],
        title=row["title"],
        content=row["content"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# PUBLIC_INTERFACE
def create_note(conn: sqlite3.Connection, title: str, content: str) -> NoteRecord:
    """
    Create a note.

    Inputs:
      - title: non-empty, validated by API layer
      - content: non-empty, validated by API layer

    Returns:
      - NoteRecord for created note

    Errors:
      - NoteConflictError if a generated id collides (extremely unlikely)
      - NotesServiceError on other failures
    """
    note_id = str(uuid.uuid4())
    now = _utc_now_iso()
    logger.info("NotesService.create_note start id=%s", note_id)
    try:
        execute(
            conn,
            """
            INSERT INTO notes (id, title, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [note_id, title, content, now, now],
        )
        row = fetchone(conn, "SELECT * FROM notes WHERE id = ?", [note_id])
        if row is None:
            raise NotesServiceError("Create succeeded but note could not be read back.")
        logger.info("NotesService.create_note end id=%s", note_id)
        return _row_to_note(row)
    except sqlite3.IntegrityError as e:
        logger.exception("NotesService.create_note conflict id=%s", note_id)
        raise NoteConflictError("Note id conflict.") from e
    except Exception as e:
        logger.exception("NotesService.create_note failed id=%s", note_id)
        raise NotesServiceError("Failed to create note.") from e


# PUBLIC_INTERFACE
def list_notes(conn: sqlite3.Connection, limit: int = 100, offset: int = 0) -> list[NoteRecord]:
    """
    List notes ordered by updated_at desc.

    Returns up to `limit` notes starting from `offset`.
    """
    logger.info("NotesService.list_notes start limit=%s offset=%s", limit, offset)
    rows = fetchall(
        conn,
        """
        SELECT * FROM notes
        ORDER BY updated_at DESC
        LIMIT ? OFFSET ?
        """,
        [limit, offset],
    )
    notes = [_row_to_note(r) for r in rows]
    logger.info("NotesService.list_notes end count=%s", len(notes))
    return notes


# PUBLIC_INTERFACE
def get_note(conn: sqlite3.Connection, note_id: str) -> NoteRecord:
    """
    Get a single note by id.

    Raises NoteNotFoundError if missing.
    """
    logger.info("NotesService.get_note start id=%s", note_id)
    row = fetchone(conn, "SELECT * FROM notes WHERE id = ?", [note_id])
    if row is None:
        logger.info("NotesService.get_note not_found id=%s", note_id)
        raise NoteNotFoundError("Note not found.")
    logger.info("NotesService.get_note end id=%s", note_id)
    return _row_to_note(row)


# PUBLIC_INTERFACE
def update_note(
    conn: sqlite3.Connection,
    note_id: str,
    title: Optional[str],
    content: Optional[str],
) -> NoteRecord:
    """
    Update a note. Title/content can be partially updated.

    Raises NoteNotFoundError if missing.
    """
    logger.info("NotesService.update_note start id=%s", note_id)
    existing = fetchone(conn, "SELECT * FROM notes WHERE id = ?", [note_id])
    if existing is None:
        logger.info("NotesService.update_note not_found id=%s", note_id)
        raise NoteNotFoundError("Note not found.")

    new_title = title if title is not None else existing["title"]
    new_content = content if content is not None else existing["content"]
    now = _utc_now_iso()

    try:
        execute(
            conn,
            """
            UPDATE notes
            SET title = ?, content = ?, updated_at = ?
            WHERE id = ?
            """,
            [new_title, new_content, now, note_id],
        )
        updated = fetchone(conn, "SELECT * FROM notes WHERE id = ?", [note_id])
        if updated is None:
            raise NotesServiceError("Update succeeded but note could not be read back.")
        logger.info("NotesService.update_note end id=%s", note_id)
        return _row_to_note(updated)
    except Exception as e:
        logger.exception("NotesService.update_note failed id=%s", note_id)
        raise NotesServiceError("Failed to update note.") from e


# PUBLIC_INTERFACE
def delete_note(conn: sqlite3.Connection, note_id: str) -> None:
    """
    Delete a note.

    Raises NoteNotFoundError if missing.
    """
    logger.info("NotesService.delete_note start id=%s", note_id)
    cur = execute(conn, "DELETE FROM notes WHERE id = ?", [note_id])
    if cur.rowcount == 0:
        logger.info("NotesService.delete_note not_found id=%s", note_id)
        raise NoteNotFoundError("Note not found.")
    logger.info("NotesService.delete_note end id=%s", note_id)


# PUBLIC_INTERFACE
def search_notes(
    conn: sqlite3.Connection,
    q: str,
    limit: int = 50,
    offset: int = 0,
) -> list[NoteRecord]:
    """
    Search notes by substring match in title/content (case-insensitive).

    This is implemented with LIKE; for future cloud sync, the query contract can
    stay stable even if implementation changes.
    """
    logger.info("NotesService.search_notes start q_len=%s limit=%s offset=%s", len(q), limit, offset)
    like = f"%{q}%"
    rows = fetchall(
        conn,
        """
        SELECT * FROM notes
        WHERE title LIKE ? COLLATE NOCASE
           OR content LIKE ? COLLATE NOCASE
        ORDER BY updated_at DESC
        LIMIT ? OFFSET ?
        """,
        [like, like, limit, offset],
    )
    notes = [_row_to_note(r) for r in rows]
    logger.info("NotesService.search_notes end count=%s", len(notes))
    return notes
