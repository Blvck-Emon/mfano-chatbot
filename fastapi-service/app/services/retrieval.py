"""
retrieval.py
============
Task 10 (Information Retrieval Design) implementation.

Lightweight retrieval strategy: MySQL FULLTEXT search in NATURAL
LANGUAGE MODE against the `knowledge_base` table, joined to
`kb_categories` for display. This avoids standing up a separate
vector database while still giving relevance-ranked results.

Upgrade path (documented, not required to run the system): populate
`knowledge_base.embedding_json` with sentence-transformer vectors and
re-rank the FULLTEXT candidates with cosine similarity in
`rerank_with_embeddings()` below. Left as a clearly marked extension
point rather than a hard dependency, keeping the base service light.
"""

from typing import List, Dict, Any

from app.config import settings


def search_knowledge_base(cursor, query: str, top_k: int = None) -> List[Dict[str, Any]]:
    top_k = top_k or settings.TOP_K_RESULTS

    sql = """
        SELECT
            kb.doc_id,
            kb.question,
            kb.content_chunk,
            kb.source_url,
            cat.name AS category,
            MATCH(kb.question, kb.content_chunk, kb.keywords)
                AGAINST (%s IN NATURAL LANGUAGE MODE) AS relevance
        FROM knowledge_base kb
        LEFT JOIN kb_categories cat ON cat.category_id = kb.category_id
        WHERE kb.status = 'active'
          AND MATCH(kb.question, kb.content_chunk, kb.keywords)
              AGAINST (%s IN NATURAL LANGUAGE MODE)
        ORDER BY relevance DESC
        LIMIT %s
    """
    cursor.execute(sql, (query, query, top_k))
    columns = [c[0] for c in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def rerank_with_embeddings(candidates: List[Dict[str, Any]], query_embedding: List[float]):
    """
    Optional semantic re-ranking hook. No-op unless callers pass a
    query embedding AND rows have `embedding_json` populated -- kept
    out of the default request path so the service has zero ML
    dependencies unless the operator opts in.
    """
    import json
    import math

    def cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    scored = []
    for row in candidates:
        emb_raw = row.get("embedding_json")
        if not emb_raw:
            scored.append((row, row.get("relevance", 0)))
            continue
        try:
            emb = json.loads(emb_raw)
            scored.append((row, cosine(query_embedding, emb)))
        except (ValueError, TypeError):
            scored.append((row, row.get("relevance", 0)))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [row for row, _ in scored]
