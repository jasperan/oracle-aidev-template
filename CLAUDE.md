# Oracle AI Dev Template

GitHub template for building AI-powered Python apps on Oracle 26ai Free Database. Ships with FastAPI, AI Vector Search, and Docker Compose for local development.

## Quick Start

```bash
# 1. Start Oracle 26ai Free (first run pulls image, takes 2-5 min)
./scripts/start-db.sh

# 2. Install Python deps
pip install -r requirements.txt

# 3. Run the API server
uvicorn app.main:app --reload
```

The API serves at `http://localhost:8000`. Swagger docs at `/docs`.

## Full Stack (Docker)

```bash
docker compose up          # starts oracle-db + app containers
docker compose up -d       # detached mode
docker compose up dev      # dev container with hot-reload (mounts ./app and ./tests)
```

## Testing

```bash
pytest tests/ -v
```

Tests that need a live Oracle container use the `db_available` fixture and skip automatically when the DB isn't running. Mock embedding tests always pass without any external dependencies.

## Project Structure

| Path | Purpose |
|------|---------|
| `app/main.py` | FastAPI app: health check, CRUD, vector search endpoints |
| `app/db.py` | Oracle connection pool via `oracledb` (lazy init, context manager) |
| `app/vector_search.py` | Embedding generation (mock or Ollama) and VECTOR_DISTANCE queries |
| `docker-compose.yml` | Oracle 26ai Free + app + dev services |
| `scripts/start-db.sh` | Start Oracle container and wait for healthy status |
| `scripts/stop-db.sh` | Stop Oracle container |
| `scripts/wait-for-db.sh` | Block until Oracle is healthy (used in CI) |
| `scripts/init-schema.sql` | Creates `documents` and `metadata` tables on first boot |
| `tests/conftest.py` | Shared fixtures: `db_available` (skip guard), `db_connection` |
| `tests/test_connection.py` | DB connectivity tests |
| `tests/test_vector_search.py` | Vector search tests (mock embeddings) |
| `.env.example` | All configurable env vars with defaults |
| `pyproject.toml` | Project metadata, deps, ruff/mypy/pytest config |

## Oracle Database Details

- **Container name**: `oracle-aidev-db`
- **Port**: 1521 (host) -> 1521 (container)
- **Service name**: `FREEPDB1`
- **Default user**: `system`
- **Default password**: `FreeP4ssw0rd!` (override via `ORACLE_PWD` env var)
- **Enterprise Manager**: port 5500 (optional)
- **Data volume**: `oracle-data` (persists across container restarts)

Connect with sqlplus:
```bash
docker exec -it oracle-aidev-db sqlplus system/${ORACLE_PWD}@FREEPDB1
```

## Environment Variables

All variables have sensible defaults. Copy `.env.example` to `.env` to customize:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ORACLE_HOST` | `localhost` | DB hostname |
| `ORACLE_PORT` | `1521` | DB port |
| `ORACLE_SERVICE` | `FREEPDB1` | PDB service name |
| `ORACLE_USER` | `system` | DB user |
| `ORACLE_PWD` | `FreeP4ssw0rd!` | DB password |
| `EMBEDDING_PROVIDER` | `mock` | `mock` or `ollama` |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `nomic-embed-text` | Embedding model name |

## Coding Conventions

- **Python 3.11+** required. Use modern syntax: `X | Y` unions, `list[T]` generics.
- **ruff** for linting and formatting. Config in `pyproject.toml` (line length 100, rules: E/F/I/UP/B).
- **mypy** for type checking. All functions should have type hints.
- **FastAPI + Pydantic v2** for the API layer. Use `BaseModel` with `Field()` for validation.
- **oracledb** (python-oracledb) for database access. Always use the connection pool from `app.db`.
- Bind variables in all SQL (`:param` style). Never concatenate user input into SQL strings.

## Oracle SQL Gotchas

- **Reserved words as column names**: avoid `mode`, `level`, `comment`, `value`, `date`, `type`, `status`, `user`, `role`, `size`. If you must use one, quote it with double quotes (`"VALUE"`), but renaming is better.
- **CLOB columns**: use `CLOB` for text longer than 4000 bytes. The `oracledb` driver handles CLOBs transparently for reads, but writes larger than 1GB need `cursor.setinputsizes()`.
- **VECTOR type**: Oracle 26ai natively supports `VECTOR` columns. No dimension declaration needed in the column definition; the index handles it.
- **HNSW indexes**: create with `CREATE VECTOR INDEX ... ORGANIZATION NEIGHBOR PARTITIONS WITH DISTANCE COSINE`. These are approximate nearest-neighbor indexes.
- **IDENTITY columns**: use `GENERATED ALWAYS AS IDENTITY` for auto-increment primary keys.
- **RETURNING INTO**: Oracle uses `RETURNING col INTO :bind_var` (not `RETURNING *`). Create bind variables with `cursor.var(int)`.
- **FETCH FIRST N ROWS ONLY**: Oracle's LIMIT equivalent. Always use this instead of `ROWNUM` for new code.
- **Timestamps**: default to `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`. Oracle doesn't have `NOW()`.
