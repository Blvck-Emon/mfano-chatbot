"""
load_csv_to_sqlite.py
=====================
Task-5/6/8 tool (Knowledge Base Development, Organization, Cleaning).

Loads a knowledge-base CSV into the SQLite database. Two layouts are
auto-detected from the header row:

  1. TRAINING DATASET   intent, question, response
       intent   -> kb_categories.name            (created if new)
       response -> knowledge_base.content_chunk  (ONE row per unique response
                                                  within an intent)
       question -> kb_questions.question_text    (linked to its response)
       e.g. mfano_bora_chatbot_training_dataset.csv
            525 questions -> 34 responses -> 21 intents

  2. LEGACY KB LAYOUT   category, question, content_chunk, keywords,
                        source_url, source_type
       (database/seed_faq.csv and the scraper's knowledge_base_scraped.csv)
       If `question` is filled it is stored in kb_questions too.

Cleaning performed along the way:
  * strips whitespace, collapses repeated spaces
  * drops empty / too-short answers
  * de-duplicates: an answer already stored in the same category is reused
    (not re-inserted); a question that already exists is skipped, so the
    loader is safe to re-run (idempotent) on a cron job

Usage:
    python load_csv_to_sqlite.py --csv ../database/mfano_bora_chatbot_training_dataset.csv
    python load_csv_to_sqlite.py --csv ../database/knowledge_base_scraped.csv --source-type scraped
    python load_csv_to_sqlite.py --csv data.csv --db /path/to/other.db --dry-run

The database must already exist:  python database/init_db.py
"""

import argparse
import csv
import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB = "data/mfano_bora_chatbot.db"
DEFAULT_CATEGORY = "faq"
FALLBACK_INTENT = "fallback"
MIN_CONTENT_CHARS = 20
MAX_QUESTION_CHARS = 500

try:  # optional convenience: pick DB_PATH up from ../.env
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass

# Accepted header names for each logical field (first match wins).
FIELD_ALIASES = {
    "category":     ("intent", "category"),
    "question":     ("question",),
    "answer":       ("response", "content_chunk", "answer"),
    "keywords":     ("keywords",),
    "source_url":   ("source_url",),
    "source_type":  ("source_type",),
}


def resolve_db_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT_DIR / path


def get_connection(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        print(f"Database not found at {db_path} - run `python database/init_db.py` first.", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    has_schema = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'kb_questions'"
    ).fetchone()
    if not has_schema:
        print("Database is missing the kb_questions table - re-run database/init_db.py "
              "(use --reset on a fresh database).", file=sys.stderr)
        sys.exit(1)
    return conn


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def pick(row: dict, field: str) -> str:
    for alias in FIELD_ALIASES[field]:
        if alias in row:
            return clean_text(row[alias])
    return ""


def detect_layout(fieldnames) -> str:
    names = {(n or "").strip().lower() for n in (fieldnames or [])}
    has_answer = bool(names & set(FIELD_ALIASES["answer"]))
    if not has_answer:
        print(f"CSV needs an answer column ({', '.join(FIELD_ALIASES['answer'])}). "
              f"Found: {sorted(names)}", file=sys.stderr)
        sys.exit(1)
    return "training-dataset" if {"intent", "question", "response"} <= names else "legacy-kb"


def get_or_create_category(cursor, name: str, stats: dict) -> int:
    name = clean_text(name) or DEFAULT_CATEGORY
    cursor.execute("SELECT category_id FROM kb_categories WHERE name = ?", (name,))  # NOCASE column
    row = cursor.fetchone()
    if row:
        return row[0]
    is_fallback = 1 if name.lower() == FALLBACK_INTENT else 0
    cursor.execute(
        "INSERT INTO kb_categories (name, is_fallback) VALUES (?, ?)", (name, is_fallback)
    )
    stats["categories_created"] += 1
    return cursor.lastrowid


def get_or_create_doc(cursor, category_id: int, content: str, keywords: str,
                      source_url: str, source_type: str, stats: dict) -> int:
    """One knowledge_base row per unique answer within a category."""
    cursor.execute(
        "SELECT doc_id FROM knowledge_base WHERE category_id = ? AND content_chunk = ?",
        (category_id, content),
    )
    row = cursor.fetchone()
    if row:
        stats["answers_reused"] += 1
        return row[0]
    cursor.execute(
        """
        INSERT INTO knowledge_base
            (category_id, content_chunk, keywords, source_url, source_type, status)
        VALUES (?, ?, ?, ?, ?, 'active')
        """,
        (category_id, content, keywords or None, source_url or None, source_type),
    )
    stats["answers_inserted"] += 1
    return cursor.lastrowid


def add_question(cursor, doc_id: int, question: str, stats: dict) -> None:
    question = question[:MAX_QUESTION_CHARS]
    cursor.execute(
        "INSERT OR IGNORE INTO kb_questions (doc_id, question_text) VALUES (?, ?)",
        (doc_id, question),
    )
    if cursor.rowcount:
        stats["questions_inserted"] += 1
    else:
        stats["questions_duplicate"] += 1


def load_csv(path: str, cursor, source_type_arg: str | None):
    stats = {
        "layout": "",
        "categories_created": 0,
        "answers_inserted": 0, "answers_reused": 0,
        "questions_inserted": 0, "questions_duplicate": 0,
        "rows_skipped_short": 0,
    }

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [(n or "").strip().lower() for n in (reader.fieldnames or [])]
        layout = detect_layout(reader.fieldnames)
        stats["layout"] = layout
        default_type = source_type_arg or ("faq" if layout == "training-dataset" else "manual")

        for raw in reader:
            content = pick(raw, "answer")
            if len(content) < MIN_CONTENT_CHARS:
                stats["rows_skipped_short"] += 1
                continue

            category_name = pick(raw, "category") or DEFAULT_CATEGORY
            question = pick(raw, "question")
            source_url = pick(raw, "source_url")
            source_type = pick(raw, "source_type") or default_type
            keywords = pick(raw, "keywords")
            if not keywords and layout == "training-dataset":
                # Dublin Core-style tag: the intent label, e.g. "career resources"
                keywords = category_name.replace("_", " ").lower()

            category_id = get_or_create_category(cursor, category_name, stats)
            doc_id = get_or_create_doc(cursor, category_id, content, keywords,
                                       source_url, source_type, stats)
            if question:
                add_question(cursor, doc_id, question, stats)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Load a KB CSV into the SQLite database")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--db", default=os.environ.get("DB_PATH", DEFAULT_DB),
                        help="SQLite file (default: $DB_PATH or data/mfano_bora_chatbot.db)")
    parser.add_argument("--source-type", default=None, choices=["manual", "scraped", "faq"],
                        help="default source_type (training dataset -> faq, legacy -> manual)")
    parser.add_argument("--dry-run", action="store_true", help="parse and validate, then roll back")
    args = parser.parse_args()

    db_path = resolve_db_path(args.db)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    print(f"Loading {args.csv} -> {db_path}")
    try:
        stats = load_csv(args.csv, cursor, args.source_type)
        if args.dry_run:
            conn.rollback()
            print("(dry run - nothing written)")
        else:
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    print(f"Layout detected      : {stats['layout']}")
    print(f"Categories created   : {stats['categories_created']}")
    print(f"Answers inserted     : {stats['answers_inserted']} (reused existing: {stats['answers_reused']})")
    print(f"Questions inserted   : {stats['questions_inserted']} (duplicates skipped: {stats['questions_duplicate']})")
    print(f"Rows skipped (short) : {stats['rows_skipped_short']}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
