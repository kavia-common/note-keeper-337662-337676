"""
SQLite adapter layer for the notes backend.

This module owns:
- connecting to SQLite based on environment configuration
- initializing the schema (idempotent)
- low-level query execution helpers

The higher-level "service layer" should use this module rather than touching sqlite3
directly, to keep I/O boundaries clear and debuggable.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable, Optional


@dataclass(frozen=True)
class SQLiteConfig:
    """Typed configuration for SQLite access."""

    db_path: str


class SQLiteError(Exception):
    """Base error for SQLite adapter operations."""


class SQLiteNotFoundError(SQLiteError):
    """Raised when a requested row is not found."""


def _get_sqlite_config_from_env() -> SQLiteConfig:
    """
    Load SQLite config from environment variables.

    Expected env var (provided by the database container):
    - SQLITE_DB: path to SQLite database file
    """
    db_path = os.getenv("SQLITE_DB")
    if not db_path:
        raise SQLiteError(
            "Missing required environment variable SQLITE_DB (path to SQLite database)."
        )
    return SQLiteConfig(db_path=db_path)


def get_connection() -> sqlite3.Connection:
    """
    Create a sqlite3 connection using environment configuration.

    The connection uses Row objects for name-based access.
    """
    cfg = _get_sqlite_config_from_env()
    conn = sqlite3.connect(cfg.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Ensure foreign keys are enforced (safe even if none are used yet).
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """
    Ensure the database schema exists (idempotent).

    Current schema:
    - notes: stores user notes (single-user for now, cloud-sync-ready fields included)
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON notes(updated_at);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title);")
    conn.commit()


def execute(
    conn: sqlite3.Connection,
    sql: str,
    params: Optional[Iterable[Any]] = None,
) -> sqlite3.Cursor:
    """
    Execute a statement and commit.

    This helper centralizes commits and makes it easy to add logging later if needed.
    """
    cur = conn.execute(sql, params or [])
    conn.commit()
    return cur


def fetchone(
    conn: sqlite3.Connection,
    sql: str,
    params: Optional[Iterable[Any]] = None,
) -> Optional[sqlite3.Row]:
    """Fetch a single row or return None."""
    cur = conn.execute(sql, params or [])
    return cur.fetchone()


def fetchall(
    conn: sqlite3.Connection,
    sql: str,
    params: Optional[Iterable[Any]] = None,
) -> list[sqlite3.Row]:
    """Fetch all rows."""
    cur = conn.execute(sql, params or [])
    return list(cur.fetchall())
