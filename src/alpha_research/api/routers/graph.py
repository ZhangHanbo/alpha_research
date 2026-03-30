"""Knowledge graph endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from alpha_research.api.models import GraphEdge, GraphNode

router = APIRouter(prefix="/api/graph", tags=["graph"])


def _get_store():
    from alpha_research.api.app import get_store

    return get_store()


@router.get("/nodes", response_model=list[GraphNode])
def list_graph_nodes():
    """Return papers as graph nodes."""
    store = _get_store()
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
def list_graph_edges():
    """Return paper_relations as graph edges."""
    store = _get_store()
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
