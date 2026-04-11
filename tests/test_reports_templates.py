"""Unit tests for ``alpha_research.reports.templates``."""

from __future__ import annotations

import pytest

from alpha_research.reports.templates import generate_report


def _eval(
    title: str = "Tactile Servoing",
    arxiv: str = "2401.12345",
    with_scores: bool = True,
    with_sig: bool = True,
) -> dict:
    d: dict = {
        "title": title,
        "authors": ["Alice", "Bob"],
        "year": 2024,
        "venue": "RSS",
        "arxiv_id": arxiv,
        "abstract": "We present a tactile servoing method for deformable manipulation.",
    }
    if with_scores:
        d["rubric_scores"] = {
            "B.1 significance": {"score": 4, "confidence": "medium", "evidence": ["Section 2"]},
            "B.3 formalization": {"score": 3, "confidence": "high", "evidence": []},
        }
    if with_sig:
        d["significance_assessment"] = {
            "hamming_score": 4,
            "durability_risk": "low",
            "compounding_value": "high",
            "motivation_type": "goal_driven",
            "concrete_consequence": "Enables assembly of flexible parts.",
        }
    return d


def test_digest_mode_multi_paper(report) -> None:
    evals = [_eval(title="Paper A"), _eval(title="Paper B", arxiv="2401.00002")]
    output = generate_report(evals, mode="digest", title="Weekly Digest")
    passed = (
        output.startswith("# Research Digest: Weekly Digest")
        and "Paper A" in output
        and "Paper B" in output
        and "| B.1 significance |" in output
    )
    report.record(
        name="digest template renders multi-paper summary",
        purpose="Produce a weekly digest with rubric rows for each paper.",
        inputs={"papers": ["Paper A", "Paper B"], "title": "Weekly Digest"},
        expected={"header": "# Research Digest: Weekly Digest", "contains_both": True, "contains_rubric_row": True},
        actual={
            "header": output.splitlines()[0],
            "contains_both": "Paper A" in output and "Paper B" in output,
            "contains_rubric_row": "| B.1 significance |" in output,
        },
        passed=passed,
        conclusion="Digest mode is stable and renders all rubric dimensions in a table.",
    )
    assert passed


def test_deep_mode_single_paper(report) -> None:
    ev = _eval(title="Deep Eval Paper")
    output = generate_report([ev], mode="deep")
    passed = (
        output.startswith("# Paper Evaluation: Deep Eval Paper")
        and "Hamming test:** 4/5" in output
        and "B.1 significance" in output
    )
    report.record(
        name="deep template renders single-paper evaluation",
        purpose="Deep mode renders rubric + significance + task chain for one paper.",
        inputs={"paper": ev["title"]},
        expected={
            "header": "# Paper Evaluation: Deep Eval Paper",
            "contains_hamming": True,
            "contains_rubric": True,
        },
        actual={
            "header": output.splitlines()[0],
            "contains_hamming": "Hamming test:** 4/5" in output,
            "contains_rubric": "B.1 significance" in output,
        },
        passed=passed,
        conclusion="Deep mode is the canonical single-paper artefact used by the CLI evaluate verb.",
    )
    assert passed


def test_deep_mode_no_evaluations(report) -> None:
    output = generate_report([], mode="deep")
    passed = output.strip().startswith("# No evaluations provided")
    report.record(
        name="deep mode on empty list returns a no-op header",
        purpose="An empty evaluations list in deep mode should return a friendly placeholder.",
        inputs={"evaluations": []},
        expected="# No evaluations provided.",
        actual=output.strip(),
        passed=passed,
        conclusion="The template never crashes on empty input — it degrades gracefully.",
    )
    assert passed


def test_survey_mode_removed(report) -> None:
    raised = False
    message = ""
    try:
        generate_report([], mode="survey")
    except ValueError as e:
        raised = True
        message = str(e)
    passed = raised and "run_write" in message
    report.record(
        name="survey mode raises a helpful ValueError",
        purpose="The survey mode was removed in R3. Calls must point at alpha_review.sdk.run_write.",
        inputs={"mode": "survey"},
        expected={"raises": True, "mentions_run_write": True},
        actual={"raises": raised, "message": message},
        passed=passed,
        conclusion="The error message guides the caller to the new API instead of silently failing.",
    )
    assert passed


def test_unknown_mode_raises(report) -> None:
    raised = False
    try:
        generate_report([_eval()], mode="foobar")
    except ValueError:
        raised = True
    report.record(
        name="unknown mode raises ValueError",
        purpose="generate_report should reject any mode other than digest/deep/survey.",
        inputs={"mode": "foobar"},
        expected={"raises": True},
        actual={"raises": raised},
        passed=raised,
        conclusion="Unknown modes fail loudly rather than default to a lossy output.",
    )
    assert raised
