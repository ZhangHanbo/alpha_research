"""Tests for report generation tool."""

from __future__ import annotations

import pytest

from alpha_research.tools.report import generate_report


# ---------------------------------------------------------------------------
# Sample evaluation data
# ---------------------------------------------------------------------------

def _make_eval(
    title: str = "Test Paper",
    arxiv_id: str = "2301.12345",
    **overrides,
) -> dict:
    """Create a sample evaluation dict."""
    data = {
        "title": title,
        "arxiv_id": arxiv_id,
        "authors": ["Alice", "Bob"],
        "year": 2023,
        "venue": "RSS",
        "abstract": "We present a method for robot manipulation using tactile feedback.",
        "rubric_scores": {
            "Significance": {"score": 4, "confidence": "medium", "evidence": ["Addresses contact-rich assembly"]},
            "Technical Approach": {"score": 3, "confidence": "medium", "evidence": ["Uses diffusion policy"]},
            "Experimental Rigor": {"score": 2, "confidence": "high", "evidence": ["Only 5 trials"]},
        },
        "significance_assessment": {
            "hamming_score": 4,
            "hamming_reasoning": "Important problem in manipulation.",
            "concrete_consequence": "Enables assembly without CAD models.",
            "durability_risk": "low",
            "durability_reasoning": "Contact manipulation remains relevant.",
            "compounding_value": "high",
            "compounding_reasoning": "Enables downstream assembly tasks.",
            "motivation_type": "goal_driven",
        },
        "task_chain": {
            "task": "Contact-rich assembly",
            "problem": "Assembly without CAD models",
            "challenge": "Uncertain contact dynamics",
            "approach": "Diffusion policy with tactile feedback",
            "one_sentence": "We use diffusion policies conditioned on tactile feedback to handle uncertain contact.",
            "chain_complete": True,
            "chain_coherent": True,
        },
        "has_formal_problem_def": True,
        "formal_framework": "Constrained optimization",
        "structure_identified": ["convexity", "contact constraints"],
        "strengths": ["Novel use of tactile feedback", "Real robot experiments"],
        "weaknesses": ["Only 5 trials per condition", "No failure analysis"],
        "related_papers": [
            {"paper_id": "2201.00001", "relation_type": "extends", "evidence": "Adds tactile input"},
        ],
        "open_questions": ["Would this work with different grippers?"],
        "human_review_flags": ["Mathematical assessment requires human review"],
        "extraction_limitations": ["Equations may not be fully extracted"],
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDigestMode:
    def test_basic_digest(self):
        evals = [_make_eval(title="Paper A"), _make_eval(title="Paper B", arxiv_id="2301.99999")]
        report = generate_report(evals, mode="digest", title="Weekly Digest")

        assert "# Research Digest: Weekly Digest" in report
        assert "Paper A" in report
        assert "Paper B" in report
        assert "Papers reviewed:** 2" in report

    def test_empty_digest(self):
        report = generate_report([], mode="digest")
        assert "Papers reviewed:** 0" in report

    def test_digest_contains_scores(self):
        report = generate_report([_make_eval()], mode="digest")
        assert "Significance" in report
        assert "4/5" in report

    def test_digest_contains_significance(self):
        report = generate_report([_make_eval()], mode="digest")
        assert "Hamming=" in report

    def test_digest_contains_flags(self):
        report = generate_report([_make_eval()], mode="digest")
        assert "human review" in report.lower()


class TestDeepMode:
    def test_basic_deep(self):
        report = generate_report([_make_eval()], mode="deep")

        assert "# Paper Evaluation: Test Paper" in report
        assert "Alice" in report
        assert "RSS" in report

    def test_deep_has_all_sections(self):
        report = generate_report([_make_eval()], mode="deep")

        assert "## Summary" in report
        assert "## Task Chain" in report
        assert "## Rubric Evaluation" in report
        assert "## Significance Assessment" in report
        assert "## Problem Formalization Assessment" in report
        assert "## Strengths" in report
        assert "## Weaknesses" in report
        assert "## Connections to Prior Work" in report
        assert "## Open Questions" in report

    def test_deep_task_chain(self):
        report = generate_report([_make_eval()], mode="deep")
        assert "Contact-rich assembly" in report
        assert "Diffusion policy" in report

    def test_deep_rubric_table(self):
        report = generate_report([_make_eval()], mode="deep")
        assert "| **Significance**" in report
        assert "4/5" in report
        assert "medium" in report

    def test_deep_significance_assessment(self):
        report = generate_report([_make_eval()], mode="deep")
        assert "Hamming test" in report
        assert "Durability test" in report
        assert "Compounding value" in report
        assert "HUMAN JUDGMENT REQUIRED" in report

    def test_deep_formalization(self):
        report = generate_report([_make_eval()], mode="deep")
        assert "Formal statement present?" in report
        assert "Yes" in report
        assert "Constrained optimization" in report

    def test_deep_empty_evaluations(self):
        report = generate_report([], mode="deep")
        assert "No evaluations" in report

    def test_deep_minimal_eval(self):
        """Test with minimal evaluation data (no optional fields)."""
        minimal = {
            "title": "Minimal Paper",
            "authors": [],
            "abstract": "",
            "rubric_scores": {},
            "significance_assessment": None,
            "task_chain": None,
            "has_formal_problem_def": False,
        }
        report = generate_report([minimal], mode="deep")
        assert "Minimal Paper" in report
        assert "No rubric scores available" in report


class TestSurveyModeRemoved:
    """The ``survey`` mode was removed in the R3 refactor — alpha_review's
    ``run_write`` pipeline produces LaTeX surveys with BibTeX and PDF, which
    supersedes our hand-written markdown survey template."""

    def test_survey_mode_raises_with_helpful_message(self):
        with pytest.raises(ValueError, match="removed in the R3 refactor"):
            generate_report([_make_eval()], mode="survey")


class TestInvalidMode:
    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown report mode"):
            generate_report([], mode="invalid")
