"""Tests for arxiv_search tool."""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from alpha_research.models.research import PaperCandidate
from alpha_research.tools.arxiv_search import (
    _build_query,
    _extract_arxiv_id,
    _result_to_candidate,
    search_arxiv,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_mock_result(
    entry_id: str = "http://arxiv.org/abs/2301.12345v1",
    title: str = "Test Paper on Robot Learning",
    summary: str = "We propose a novel method for robot manipulation.",
    authors: list[str] | None = None,
    published: datetime | None = None,
) -> MagicMock:
    """Create a mock arxiv.Result object."""
    result = MagicMock()
    result.entry_id = entry_id
    result.title = title
    result.summary = summary
    result.authors = [MagicMock(__str__=lambda self, n=n: n) for n in (authors or ["Alice", "Bob"])]
    result.published = published or datetime(2023, 1, 15)
    return result


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestBuildQuery:
    def test_no_categories(self):
        assert _build_query("robot manipulation", None) == "robot manipulation"

    def test_empty_categories(self):
        assert _build_query("robot", []) == "robot"

    def test_single_category(self):
        q = _build_query("robot", ["cs.RO"])
        assert "cat:cs.RO" in q
        assert "(robot)" in q

    def test_multiple_categories(self):
        q = _build_query("robot", ["cs.RO", "cs.AI"])
        assert "cat:cs.RO" in q
        assert "cat:cs.AI" in q
        assert " OR " in q


class TestExtractArxivId:
    def test_standard_url(self):
        assert _extract_arxiv_id("http://arxiv.org/abs/2301.12345v1") == "2301.12345"

    def test_no_version(self):
        assert _extract_arxiv_id("http://arxiv.org/abs/2301.12345") == "2301.12345"

    def test_old_format(self):
        result = _extract_arxiv_id("http://arxiv.org/abs/cs/0612047v2")
        assert result == "cs/0612047"


class TestResultToCandidate:
    def test_basic_conversion(self):
        mock = _make_mock_result()
        candidate = _result_to_candidate(mock)

        assert isinstance(candidate, PaperCandidate)
        assert candidate.arxiv_id == "2301.12345"
        assert candidate.title == "Test Paper on Robot Learning"
        assert candidate.abstract == "We propose a novel method for robot manipulation."
        assert candidate.authors == ["Alice", "Bob"]
        assert candidate.year == 2023
        assert candidate.source == "arxiv"

    def test_empty_summary(self):
        mock = _make_mock_result(summary="")
        candidate = _result_to_candidate(mock)
        assert candidate.abstract == ""


@pytest.mark.asyncio
class TestSearchArxiv:
    @patch("alpha_research.tools.arxiv_search._fetch_results")
    @patch("alpha_research.tools.arxiv_search._last_request_time", 0.0)
    async def test_basic_search(self, mock_fetch):
        """Test that search_arxiv returns PaperCandidate objects."""
        mock_fetch.return_value = [
            _make_mock_result(
                entry_id="http://arxiv.org/abs/2301.00001v1",
                title="Paper One",
            ),
            _make_mock_result(
                entry_id="http://arxiv.org/abs/2301.00002v1",
                title="Paper Two",
            ),
        ]

        results = await search_arxiv("robot manipulation", max_results=10)

        assert len(results) == 2
        assert all(isinstance(r, PaperCandidate) for r in results)
        assert results[0].title == "Paper One"
        assert results[1].title == "Paper Two"
        mock_fetch.assert_called_once()

    @patch("alpha_research.tools.arxiv_search._fetch_results")
    @patch("alpha_research.tools.arxiv_search._last_request_time", 0.0)
    async def test_date_filtering(self, mock_fetch):
        """Test that date filters are applied."""
        mock_fetch.return_value = [
            _make_mock_result(
                entry_id="http://arxiv.org/abs/2301.00001v1",
                title="Old Paper",
                published=datetime(2022, 6, 1),
            ),
            _make_mock_result(
                entry_id="http://arxiv.org/abs/2301.00002v1",
                title="New Paper",
                published=datetime(2023, 6, 1),
            ),
        ]

        results = await search_arxiv(
            "robot",
            date_start="2023-01-01",
            date_end="2023-12-31",
        )

        assert len(results) == 1
        assert results[0].title == "New Paper"

    @patch("alpha_research.tools.arxiv_search._fetch_results")
    @patch("alpha_research.tools.arxiv_search._last_request_time", 0.0)
    async def test_empty_results(self, mock_fetch):
        """Test handling of empty results."""
        mock_fetch.return_value = []

        results = await search_arxiv("nonexistent topic xyz")
        assert results == []

    @patch("alpha_research.tools.arxiv_search._fetch_results")
    @patch("alpha_research.tools.arxiv_search._last_request_time", 0.0)
    async def test_category_filter_passed(self, mock_fetch):
        """Test that categories are passed to query builder."""
        mock_fetch.return_value = []

        await search_arxiv("robot", categories=["cs.RO", "cs.AI"])
        # Verify the Search object was created with category filter
        mock_fetch.assert_called_once()
        search_obj = mock_fetch.call_args[0][0]
        assert "cat:cs.RO" in search_obj.query
        assert "cat:cs.AI" in search_obj.query
