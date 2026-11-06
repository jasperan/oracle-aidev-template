"""The app must never fall back to a repository-shipped database credential."""

import importlib

import pytest


def test_no_default_password_and_pool_fails_closed(monkeypatch):
    monkeypatch.delenv("ORACLE_PWD", raising=False)
    import app.db as db

    reloaded = importlib.reload(db)
    try:
        assert reloaded.PASSWORD is None
        reloaded._pool = None
        with pytest.raises(RuntimeError, match="ORACLE_PWD"):
            reloaded.get_pool()
        assert reloaded._pool is None
    finally:
        importlib.reload(db)


def test_health_check_reports_unhealthy_without_password(monkeypatch):
    monkeypatch.delenv("ORACLE_PWD", raising=False)
    import app.db as db

    reloaded = importlib.reload(db)
    try:
        result = reloaded.check_health()
        assert result["status"] == "unhealthy"
        assert "ORACLE_PWD" in result["error"]
    finally:
        importlib.reload(db)
