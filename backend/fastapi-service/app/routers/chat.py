"""
POST /api/v1/chat/query
========================
The single endpoint the frontend floating widget calls. Implements the
data-pipeline workflow from the requirements doc, adapted to SQLite:

    1. Receive user message (+ optional session_id)
    2. FTS5 search the training questions + knowledge_base for top-K chunks
    3. Send chunks + question to Groq LLM with a guardrail system prompt
       (a hit on the `fallback` intent skips the LLM and returns its
       stored reply, flagged as a fallback)
    4. Log both turns to SQLite (chat_sessions/chat_logs), track KB gaps
    5. Return the reply + which KB sources were used
"""

import sqlite3

from fastapi import APIRouter, Depends, Request

from app.db import get_connection
from app.models import ChatQueryRequest, ChatQueryResponse, SourceRef
from app.services import retrieval, llm, logger as chat_logger

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/query", response_model=ChatQueryResponse)
def chat_query(payload: ChatQueryRequest, request: Request, conn: sqlite3.Connection = Depends(get_connection)):
    # The connection is in autocommit mode (see app/db.py): every statement is
    # committed immediately, so no write lock is held while waiting on the LLM.
    cursor = conn.cursor()

    client_ip = request.client.host if request.client else ""
    ip_hash = chat_logger.hash_ip(client_ip)
    session_id = chat_logger.ensure_session(cursor, payload.session_id, ip_hash)

    # 1. Log the incoming user message.
    chat_logger.log_message(cursor, session_id, "user", payload.message)

    # 2. Retrieve relevant KB chunks (Task 10).
    hits = retrieval.search_knowledge_base(cursor, payload.message)
    top = hits[0] if hits else None

    # 3. Generate the reply.
    if top and top.get("is_fallback"):
        # The dataset's `fallback` intent: answer with its stored reply, no LLM call.
        kb_rows = [top]
        reply = top["content_chunk"]
        fallback = True
    else:
        # Fallback-intent rows are never useful as grounding context for a real answer.
        kb_rows = [row for row in hits if not row.get("is_fallback")]
        reply = llm.generate_reply(payload.message, kb_rows)
        fallback = llm.is_fallback_reply(reply) or not kb_rows

    # 4. Log the bot reply + track gaps for unanswered queries.
    top_doc_id = kb_rows[0]["doc_id"] if kb_rows else None
    chat_logger.log_message(
        cursor, session_id, "bot", reply,
        intent_matched=(kb_rows[0].get("category") if kb_rows else None),
        doc_id_matched=top_doc_id,
        was_fallback=fallback,
    )
    if fallback:
        chat_logger.log_gap(cursor, payload.message)

    cursor.close()

    sources = [
        SourceRef(doc_id=row["doc_id"], category=row.get("category"), source_url=row.get("source_url"))
        for row in kb_rows
    ] if not fallback else []

    return ChatQueryResponse(session_id=session_id, reply=reply, is_fallback=fallback, sources=sources)
