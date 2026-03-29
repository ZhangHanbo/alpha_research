"""Tests for semantic_scholar tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from alpha_research.models.research import PaperCandidate, PaperMetadata
from alpha_research.tools.semantic_scholar import (
    _parse_candidate,
    _parse_metadata,
    get_citations,
    get_paper_metadata,
    get_references,
    search_papers,
)


# ---------------------------------------------------------------------------
# Sample API responses
# ---------------------------------------------------------------------------

SAMPLE_PAPER_RESPONSE = {
    "paperId": "abc123",
    "title": "Learning Dexterous Manipulation",
    "authors": [
        {"authorId": "1", "name": "Alice Researcher"},
        {"authorId": "2", "name": "Bob Scientist"},
    ],
    "abstract": "We present a method for dexterous manipulation.",
    "year": 2023,
    "venue": "RSS",
    "citationCount": 42,
    "influentialCitationCount": 5,
    "tldr": {"text": "A new dexterous manipulation method using RL."},
    "externalIds": {"ArXiv": "2301.12345", "DOI": "10.1234/test"},
    "url": "https://www.semanticscholar.org/paper/abc123",
    "references": [{"paperId": "ref1"}, {"paperId": "ref2"}],
    "citations": [{"paperId": "cit1"}],
    "fieldsOfStudy": ["Computer Science"],
}

SAMPLE_SEARCH_RESPONSE = {
    "total": 2,
    "data": [
        {
            "paperId": "p1",
            "title": "Paper One",
            "authors": [{"name": "Author A"}],
            "abstract": "First paper abstract.",
            "year": 2023,
            "venue": "ICRA",
            "citationCount": 10,
            "influentialCitationCount": 1,
            "tldr": None,
            "externalIds": {"ArXiv": "2301.00001"},
            "url": "https://s2.org/p1",
        },
        {
            "paperId": "p2",
            "title": "Paper Two",
            "authors": [{"name": "Author B"}, {"name": "Author C"}],
            "abstract": "Second paper abstract.",
            "year": 2022,
            "venue": "CoRL",
            "citationCount": 25,
            "influentialCitationCount": 3,
            "tldr": {"text": "A summary of paper two."},
            "externalIds": {"ArXiv": "2201.00002", "DOI": "10.5678/test2"},
            "url": "https://s2.org/p2",
        },
    ],
}

SAMPLE_REFERENCES_RESPONSE = {
    "data": [
        {
            "citedPaper": {
                "paperId": "ref1",
                "title": "Referenced Paper",
                "authors": [{"name": "Ref Author"}],
                "abstract": "A referenced paper.",
                "year": 2020,
                "venue": "NeurIPS",
                "citationCount": 100,
                "influentialCitationCount": 20,
                "tldr": None,
                "externalIds": {"ArXiv": "2001.11111"},
                "url": "https://s2.org/ref1",
            }
        },
        {
            "citedPaper": {
                "paperId": None,
                "title": None,
                "authors": [],
            }
        },
    ],
}

SAMPLE_CITATIONS_RESPONSE = {
    "data": [
        {
            "citingPaper": {
                "paperId": "cit1",
                "title": "Citing Paper",
                "authors": [{"name": "Citer One"}],
                "abstract": "We extend the prior work.",
                "year": 2024,
                "venue": "IROS",
                "citationCount": 3,
                "influentialCitationCount": 0,
                "tldr": None,
                "externalIds": {},
                "url": "https://s2.org/cit1",
            }
        },
    ],
}


# ---------------------------------------------------------------------------
# Unit tests for parsers
# ---------------------------------------------------------------------------

class TestParseMetadata:
    def test_full_response(self):
        meta = _parse_metadata(SAMPLE_PAPER_RESPONSE)
        assert isinstance(meta, PaperMetadata)
        assert meta.citation_count == 42
        assert meta.influential_citation_count == 5
        assert meta.references_count == 2
        assert meta.tldr == "A new dexterous manipulation method using RL."
        assert meta.venue_normalized == "RSS"
        assert "Computer Science" in meta.fields_of_study

    def test_missing_fields(self):
        meta = _parse_metadata({"paperId": "x"})
        assert meta.citation_count == 0
        assert meta.influential_citation_count == 0
        assert meta.tldr is None
        assert meta.fields_of_study == []

    def test_none_tldr(self):
        data = {**SAMPLE_PAPER_RESPONSE, "tldr": None}
        meta = _parse_metadata(data)
        assert meta.tldr is None


class TestParseCandidate:
    def test_full_parse(self):
        data = SAMPLE_SEARCH_RESPONSE["data"][0]
        candidate = _parse_candidate(data)
        assert isinstance(candidate, PaperCandidate)
        assert candidate.title == "Paper One"
        assert candidate.arxiv_id == "2301.00001"
        assert candidate.s2_id == "p1"
        assert candidate.authors == ["Author A"]
        assert candidate.source == "semantic_scholar"

    def test_citation_graph_source(self):
        data = SAMPLE_SEARCH_RESPONSE["data"][0]
        candidate = _parse_candidate(data, source="citation_graph")
        assert candidate.source == "citation_graph"

    def test_missing_external_ids(self):
        data = {
            "paperId": "p3",
            "title": "Paper Three",
            "authors": [],
            "externalIds": None,
        }
        candidate = _parse_candidate(data)
        assert candidate.arxiv_id is None
        assert candidate.doi is None


# ---------------------------------------------------------------------------
# Async API tests (mocked httpx)
# ---------------------------------------------------------------------------

def _mock_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    """Create a mock httpx.Response."""
    response = httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://test"),
    )
    return response


@pytest.mark.asyncio
class TestGetPaperMetadata:
    @patch("alpha_research.tools.semantic_scholar.httpx.AsyncClient")
    async def test_get_metadata(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            return_value=_mock_response(SAMPLE_PAPER_RESPONSE)
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        meta = await get_paper_metadata("ArXiv:2301.12345")

        assert isinstance(meta, PaperMetadata)
        assert meta.citation_count == 42
        mock_client.request.assert_called_once()

    @patch("alpha_research.tools.semantic_scholar.httpx.AsyncClient")
    async def test_get_metadata_by_s2_id(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            return_value=_mock_response(SAMPLE_PAPER_RESPONSE)
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        meta = await get_paper_metadata("abc123")
        assert isinstance(meta, PaperMetadata)


@pytest.mark.asyncio
class TestSearchPapers:
    @patch("alpha_research.tools.semantic_scholar.httpx.AsyncClient")
    async def test_search(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            return_value=_mock_response(SAMPLE_SEARCH_RESPONSE)
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        results = await search_papers("robot manipulation", limit=10)

        assert len(results) == 2
        assert all(isinstance(r, PaperCandidate) for r in results)
        assert results[0].title == "Paper One"
        assert results[1].title == "Paper Two"

    @patch("alpha_research.tools.semantic_scholar.httpx.AsyncClient")
    async def test_search_empty(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            return_value=_mock_response({"total": 0, "data": []})
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        results = await search_papers("nonexistent")
        assert results == []


@pytest.mark.asyncio
class TestGetReferences:
    @patch("alpha_research.tools.semantic_scholar.httpx.AsyncClient")
    async def test_get_references(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            return_value=_mock_response(SAMPLE_REFERENCES_RESPONSE)
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        results = await get_references("abc123")

        # Should skip the entry with no title
        assert len(results) == 1
        assert results[0].title == "Referenced Paper"
        assert results[0].source == "citation_graph"


@pytest.mark.asyncio
class TestGetCitations:
    @patch("alpha_research.tools.semantic_scholar.httpx.AsyncClient")
    async def test_get_citations(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            return_value=_mock_response(SAMPLE_CITATIONS_RESPONSE)
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        results = await get_citations("abc123")

        assert len(results) == 1
        assert results[0].title == "Citing Paper"
        assert results[0].year == 2024
