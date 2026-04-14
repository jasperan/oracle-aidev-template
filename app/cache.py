"""Semantic cache: skip the LLM when a similar question was already answered.

Stores query-response pairs with vector embeddings. On new queries, checks if
a semantically similar question exists within a cosine distance threshold.
If found, returns the cached response. If not, the caller generates a fresh
response and stores it.

This is something standalone vector DBs can't do natively: SQL + vector
similarity in one atomic transaction, with ACID guarantees on the cache.
"""

import os
from typing import Any

from app.db import get_connection
from app.vector_search import embed

CACHE_THRESHOLD = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.15"))


def lookup(query: str) -> dict[str, Any] | None:
    """Check if a semantically similar query exists in the cache.

    Returns the cached response if cosine distance < threshold, else None.
    """
    query_vec = embed(query)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, query_text, response_text, model_name,
                       VECTOR_DISTANCE(query_embedding, :qvec, COSINE) AS distance
                FROM semantic_cache
                WHERE VECTOR_DISTANCE(query_embedding, :qvec, COSINE) < :threshold
                ORDER BY VECTOR_DISTANCE(query_embedding, :qvec, COSINE)
                FETCH FIRST 1 ROWS ONLY
                """,
                {"qvec": query_vec, "threshold": CACHE_THRESHOLD},
            )
            row = cur.fetchone()
            if row is None:
                return None

            # Bump hit count
            cur.execute(
                "UPDATE semantic_cache SET hit_count = hit_count + 1 WHERE id = :id",
                {"id": row[0]},
            )
            conn.commit()

            return {
                "query_text": row[1],
                "response_text": row[2],
                "model_name": row[3],
                "distance": float(row[4]),
                "cached": True,
            }


def store(query: str, response: str, model_name: str = "unknown") -> int:
    """Store a query-response pair in the semantic cache. Returns the cache entry ID."""
    query_vec = embed(query)
    with get_connection() as conn:
        with conn.cursor() as cur:
            id_var = cur.var(int)
            cur.execute(
                """
                INSERT INTO semantic_cache
                    (query_text, query_embedding, response_text, model_name)
                VALUES (:query, :qvec, :response, :model)
                RETURNING id INTO :new_id
                """,
                {
                    "query": query,
                    "qvec": query_vec,
                    "response": response,
                    "model": model_name,
                    "new_id": id_var,
                },
            )
            conn.commit()
            return int(id_var.getvalue()[0])


def invalidate(query: str, threshold: float | None = None) -> int:
    """Delete cache entries similar to the given query. Returns count deleted."""
    thresh = threshold or CACHE_THRESHOLD
    query_vec = embed(query)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM semantic_cache
                WHERE VECTOR_DISTANCE(query_embedding, :qvec, COSINE) < :threshold
                """,
                {"qvec": query_vec, "threshold": thresh},
            )
            count: int = cur.rowcount
            conn.commit()
            return count


def stats() -> dict[str, Any]:
    """Return cache statistics."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*), COALESCE(SUM(hit_count), 0) FROM semantic_cache"
            )
            row = cur.fetchone()
            return {
                "total_entries": row[0],
                "total_hits": int(row[1]),
            }
