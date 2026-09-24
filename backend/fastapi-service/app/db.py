"""
Lightweight SQLite access for the FastAPI service.

SQLite connections are cheap, so each request opens its own connection
(no pool needed) and closes it afterwards. Settings that matter:

  * isolation_level=None  -> autocommit, same as the old MySQL pool
                             (autocommit=True). Crucially this means no
                             write lock is held while the request waits on
                             the Groq API, so the PHP admin panel and other
                             chat requests are never blocked.
  * check_same_thread=False -> FastAPI may run a sync dependency and the
                             endpoint on different worker threads; each
                             connection is still used by one request only.
  * row_factory=sqlite3.Row -> rows support both row[0] and row["name"].
  * foreign_keys=ON        -> SQLite leaves FK enforcement off by default.
"""

import sqlite3
from pathlib import Path

from fastapi import HTTPException

from app.config import settings


def connect(db_path: str | None = None) -> sqlite3.Connection:
    path = Path(db_path or settings.DB_PATH)
    if not path.exists():
        # sqlite3.connect() would silently create an empty file; fail clearly instead.
        raise FileNotFoundError(
            f"SQLite database not found at {path}. Run: python database/init_db.py"
        )
    conn = sqlite3.connect(
        path,
        timeout=settings.DB_BUSY_TIMEOUT_SECONDS,
        isolation_level=None,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_connection():
    """FastAPI dependency: yields a connection, always closed afterwards."""
    try:
        conn = connect()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    try:
        yield conn
    finally:
        conn.close()
