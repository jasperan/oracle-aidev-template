# Oracle Database Development Skill

Use this skill when building features on Oracle 26ai Free Database. Covers table creation, vector search, connection patterns, and common gotchas.

## Connection Pattern (oracledb)

```python
import oracledb

# Simple connection
conn = oracledb.connect(user="system", password="...", dsn="localhost:1521/FREEPDB1")

# Connection pool (preferred for web apps)
pool = oracledb.create_pool(user="system", password="...", dsn="localhost:1521/FREEPDB1", min=2, max=10)
conn = pool.acquire()
# ... use conn ...
pool.release(conn)
```

Use `app/db.py` for the pool. Call `get_connection()` as a context manager.

## Creating Tables

```sql
CREATE TABLE documents (
    id          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title       VARCHAR2(500) NOT NULL,
    content     CLOB,
    embedding   VECTOR,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Vector Columns and Indexes

Add a VECTOR column for embeddings:

```sql
ALTER TABLE my_table ADD (embedding VECTOR);
```

Create an HNSW index for fast similarity search:

```sql
CREATE VECTOR INDEX idx_my_embedding
    ON my_table (embedding)
    ORGANIZATION NEIGHBOR PARTITIONS
    WITH DISTANCE COSINE;
```

Distance metrics: `COSINE`, `EUCLIDEAN`, `DOT`, `MANHATTAN`.

## Vector Similarity Search

```sql
SELECT id, title,
       VECTOR_DISTANCE(embedding, :query_vec, COSINE) AS distance
FROM documents
ORDER BY VECTOR_DISTANCE(embedding, :query_vec, COSINE)
FETCH FIRST :top_k ROWS ONLY;
```

In Python with oracledb, pass vectors as lists of floats:

```python
cur.execute(query, {"query_vec": [0.1, 0.2, ...], "top_k": 5})
```

## RETURNING INTO (Get Generated IDs)

Oracle doesn't support `RETURNING id` directly in Python. Use output variables:

```python
id_var = cur.var(int)
cur.execute(
    "INSERT INTO docs (title) VALUES (:title) RETURNING id INTO :new_id",
    {"title": "test", "new_id": id_var}
)
conn.commit()
new_id = id_var.getvalue()[0]
```

## Common Gotchas

**No LIMIT keyword.** Use `FETCH FIRST N ROWS ONLY`:
```sql
SELECT * FROM docs FETCH FIRST 10 ROWS ONLY;
```

**Reserved words as column names.** Avoid: `mode`, `level`, `comment`, `value`, `date`, `type`, `status`, `key`, `name`. If you must, quote them: `"mode"`. Better to rename (e.g., `val` instead of `value`).

**CLOB handling.** Large text goes in CLOB columns. oracledb reads them as strings by default. For writes, pass Python strings directly.

**Transactions.** Oracle doesn't auto-commit. Always call `conn.commit()` after INSERT/UPDATE/DELETE. Or use `conn.autocommit = True`.

**IF NOT EXISTS.** Supported in Oracle 23ai+ for CREATE TABLE and CREATE INDEX. Use `CREATE TABLE IF NOT EXISTS` and `CREATE VECTOR INDEX IF NOT EXISTS`.

**DUAL table.** For expressions without a real table: `SELECT SYSDATE FROM DUAL`.

**Bind variables.** Always use `:name` style bind variables, never f-strings or string concatenation:
```python
# Good
cur.execute("SELECT * FROM docs WHERE id = :id", {"id": 42})

# Bad (SQL injection risk)
cur.execute(f"SELECT * FROM docs WHERE id = {user_input}")
```
