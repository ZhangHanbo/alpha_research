"""ArXiv search tool using the arxiv Python library.

Provides structured search with category filtering and rate limiting.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import arxiv

from alpha_research.models.research import PaperCandidate

# Rate limit: 1 request per 3 seconds
_RATE_LIMIT_SECONDS = 3.0
_last_request_time: float = 0.0

# Default robotics-relevant categories
DEFAULT_CATEGORIES = ["cs.RO", "cs.AI", "cs.LG", "cs.CV"]


async def search_arxiv(
    query: str,
    categories: list[str] | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    max_results: int = 20,
) -> list[PaperCandidate]:
    """Search ArXiv for papers matching the query.

    Args:
        query: Search query string.
        categories: ArXiv categories to filter (e.g. ["cs.RO", "cs.AI"]).
            If None, no category filter is applied.
        date_start: Start date filter as "YYYY-MM-DD".
        date_end: End date filter as "YYYY-MM-DD".
        max_results: Maximum number of results to return.

    Returns:
        List of PaperCandidate objects.
    """
    global _last_request_time

    # Build category filter into query
    full_query = _build_query(query, categories)

    # Rate limiting
    now = asyncio.get_event_loop().time()
    elapsed = now - _last_request_time
    if elapsed < _RATE_LIMIT_SECONDS:
        await asyncio.sleep(_RATE_LIMIT_SECONDS - elapsed)

    # Execute search in thread pool (arxiv library is synchronous)
    search = arxiv.Search(
        query=full_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    results = await asyncio.to_thread(_fetch_results, search)
    _last_request_time = asyncio.get_event_loop().time()

    # Parse date filters
    start_dt = _parse_date(date_start) if date_start else None
    end_dt = _parse_date(date_end) if date_end else None

    candidates: list[PaperCandidate] = []
    for result in results:
        # Apply date filtering
        published = result.published
        if start_dt and published < start_dt:
            continue
        if end_dt and published > end_dt:
            continue

        candidate = _result_to_candidate(result)
        candidates.append(candidate)

    return candidates


def _build_query(query: str, categories: list[str] | None) -> str:
    """Build an ArXiv API query string with optional category filter."""
    if not categories:
        return query

    cat_filter = " OR ".join(f"cat:{cat}" for cat in categories)
    return f"({query}) AND ({cat_filter})"


def _fetch_results(search: arxiv.Search) -> list[arxiv.Result]:
    """Fetch results from ArXiv (synchronous, run in thread pool)."""
    client = arxiv.Client()
    return list(client.results(search))


def _parse_date(date_str: str) -> datetime:
    """Parse a YYYY-MM-DD date string to datetime."""
    return datetime.strptime(date_str, "%Y-%m-%d")


def _extract_arxiv_id(entry_id: str) -> str:
    """Extract the ArXiv ID from the full entry URL.

    Example: "http://arxiv.org/abs/2301.12345v1" -> "2301.12345"
    """
    # entry_id is like http://arxiv.org/abs/2301.12345v1
    raw_id = entry_id.split("/abs/")[-1]
    # Strip version suffix
    if "v" in raw_id:
        raw_id = raw_id.rsplit("v", 1)[0]
    return raw_id


def _result_to_candidate(result: arxiv.Result) -> PaperCandidate:
    """Convert an arxiv.Result to a PaperCandidate."""
    arxiv_id = _extract_arxiv_id(result.entry_id)
    authors = [str(a) for a in result.authors]

    return PaperCandidate(
        arxiv_id=arxiv_id,
        title=result.title,
        authors=authors,
        abstract=result.summary or "",
        year=result.published.year if result.published else None,
        url=result.entry_id,
        source="arxiv",
    )
