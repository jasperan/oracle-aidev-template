# Copilot Instructions: Oracle AI Dev Template

FastAPI app backed by Oracle 26ai Free with AI Vector Search.

## Stack

- Python 3.11+, FastAPI, Pydantic v2, oracledb
- Oracle 26ai Free on port 1521, service `FREEPDB1`, container `oracle-aidev-db`
- Embeddings: mock (default) or Ollama

## Key Files

- `app/main.py` -- FastAPI endpoints (health, CRUD, vector search, RAG, cache, ingest)
- `app/db.py` -- Connection pool (`get_connection()` context manager)
- `app/vector_search.py` -- Embedding + `VECTOR_DISTANCE` queries
- `app/rag.py` -- RAG pipeline: vector search retrieval + Ollama generation
- `app/cache.py` -- Semantic cache with vector similarity lookup
- `app/chunking.py` -- Document chunking with overlap for ingestion
- `scripts/init-schema.sql` -- Table DDL with VECTOR columns and HNSW indexes

## Running

```bash
./scripts/start-db.sh              # start Oracle container
uvicorn app.main:app --reload      # start API server
pytest tests/ -v                   # run tests (DB tests auto-skip)
docker compose up                  # full stack
```

Endpoints:
- `GET /` -- health check
- `POST /documents`, `GET /documents` -- document CRUD
- `POST /search` -- vector similarity search
- `POST /rag` -- retrieve context + generate answer via Ollama
- `GET /cache/stats` -- cache hit/miss statistics
- `DELETE /cache` -- flush semantic cache
- `POST /documents/ingest` -- split and ingest a large document as chunks

## Code Style

- Type hints on all functions
- ruff for linting (line length 100, rules: E/F/I/UP/B)
- Bind variables in SQL (`:param`), never string concatenation
- Use the connection pool from `app.db`, not standalone connections

## Oracle SQL Rules

- Auto-increment: `NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY`
- Vector columns: `VECTOR` type (no dimension in DDL)
- Vector index: `CREATE VECTOR INDEX ... ORGANIZATION NEIGHBOR PARTITIONS WITH DISTANCE COSINE`
- Similarity: `VECTOR_DISTANCE(col, :vec, COSINE)` + `ORDER BY` + `FETCH FIRST N ROWS ONLY`
- RETURNING: `RETURNING col INTO :bind_var` with `cursor.var(int)` -- not `RETURNING *`
- Pagination: `FETCH FIRST :n ROWS ONLY` -- not `ROWNUM`
- Timestamps: `CURRENT_TIMESTAMP` -- not `NOW()`
- CLOB for text > 4000 bytes

## RAG and Cache SQL Patterns

**Semantic cache lookup (find similar cached query):**
```sql
SELECT id, query_text, response_text,
       VECTOR_DISTANCE(query_embedding, :query_vec, COSINE) AS distance
FROM semantic_cache
WHERE VECTOR_DISTANCE(query_embedding, :query_vec, COSINE) < :threshold
ORDER BY VECTOR_DISTANCE(query_embedding, :query_vec, COSINE)
FETCH FIRST 1 ROWS ONLY
```

**Cache insert (store query-response pair):**
```sql
INSERT INTO semantic_cache (query_text, response_text, query_embedding)
VALUES (:query, :response, :embedding)
```

**RAG retrieval (fetch top-k context chunks):**
```sql
SELECT id, content, parent_id, chunk_index,
       VECTOR_DISTANCE(embedding, :query_vec, COSINE) AS distance
FROM document_chunks
ORDER BY VECTOR_DISTANCE(embedding, :query_vec, COSINE)
FETCH FIRST :top_k ROWS ONLY
```

**Document chunk storage:**
```sql
INSERT INTO document_chunks (content, embedding, parent_id, chunk_index)
VALUES (:content, :embedding, :parent_id, :chunk_index)
```

## Avoid These Column Names

SQL reserved words: `mode`, `level`, `comment`, `value`, `date`, `type`, `status`, `user`, `role`, `size`. Rename or double-quote them.
