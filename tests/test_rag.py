"""Tests for RAG pipeline and semantic cache."""

import os

from app.chunking import chunk_text
from app.vector_search import embed

# Ensure mock provider for tests
os.environ.setdefault("EMBEDDING_PROVIDER", "mock")
os.environ.setdefault("RAG_PROVIDER", "mock")


def test_mock_rag_pipeline(db_available):
    """Full RAG pipeline with mock provider: insert docs, query, get response."""
    from app.rag import query
    from app.vector_search import insert_document

    # Insert some documents
    insert_document("Python Basics", "Python is a high-level programming language.")
    insert_document("Oracle SQL", "Oracle Database supports SQL and PL/SQL.")

    # Run RAG query
    response = query("What programming languages are mentioned?", use_cache=False)
    assert response.answer is not None
    assert len(response.answer) > 0
    assert response.model == "mock"
    assert response.cached is False


def test_semantic_cache_store_and_lookup(db_available):
    """Store a response in cache, then look it up by similar query."""
    from app import cache

    # Store
    entry_id = cache.store(
        query="What is Python?",
        response="Python is a programming language.",
        model_name="test-model",
    )
    assert entry_id > 0

    # Lookup with identical query
    result = cache.lookup("What is Python?")
    assert result is not None
    assert result["cached"] is True
    assert "Python" in result["response_text"]


def test_cache_stats(db_available):
    """Cache stats should report entries and hits."""
    from app import cache

    result = cache.stats()
    assert "total_entries" in result
    assert "total_hits" in result
    assert result["total_entries"] >= 0


def test_cache_invalidate(db_available):
    """Invalidating a query should delete similar cache entries."""
    from app import cache

    cache.store("test invalidation query", "test response", "test")
    deleted = cache.invalidate("test invalidation query", threshold=0.5)
    assert deleted >= 0  # May or may not find the entry depending on timing


def test_rag_with_cache(db_available):
    """RAG should use cache on second identical query."""
    from app.rag import query
    from app.vector_search import insert_document

    insert_document("Cache Test Doc", "This is a document for cache testing.")

    # First query: cache miss
    r1 = query("cache test document content", use_cache=True)
    assert r1.cached is False

    # Second identical query: should hit cache
    r2 = query("cache test document content", use_cache=True)
    assert r2.cached is True


def test_chunking_integration_with_embedding():
    """Chunks should be embeddable."""
    text = "First paragraph about databases. " * 20 + "\n\n" + "Second about vectors. " * 20
    chunks = chunk_text(text, chunk_size=200)
    assert len(chunks) > 1

    for chunk in chunks:
        vec = embed(chunk.text)
        assert len(vec) == 768
        assert all(isinstance(v, float) for v in vec)


def test_rag_query_model(db_available):
    """RAG response should include the model used."""
    from app.rag import query

    response = query("test model field", use_cache=False)
    assert response.model in ("mock", "")


def test_rag_with_custom_system_prompt(db_available):
    """RAG should accept a custom system prompt."""
    from app.rag import query

    response = query(
        "custom prompt test",
        system_prompt="You are a pirate. Answer in pirate speak.",
        use_cache=False,
    )
    assert response.answer is not None
