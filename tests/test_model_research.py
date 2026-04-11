"""Unit tests for ``alpha_research.models.research`` with per-case report.

Writes ``tests/reports/test_model_research.md``.
"""

from __future__ import annotations

import pytest

from alpha_research.models.research import (
    Evaluation,
    EvaluationStatus,
    ExtractionQuality,
    Paper,
    PaperCandidate,
    PaperStatus,
    RubricScore,
    SearchQuery,
    SearchState,
    SearchStatus,
    SignificanceAssessment,
    TaskChain,
)


def test_task_chain_completeness(report) -> None:
    tc = TaskChain(
        task="Pick deformable objects",
        problem="Unknown dynamics",
        challenge="Contact discontinuities",
        approach="Tactile servoing",
        one_sentence="Tactile feedback enables sub-mm alignment",
        chain_complete=True,
        chain_coherent=True,
    )
    completeness = tc.compute_completeness()
    passed = completeness == 1.0 and tc.broken_links == []
    report.record(
        name="full task chain has completeness 1.0",
        purpose="TaskChain.compute_completeness counts populated fields / 5.",
        inputs=tc.model_dump(),
        expected={"completeness": 1.0, "broken_links": []},
        actual={"completeness": completeness, "broken_links": tc.broken_links},
        passed=passed,
        conclusion="A complete chain gates forward stage transitions (g2, g3, g4).",
    )
    assert passed


def test_task_chain_broken_links(report) -> None:
    tc = TaskChain(task="Pick", problem="Grasp")
    passed = tc.compute_completeness() == pytest.approx(0.4) and {"challenge", "approach", "one_sentence"}.issubset(
        set(tc.broken_links)
    )
    report.record(
        name="partial chain lists broken links",
        purpose="compute_completeness + broken_links identify the missing chain fields.",
        inputs={"task": "Pick", "problem": "Grasp"},
        expected={"completeness": 0.4, "broken_links_contains": ["challenge", "approach", "one_sentence"]},
        actual={"completeness": tc.compute_completeness(), "broken_links": tc.broken_links},
        passed=passed,
        conclusion="Broken links drive diagnostic skills that prompt the researcher to fill the gap.",
    )
    assert passed


def test_rubric_score_bounds_enforced(report) -> None:
    # Valid
    rs_ok = RubricScore(score=4, confidence="high", evidence=["Section 3"])
    invalid_below = False
    invalid_above = False
    try:
        RubricScore(score=0, confidence="high")
    except Exception:
        invalid_below = True
    try:
        RubricScore(score=6, confidence="high")
    except Exception:
        invalid_above = True

    passed = rs_ok.score == 4 and invalid_below and invalid_above
    report.record(
        name="rubric score must be in [1, 5]",
        purpose="Pydantic enforces Field(ge=1, le=5) on RubricScore.score.",
        inputs={"valid": 4, "invalid_low": 0, "invalid_high": 6},
        expected={"valid_accepted": True, "low_rejected": True, "high_rejected": True},
        actual={"valid_accepted": rs_ok.score == 4, "low_rejected": invalid_below, "high_rejected": invalid_above},
        passed=passed,
        conclusion="The 1–5 scale matches Appendix B of the research guideline.",
    )
    assert passed


def test_paper_primary_id_fallback(report) -> None:
    p1 = Paper(title="t", arxiv_id="2401.00001", s2_id="s2x", doi="10.0/x")
    p2 = Paper(title="t", s2_id="s2x")
    p3 = Paper(title="Just a Title")

    passed = p1.primary_id == "2401.00001" and p2.primary_id == "s2x" and p3.primary_id == "Just a Title"
    report.record(
        name="Paper.primary_id prefers arxiv_id > s2_id > doi > title",
        purpose="Verify the fallback chain for a paper identifier.",
        inputs=[
            {"arxiv_id": "2401.00001", "s2_id": "s2x", "doi": "10.0/x"},
            {"s2_id": "s2x"},
            {"title only": True},
        ],
        expected=["2401.00001", "s2x", "Just a Title"],
        actual=[p1.primary_id, p2.primary_id, p3.primary_id],
        passed=passed,
        conclusion="A paper always has SOME primary identifier so JSONL records can dedupe.",
    )
    assert passed


def test_significance_assessment_defaults(report) -> None:
    sa = SignificanceAssessment()
    passed = (
        sa.hamming_score == 3
        and sa.durability_risk == "medium"
        and sa.compounding_value == "medium"
        and sa.motivation_type == "unclear"
    )
    report.record(
        name="SignificanceAssessment defaults are conservative",
        purpose="Defaults should start from 'unknown/medium' so the researcher is forced to commit values.",
        inputs={},
        expected={"hamming_score": 3, "durability_risk": "medium", "compounding_value": "medium", "motivation_type": "unclear"},
        actual=sa.model_dump(),
        passed=passed,
        conclusion="Mid-range defaults prevent the tool from pretending to have assessed significance.",
    )
    assert passed


def test_evaluation_json_roundtrip(report) -> None:
    ev = Evaluation(
        paper_id="arxiv:2401.12345",
        task_chain=TaskChain(task="Grasp deformable objects"),
        has_formal_problem_def=True,
        formal_framework="POMDP",
        rubric_scores={"B.1": RubricScore(score=4, confidence="medium")},
    )
    data = ev.model_dump(mode="json")
    ev2 = Evaluation.model_validate(data)
    passed = (
        ev2.paper_id == ev.paper_id
        and ev2.formal_framework == "POMDP"
        and ev2.rubric_scores["B.1"].score == 4
    )
    report.record(
        name="Evaluation serializes through JSON without data loss",
        purpose="Pydantic model_dump/model_validate round-trip for nested rubric scores and task chain.",
        inputs=data,
        expected={"paper_id": ev.paper_id, "formal_framework": "POMDP", "B.1.score": 4},
        actual={"paper_id": ev2.paper_id, "formal_framework": ev2.formal_framework, "B.1.score": ev2.rubric_scores["B.1"].score},
        passed=passed,
        conclusion="Round-trip integrity is required because evaluations are persisted to evaluation.jsonl.",
    )
    assert passed


def test_search_state_and_status(report) -> None:
    ss = SearchState(
        papers_found={"p1": PaperCandidate(title="Test Paper")},
        status=SearchStatus.CONVERGED,
    )
    passed = ss.status == SearchStatus.CONVERGED and "p1" in ss.papers_found
    report.record(
        name="SearchState holds a keyed map of candidates and status",
        purpose="A SearchState with one candidate and CONVERGED status should instantiate without error.",
        inputs={"papers_found": {"p1": {"title": "Test Paper"}}, "status": "converged"},
        expected={"status": "converged", "candidates": ["p1"]},
        actual={"status": ss.status.value, "candidates": list(ss.papers_found.keys())},
        passed=passed,
        conclusion="SearchState is the Pydantic shell for SM-1; its enum types are round-trippable.",
    )
    assert passed


def test_extraction_quality_invalid_level(report) -> None:
    detected = False
    try:
        ExtractionQuality(overall="excellent")  # not a Literal value
    except Exception:
        detected = True
    report.record(
        name="ExtractionQuality.overall rejects values outside the Literal",
        purpose="Pydantic Literal type enforces high/medium/low/abstract_only.",
        inputs={"overall": "excellent"},
        expected={"raises": True},
        actual={"raises": detected},
        passed=detected,
        conclusion="Strict Literal typing keeps downstream UI rendering deterministic.",
    )
    assert detected


def test_paper_status_enum_values(report) -> None:
    values = {p.value for p in PaperStatus}
    expected = {"discovered", "fetched", "extracted", "validated", "enriched", "stored"}
    passed = values == expected
    report.record(
        name="PaperStatus enum matches SM-2 pipeline",
        purpose="Regression guard: the PaperStatus enum must match the six stages in SM-2.",
        inputs={},
        expected=sorted(expected),
        actual=sorted(values),
        passed=passed,
        conclusion="Any drift in the enum would silently break JSONL records that filter by status.",
    )
    assert passed


def test_search_query_defaults(report) -> None:
    q = SearchQuery(query="grasping", source="arxiv")
    passed = q.max_results == 50 and q.categories == [] and q.executed_at is None
    report.record(
        name="SearchQuery defaults",
        purpose="Unspecified fields default to empty lists / None / max_results=50.",
        inputs={"query": "grasping", "source": "arxiv"},
        expected={"max_results": 50, "categories": [], "executed_at": None},
        actual={"max_results": q.max_results, "categories": q.categories, "executed_at": q.executed_at},
        passed=passed,
        conclusion="Reasonable defaults let callers construct searches with only query + source.",
    )
    assert passed


def test_evaluation_status_default(report) -> None:
    ev = Evaluation(paper_id="p")
    passed = ev.status == EvaluationStatus.SKIMMED and ev.novelty_vs_store == "unknown"
    report.record(
        name="Evaluation starts as SKIMMED and unknown novelty",
        purpose="New evaluations should initialise to the earliest state in SM-3.",
        inputs={"paper_id": "p"},
        expected={"status": "skimmed", "novelty_vs_store": "unknown"},
        actual={"status": ev.status.value, "novelty_vs_store": ev.novelty_vs_store},
        passed=passed,
        conclusion="Forced 'unknown' novelty means the researcher must explicitly declare it.",
    )
    assert passed
