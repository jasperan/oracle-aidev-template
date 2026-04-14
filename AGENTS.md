# Agent Instructions: Oracle AI Dev Template

These instructions are for any AI coding agent working on this repository. The project is a GitHub template for building AI-powered Python apps on Oracle 26ai Free Database with FastAPI and AI Vector Search.

## Setup and Running

Start the Oracle database:
```bash
./scripts/start-db.sh
```

Run the API server:
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run the full stack via Docker:
```bash
docker compose up
```

Run tests:
```bash
pytest tests/ -v
```

Tests with the `db_available` fixture skip automatically when Oracle isn't running. Mock embedding tests always work.

## Architecture

```
app/
  main.py            - FastAPI application (health, CRUD, vector search, RAG, cache, ingest endpoints)
  db.py              - Oracle connection pool (oracledb, lazy init, context manager)
  vector_search.py   - Embedding generation + VECTOR_DISTANCE similarity queries
  rag.py             - RAG pipeline: retrieve context via vector search, generate answers via Ollama
  cache.py           - Semantic cache: store query-response pairs with embeddings, skip LLM on similar repeats
  chunking.py        - Document chunking: split large docs into overlapping chunks for ingestion
scripts/
  start-db.sh        - Start Oracle container, wait for healthy
  stop-db.sh         - Stop Oracle container
  wait-for-db.sh     - Block until Oracle healthy (CI use)
  init-schema.sql    - DDL: documents table (with VECTOR column), metadata table
tests/
  conftest.py        - Fixtures: db_available (skip guard), db_connection
  test_connection.py - DB connectivity tests
  test_vector_search.py - Vector search tests (mock embeddings)
```

## Oracle Database Connection

- **Host**: `localhost` (env: `ORACLE_HOST`)
- **Port**: `1521` (env: `ORACLE_PORT`)
- **Service**: `FREEPDB1` (env: `ORACLE_SERVICE`)
- **User**: `system` (env: `ORACLE_USER`)
- **Password**: `FreeP4ssw0rd!` (env: `ORACLE_PWD`)
- **Container name**: `oracle-aidev-db`

The app uses `oracledb.create_pool()` for connection pooling. Always acquire connections through `app.db.get_connection()`, which returns a context manager.

## Coding Rules

1. **Python 3.11+**. Use `X | Y` union syntax, `list[T]` generics, type hints on all functions.
2. **ruff** for linting (line length 100, rules: E/F/I/UP/B). **mypy** for type checking.
3. **Bind variables** in all SQL (`:param` style). Never concatenate user input into queries.
4. **FastAPI + Pydantic v2** for endpoints. Use `BaseModel` with `Field()` for request/response models.
5. Use the existing connection pool from `app.db`. Don't create standalone connections.

## Oracle SQL Rules

When writing Oracle SQL for this project:

- **Avoid SQL reserved words as column names**: `mode`, `level`, `comment`, `value`, `date`, `type`, `status`, `user`, `role`, `size`. Rename the column or quote it with double quotes if unavoidable.
- **CLOB for long text**: use `CLOB` type for text exceeding 4000 bytes.
- **VECTOR columns**: Oracle 26ai supports native `VECTOR` type. No dimension needed in the column DDL.
- **HNSW indexes**: `CREATE VECTOR INDEX ... ORGANIZATION NEIGHBOR PARTITIONS WITH DISTANCE COSINE`
- **Similarity search**: `VECTOR_DISTANCE(column, :query_vec, COSINE)` with `ORDER BY` and `FETCH FIRST N ROWS ONLY`.
- **Auto-increment**: `NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY`
- **RETURNING**: Oracle uses `RETURNING col INTO :bind_var`, not `RETURNING *`. Create the bind variable with `cursor.var(int)`.
- **Pagination**: use `FETCH FIRST :n ROWS ONLY`. Don't use `ROWNUM` in new code.
- **Timestamps**: `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`. Oracle doesn't have a `NOW()` function.

## Embedding Configuration

The `EMBEDDING_PROVIDER` env var controls embedding generation:
- `mock` (default): deterministic hash-based vectors, no external dependencies. Good for testing.
- `ollama`: real embeddings via local Ollama instance (`OLLAMA_HOST`, `OLLAMA_MODEL` env vars).

## RAG Pipeline

The `POST /rag` endpoint retrieves relevant document chunks via vector search, then generates an answer using Ollama. Controlled by `RAG_PROVIDER` (default: `ollama`), `OLLAMA_CHAT_MODEL`, and `RAG_TOP_K`. Set `RAG_USE_CACHE=true` to check the semantic cache before calling the LLM.

## Semantic Cache

The cache stores query-response pairs with vector embeddings. On repeated or similar questions (within `CACHE_SIMILARITY_THRESHOLD`), the cached response is returned without hitting the LLM.

- `GET /cache/stats` -- cache hit/miss counts and entry total.
- `DELETE /cache` -- flush all cached entries.

## Document Chunking

The `POST /documents/ingest` endpoint accepts a large document and splits it into overlapping chunks. Each chunk is stored with a `parent_id` linking back to the original document and a `chunk_index` for ordering.

## Testing Strategy

- Tests requiring Oracle use the `db_available` fixture from `conftest.py`.
- When Oracle isn't running, DB tests skip with a clear message.
- Mock embedding tests validate vector search logic without any external services.
- Run `pytest tests/ -v` before committing changes.

## Environment Variables

All variables have defaults. See `.env.example` for the complete list. Key ones:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ORACLE_HOST` | `localhost` | DB hostname |
| `ORACLE_PORT` | `1521` | DB listener port |
| `ORACLE_SERVICE` | `FREEPDB1` | Pluggable database service name |
| `ORACLE_PWD` | `FreeP4ssw0rd!` | DB password |
| `EMBEDDING_PROVIDER` | `mock` | Embedding backend: `mock` or `ollama` |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `RAG_PROVIDER` | `ollama` | RAG generation backend |
| `OLLAMA_CHAT_MODEL` | `llama3` | Ollama model for RAG generation |
| `RAG_TOP_K` | `5` | Number of chunks retrieved for RAG context |
| `RAG_USE_CACHE` | `true` | Check semantic cache before calling LLM |
| `CACHE_SIMILARITY_THRESHOLD` | `0.95` | Cosine similarity threshold for cache hits |
