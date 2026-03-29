"""Tests for paper_fetch tool."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alpha_research.models.research import ExtractionQuality, Paper, PaperStatus
from alpha_research.tools.paper_fetch import (
    _assess_quality,
    _detect_sections,
    _extract_title_from_text,
    _normalize_section_name,
    fetch_and_extract,
)


# ---------------------------------------------------------------------------
# Section detection tests
# ---------------------------------------------------------------------------

class TestSectionDetection:
    def test_numbered_sections(self):
        text = (
            "Some title\n"
            "Author names\n\n"
            "1. Introduction\n"
            "This paper introduces a new method.\n\n"
            "2. Related Work\n"
            "Prior work has explored this topic.\n\n"
            "3. Method\n"
            "We propose the following approach.\n\n"
            "4. Experiments\n"
            "We evaluate on three benchmarks.\n\n"
            "5. Conclusion\n"
            "We presented a new method.\n"
        )
        sections = _detect_sections(text)

        assert "introduction" in sections
        assert "related_work" in sections
        assert "method" in sections
        assert "experiments" in sections
        assert "conclusion" in sections

    def test_allcaps_sections(self):
        text = (
            "ABSTRACT\n"
            "This is the abstract text.\n\n"
            "INTRODUCTION\n"
            "We introduce our work.\n\n"
            "RELATED WORK\n"
            "Previous approaches include...\n\n"
            "CONCLUSION\n"
            "We conclude.\n"
        )
        sections = _detect_sections(text)

        assert "abstract" in sections
        assert "introduction" in sections
        assert "related_work" in sections
        assert "conclusion" in sections

    def test_roman_numeral_sections(self):
        text = (
            "I. INTRODUCTION\n"
            "We present a system.\n\n"
            "II. RELATED WORK\n"
            "Others have done this.\n\n"
            "III. EXPERIMENTS\n"
            "We tested our system.\n\n"
            "IV. CONCLUSION\n"
            "We conclude.\n"
        )
        sections = _detect_sections(text)

        assert "introduction" in sections
        assert "related_work" in sections
        assert "experiments" in sections
        assert "conclusion" in sections

    def test_markdown_headers(self):
        text = (
            "# Introduction\n"
            "This paper introduces.\n\n"
            "## Method\n"
            "Our approach is.\n\n"
            "## Results\n"
            "We found that.\n"
        )
        sections = _detect_sections(text)

        assert "introduction" in sections
        assert "method" in sections
        assert "experiments" in sections  # "results" normalizes to "experiments"

    def test_no_sections_detected(self):
        text = "Just some plain text without any clear section headers."
        sections = _detect_sections(text)
        assert sections == {}


class TestNormalizeSectionName:
    def test_canonical_names(self):
        assert _normalize_section_name("Introduction") == "introduction"
        assert _normalize_section_name("RELATED WORK") == "related_work"
        assert _normalize_section_name("Methods") == "method"
        assert _normalize_section_name("Methodology") == "method"
        assert _normalize_section_name("Experimental Results") == "experiments"
        assert _normalize_section_name("Conclusions") == "conclusion"
        assert _normalize_section_name("References") == "references"

    def test_unknown_name(self):
        assert _normalize_section_name("System Design") == "system_design"


class TestExtractTitle:
    def test_basic_title(self):
        text = "A Novel Approach to Robot Manipulation\nAuthor One, Author Two\n\nAbstract..."
        title = _extract_title_from_text(text)
        assert "Novel Approach" in title

    def test_empty_text(self):
        assert _extract_title_from_text("") == "Unknown Title"

    def test_multiline_title(self):
        text = "Learning Dexterous Manipulation\nwith Tactile Feedback\n\nAuthors here"
        title = _extract_title_from_text(text)
        assert "Learning Dexterous Manipulation" in title
        assert "Tactile Feedback" in title


class TestAssessQuality:
    def test_high_quality(self):
        text = "x" * 5000
        sections = {"introduction": "...", "method": "...", "experiments": "...", "conclusion": "..."}
        quality = _assess_quality(text, sections)
        assert quality.overall == "high"

    def test_no_sections(self):
        text = "x" * 5000
        quality = _assess_quality(text, {})
        assert quality.overall == "low"
        assert any("No section" in i for i in quality.flagged_issues)

    def test_empty_text(self):
        quality = _assess_quality("", {})
        assert quality.overall == "abstract_only"

    def test_few_sections(self):
        text = "x" * 5000
        sections = {"introduction": "...", "conclusion": "..."}
        quality = _assess_quality(text, sections)
        assert quality.overall == "medium"

    def test_math_detection(self):
        text = "The loss function is $\\sum_{i} L_i$" + "x" * 5000
        sections = {"intro": "...", "method": "...", "results": "..."}
        quality = _assess_quality(text, sections)
        assert quality.math_preserved is True

    def test_short_text(self):
        quality = _assess_quality("short text", {"intro": "..."})
        assert quality.overall == "low"


# ---------------------------------------------------------------------------
# Integration test (with mocked PDF)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestFetchAndExtract:
    @patch("alpha_research.tools.paper_fetch._download_pdf", new_callable=AsyncMock)
    @patch("alpha_research.tools.paper_fetch.fitz")
    async def test_fetch_and_extract(self, mock_fitz, mock_download, tmp_path):
        """Test fetch_and_extract with mocked PDF."""
        # Set up mock PDF
        pdf_text = (
            "A Great Paper on Robots\n"
            "Author One, Author Two\n\n"
            "ABSTRACT\n"
            "We present a robot system.\n\n"
            "INTRODUCTION\n"
            "Robots are important for many applications.\n\n"
            "METHOD\n"
            "Our approach uses reinforcement learning with tactile feedback.\n\n"
            "EXPERIMENTS\n"
            "We tested on 10 objects with 20 trials each.\n\n"
            "CONCLUSION\n"
            "We demonstrated effective manipulation.\n\n"
            "REFERENCES\n"
            "[1] Some reference.\n"
        )

        mock_page = MagicMock()
        mock_page.get_text.return_value = pdf_text

        mock_doc = MagicMock()
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_fitz.open.return_value = mock_doc

        # Create a fake PDF file so the "exists" check passes
        pdf_path = tmp_path / "2301.12345.pdf"
        pdf_path.write_bytes(b"fake pdf content")

        paper = await fetch_and_extract("2301.12345", output_dir=str(tmp_path))

        assert isinstance(paper, Paper)
        assert paper.arxiv_id == "2301.12345"
        assert paper.extraction_source == "pdf"
        assert paper.status == PaperStatus.EXTRACTED
        assert paper.extraction_quality is not None

        # Should have detected sections
        assert len(paper.sections) > 0
        assert "abstract" in paper.sections or "introduction" in paper.sections

    @patch("alpha_research.tools.paper_fetch._download_pdf", new_callable=AsyncMock)
    @patch("alpha_research.tools.paper_fetch.fitz")
    async def test_fetch_creates_output_dir(self, mock_fitz, mock_download, tmp_path):
        """Test that output directory is created if missing."""
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Title\n\nSome text content " * 100

        mock_doc = MagicMock()
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_fitz.open.return_value = mock_doc

        new_dir = tmp_path / "new_subdir" / "papers"
        # File won't exist, so download will be called
        paper = await fetch_and_extract("2301.99999", output_dir=str(new_dir))

        assert isinstance(paper, Paper)
        mock_download.assert_called_once()
