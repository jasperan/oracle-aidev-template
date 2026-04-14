"""RAG (Retrieval-Augmented Generation) pipeline.

Full loop: query -> semantic cache check -> vector retrieval -> LLM generation -> cache store.

Uses Ollama for generation (with a mock fallback that returns retrieved context as-is).
Draws patterns from ragcli's RAG engine and oci-genai-service's pipeline.
"""

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from app import cache
from app.vector_search import search_similar

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen3:8b")
RAG_PROVIDER = os.getenv("RAG_PROVIDER", "mock")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_USE_CACHE = os.getenv("RAG_USE_CACHE", "true").lower() == "true"

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question based on the provided context. "
    "If the context doesn't contain enough information, say so honestly. "
    "Cite specific parts of the context when possible."
)


@dataclass
class RAGResponse:
    """Structured response from the RAG pipeline."""

    answer: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    cached: bool = False
    cache_distance: float | None = None
    model: str = ""


def _build_context(sources: list[dict[str, Any]]) -> str:
    """Format retrieved documents into a context string for the LLM."""
    if not sources:
        return "No relevant documents found."

    parts = []
    for i, doc in enumerate(sources, 1):
        title = doc.get("title", "Untitled")
        content = doc.get("content", "")
        distance = doc.get("distance", 0)
        parts.append(f"[{i}] {title} (relevance: {1 - distance:.2f})\n{content}")

    return "\n\n---\n\n".join(parts)


def _generate_mock(context: str, query: str, system_prompt: str) -> str:
    """Mock generation: return context summary without calling an LLM."""
    return (
        f"[Mock RAG response - set RAG_PROVIDER=ollama for real generation]\n\n"
        f"Query: {query}\n\n"
        f"Retrieved context:\n{context}"
    )


def _generate_ollama(context: str, query: str, system_prompt: str) -> str:
    """Generate a response using Ollama chat API."""
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}",
        },
    ]
    resp = httpx.post(
        f"{OLLAMA_HOST}/api/chat",
        json={"model": OLLAMA_CHAT_MODEL, "messages": messages, "stream": False},
        timeout=120.0,
    )
    resp.raise_for_status()
    result: str = resp.json()["message"]["content"]
    return result


def query(
    question: str,
    top_k: int | None = None,
    system_prompt: str | None = None,
    use_cache: bool | None = None,
) -> RAGResponse:
    """Run the full RAG pipeline.

    1. Check semantic cache for a similar past question
    2. If cache miss, retrieve relevant documents via vector search
    3. Generate answer using LLM (or mock)
    4. Store result in semantic cache
    5. Return structured response
    """
    k = top_k or RAG_TOP_K
    prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
    should_cache = use_cache if use_cache is not None else RAG_USE_CACHE

    # Step 1: Check semantic cache
    if should_cache:
        cached = cache.lookup(question)
        if cached is not None:
            return RAGResponse(
                answer=cached["response_text"],
                cached=True,
                cache_distance=cached["distance"],
                model=cached["model_name"],
            )

    # Step 2: Retrieve relevant documents
    sources = search_similar(question, top_k=k)

    # Step 3: Build context and generate
    context = _build_context(sources)

    if RAG_PROVIDER == "ollama":
        answer = _generate_ollama(context, question, prompt)
        model = OLLAMA_CHAT_MODEL
    else:
        answer = _generate_mock(context, question, prompt)
        model = "mock"

    # Step 4: Store in semantic cache
    if should_cache:
        cache.store(question, answer, model_name=model)

    # Step 5: Return response
    return RAGResponse(
        answer=answer,
        sources=sources,
        cached=False,
        model=model,
    )
