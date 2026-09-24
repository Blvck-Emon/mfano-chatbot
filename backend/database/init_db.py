"""
init_db.py
==========
Creates the SQLite database from database/schema.sql (replaces the old
`mysql < schema.sql` step). Uses only the Python standard library.

Usage:
    python database/init_db.py                 # create if missing (safe to re-run)
    python database/init_db.py --reset         # DELETE the DB file and rebuild it
    python database/init_db.py --db /path/x.db

The DB location comes from --db, else the DB_PATH environment variable
(.env is read if python-dotenv is installed), else data/mfano_bora_chatbot.db.
Relative paths are resolved from the project root.
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
DEFAULT_DB = "data/mfano_bora_chatbot.db"

try:  # optional convenience: pick DB_PATH up from ../.env
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass


def resolve_db_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT_DIR / path


def fts5_available() -> bool:
    try:
        sqlite3.connect(":memory:").execute("CREATE VIRTUAL TABLE t USING fts5(x)")
        return True
    except sqlite3.OperationalError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the Mfano Bora SQLite database")
    parser.add_argument("--db", default=os.environ.get("DB_PATH", DEFAULT_DB))
    parser.add_argument("--reset", action="store_true", help="delete and rebuild the database")
    args = parser.parse_args()

    if not fts5_available():
        print("This Python's SQLite build has no FTS5 support (need SQLite 3.24+ with FTS5).", file=sys.stderr)
        return 1

    db_path = resolve_db_path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if args.reset:
        for suffix in ("", "-wal", "-shm"):
            Path(str(db_path) + suffix).unlink(missing_ok=True)
        print(f"Removed existing database at {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
        tables = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE '%\\_fts%' ESCAPE '\\' AND name NOT LIKE 'sqlite\\_%' ESCAPE '\\'"
        ).fetchone()[0]
        categories = conn.execute("SELECT COUNT(*) FROM kb_categories").fetchone()[0]
        print(f"Database ready: {db_path}")
        print(f"  tables: {tables} | kb_categories seeded: {categories}")
    finally:
        conn.close()

    print("Reminder: the web-server user (PHP) and the FastAPI user must both be able to")
    print("write to this file AND its directory (SQLite WAL creates -wal/-shm files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
