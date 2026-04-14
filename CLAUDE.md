# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

GitHub template for building AI apps on Oracle 26ai Free Database. Ships with FastAPI, AI Vector Search, RAG, semantic caching, document chunking, Docker Compose, and multi-agent support (Claude, Copilot, Codex, Gemini).

## Commands

```bash
# Start Oracle 26ai Free (first run pulls image, takes 2-5 min)
./scripts/start-db.sh

# Install deps and run the API server locally
pip install -e ".[dev]"
uvicorn app.main:app --reload        # http://localhost:8000, Swagger at /docs

# Full stack via Docker
docker compose up -d oracle-db       # DB only (wait ~2 min for first-boot init)
docker compose up                    # oracle-db + prod app
docker compose up dev                # dev container with hot-reload (port 8001)

# Testing
pytest tests/ -v                                    # full suite (DB tests auto-skip if Oracle unreachable)
pytest tests/test_vector_search.py -k "mock" -v     # mock-only, no DB needed
pytest tests/test_chunking.py -v                    # chunking logic, no DB needed

# Linting and type checking
ruff check app/ tests/
mypy app/ --ignore-missing-imports
```

## Architecture

```
Client -> FastAPI (app/main.py)
              |
              +-- app/db.py            -> Oracle 26ai Free (FREEPDB1:1521)
              +-- app/vector_search.py -> embed() -> mock or Ollama
              +-- app/chunking.py      -> chunk_text() (sliding window)
              +-- app/rag.py           -> retrieve + generate via Ollama LLM
              +-- app/cache.py         -> semantic_cache table (vector similarity)
```

### Module Roles

- `app/db.py`: Lazy-init connection pool via `oracledb`. All DB access goes through `get_connection()` context manager.
- `app/vector_search.py`: Two embedding providers via `EMBEDDING_PROVIDER` env var. `mock` = deterministic hash-based vectors (no external deps). `ollama` = calls a local Ollama instance.
- `app/chunking.py`: Sliding-window text chunker. Returns `Chunk` dataclasses with `.text`, `.index`, `.start`, `.end`.
- `app/rag.py`: Retrieves top-k docs via vector search, stuffs them into a prompt, calls Ollama for generation. Returns a dataclass serialized with `asdict()`.
- `app/cache.py`: Semantic cache backed by `semantic_cache` table. Checks for similar past questions before hitting the LLM. Tracks `hit_count`. Supports threshold-based invalidation.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check (returns DB status) |
| `POST` | `/documents` | Insert a document (auto-embeds content) |
| `POST` | `/documents/ingest` | Ingest large doc: auto-chunks + embeds each chunk |
| `GET` | `/documents` | List stored documents (default limit 50) |
| `POST` | `/search` | Semantic similarity search |
| `POST` | `/rag` | RAG: retrieve context + generate answer via Ollama |
| `GET` | `/cache/stats` | Semantic cache stats (total entries, hits) |
| `DELETE` | `/cache` | Invalidate cache entries by similarity threshold |

## Database Schema

Three main tables created by `scripts/init-schema.sql` on first container boot:

- `documents`: `id`, `title`, `content` (CLOB), `embedding` (VECTOR), `parent_id` (self-ref FK for chunks), `chunk_index`, timestamps
- `metadata`: simple key-value store (VARCHAR2 key, CLOB val)
- `semantic_cache`: `query_text`, `query_embedding`, `response_text`, `model_name`, `hit_count`

Vector indexes (`idx_documents_embedding`, `idx_cache_embedding`) use HNSW with COSINE distance.

## Oracle Database

- **Container**: `oracle-aidev-db` on port 1521 (also exposes EM on 5500), service `FREEPDB1`
- **Default creds**: `system` / `FreeP4ssw0rd!` (override via `ORACLE_PWD`)
- **sqlplus**: `docker exec -it oracle-aidev-db sqlplus system/${ORACLE_PWD}@FREEPDB1`
- **Data volume**: `oracle-data` persists across restarts
- **Schema init**: `scripts/init-schema.sql` is mounted to `/opt/oracle/scripts/startup/` and runs automatically on first boot only. Re-run manually if you wipe the volume.

## Oracle SQL Rules

- Auto-increment: `NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY`
- Vector columns: `VECTOR` type (no dimension in DDL)
- Vector index: `CREATE VECTOR INDEX ... ORGANIZATION NEIGHBOR PARTITIONS WITH DISTANCE COSINE`
- Similarity: `VECTOR_DISTANCE(col, :vec, COSINE)` + `ORDER BY` + `FETCH FIRST N ROWS ONLY`
- RETURNING: `RETURNING col INTO :bind_var` with `cursor.var(int)`, not `RETURNING *`
- Pagination: `FETCH FIRST :n ROWS ONLY`, not `ROWNUM`
- Timestamps: `CURRENT_TIMESTAMP`, not `NOW()`
- Avoid reserved words as column names: `mode`, `level`, `comment`, `value`, `date`, `type`, `status`, `user`, `role`, `size`

## Environment Variables

Copy `.env.example` to `.env`. Key vars:

| Variable | Default | Notes |
|----------|---------|-------|
| `ORACLE_PWD` | `FreeP4ssw0rd!` | DB password |
| `ORACLE_HOST` | `localhost` | `oracle-db` when running inside Docker |
| `ORACLE_PORT` | `1521` | |
| `EMBEDDING_PROVIDER` | `mock` | `mock` or `ollama` |
| `OLLAMA_HOST` | `http://localhost:11434` | |
| `OLLAMA_MODEL` | `nomic-embed-text` | embedding model |

## Code Conventions

- Python 3.11+, type hints on all functions
- ruff for linting (line length 100, rules: E/F/I/UP/B)
- Bind variables in SQL (`:param` style), never string concatenation
- Use the connection pool from `app.db`, not standalone `oracledb.connect()` calls
- CLOB for text > 4000 bytes
- RAG/cache responses are dataclasses; serialize with `asdict()` before returning from endpoints
