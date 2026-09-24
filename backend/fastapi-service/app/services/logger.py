"""
logger.py
=========
Task 15/17 support: persists chat turns to SQLite for security auditing,
KPI aggregation, and the admin dashboard's chat log viewer. Also feeds
`kb_gap_log` when the bot falls back, so unanswered questions surface
for Task 13 (Information Gap Analysis).
"""

import hashlib
import uuid
from typing import Optional


def hash_ip(ip: str) -> Optional[str]:
    """One-way hash so raw IPs are never stored (Task 15: privacy)."""
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def ensure_session(cursor, session_id: Optional[str], ip_hash: Optional[str]) -> str:
    if session_id:
        cursor.execute("SELECT session_id FROM chat_sessions WHERE session_id = ?", (session_id,))
        if cursor.fetchone():
            return session_id

    new_id = session_id or str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO chat_sessions (session_id, ip_hash, status) VALUES (?, ?, 'active')",
        (new_id, ip_hash),
    )
    return new_id


def log_message(cursor, session_id: str, sender_type: str, message_text: str,
                 intent_matched: Optional[str] = None, doc_id_matched: Optional[int] = None,
                 was_fallback: bool = False):
    cursor.execute(
        """
        INSERT INTO chat_logs (session_id, sender_type, message_text, intent_matched, doc_id_matched, was_fallback)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session_id, sender_type, message_text, intent_matched, doc_id_matched, int(was_fallback)),
    )


def log_gap(cursor, query_text: str):
    """Track (or bump the frequency of) a question the KB couldn't answer."""
    cursor.execute(
        "SELECT gap_id, frequency FROM kb_gap_log WHERE unanswered_query = ? AND status != 'resolved'",
        (query_text,),
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(
            "UPDATE kb_gap_log SET frequency = frequency + 1 WHERE gap_id = ?", (row[0],)
        )
    else:
        cursor.execute(
            "INSERT INTO kb_gap_log (unanswered_query, frequency) VALUES (?, 1)", (query_text,)
        )
