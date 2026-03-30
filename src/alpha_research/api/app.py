"""Main FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alpha_research.knowledge.store import KnowledgeStore

# ---------------------------------------------------------------------------
# Shared store singleton
# ---------------------------------------------------------------------------

_store: KnowledgeStore | None = None


def get_store() -> KnowledgeStore:
    """Return the shared KnowledgeStore instance (created at startup)."""
    global _store
    if _store is None:
        _store = KnowledgeStore(db_path="data/knowledge.db")
    return _store


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the knowledge store on startup."""
    global _store
    _store = KnowledgeStore(db_path="data/knowledge.db")
    yield
    # Cleanup (nothing needed for SQLite)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Alpha Research API",
    description="Backend API for the multi-agent research & review system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Mount routers
# ---------------------------------------------------------------------------

from alpha_research.api.routers.agent import router as agent_router  # noqa: E402
from alpha_research.api.routers.evaluations import router as evaluations_router  # noqa: E402
from alpha_research.api.routers.graph import router as graph_router  # noqa: E402
from alpha_research.api.routers.papers import router as papers_router  # noqa: E402

app.include_router(papers_router)
app.include_router(evaluations_router)
app.include_router(graph_router)
app.include_router(agent_router)


@app.get("/api/health")
def health_check():
    """Simple health check."""
    return {"status": "ok"}
