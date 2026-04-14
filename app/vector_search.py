"""Oracle AI Vector Search helpers.

Provides embedding generation and similarity search against the documents table.
Supports two embedding providers:
  - "mock": deterministic hash-based vectors (no external deps, good for testing)
  - "ollama": real embeddings via a local Ollama instance
"""

import hashlib
import os
import struct
from typing import Any

import httpx

from app.db import get_connection

EMBEDDING_DIM = 768
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "mock")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "nomic-embed-text")


def _mock_embedding(text: str) -> list[float]:
    """Generate a deterministic pseudo-embedding from text hash. Good for testing."""
    h = hashlib.sha256(text.encode()).digest()
    # Expand hash to fill EMBEDDING_DIM floats deterministically
    chunks = []
    for i in range(EMBEDDING_DIM):
        seed = hashlib.sha256(h + struct.pack(">I", i)).digest()[:4]
        val = struct.unpack(">f", seed)[0]
        # Normalize to [-1, 1]
        chunks.append(max(-1.0, min(1.0, val / 1e38)))
    return chunks


def _ollama_embedding(text: str) -> list[float]:
    """Get a real embedding from Ollama."""
    resp = httpx.post(
        f"{OLLAMA_HOST}/api/embed",
        json={"model": OLLAMA_MODEL, "input": text},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]


def embed(text: str) -> list[float]:
    """Generate an embedding vector for the given text."""
    if EMBEDDING_PROVIDER == "ollama":
        return _ollama_embedding(text)
    return _mock_embedding(text)


def insert_document(title: str, content: str) -> int:
    """Insert a document with its embedding. Returns the new document ID."""
    vector = embed(content)
    with get_connection() as conn:
        with conn.cursor() as cur:
            doc_id_var = cur.var(int)
            cur.execute(
                """
                INSERT INTO documents (title, content, embedding)
                VALUES (:title, :content, :embedding)
                RETURNING id INTO :doc_id
                """,
                {
                    "title": title,
                    "content": content,
                    "embedding": vector,
                    "doc_id": doc_id_var,
                },
            )
            conn.commit()
            return doc_id_var.getvalue()[0]


def search_similar(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Find the top_k most similar documents to the query text."""
    query_vector = embed(query)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, content,
                       VECTOR_DISTANCE(embedding, :query_vec, COSINE) AS distance
                FROM documents
                ORDER BY VECTOR_DISTANCE(embedding, :query_vec, COSINE)
                FETCH FIRST :top_k ROWS ONLY
                """,
                {"query_vec": query_vector, "top_k": top_k},
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "title": r[1],
                    "content": r[2],
                    "distance": float(r[3]),
                }
                for r in rows
            ]


def list_documents(limit: int = 50) -> list[dict[str, Any]]:
    """List documents (without embeddings)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, content, created_at FROM documents "
                "ORDER BY created_at DESC FETCH FIRST :lim ROWS ONLY",
                {"lim": limit},
            )
            return [
                {"id": r[0], "title": r[1], "content": r[2], "created_at": str(r[3])}
                for r in cur.fetchall()
            ]
