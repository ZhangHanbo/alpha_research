"""Knowledge store interface for agent tool use.

Delegates to the SQLite-backed KnowledgeStore for persistence.
Provides simplified read/write wrappers that agents call via tool use.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alpha_research.knowledge.store import KnowledgeStore
from alpha_research.models.research import Evaluation, Paper

# Module-level store instance, initialised via init_store().
_store: KnowledgeStore | None = None


def init_store(path: str | Path | None = None) -> None:
    """Initialize the knowledge store.

    Args:
        path: Path to the SQLite database file.  Defaults to
            ``data/knowledge.db``.
    """
    global _store
    db_path = Path(path) if path is not None else Path("data/knowledge.db")
    _store = KnowledgeStore(db_path=db_path)


def _get_store() -> KnowledgeStore:
    """Return the active store, auto-initializing if needed."""
    global _store
    if _store is None:
        init_store()
    assert _store is not None
    return _store


def knowledge_read(
    query: str,
    topic: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Query the knowledge store for papers and evaluations.

    Args:
        query: Search query (matches against title and abstract via LIKE).
        topic: Optional topic filter (alias for query refinement).
        limit: Maximum number of results to return.

    Returns:
        List of matching paper dicts with optional evaluation data.
    """
    store = _get_store()

    # Use topic as an additional qualifier when provided
    search_term = f"{query} {topic}" if topic else query

    papers = store.query_papers(topic=search_term, limit=limit)

    results: list[dict] = []
    for paper in papers:
        entry: dict[str, Any] = {
            "arxiv_id": paper.arxiv_id,
            "s2_id": paper.s2_id,
            "doi": paper.doi,
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "year": paper.year,
            "venue": paper.venue,
            "url": paper.url,
        }

        # Attach evaluations if available
        pid = paper.primary_id
        evaluations = store.get_evaluations(pid)
        if evaluations:
            entry["evaluations"] = [
                e.model_dump(mode="json") for e in evaluations
            ]

        results.append(entry)

    return results


def knowledge_write(
    paper_data: dict,
    evaluation_data: dict | None = None,
) -> str:
    """Write a paper and optional evaluation to the knowledge store.

    Args:
        paper_data: Dict with paper fields.  Must include at least 'title'.
        evaluation_data: Optional dict with evaluation fields.

    Returns:
        The primary identifier used for storage.
    """
    store = _get_store()

    # Build a Paper model from the dict
    paper = Paper.model_validate(paper_data)
    store.save_paper(paper)

    # Optionally persist an evaluation
    if evaluation_data is not None:
        # Ensure paper_id is set
        if "paper_id" not in evaluation_data:
            evaluation_data["paper_id"] = paper.primary_id
        evaluation = Evaluation.model_validate(evaluation_data)
        store.save_evaluation(evaluation)

    return paper.primary_id
