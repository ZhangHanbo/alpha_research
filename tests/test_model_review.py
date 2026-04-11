"""Unit tests for ``alpha_research.models.review`` with per-case report.

Writes ``tests/reports/test_model_review.md``.
"""

from __future__ import annotations

import pytest

from alpha_research.models.research import TaskChain
from alpha_research.models.review import (
    AntiPatternCheck,
    Finding,
    FindingDeferral,
    FindingDispute,
    FindingResponse,
    MetricCheck,
    Review,
    ReviewQualityMetrics,
    ReviewQualityReport,
    RevisionResponse,
    Severity,
    Verdict,
)


def _finding(fid: str = "f1") -> Finding:
    return Finding(
        id=fid,
        severity=Severity.SERIOUS,
        attack_vector="baseline_strength",
        what_is_wrong="Missing diffusion baseline",
        why_it_matters="Diffusion is SOTA",
        what_would_fix="Run Diffusion Policy",
        falsification="Beat diffusion by >5pp",
        grounding="Table 2",
        fixable=True,
    )


def test_finding_requires_all_fields(report) -> None:
    raised = False
    try:
        Finding(severity=Severity.MINOR, attack_vector="x")  # type: ignore[call-arg]
    except Exception:
        raised = True
    report.record(
        name="Finding rejects missing required fields",
        purpose="Pydantic enforces what_is_wrong/why_it_matters/what_would_fix/falsification/grounding/fixable.",
        inputs={"severity": "minor", "attack_vector": "x"},
        expected={"raises": True},
        actual={"raises": raised},
        passed=raised,
        conclusion="Every finding is guaranteed to be specific, actionable, and falsifiable.",
    )
    assert raised


def test_review_all_findings_property(report) -> None:
    r = Review(
        version=1,
        summary="s",
        chain_extraction=TaskChain(),
        steel_man="a. b. c.",
        fatal_flaws=[_finding("f1")],
        serious_weaknesses=[_finding("f2"), _finding("f3")],
        minor_issues=[_finding("f4")],
        verdict=Verdict.REJECT,
        confidence=3,
    )
    ids = [f.id for f in r.all_findings]
    counts = r.finding_count
    passed = ids == ["f1", "f2", "f3", "f4"] and counts == {"fatal": 1, "serious": 2, "minor": 1}
    report.record(
        name="Review.all_findings concatenates the three buckets in order",
        purpose="The all_findings property should flatten fatal → serious → minor, and finding_count should tally each bucket.",
        inputs={"fatal": 1, "serious": 2, "minor": 1},
        expected={"ids_order": ["f1", "f2", "f3", "f4"], "counts": {"fatal": 1, "serious": 2, "minor": 1}},
        actual={"ids_order": ids, "counts": counts},
        passed=passed,
        conclusion="Helper property keeps metric code DRY across convergence, quality, and verdict checks.",
    )
    assert passed


def test_review_confidence_range(report) -> None:
    caught_low = False
    caught_high = False
    try:
        Review(
            version=1, summary="s", chain_extraction=TaskChain(),
            steel_man="a. b. c.", verdict=Verdict.ACCEPT, confidence=0,
        )
    except Exception:
        caught_low = True
    try:
        Review(
            version=1, summary="s", chain_extraction=TaskChain(),
            steel_man="a. b. c.", verdict=Verdict.ACCEPT, confidence=6,
        )
    except Exception:
        caught_high = True
    passed = caught_low and caught_high
    report.record(
        name="Review.confidence must be in [1, 5]",
        purpose="NeurIPS confidence scale is 1–5; boundary values outside are rejected.",
        inputs={"low": 0, "high": 6},
        expected={"low_rejected": True, "high_rejected": True},
        actual={"low_rejected": caught_low, "high_rejected": caught_high},
        passed=passed,
        conclusion="Confidence is strictly bounded to prevent drift beyond the standard venue scale.",
    )
    assert passed


def test_revision_response_resolution_rate(report) -> None:
    rr = RevisionResponse(
        review_version=1,
        addressed=[FindingResponse(finding_id="f1", action_taken="added baseline", evidence="Table 2")],
        deferred=[FindingDeferral(finding_id="f2", reason="needs real robot", plan="v2")],
        disputed=[FindingDispute(finding_id="f3", argument="method differs", evidence="Sec 3")],
    )
    passed = rr.resolution_rate == pytest.approx(1 / 3)
    report.record(
        name="resolution_rate counts addressed / (addressed+deferred+disputed)",
        purpose="Deferred and disputed responses should NOT count toward the resolution rate.",
        inputs={"addressed": 1, "deferred": 1, "disputed": 1},
        expected={"resolution_rate": pytest.approx(1 / 3)},
        actual={"resolution_rate": rr.resolution_rate},
        passed=passed,
        conclusion="Only an accepted fix counts as 'resolved' — the metric can't be gamed by deferring work.",
    )
    assert passed


def test_review_quality_metrics_bounds(report) -> None:
    ok = ReviewQualityMetrics(
        actionability=0.85,
        grounding=0.92,
        specificity_violations=0,
        falsifiability=0.75,
        steel_man_sentences=4,
        all_classified=True,
    )
    raised = False
    try:
        ReviewQualityMetrics(
            actionability=1.5,
            grounding=0.9,
            specificity_violations=0,
            falsifiability=0.7,
            steel_man_sentences=3,
            all_classified=True,
        )
    except Exception:
        raised = True
    passed = ok.actionability == 0.85 and raised
    report.record(
        name="ReviewQualityMetrics enforces 0≤x≤1 bounds",
        purpose="actionability/grounding/falsifiability must be valid fractions.",
        inputs={"valid": 0.85, "invalid": 1.5},
        expected={"valid_accepted": True, "invalid_rejected": True},
        actual={"valid_accepted": ok.actionability == 0.85, "invalid_rejected": raised},
        passed=passed,
        conclusion="Strict bounds prevent miscomputed metrics from propagating into the report.",
    )
    assert passed


def test_review_quality_report_passing_and_failing(report) -> None:
    pass_report = ReviewQualityReport(
        passes=True,
        metric_checks=[MetricCheck(name="actionability", passed=True, actual=0.9, threshold=0.8)],
        anti_pattern_checks=[AntiPatternCheck(pattern="dimension_averaging", detected=False)],
    )
    fail_report = ReviewQualityReport(passes=False, issues=["Vague critique found."])
    passed = pass_report.passes and not fail_report.passes
    report.record(
        name="ReviewQualityReport holds pass/fail verdict and attached issues",
        purpose="Instantiate a passing and a failing report and verify their fields.",
        inputs=[pass_report.model_dump(), fail_report.model_dump()],
        expected={"pass_report.passes": True, "fail_report.passes": False},
        actual={"pass_report.passes": pass_report.passes, "fail_report.passes": fail_report.passes},
        passed=passed,
        conclusion="Holds the structured output of evaluate_review for programmatic meta-review.",
    )
    assert passed
