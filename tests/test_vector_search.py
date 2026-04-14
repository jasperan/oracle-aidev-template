"""Tests for Oracle AI Vector Search functionality."""

import pytest

from app.vector_search import embed, insert_document, list_documents, search_similar


def test_mock_embedding_deterministic():
    """Mock embeddings should be deterministic for the same input."""
    v1 = embed("hello world")
    v2 = embed("hello world")
    assert v1 == v2
    assert len(v1) == 768


def test_mock_embedding_different_inputs():
    """Different inputs should produce different embeddings."""
    v1 = embed("hello")
    v2 = embed("goodbye")
    assert v1 != v2


def test_insert_document(db_available):
    """Insert a document and verify it gets an ID back."""
    doc_id = insert_document(
        title="Test Document",
        content="This is a test document for vector search.",
    )
    assert isinstance(doc_id, int)
    assert doc_id > 0


def test_list_documents(db_available):
    """List documents after inserting one."""
    insert_document(title="List Test", content="Document for listing test.")
    docs = list_documents(limit=10)
    assert len(docs) > 0
    assert "title" in docs[0]
    assert "content" in docs[0]


def test_search_similar(db_available):
    """Insert documents and search for similar ones."""
    insert_document(title="Python Guide", content="Python is a programming language.")
    insert_document(title="Java Guide", content="Java is a programming language.")
    insert_document(title="Cooking Tips", content="How to make a perfect sourdough bread.")

    results = search_similar("programming languages", top_k=2)
    assert len(results) <= 2
    for r in results:
        assert "id" in r
        assert "title" in r
        assert "distance" in r


@pytest.mark.parametrize("top_k", [1, 3, 5])
def test_search_top_k(db_available, top_k):
    """Verify top_k parameter is respected."""
    results = search_similar("test query", top_k=top_k)
    assert len(results) <= top_k
