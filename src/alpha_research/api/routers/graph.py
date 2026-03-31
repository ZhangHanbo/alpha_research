"""Knowledge graph endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from alpha_research.api.models import GraphEdge, GraphNode

router = APIRouter(prefix="/api/graph", tags=["graph"])


def _get_store():
    from alpha_research.api.app import get_store

    return get_store()


def _resolve_store(project_id: str | None):
    """Return the project-scoped or global store."""
    if project_id:
        from alpha_research.api.app import get_orchestrator
        orch = get_orchestrator()
        return orch.service.get_knowledge_store(project_id)
    return _get_store()


@router.get("/nodes", response_model=list[GraphNode])
def list_graph_nodes(
    project_id: str | None = Query(None, description="Scope to a project's knowledge store"),
):
    """Return papers as graph nodes."""
    store = _resolve_store(project_id)
    papers = store.query_papers(limit=500)

    nodes: list[GraphNode] = []
    for p in papers:
        pid = p.arxiv_id or p.s2_id or p.doi or p.title
        nodes.append(
            GraphNode(
                id=pid,
                title=p.title,
                year=p.year,
                venue=p.venue,
                score=None,  # Could compute average rubric score later
            )
        )
    return nodes


@router.get("/edges", response_model=list[GraphEdge])
def list_graph_edges(
    project_id: str | None = Query(None, description="Scope to a project's knowledge store"),
):
    """Return paper_relations as graph edges."""
    store = _resolve_store(project_id)
    conn = store._connect()
    try:
        rows = conn.execute(
            "SELECT paper_a_id, paper_b_id, relation_type, confidence "
            "FROM paper_relations ORDER BY id"
        ).fetchall()
        return [
            GraphEdge(
                source=row["paper_a_id"],
                target=row["paper_b_id"],
                relation_type=row["relation_type"],
                confidence=row["confidence"],
            )
            for row in rows
        ]
    finally:
        conn.close()
