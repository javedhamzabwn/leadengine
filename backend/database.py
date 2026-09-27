"""LeadEngine DuckDB access layer.

Opens the canonical company database (``data/leadengine.db``) and the
per-user auxiliary tables (``saved_search``, ``favorite``).

Connection policy:
- Read paths open a short-lived ``read_only=True`` connection per request.
- Mutations open a short-lived read-write connection guarded by a
  process-wide lock (DuckDB allows a single writer).
- ``DB_PATH`` is a module-level variable so tests can point it at a
  scratch database.

All SQL in this module is static; callers must pass values as parameters
and keep identifiers on allowlists.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import duckdb

from backend import config

# Overridable by tests (monkeypatch backend.database.DB_PATH).
DB_PATH: Path = config.DB_PATH

AUX_TABLES_DDL = """
CREATE TABLE IF NOT EXISTS saved_search (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    filters    TEXT NOT NULL,   -- JSON object of the list-endpoint filters
    created_at DOUBLE NOT NULL  -- unix epoch seconds
);
CREATE TABLE IF NOT EXISTS favorite (
    company_id TEXT PRIMARY KEY,
    created_at DOUBLE NOT NULL  -- unix epoch seconds
);
"""

_write_lock = threading.Lock()


@contextmanager
def read_connection(db_path: Path | None = None) -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a short-lived read-only connection to the database."""
    con = duckdb.connect(str(db_path or DB_PATH), read_only=True)
    try:
        yield con
    finally:
        con.close()


@contextmanager
def write_connection(db_path: Path | None = None) -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a short-lived read-write connection, serialized by a lock."""
    with _write_lock:
        con = duckdb.connect(str(db_path or DB_PATH), read_only=False)
        try:
            yield con
        finally:
            con.close()


def ensure_aux_tables(db_path: Path | None = None) -> None:
    """Create saved_search / favorite tables when missing. Idempotent."""
    with write_connection(db_path) as con:
        for stmt in AUX_TABLES_DDL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                con.execute(stmt)


def company_count(db_path: Path | None = None) -> int:
    """Exact row count of the canonical company table."""
    with read_connection(db_path) as con:
        row = con.execute("SELECT COUNT(*) FROM company").fetchone()
        return int(row[0]) if row else 0


__all__ = [
    "DB_PATH",
    "read_connection",
    "write_connection",
    "ensure_aux_tables",
    "company_count",
]
