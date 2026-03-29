"""Semantic Scholar API tool.

Uses the S2 Academic Graph API for paper metadata, citations, and references.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from alpha_research.models.research import PaperCandidate, PaperMetadata

logger = logging.getLogger(__name__)

S2_BASE_URL = "https://api.semanticscholar.org/graph/v1"

# Fields to request from S2 API
PAPER_FIELDS = (
    "title,authors,abstract,year,venue,citationCount,"
    "influentialCitationCount,tldr,externalIds,url,"
    "references,citations,fieldsOfStudy"
)

SEARCH_FIELDS = (
    "title,authors,abstract,year,venue,citationCount,"
    "influentialCitationCount,tldr,externalIds,url"
)

# Rate limiting: initial backoff in seconds
_INITIAL_BACKOFF = 1.0
_MAX_BACKOFF = 30.0
_MAX_RETRIES = 3


async def _request_with_backoff(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs,
) -> httpx.Response:
    """Make an HTTP request with exponential backoff on rate limits."""
    backoff = _INITIAL_BACKOFF
    for attempt in range(_MAX_RETRIES + 1):
        response = await client.request(method, url, **kwargs)

        if response.status_code == 429:
            if attempt < _MAX_RETRIES:
                logger.warning(
                    "S2 rate limit hit, backing off %.1fs (attempt %d/%d)",
                    backoff, attempt + 1, _MAX_RETRIES,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)
                continue
            else:
                response.raise_for_status()

        response.raise_for_status()
        return response

    # Should not reach here, but satisfy type checker
    raise httpx.HTTPStatusError(
        "Max retries exceeded", request=None, response=response  # type: ignore[arg-type]
    )


async def get_paper_metadata(paper_id: str) -> PaperMetadata:
    """Get detailed metadata for a paper from Semantic Scholar.

    Args:
        paper_id: Semantic Scholar paper ID, or ArXiv ID prefixed with "ArXiv:"
            (e.g. "ArXiv:2301.12345").

    Returns:
        PaperMetadata model.
    """
    url = f"{S2_BASE_URL}/paper/{paper_id}"
    params = {"fields": PAPER_FIELDS}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await _request_with_backoff(client, "GET", url, params=params)

    data = response.json()
    return _parse_metadata(data)


async def search_papers(
    query: str,
    limit: int = 10,
) -> list[PaperCandidate]:
    """Search Semantic Scholar for papers.

    Args:
        query: Search query string.
        limit: Maximum number of results.

    Returns:
        List of PaperCandidate objects.
    """
    url = f"{S2_BASE_URL}/paper/search"
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": SEARCH_FIELDS,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await _request_with_backoff(client, "GET", url, params=params)

    data = response.json()
    papers = data.get("data", [])

    return [_parse_candidate(p, source="semantic_scholar") for p in papers]


async def get_references(paper_id: str) -> list[PaperCandidate]:
    """Get papers referenced by the given paper.

    Args:
        paper_id: Semantic Scholar paper ID or "ArXiv:..." ID.

    Returns:
        List of PaperCandidate objects for referenced papers.
    """
    url = f"{S2_BASE_URL}/paper/{paper_id}/references"
    params = {"fields": SEARCH_FIELDS, "limit": 500}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await _request_with_backoff(client, "GET", url, params=params)

    data = response.json()
    entries = data.get("data", [])

    candidates = []
    for entry in entries:
        cited = entry.get("citedPaper", {})
        if cited and cited.get("title"):
            candidates.append(_parse_candidate(cited, source="citation_graph"))

    return candidates


async def get_citations(paper_id: str) -> list[PaperCandidate]:
    """Get papers that cite the given paper.

    Args:
        paper_id: Semantic Scholar paper ID or "ArXiv:..." ID.

    Returns:
        List of PaperCandidate objects for citing papers.
    """
    url = f"{S2_BASE_URL}/paper/{paper_id}/citations"
    params = {"fields": SEARCH_FIELDS, "limit": 500}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await _request_with_backoff(client, "GET", url, params=params)

    data = response.json()
    entries = data.get("data", [])

    candidates = []
    for entry in entries:
        citing = entry.get("citingPaper", {})
        if citing and citing.get("title"):
            candidates.append(_parse_candidate(citing, source="citation_graph"))

    return candidates


def _parse_metadata(data: dict) -> PaperMetadata:
    """Parse S2 API response into PaperMetadata."""
    external_ids = data.get("externalIds", {}) or {}
    tldr = data.get("tldr")
    tldr_text = tldr.get("text") if isinstance(tldr, dict) else None

    return PaperMetadata(
        citation_count=data.get("citationCount", 0) or 0,
        influential_citation_count=data.get("influentialCitationCount", 0) or 0,
        references_count=len(data.get("references", []) or []),
        tldr=tldr_text,
        code_url=external_ids.get("GitHub"),
        venue_normalized=data.get("venue") or None,
        fields_of_study=data.get("fieldsOfStudy", []) or [],
    )


def _parse_candidate(
    data: dict,
    source: str = "semantic_scholar",
) -> PaperCandidate:
    """Parse an S2 paper object into a PaperCandidate."""
    external_ids = data.get("externalIds", {}) or {}
    authors_data = data.get("authors", []) or []
    authors = [a.get("name", "") for a in authors_data if a.get("name")]

    return PaperCandidate(
        arxiv_id=external_ids.get("ArXiv"),
        s2_id=data.get("paperId"),
        doi=external_ids.get("DOI"),
        title=data.get("title", ""),
        authors=authors,
        abstract=data.get("abstract", "") or "",
        venue=data.get("venue") or None,
        year=data.get("year"),
        url=data.get("url"),
        source=source,
    )
