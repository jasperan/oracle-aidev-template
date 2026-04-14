"""Shared test fixtures for Oracle AI Dev Template."""

import os

import pytest

# Default to mock embeddings in tests
os.environ.setdefault("EMBEDDING_PROVIDER", "mock")


@pytest.fixture(scope="session")
def db_available():
    """Check if Oracle DB is reachable. Skip tests if not."""
    try:
        import oracledb

        conn = oracledb.connect(
            user=os.getenv("ORACLE_USER", "system"),
            password=os.getenv("ORACLE_PWD", "FreeP4ssw0rd!"),
            dsn=f"{os.getenv('ORACLE_HOST', 'localhost')}:"
            f"{os.getenv('ORACLE_PORT', '1521')}/"
            f"{os.getenv('ORACLE_SERVICE', 'FREEPDB1')}",
        )
        conn.close()
        return True
    except Exception:
        pytest.skip("Oracle DB not available")


@pytest.fixture
def db_connection(db_available):
    """Provide a test database connection."""
    from app.db import get_connection

    with get_connection() as conn:
        yield conn
