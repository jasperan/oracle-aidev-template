"""Oracle AI Dev Template - FastAPI Application.

Endpoints:
  GET  /           Health check
  GET  /docs       Interactive API docs (Swagger)
  POST /documents  Insert a document (auto-embeds)
  GET  /documents  List documents
  POST /search     Semantic similarity search
"""

from contextlib import asynccontextmanager

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
    description="Starter API backed by Oracle 26ai Free with AI Vector Search.",
    lifespan=lifespan,
)


# --- Request/Response models ---


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)


class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=100)


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


@app.get("/documents")
def get_documents(limit: int = 50):
    """List stored documents."""
    return list_documents(limit=limit)


@app.post("/search")
def search(q: SearchQuery):
    """Semantic similarity search across documents."""
    results = search_similar(q.query, top_k=q.top_k)
    return {"query": q.query, "results": results}
