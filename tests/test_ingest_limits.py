"""Ingest is bounded before any embedding or insert can happen."""

import pytest
from fastapi.testclient import TestClient

from app import main as main_mod


@pytest.fixture
def client():
    return TestClient(main_mod.app, raise_server_exceptions=False)


def test_content_longer_than_the_limit_is_rejected(client):
    resp = client.post(
        "/documents/ingest",
        json={"title": "t", "content": "x" * (main_mod.MAX_CONTENT_CHARS + 1)},
    )
    assert resp.status_code == 422


def test_chunk_count_over_the_limit_never_reaches_the_store(client, monkeypatch):
    calls = []
    monkeypatch.setattr(main_mod, "insert_document", lambda *a, **k: calls.append(a))

    text = ("Vector databases store embeddings and answer similarity queries. " * 3000)[:150_000]
    resp = client.post(
        "/documents/ingest",
        json={"title": "t", "content": text, "chunk_size": 100, "chunk_overlap": 0},
    )

    assert resp.status_code == 413
    assert "chunks" in resp.json()["detail"]
    assert calls == []


def test_document_create_is_bounded_too(client):
    resp = client.post(
        "/documents",
        json={"title": "t", "content": "x" * (main_mod.MAX_CONTENT_CHARS + 1)},
    )
    assert resp.status_code == 422
