"""
load_csv_to_mysql.py
=====================
Task-5/6/8 tool (Knowledge Base Development, Organization, Cleaning).

Loads one or more knowledge-base CSV files (the hand-curated
`database/seed_faq.csv` and/or the scraper's
`database/knowledge_base_scraped.csv`) into the MySQL
`knowledge_base` table, performing basic cleaning along the way:

  * strips whitespace, collapses repeated spaces
  * drops empty/too-short rows
  * de-duplicates against existing rows (same source_url + first 120
    chars of content_chunk) so re-running the scraper + loader on a
    cron job doesn't create duplicate KB entries
  * resolves the human-readable `category` column to the correct
    `kb_categories.category_id`, creating the category if it is new

Usage:
    python load_csv_to_mysql.py --csv ../database/seed_faq.csv
    python load_csv_to_mysql.py --csv ../database/knowledge_base_scraped.csv

Reads DB credentials from environment variables (see ../.env.example):
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import argparse
import csv
import os
import re
import sys

import mysql.connector
from mysql.connector import errorcode

MIN_CONTENT_CHARS = 20


def get_connection():
    try:
        return mysql.connector.connect(
            host=os.environ.get("DB_HOST", "127.0.0.1"),
            port=int(os.environ.get("DB_PORT", 3306)),
            user=os.environ.get("DB_USER", "mfano_app"),
            password=os.environ.get("DB_PASSWORD", ""),
            database=os.environ.get("DB_NAME", "mfano_bora_chatbot"),
        )
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("DB access denied - check DB_USER/DB_PASSWORD.", file=sys.stderr)
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist - run database/schema.sql first.", file=sys.stderr)
        else:
            print(f"DB connection error: {err}", file=sys.stderr)
        sys.exit(1)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def get_or_create_category(cursor, name: str) -> int:
    name = clean_text(name) or "General FAQ"
    cursor.execute("SELECT category_id FROM kb_categories WHERE name = %s", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO kb_categories (name) VALUES (%s)", (name,))
    return cursor.lastrowid


def row_exists(cursor, source_url: str, content_chunk: str) -> bool:
    fingerprint = content_chunk[:120]
    cursor.execute(
        """
        SELECT doc_id FROM knowledge_base
        WHERE (source_url = %s AND source_url <> '')
           OR content_chunk LIKE %s
        LIMIT 1
        """,
        (source_url, f"{fingerprint}%"),
    )
    return cursor.fetchone() is not None


def load_csv(path: str, cursor, source_type_default: str):
    inserted, skipped_dupe, skipped_short = 0, 0, 0

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            content = clean_text(raw.get("content_chunk", ""))
            if len(content) < MIN_CONTENT_CHARS:
                skipped_short += 1
                continue

            question = clean_text(raw.get("question", ""))
            keywords = clean_text(raw.get("keywords", ""))
            source_url = clean_text(raw.get("source_url", ""))
            source_type = clean_text(raw.get("source_type", "")) or source_type_default
            category_name = clean_text(raw.get("category", "")) or "General FAQ"

            if row_exists(cursor, source_url, content):
                skipped_dupe += 1
                continue

            category_id = get_or_create_category(cursor, category_name)

            cursor.execute(
                """
                INSERT INTO knowledge_base
                    (category_id, question, content_chunk, keywords, source_url, source_type, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'active')
                """,
                (category_id, question or None, content, keywords or None, source_url or None, source_type),
            )
            inserted += 1

    return inserted, skipped_dupe, skipped_short


def main():
    parser = argparse.ArgumentParser(description="Load a KB CSV into MySQL")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--source-type", default="manual", choices=["manual", "scraped", "faq"])
    args = parser.parse_args()

    conn = get_connection()
    cursor = conn.cursor()

    print(f"Loading {args.csv} ...")
    inserted, dupes, short = load_csv(args.csv, cursor, args.source_type)
    conn.commit()

    print(f"Inserted: {inserted} | Skipped (duplicate): {dupes} | Skipped (too short): {short}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
