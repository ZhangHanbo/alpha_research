"""Knowledge store interface for agent tool use.

Simplified read/write wrappers that the agent calls via tool use.
These will be backed by the knowledge store (SQLite) once implemented.
For Phase 1, they operate on an in-memory dict as a placeholder.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# In-memory store for Phase 1 (will be replaced by SQLite-backed store)
_store: dict[str, dict[str, Any]] = {}

# Persistence path (optional, for across-session use)
_STORE_PATH: Path | None = None


def init_store(path: str | Path | None = None) -> None:
    """Initialize the knowledge store, optionally loading from disk.

    Args:
        path: Path to a JSON file for persistence. If None, in-memory only.
    """
    global _store, _STORE_PATH

    if path is not None:
        _STORE_PATH = Path(path)
        if _STORE_PATH.exists():
            _store = json.loads(_STORE_PATH.read_text())
        else:
            _store = {}
    else:
        _STORE_PATH = None
        _store = {}


def _persist() -> None:
    """Write store to disk if a persistence path is set."""
    if _STORE_PATH is not None:
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STORE_PATH.write_text(json.dumps(_store, indent=2, default=str))


def knowledge_read(
    query: str,
    topic: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Query the knowledge store for papers and evaluations.

    Args:
        query: Search query (matches against title, abstract, topics).
        topic: Optional topic filter.
        limit: Maximum number of results to return.

    Returns:
        List of matching entries as dicts.
    """
    query_lower = query.lower()
    results: list[dict] = []

    for entry_id, entry in _store.items():
        # Simple text matching against title, abstract, and topics
        searchable = " ".join([
            entry.get("title", ""),
            entry.get("abstract", ""),
            " ".join(entry.get("topics", [])),
        ]).lower()

        if query_lower in searchable:
            # Apply topic filter if specified
            if topic is not None:
                entry_topics = [t.lower() for t in entry.get("topics", [])]
                if topic.lower() not in entry_topics:
                    continue

            results.append({"id": entry_id, **entry})

        if len(results) >= limit:
            break

    return results


def knowledge_write(
    paper_data: dict,
    evaluation_data: dict | None = None,
) -> str:
    """Write a paper and optional evaluation to the knowledge store.

    Args:
        paper_data: Dict with at least 'title'. Should include arxiv_id,
            authors, abstract, year, venue, etc.
        evaluation_data: Optional dict with evaluation results (rubric scores,
            significance assessment, etc.).

    Returns:
        The entry ID (arxiv_id or generated).
    """
    # Determine entry ID
    entry_id = (
        paper_data.get("arxiv_id")
        or paper_data.get("s2_id")
        or paper_data.get("doi")
        or f"entry_{len(_store)}"
    )

    # Build entry
    entry: dict[str, Any] = {
        "title": paper_data.get("title", ""),
        "authors": paper_data.get("authors", []),
        "abstract": paper_data.get("abstract", ""),
        "year": paper_data.get("year"),
        "venue": paper_data.get("venue"),
        "arxiv_id": paper_data.get("arxiv_id"),
        "s2_id": paper_data.get("s2_id"),
        "doi": paper_data.get("doi"),
        "url": paper_data.get("url"),
        "topics": paper_data.get("topics", []),
        "stored_at": datetime.now().isoformat(),
    }

    if evaluation_data is not None:
        entry["evaluation"] = evaluation_data

    # Merge with existing entry if present (update, not overwrite)
    if entry_id in _store:
        existing = _store[entry_id]
        existing.update({k: v for k, v in entry.items() if v is not None})
        if evaluation_data is not None:
            existing["evaluation"] = evaluation_data
    else:
        _store[entry_id] = entry

    _persist()
    return entry_id
