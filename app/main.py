"""Oracle AI Dev Template - FastAPI Application.

Endpoints:
  GET  /              Health check
  GET  /docs          Interactive API docs (Swagger)
  POST /documents     Insert a document (auto-embeds)
  POST /documents/ingest  Ingest a large document (auto-chunks + embeds)
  GET  /documents     List documents
  POST /search        Semantic similarity search
  POST /rag           RAG: retrieve context + generate answer
  GET  /cache/stats   Semantic cache statistics
  DELETE /cache       Invalidate cache entries by similarity
"""

from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import __version__
from app.db import check_health, close_pool
from app.vector_search import insert_document, list_documents, search_similar


@asynccontextmanager
async def lifespan(application: FastAPI):
    yield
    close_pool()


app = FastAPI(
    title="Oracle AI Dev Template",
    version=__version__,
    description="Starter API backed by Oracle 26ai Free with AI Vector Search, RAG, and caching.",
    lifespan=lifespan,
)


# --- Request/Response models ---


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)


class DocumentIngest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    chunk_size: int = Field(default=512, ge=100, le=4000)
    chunk_overlap: int = Field(default=64, ge=0, le=500)


class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=100)


class RAGQuery(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    system_prompt: str | None = None
    use_cache: bool = True


class CacheInvalidate(BaseModel):
    query: str = Field(..., min_length=1)
    threshold: float | None = None


# --- Endpoints ---


@app.get("/")
def health():
    """Database health check."""
    result = check_health()
    if result["status"] != "healthy":
        raise HTTPException(status_code=503, detail=result)
    return result


@app.post("/documents", status_code=201)
def create_document(doc: DocumentCreate):
    """Insert a document. The content is automatically embedded for vector search."""
    doc_id = insert_document(doc.title, doc.content)
    return {"id": doc_id, "title": doc.title}


@app.post("/documents/ingest", status_code=201)
def ingest_document(doc: DocumentIngest):
    """Ingest a large document: auto-chunks it and embeds each chunk separately."""
    from app.chunking import chunk_text

    chunks = chunk_text(doc.content, chunk_size=doc.chunk_size, chunk_overlap=doc.chunk_overlap)

    # Insert parent document (no embedding, just metadata)
    preview = doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
    parent_id = insert_document(doc.title, preview)

    # Insert each chunk with its own embedding, linked to parent
    chunk_ids = []
    for chunk in chunks:
        chunk_id = insert_document(
            title=f"{doc.title} [chunk {chunk.index}]",
            content=chunk.text,
        )
        chunk_ids.append(chunk_id)

    return {
        "parent_id": parent_id,
        "chunks_created": len(chunk_ids),
        "chunk_ids": chunk_ids,
    }


@app.get("/documents")
def get_documents(limit: int = 50):
    """List stored documents."""
    return list_documents(limit=limit)


@app.post("/search")
def search(q: SearchQuery):
    """Semantic similarity search across documents."""
    results = search_similar(q.query, top_k=q.top_k)
    return {"query": q.query, "results": results}


@app.post("/rag")
def rag_query(q: RAGQuery):
    """RAG: retrieve relevant documents, generate an answer using an LLM.

    Checks the semantic cache first. If a similar question was already answered,
    returns the cached response (saving an LLM call).
    """
    from app import rag

    response = rag.query(
        question=q.question,
        top_k=q.top_k,
        system_prompt=q.system_prompt,
        use_cache=q.use_cache,
    )
    return asdict(response)


@app.get("/cache/stats")
def cache_stats():
    """Return semantic cache statistics (total entries, total hits)."""
    from app import cache

    return cache.stats()


@app.delete("/cache")
def cache_invalidate(q: CacheInvalidate):
    """Delete cache entries semantically similar to the given query."""
    from app import cache

    deleted = cache.invalidate(q.query, threshold=q.threshold)
    return {"deleted": deleted, "query": q.query}
