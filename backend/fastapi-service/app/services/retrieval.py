"""
retrieval.py
============
Task 10 (Information Retrieval Design) implementation.

Lightweight retrieval strategy using SQLite FTS5 (BM25 ranking, Porter
stemming) -- the replacement for MySQL's FULLTEXT ... NATURAL LANGUAGE MODE.
Three stages, in priority order:

  0. EXACT       the message equals a curated training question (ignoring
                 case, spacing and trailing punctuation). Deterministic:
                 every question in the training CSV returns its own answer.
  1. QUESTIONS   `kb_questions_fts` -- fuzzy match against the training
                 questions. A hit returns the linked answer, so "Where's
                 your office?" finds the 'location' reply even though the
                 answer text never says "office".
  2. CONTENT     `knowledge_base_fts` -- answer text + keywords; covers
                 scraped web chunks and admin-entered content that has no
                 training questions.

Earlier stages rank first; remaining slots are filled by later stages. Each
document appears at most once.

Every row returned has: doc_id, question (the matched training question, or
None), content_chunk, source_url, category, is_fallback, relevance
(higher = better).

Upgrade path (documented, not required to run the system): populate
`knowledge_base.embedding_json` with sentence-transformer vectors and
re-rank the FTS candidates with cosine similarity in
`rerank_with_embeddings()` below. Left as a clearly marked extension
point rather than a hard dependency, keeping the base service light.
"""

import re
from typing import Any, Dict, List

from app.config import settings

# Ignored when building the search expression so that filler words alone
# ("what is the ...") never count as a match -- the same job MySQL's
# built-in InnoDB stopword list used to do. Domain words are NOT listed.
_STOPWORDS = frozenset("""
a an the and or but if of to in on at by for with from as into onto over
is are was were be been being am do does did done can could will would
should shall may might must have has had having
i me my mine we us our ours you your yours he him his she her it its they them their
this that these those there here what which who whom whose how when where why
about please tell show give let get want like know any some
""".split())

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_MIN_TOKEN_LEN = 2  # keeps short domain terms such as "cv" and "ai"

# How many raw hits to pull per index before de-duplicating per document.
_CANDIDATE_MULTIPLIER = 8


def build_match_expression(query: str) -> str:
    """
    Turn free text into a safe FTS5 expression: "tok1" OR "tok2" OR ...
    Only \\w+ tokens are emitted (each double-quoted), so user input can
    never inject FTS5 syntax. If the message is made only of stopwords
    ("who are you?") they are used as-is rather than returning nothing.
    """
    tokens = [t for t in _WORD_RE.findall((query or "").lower()) if len(t) >= _MIN_TOKEN_LEN]
    content_tokens = [t for t in tokens if t not in _STOPWORDS]
    chosen = content_tokens or tokens
    # de-duplicate, keep order
    chosen = list(dict.fromkeys(chosen))
    return " OR ".join(f'"{t}"' for t in chosen)


_EXACT_SQL = """
    SELECT kb.doc_id                       AS doc_id,
           kq.question_text                AS question,
           kb.content_chunk                AS content_chunk,
           kb.source_url                   AS source_url,
           cat.name                        AS category,
           COALESCE(cat.is_fallback, 0)    AS is_fallback
    FROM kb_questions kq
    JOIN knowledge_base kb ON kb.doc_id = kq.doc_id
    LEFT JOIN kb_categories cat ON cat.category_id = kb.category_id
    WHERE lower(rtrim(kq.question_text, '?!. ')) = ?
      AND kb.status = 'active'
    ORDER BY kq.question_id
    LIMIT 1
"""


def normalise_question(text: str) -> str:
    """Lower-case, collapse whitespace, drop trailing ?!. -- mirrors _EXACT_SQL."""
    return re.sub(r"\s+", " ", (text or "").strip()).lower().rstrip("?!. ")


_QUESTION_SQL = """
    SELECT kb.doc_id                       AS doc_id,
           kq.question_text                AS question,
           kb.content_chunk                AS content_chunk,
           kb.source_url                   AS source_url,
           cat.name                        AS category,
           COALESCE(cat.is_fallback, 0)    AS is_fallback,
           bm25(kb_questions_fts)          AS score
    FROM kb_questions_fts
    JOIN kb_questions kq  ON kq.question_id = kb_questions_fts.rowid
    JOIN knowledge_base kb ON kb.doc_id = kq.doc_id
    LEFT JOIN kb_categories cat ON cat.category_id = kb.category_id
    WHERE kb_questions_fts MATCH ?
      AND kb.status = 'active'
    ORDER BY score
    LIMIT ?
"""

# bm25 weights follow the FTS column order (content_chunk, keywords):
# a keyword match counts double.
_CONTENT_SQL = """
    SELECT kb.doc_id                       AS doc_id,
           NULL                            AS question,
           kb.content_chunk                AS content_chunk,
           kb.source_url                   AS source_url,
           cat.name                        AS category,
           COALESCE(cat.is_fallback, 0)    AS is_fallback,
           bm25(knowledge_base_fts, 1.0, 2.0) AS score
    FROM knowledge_base_fts
    JOIN knowledge_base kb ON kb.doc_id = knowledge_base_fts.rowid
    LEFT JOIN kb_categories cat ON cat.category_id = kb.category_id
    WHERE knowledge_base_fts MATCH ?
      AND kb.status = 'active'
    ORDER BY score
    LIMIT ?
"""


def search_knowledge_base(cursor, query: str, top_k: int = None) -> List[Dict[str, Any]]:
    top_k = top_k or settings.TOP_K_RESULTS
    match = build_match_expression(query)
    if not match:
        return []  # nothing searchable (empty / punctuation-only message)

    limit = top_k * _CANDIDATE_MULTIPLIER
    results: Dict[int, Dict[str, Any]] = {}

    # Stage 0: exact match on a curated training question always ranks first.
    cursor.execute(_EXACT_SQL, (normalise_question(query),))
    exact = cursor.fetchone()
    if exact:
        row = dict(exact)
        row["relevance"] = 1e9  # sentinel: above any BM25 score
        results[row["doc_id"]] = row

    for sql in (_QUESTION_SQL, _CONTENT_SQL):
        cursor.execute(sql, (match, limit))
        for raw in cursor.fetchall():
            row = dict(raw)
            if row["doc_id"] in results:
                continue  # keep the best-ranked hit per document
            # FTS5 bm25() is lower-is-better (negative); expose higher-is-better.
            row["relevance"] = -float(row.pop("score"))
            results[row["doc_id"]] = row
            if len(results) >= top_k:
                break
        if len(results) >= top_k:
            break

    return list(results.values())


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
