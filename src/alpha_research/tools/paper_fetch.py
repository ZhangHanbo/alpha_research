"""Paper fetch and text extraction tool.

Downloads PDFs from ArXiv and extracts structured text using pymupdf.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import fitz  # pymupdf
import httpx

from alpha_research.models.research import (
    ExtractionQuality,
    Paper,
    PaperStatus,
)

ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}.pdf"

# Section header patterns (ordered by priority)
# Matches patterns like:
#   "1. Introduction", "2.1 Method", "## Method",
#   "III. EXPERIMENTS", "ABSTRACT", "A. Appendix Title"
SECTION_PATTERNS: list[re.Pattern[str]] = [
    # Markdown-style headers
    re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE),
    # Numbered sections: "1. Introduction", "2.1. Method"
    re.compile(r"^(\d+\.[\d.]*)\s+([A-Z][A-Za-z\s:&-]+)$", re.MULTILINE),
    # Roman numeral sections: "III. EXPERIMENTS"
    re.compile(
        r"^(I{1,3}|IV|V|VI{0,3}|IX|X{0,3})\.\s+([A-Z][A-Z\s:&-]+)$",
        re.MULTILINE,
    ),
    # Letter sections: "A. Appendix Title"
    re.compile(r"^([A-Z])\.\s+([A-Z][A-Za-z\s:&-]+)$", re.MULTILINE),
    # ALL-CAPS standalone headers
    re.compile(
        r"^(ABSTRACT|INTRODUCTION|RELATED WORK|METHODOLOGY|METHOD|METHODS|"
        r"APPROACH|EXPERIMENTS|EXPERIMENTAL RESULTS|RESULTS|"
        r"DISCUSSION|CONCLUSION|CONCLUSIONS|REFERENCES|ACKNOWLEDGMENTS|"
        r"ACKNOWLEDGEMENTS|APPENDIX)$",
        re.MULTILINE,
    ),
]

# Canonical section names for normalization
CANONICAL_SECTIONS = {
    "abstract": "abstract",
    "introduction": "introduction",
    "related work": "related_work",
    "background": "background",
    "method": "method",
    "methods": "method",
    "methodology": "method",
    "approach": "method",
    "proposed method": "method",
    "proposed approach": "method",
    "experiments": "experiments",
    "experimental results": "experiments",
    "results": "experiments",
    "evaluation": "experiments",
    "discussion": "discussion",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
    "references": "references",
    "acknowledgments": "acknowledgments",
    "acknowledgements": "acknowledgments",
    "appendix": "appendix",
}


async def fetch_and_extract(
    arxiv_id: str,
    output_dir: str = "data/papers",
) -> Paper:
    """Download a paper from ArXiv and extract structured text.

    Args:
        arxiv_id: The ArXiv paper ID (e.g. "2301.12345").
        output_dir: Directory to save downloaded PDFs.

    Returns:
        A Paper model with extracted text and sections.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pdf_path = output_path / f"{arxiv_id.replace('/', '_')}.pdf"

    # Download PDF
    if not pdf_path.exists():
        await _download_pdf(arxiv_id, pdf_path)

    # Extract text
    full_text, sections, quality = _extract_text(pdf_path)

    paper = Paper(
        arxiv_id=arxiv_id,
        title=_extract_title_from_text(full_text),
        full_text=full_text,
        sections=sections,
        extraction_source="pdf",
        extraction_quality=quality,
        status=PaperStatus.EXTRACTED,
        url=f"https://arxiv.org/abs/{arxiv_id}",
    )

    return paper


async def _download_pdf(arxiv_id: str, dest: Path) -> None:
    """Download a PDF from ArXiv."""
    url = ARXIV_PDF_URL.format(arxiv_id=arxiv_id)
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        dest.write_bytes(response.content)


def _extract_text(pdf_path: Path) -> tuple[str, dict[str, str], ExtractionQuality]:
    """Extract text and detect sections from a PDF.

    Returns:
        Tuple of (full_text, sections_dict, quality_assessment).
    """
    doc = fitz.open(str(pdf_path))
    pages: list[str] = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()

    full_text = "\n".join(pages)

    # Detect sections
    sections = _detect_sections(full_text)

    # Assess quality
    quality = _assess_quality(full_text, sections)

    return full_text, sections, quality


def _detect_sections(text: str) -> dict[str, str]:
    """Detect and extract sections from paper text.

    Uses regex patterns to find section headers, then extracts content
    between consecutive headers.
    """
    # Find all section header positions
    header_positions: list[tuple[int, str]] = []

    for pattern in SECTION_PATTERNS:
        for match in pattern.finditer(text):
            # Get the section name from the match
            groups = match.groups()
            if len(groups) == 1:
                name = groups[0].strip()
            else:
                # For numbered/lettered sections, the name is the last group
                name = groups[-1].strip()

            start = match.start()
            header_positions.append((start, name))

    if not header_positions:
        return {}

    # Sort by position
    header_positions.sort(key=lambda x: x[0])

    # Deduplicate: if two headers are within 5 chars, keep the first
    deduped: list[tuple[int, str]] = []
    for pos, name in header_positions:
        if deduped and pos - deduped[-1][0] < 5:
            continue
        deduped.append((pos, name))

    # Extract content between headers
    sections: dict[str, str] = {}
    for i, (pos, name) in enumerate(deduped):
        # Find the end of the header line
        header_end = text.find("\n", pos)
        if header_end == -1:
            header_end = pos + len(name)

        # Content goes from end of header to start of next header
        if i + 1 < len(deduped):
            content = text[header_end:deduped[i + 1][0]]
        else:
            content = text[header_end:]

        # Normalize section name
        normalized = _normalize_section_name(name)
        content = content.strip()

        if content:
            # If we already have this section, append
            if normalized in sections:
                sections[normalized] += "\n" + content
            else:
                sections[normalized] = content

    return sections


def _normalize_section_name(name: str) -> str:
    """Normalize a section name to a canonical form."""
    lower = name.lower().strip()
    return CANONICAL_SECTIONS.get(lower, lower.replace(" ", "_"))


def _extract_title_from_text(text: str) -> str:
    """Extract paper title from the first lines of text.

    Heuristic: the title is usually the first non-empty line(s) of the PDF.
    """
    lines = text.strip().split("\n")
    title_lines: list[str] = []
    for line in lines[:5]:  # Check first 5 lines
        stripped = line.strip()
        if stripped:
            title_lines.append(stripped)
            # Title is usually 1-2 lines
            if len(title_lines) >= 2:
                break
        elif title_lines:
            break  # Empty line after title content

    return " ".join(title_lines) if title_lines else "Unknown Title"


def _assess_quality(
    text: str,
    sections: dict[str, str],
) -> ExtractionQuality:
    """Assess the quality of text extraction."""
    issues: list[str] = []
    sections_detected = list(sections.keys())

    # Check for math preservation (look for LaTeX-like content)
    math_preserved = bool(re.search(r"[\\$∑∫∏∂∇]", text))

    # Determine overall quality
    if not text.strip():
        overall = "abstract_only"
        issues.append("No text extracted from PDF")
    elif len(sections) == 0:
        overall = "low"
        issues.append("No section headers detected")
    elif len(sections) < 3:
        overall = "medium"
        issues.append("Few sections detected — possible extraction issues")
    else:
        overall = "high"

    # Check for common extraction problems
    if text.count("\ufffd") > 10:  # Replacement characters
        issues.append("Many replacement characters — possible encoding issues")
        if overall == "high":
            overall = "medium"

    # Check text length — very short might mean extraction failed
    if len(text) < 1000 and overall != "abstract_only":
        overall = "low"
        issues.append("Very short text — likely incomplete extraction")

    return ExtractionQuality(
        overall=overall,
        math_preserved=math_preserved,
        sections_detected=sections_detected,
        flagged_issues=issues,
    )
