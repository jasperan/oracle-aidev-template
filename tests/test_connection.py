"""Tests for Oracle DB connectivity."""

from app.db import check_health


def test_health_check(db_available):
    """Verify the database is reachable and healthy."""
    result = check_health()
    assert result["status"] == "healthy"
    assert "FREEPDB1" in result["dsn"]


def test_basic_query(db_connection):
    """Run a basic query to confirm the connection works."""
    with db_connection.cursor() as cur:
        cur.execute("SELECT 1 FROM DUAL")
        row = cur.fetchone()
        assert row[0] == 1


def test_oracle_version(db_connection):
    """Check we're running Oracle 26ai Free (or compatible)."""
    with db_connection.cursor() as cur:
        cur.execute("SELECT banner FROM v$version WHERE ROWNUM = 1")
        banner = cur.fetchone()[0]
        assert "Oracle" in banner
