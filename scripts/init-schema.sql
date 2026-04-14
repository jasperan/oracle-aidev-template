-- Oracle AI Dev Template: Initial Schema
-- This runs automatically on first container startup via /opt/oracle/scripts/startup/

-- Connect to the pluggable database
ALTER SESSION SET CONTAINER = FREEPDB1;

-- Documents table: stores text content with vector embeddings
CREATE TABLE IF NOT EXISTS documents (
    id          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title       VARCHAR2(500) NOT NULL,
    content     CLOB,
    embedding   VECTOR,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vector similarity index for fast nearest-neighbor search
-- Uses HNSW (Hierarchical Navigable Small World) algorithm
CREATE VECTOR INDEX IF NOT EXISTS idx_documents_embedding
    ON documents (embedding)
    ORGANIZATION NEIGHBOR PARTITIONS
    WITH DISTANCE COSINE;

-- Chunking support: parent_id links chunks back to the original document
ALTER TABLE documents ADD (
    parent_id   NUMBER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index NUMBER
);

-- Simple key-value metadata table (useful for app config, caching)
CREATE TABLE IF NOT EXISTS metadata (
    key         VARCHAR2(200) PRIMARY KEY,
    val         CLOB,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Semantic cache: stores query-response pairs with vector embeddings
-- for fast similarity lookup. Skips the LLM when a similar question
-- was already answered.
CREATE TABLE IF NOT EXISTS semantic_cache (
    id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    query_text      CLOB NOT NULL,
    query_embedding VECTOR,
    response_text   CLOB NOT NULL,
    model_name      VARCHAR2(200),
    hit_count       NUMBER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VECTOR INDEX IF NOT EXISTS idx_cache_embedding
    ON semantic_cache (query_embedding)
    ORGANIZATION NEIGHBOR PARTITIONS
    WITH DISTANCE COSINE;

COMMIT;
