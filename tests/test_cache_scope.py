"""Cache entries are namespaced by server policy and model."""

from contextlib import contextmanager

import app.cache as cache
import app.rag as rag


def _record_queries(monkeypatch):
    seen = []

    class _Cursor:
        rowcount = 0

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, sql, params=None):
            seen.append((" ".join(sql.split()), dict(params or {})))

        def fetchone(self):
            return None

        def fetchall(self):
            return []

        def var(self, _typ):
            class _Var:
                def getvalue(self):
                    return [1]

            return _Var()

    class _Conn:
        def cursor(self):
            return _Cursor()

        def commit(self):
            pass

        def rollback(self):
            pass

    @contextmanager
    def _cm():
        yield _Conn()

    monkeypatch.setattr(cache, "get_connection", _cm)
    return seen


def test_lookup_and_store_bind_the_scope(monkeypatch):
    seen = _record_queries(monkeypatch)

    cache.lookup("q", scope="scope-a")
    cache.store("q", "an answer", model_name="mock", scope="scope-a")

    lookup_sql, lookup_params = seen[0]
    store_sql, store_params = seen[1]
    assert "scope_key = :scope" in lookup_sql
    assert lookup_params["scope"] == "scope-a"
    assert "scope_key" in store_sql
    assert store_params["scope"] == "scope-a"


def test_scope_key_depends_on_policy_and_model():
    base = cache.scope_key("policy", "mock")
    assert base == cache.scope_key("policy", "mock")
    assert base != cache.scope_key("other policy", "mock")
    assert base != cache.scope_key("policy", "other-model")


def test_rag_scopes_the_cache_by_prompt(monkeypatch):
    scopes = []

    monkeypatch.setattr(rag.cache, "lookup", lambda q, scope="": scopes.append(scope))
    monkeypatch.setattr(rag.cache, "store", lambda *a, **k: scopes.append(k.get("scope")))
    monkeypatch.setattr(rag, "search_similar", lambda q, top_k=5: [])

    rag.query("same question", use_cache=True)
    rag.query("same question", system_prompt="a different policy", use_cache=True)

    assert len(scopes) == 4
    assert scopes[0] == scopes[1]
    assert scopes[2] == scopes[3]
    assert scopes[0] != scopes[2]
