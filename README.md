# Oracle AI Dev Template

GitHub template for building AI apps on Oracle 26ai Free Database.

[![CI](https://github.com/jasperan/oracle-aidev-template/actions/workflows/ci.yml/badge.svg)](https://github.com/jasperan/oracle-aidev-template/actions/workflows/ci.yml)

Click **"Use this template"** on GitHub to create your own repo from this starter. You get a working FastAPI app, Oracle AI Vector Search, Docker Compose, and a test suite out of the box.

## Quick Start

```bash
# 1. Clone your new repo
git clone https://github.com/YOUR_USER/YOUR_REPO.git
cd YOUR_REPO
cp .env.example .env

# 2. Start Oracle 26ai Free
docker compose up -d oracle-db
# First boot takes ~2 minutes while Oracle initializes

# 3. Run the app
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The API is live at `http://localhost:8000`. Hit `http://localhost:8000/docs` for the interactive Swagger UI.

## What's Included

- **FastAPI** REST API with health checks, CRUD, search, RAG, and caching endpoints
- **Oracle AI Vector Search** with mock embeddings (swap in Ollama for real ones)
- **RAG pipeline** that retrieves context via vector search and generates answers with an LLM
- **Semantic cache** that skips the LLM when a similar question was already answered
- **Document chunking** with overlap for ingesting large documents
- **Docker Compose** with Oracle 26ai Free, production app, and dev (hot reload) services
- **Automated schema init** on first database boot
- **Pytest suite** with mock and integration tests
- **Ruff + mypy** for linting and type checking
- **Multi-agent support** for AI coding assistants (Claude, Copilot, Codex, Gemini)

## Architecture

```
Client Request
      |
      v
  FastAPI App (app/main.py)
      |
      +-- app/db.py ------------> Oracle 26ai Free (FREEPDB1)
      |                                |
      +-- app/vector_search.py         +-- documents table + VECTOR index
      |     +-- embed() -> Mock/Ollama +-- semantic_cache table + VECTOR index
      |
      +-- app/chunking.py -----> Splits large docs into overlapping chunks
      |
      +-- app/rag.py ----------> Retrieve context + generate answer
      |     +-- cache check -> vector search -> LLM -> cache store
      |
      +-- app/cache.py --------> Semantic similarity cache (skip LLM on repeats)
```

The RAG pipeline checks the semantic cache first. If a similar question was already answered (cosine distance below threshold), it returns the cached response instantly. Otherwise it retrieves context via vector search, generates an answer with an LLM, and stores the result for future queries.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check (returns DB status) |
| `POST` | `/documents` | Insert a document (auto-embeds the content) |
| `POST` | `/documents/ingest` | Ingest a large doc (auto-chunks + embeds each chunk) |
| `GET` | `/documents` | List stored documents |
| `POST` | `/search` | Semantic similarity search |
| `POST` | `/rag` | RAG: retrieve context + generate answer via LLM |
| `GET` | `/cache/stats` | Semantic cache statistics |
| `DELETE` | `/cache` | Invalidate cache entries by similarity |

Full interactive docs at `/docs` (Swagger) or `/redoc`.

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|----------|---------|-------------|
| `ORACLE_PWD` | `FreeP4ssw0rd!` | Database password |
| `ORACLE_USER` | `system` | Database user |
| `ORACLE_HOST` | `localhost` | Database host |
| `ORACLE_PORT` | `1521` | Database port |
| `ORACLE_SERVICE` | `FREEPDB1` | PDB service name |
| `APP_PORT` | `8000` | Production app port |
| `DEV_PORT` | `8001` | Dev app port (hot reload) |
| `EMBEDDING_PROVIDER` | `mock` | `mock` or `ollama` |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `RAG_PROVIDER` | `mock` | `mock` or `ollama` |
| `OLLAMA_CHAT_MODEL` | `qwen3:8b` | LLM for RAG generation |
| `RAG_TOP_K` | `5` | Number of docs to retrieve for context |
| `RAG_USE_CACHE` | `true` | Enable semantic caching |
| `CACHE_SIMILARITY_THRESHOLD` | `0.15` | Cosine distance for cache hits |

## Development

**Full stack with Docker Compose:**

```bash
docker compose up -d        # All services (DB + app + dev)
docker compose up -d dev    # Dev service only (hot reload on code changes)
```

**Testing:**

```bash
# Mock-only tests (no DB needed)
pytest tests/test_vector_search.py::test_mock_embedding_deterministic -v
pytest tests/test_vector_search.py::test_mock_embedding_different_inputs -v

# Full suite (requires running Oracle DB)
pytest tests/ -v
```

**Linting and type checking:**

```bash
ruff check app/ tests/
mypy app/ --ignore-missing-imports
```

## AI Coding Agent Support

This template works with AI coding assistants. Each tool reads its own instruction file:

| Agent | Config File |
|-------|-------------|
| Claude Code | `CLAUDE.md` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| OpenAI Codex | `AGENTS.md` |
| Google Gemini | `GEMINI.md` |

These files tell the agent about the project structure, how to run tests, and what conventions to follow. Create whichever ones you need for your workflow.

## License

MIT. See [LICENSE](LICENSE).
