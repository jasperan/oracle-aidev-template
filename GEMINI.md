# Gemini Instructions: Oracle AI Dev Template

This is a GitHub template for building AI-powered Python apps on Oracle 26ai Free Database with FastAPI and AI Vector Search.

## Project Context

You are working on a FastAPI application backed by Oracle 26ai Free. The app provides document CRUD operations and semantic similarity search using Oracle's native VECTOR type and HNSW indexes.

## How to Start

```bash
# Start Oracle 26ai Free container
./scripts/start-db.sh

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload

# Or run everything via Docker
docker compose up
```

## How to Test

```bash
pytest tests/ -v
```

DB-dependent tests auto-skip when Oracle isn't running. Mock embedding tests always pass.

## Key Files

- `app/main.py` -- FastAPI app with health check (`GET /`), document CRUD (`POST/GET /documents`), vector search (`POST /search`), RAG (`POST /rag`), cache (`GET /cache/stats`, `DELETE /cache`), and document ingestion (`POST /documents/ingest`)
- `app/db.py` -- Oracle connection pool using `oracledb`. Lazy init, context manager pattern via `get_connection()`
- `app/vector_search.py` -- Embedding generation (mock hash-based or Ollama) and `VECTOR_DISTANCE` similarity queries
- `app/rag.py` -- RAG pipeline: retrieve context chunks via vector search, generate answers via Ollama
- `app/cache.py` -- Semantic cache: store query-response pairs with vector embeddings, skip LLM on similar repeat questions
- `app/chunking.py` -- Document chunking: split large documents into overlapping chunks for ingestion
- `scripts/init-schema.sql` -- Creates `documents` table (with `VECTOR` column + HNSW index) and `metadata` table
- `docker-compose.yml` -- Oracle 26ai Free (`oracle-aidev-db`), production app, and dev container with hot-reload
- `tests/conftest.py` -- Fixtures: `db_available` (skips when no DB), `db_connection` (provides live connection)

## Oracle Database

- **Container**: `oracle-aidev-db`
- **Port**: 1521
- **Service**: `FREEPDB1`
- **User/Password**: `system` / `FreeP4ssw0rd!` (configurable via env vars)

Connect via sqlplus:
```bash
docker exec -it oracle-aidev-db sqlplus system/${ORACLE_PWD}@FREEPDB1
```

## Coding Standards

- Python 3.11+ with type hints on all functions
- `ruff` for linting (line length 100). `mypy` for type checking.
- FastAPI + Pydantic v2 for the API layer
- `oracledb` for database access, always through the pool in `app.db`
- Bind variables (`:param` style) in all SQL. Never concatenate user input.

## Oracle SQL Patterns

Follow these patterns when writing Oracle SQL:

**Table creation:**
```sql
CREATE TABLE items (
    id          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR2(200) NOT NULL,
    description CLOB,
    embedding   VECTOR,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Vector index:**
```sql
CREATE VECTOR INDEX idx_items_embedding
    ON items (embedding)
    ORGANIZATION NEIGHBOR PARTITIONS
    WITH DISTANCE COSINE;
```

**Similarity search:**
```sql
SELECT id, name,
       VECTOR_DISTANCE(embedding, :query_vec, COSINE) AS distance
FROM items
ORDER BY VECTOR_DISTANCE(embedding, :query_vec, COSINE)
FETCH FIRST :top_k ROWS ONLY
```

**RETURNING INTO (not RETURNING *):**
```python
doc_id_var = cur.var(int)
cur.execute(
    "INSERT INTO items (name) VALUES (:name) RETURNING id INTO :doc_id",
    {"name": "test", "doc_id": doc_id_var},
)
new_id = doc_id_var.getvalue()[0]
```

## RAG Pipeline

The `POST /rag` endpoint retrieves relevant document chunks via vector search, then generates an answer using Ollama. Controlled by `RAG_PROVIDER` (default: `ollama`), `OLLAMA_CHAT_MODEL`, and `RAG_TOP_K`. Set `RAG_USE_CACHE=true` to check the semantic cache before calling the LLM.

## Semantic Cache

The cache stores query-response pairs with vector embeddings. On repeated or similar questions (within `CACHE_SIMILARITY_THRESHOLD`), the cached response is returned without hitting the LLM.

- `GET /cache/stats` -- cache hit/miss counts and entry total.
- `DELETE /cache` -- flush all cached entries.

## Document Chunking

The `POST /documents/ingest` endpoint accepts a large document and splits it into overlapping chunks. Each chunk is stored with a `parent_id` linking back to the original document and a `chunk_index` for ordering.

## Common Pitfalls

- **Reserved words as columns**: don't use `mode`, `level`, `comment`, `value`, `date`, `type`, `status`, `user`, `role`, `size` as column names. Rename them or quote with double quotes.
- **CLOB handling**: `CLOB` for text > 4000 bytes. Reads work transparently; large writes (> 1GB) need `cursor.setinputsizes()`.
- **No NOW()**: use `CURRENT_TIMESTAMP` instead.
- **No LIMIT**: use `FETCH FIRST N ROWS ONLY` instead.
- **No RETURNING ***: use `RETURNING col INTO :bind_var` with `cursor.var()`.

## Environment Variables

Defaults work out of the box. Override via `.env` file (see `.env.example`):

| Variable | Default | Notes |
|----------|---------|-------|
| `ORACLE_HOST` | `localhost` | |
| `ORACLE_PORT` | `1521` | |
| `ORACLE_SERVICE` | `FREEPDB1` | |
| `ORACLE_PWD` | `FreeP4ssw0rd!` | |
| `EMBEDDING_PROVIDER` | `mock` | `mock` or `ollama` |
| `OLLAMA_HOST` | `http://localhost:11434` | Only needed when provider is `ollama` |
| `OLLAMA_MODEL` | `nomic-embed-text` | Only needed when provider is `ollama` |
| `RAG_PROVIDER` | `ollama` | RAG generation backend |
| `OLLAMA_CHAT_MODEL` | `llama3` | Ollama model for RAG generation |
| `RAG_TOP_K` | `5` | Number of chunks retrieved for RAG context |
| `RAG_USE_CACHE` | `true` | Check semantic cache before calling LLM |
| `CACHE_SIMILARITY_THRESHOLD` | `0.95` | Cosine similarity threshold for cache hits |
