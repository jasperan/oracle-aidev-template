"""Shared test fixtures for Oracle AI Dev Template."""

import os

import pytest

# Default to mock embeddings in tests
os.environ.setdefault("EMBEDDING_PROVIDER", "mock")


@pytest.fixture(scope="session")
def db_available():
    """Check if Oracle DB is reachable. Skip tests if not."""
    from app.db import check_health

    if check_health()["status"] != "healthy":
        pytest.skip("Oracle DB not available")
    return True


@pytest.fixture
def db_connection(db_available):
    """Provide a test database connection."""
    from app.db import get_connection

    with get_connection() as conn:
        yield conn
