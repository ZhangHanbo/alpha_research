"""Report-emitting unit tests for ``alpha_research.tools.paper_fetch``.

Complements the existing ``test_paper_fetch.py`` by routing every case
through the ``report`` fixture so a human-readable module report lands
at ``tests/reports/test_paper_fetch_report.md``.
"""

from __future__ import annotations

from alpha_research.tools.paper_fetch import (
    _assess_quality,
    _detect_sections,
    _extract_title_from_text,
    _normalize_section_name,
)


SAMPLE_TEXT = """\
Tactile Servoing for Deformable Manipulation

Alice Author and Bob Author

ABSTRACT
We present a tactile servoing method for manipulating deformable objects.
This section describes our contribution and summarises the results.

1. Introduction
Deformable objects remain one of the hardest categories for manipulation.
We focus on soft bags and cables.

2. Method
Our approach uses a residual controller on top of a low-level admittance loop.
We leverage marker tracking from GelSight sensors to recover contact geometry.

3. Experiments
We evaluate on 10 trials across 5 object categories and compare to 3 baselines.
Results in Table 1 and Figure 2 show consistent improvements.

4. Conclusion
Tactile feedback is essential for sub-mm alignment on deformable geometry.

References
[1] Smith et al. 2023
"""


def test_normalize_section_name(report) -> None:
    cases = {
        "Introduction": "introduction",
        "METHODS": "method",
        "Related Work": "related_work",
        "Experimental Results": "experiments",
        "Conclusions": "conclusion",
    }
    actual = {k: _normalize_section_name(k) for k in cases}
    passed = actual == cases
    report.record(
        name="_normalize_section_name maps synonyms to canonical keys",
        purpose="Paper sections should normalise across header variants so downstream code has stable keys.",
        inputs=list(cases.keys()),
        expected=cases,
        actual=actual,
        passed=passed,
        conclusion="Normalisation lets skills reference e.g. paper['sections']['method'] reliably.",
    )
    assert passed


def test_detect_sections_finds_numbered_headers(report) -> None:
    sections = _detect_sections(SAMPLE_TEXT)
    expected_keys = {"abstract", "introduction", "method", "experiments", "conclusion"}
    present = expected_keys & set(sections.keys())
    passed = present == expected_keys
    report.record(
        name="numbered + ALL-CAPS sections are detected",
        purpose="_detect_sections should recognise 'ABSTRACT', '1. Introduction', etc.",
        inputs={"text_first_line": SAMPLE_TEXT.splitlines()[0]},
        expected=sorted(expected_keys),
        actual=sorted(sections.keys()),
        passed=passed,
        conclusion="Canonical sections are present, which lets skills read the right section by name.",
    )
    assert passed


def test_extract_title_from_text(report) -> None:
    title = _extract_title_from_text(SAMPLE_TEXT)
    passed = "Tactile Servoing" in title
    report.record(
        name="title extracted from first non-empty line(s)",
        purpose="The first content line of a PDF is conventionally the title.",
        inputs={"first_line": SAMPLE_TEXT.splitlines()[0]},
        expected="contains 'Tactile Servoing'",
        actual=title,
        passed=passed,
        conclusion="Heuristic is good enough for offline extraction and matches arXiv metadata in practice.",
    )
    assert passed


def test_assess_quality_high_when_sections_detected(report) -> None:
    sections = _detect_sections(SAMPLE_TEXT)
    # Pad to >1000 chars so the 'short text' branch is not triggered
    text = SAMPLE_TEXT + ("\nFiller content. " * 80)
    quality = _assess_quality(text, sections)
    passed = quality.overall == "high"
    report.record(
        name="quality is 'high' when multiple sections are detected",
        purpose="_assess_quality should classify a well-structured paper as high quality.",
        inputs={"section_count": len(sections), "text_length": len(text)},
        expected={"overall": "high"},
        actual={"overall": quality.overall, "flagged_issues": quality.flagged_issues},
        passed=passed,
        conclusion="Good section detection and non-trivial text length indicates a usable extraction.",
    )
    assert passed


def test_assess_quality_abstract_only_on_empty_text(report) -> None:
    quality = _assess_quality("", {})
    passed = quality.overall == "abstract_only"
    report.record(
        name="empty text assessed as abstract_only",
        purpose="Empty extraction should be classified as 'abstract_only' with a flagged issue.",
        inputs={"text": "", "sections": {}},
        expected={"overall": "abstract_only"},
        actual={"overall": quality.overall, "flagged_issues": quality.flagged_issues},
        passed=passed,
        conclusion="Empty PDFs are caught early so downstream skills don't waste LLM calls.",
    )
    assert passed


def test_assess_quality_detects_math(report) -> None:
    text = "The loss function is $\\sum_{i} L_i$ " + ("filler text. " * 100)
    sections = {"abstract": "a", "method": "m", "experiments": "e"}
    quality = _assess_quality(text, sections)
    passed = quality.math_preserved is True
    report.record(
        name="math symbols detected in extracted text",
        purpose="_assess_quality inspects for LaTeX / Unicode math markers.",
        inputs={"snippet": text[:60] + "..."},
        expected={"math_preserved": True},
        actual={"math_preserved": quality.math_preserved},
        passed=passed,
        conclusion="Math preservation is a proxy for usable formalization extraction.",
    )
    assert passed
