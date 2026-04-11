"""Unit tests for ``alpha_research.metrics.review_quality``.

Every case writes a row to ``tests/reports/test_review_quality.md``.
"""

from __future__ import annotations

from alpha_research.metrics.review_quality import (
    check_anti_patterns,
    check_steel_man,
    compute_actionability,
    compute_all_metrics,
    compute_falsifiability,
    compute_grounding,
    count_vague_critiques,
    evaluate_review,
)
from alpha_research.models.research import TaskChain
from alpha_research.models.review import (
    Finding,
    Review,
    Severity,
    Verdict,
)


def _finding(
    severity: Severity = Severity.SERIOUS,
    what_is_wrong: str = "Baseline is missing",
    what_would_fix: str = "Add the baseline.",
    grounding: str = "Table 2",
    falsification: str = "Beat baseline by 5pp",
    fid: str = "f1",
) -> Finding:
    return Finding(
        id=fid,
        severity=severity,
        attack_vector="baseline_strength",
        what_is_wrong=what_is_wrong,
        why_it_matters="matters",
        what_would_fix=what_would_fix,
        falsification=falsification,
        grounding=grounding,
        fixable=True,
    )


def _review(findings: list[Finding], steel: str = "One. Two. Three. Four.", verdict: Verdict = Verdict.WEAK_ACCEPT) -> Review:
    serious = [f for f in findings if f.severity == Severity.SERIOUS]
    fatal = [f for f in findings if f.severity == Severity.FATAL]
    minors = [f for f in findings if f.severity == Severity.MINOR]
    return Review(
        version=1,
        summary="s",
        chain_extraction=TaskChain(),
        steel_man=steel,
        fatal_flaws=fatal,
        serious_weaknesses=serious,
        minor_issues=minors,
        verdict=verdict,
        confidence=3,
    )


# ---------------------------------------------------------------------------
# Individual metric functions
# ---------------------------------------------------------------------------

def test_actionability_full(report) -> None:
    r = _review([_finding(), _finding(fid="f2")])
    act = compute_actionability(r)
    passed = act == 1.0
    report.record(
        name="all findings have what_would_fix",
        purpose="Actionability is fraction with a non-empty what_would_fix field.",
        inputs={"findings": 2, "what_would_fix_populated": 2},
        expected={"actionability": 1.0},
        actual={"actionability": act},
        passed=passed,
        conclusion="Every finding is paired with a fix → 100% actionability.",
    )
    assert passed


def test_grounding_half(report) -> None:
    r = _review([
        _finding(grounding="Section 3"),
        _finding(grounding="   ", fid="f2"),
    ])
    grd = compute_grounding(r)
    passed = grd == 0.5
    report.record(
        name="grounding counts only non-empty references",
        purpose="Grounding is fraction of serious/fatal findings with a non-empty grounding field.",
        inputs={"findings": 2, "grounded": 1},
        expected={"grounding": 0.5},
        actual={"grounding": grd},
        passed=passed,
        conclusion="Reviews with ungrounded critiques fail the grounding bar at 0.5.",
    )
    assert passed


def test_vague_critique_detection(report) -> None:
    r = _review([
        _finding(what_is_wrong="The baselines are weak"),  # vague — no evidence
        _finding(what_is_wrong="Baseline is weak — Section 3 shows 0.85 vs 0.83", fid="f2"),  # rescued by evidence
    ])
    vague = count_vague_critiques(r)
    passed = vague == 1
    report.record(
        name="vague critique is detected and specific critique is not",
        purpose="count_vague_critiques counts findings whose what_is_wrong is vague AND has no evidence markers.",
        inputs={
            "findings": [
                "The baselines are weak",
                "Baseline is weak — Section 3 shows 0.85 vs 0.83",
            ]
        },
        expected={"vague_count": 1},
        actual={"vague_count": vague},
        passed=passed,
        conclusion=(
            "Mentioning 'Section 3' and a concrete number rescues the second critique. "
            "The first has no evidence, so it is flagged as vague."
        ),
    )
    assert passed


def test_steel_man_sentences(report) -> None:
    count = check_steel_man(_review([], steel="First point. Second point. Third point."))
    passed = count == 3
    report.record(
        name="steel-man sentence counting",
        purpose="check_steel_man splits on '. ' and counts non-empty sentences.",
        inputs="First point. Second point. Third point.",
        expected=3,
        actual=count,
        passed=passed,
        conclusion="Three sentences satisfy the minimum steel-man requirement per review_plan §1.8.",
    )
    assert passed


def test_compute_all_metrics_bundle(report) -> None:
    r = _review([_finding()])
    m = compute_all_metrics(r)
    passed = (
        m.actionability == 1.0
        and m.grounding == 1.0
        and m.specificity_violations == 0
        and m.falsifiability == 1.0
        and m.steel_man_sentences >= 3
        and m.all_classified is True
    )
    report.record(
        name="compute_all_metrics bundles individual metrics",
        purpose="Single call returns a ReviewQualityMetrics with every field computed.",
        inputs={"findings": 1},
        expected="all metrics pass default thresholds",
        actual=m.model_dump(),
        passed=passed,
        conclusion="A clean single-finding review passes every quality metric.",
    )
    assert passed


# ---------------------------------------------------------------------------
# evaluate_review (end-to-end)
# ---------------------------------------------------------------------------

def test_evaluate_review_passes_clean_review(report) -> None:
    r = _review([_finding()])
    result = evaluate_review(r)
    passed = result.passes is True and result.recommendation == "pass"
    report.record(
        name="evaluate_review accepts a clean review",
        purpose="A review with all grounded, actionable, falsifiable findings passes the meta-review.",
        inputs={"findings": 1, "steel_man_sentences": 4, "vague_critiques": 0},
        expected={"passes": True, "recommendation": "pass"},
        actual={"passes": result.passes, "recommendation": result.recommendation, "issues": result.issues},
        passed=passed,
        conclusion="End-to-end meta-reviewer returns pass when every per-metric check succeeds.",
    )
    assert passed


def test_evaluate_review_flags_vague_critiques(report) -> None:
    r = _review([_finding(what_is_wrong="Paper is weak"), _finding(fid="f2", what_is_wrong="Experiments are insufficient")])
    result = evaluate_review(r)
    passed = result.passes is False and any("vague" in i for i in result.issues)
    report.record(
        name="evaluate_review flags vague critiques",
        purpose="Reviews with specificity violations should be marked revise_and_resubmit.",
        inputs=[
            "Paper is weak",
            "Experiments are insufficient",
        ],
        expected={"passes": False, "recommendation": "revise_and_resubmit"},
        actual={
            "passes": result.passes,
            "recommendation": result.recommendation,
            "issues": result.issues,
        },
        passed=passed,
        conclusion="The meta-reviewer catches reviews that rely on vague phrasing with no concrete evidence.",
    )
    assert passed


# ---------------------------------------------------------------------------
# Anti-pattern checks
# ---------------------------------------------------------------------------

def test_anti_pattern_dimension_averaging(report) -> None:
    r = _review(
        [
            _finding(severity=Severity.FATAL, fid="f1"),
            _finding(severity=Severity.SERIOUS, fid="f2"),
        ],
        verdict=Verdict.WEAK_ACCEPT,
    )
    checks = check_anti_patterns(r)
    dim_avg = next(c for c in checks if c.pattern == "dimension_averaging")
    passed = dim_avg.detected is True
    report.record(
        name="WEAK_ACCEPT with fatal + serious is dimension-averaging",
        purpose="A verdict that accepts a paper despite 2+ severe findings is flagged as dimension averaging.",
        inputs={"verdict": "weak_accept", "fatal": 1, "serious": 1},
        expected={"dimension_averaging_detected": True},
        actual={"dimension_averaging_detected": dim_avg.detected, "evidence": dim_avg.evidence},
        passed=passed,
        conclusion="Catches reviewers who wash out severe issues by averaging across dimensions.",
    )
    assert passed
