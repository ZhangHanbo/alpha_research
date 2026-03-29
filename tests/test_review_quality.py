"""Tests for review quality metrics and MetaReviewer.

Covers:
  - compute_actionability
  - compute_grounding
  - compute_falsifiability
  - count_vague_critiques
  - check_steel_man
  - check_anti_patterns (dimension averaging, severity regression, declining specificity)
  - evaluate_review (good, vague, low actionability, short steel-man)
  - MetaReviewer.check integration
"""

from __future__ import annotations

import pytest

from alpha_research.agents.meta_reviewer import MetaReviewer
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
    ReviewQualityReport,
    Severity,
    Verdict,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_finding(
    severity: Severity = Severity.SERIOUS,
    what_is_wrong: str = "The evaluation uses only 5 trials (Table 2)",
    what_would_fix: str = "Run at least 30 trials with variance reporting",
    grounding: str = "Section 4.2, Table 2",
    falsification: str = "If 30 trials show same mean, critique is invalid",
    finding_id: str = "",
) -> Finding:
    return Finding(
        id=finding_id,
        severity=severity,
        attack_vector="experimental_validity",
        what_is_wrong=what_is_wrong,
        why_it_matters="Conclusions may not be statistically reliable",
        what_would_fix=what_would_fix,
        falsification=falsification,
        grounding=grounding,
        fixable=True,
    )


def _make_chain() -> TaskChain:
    return TaskChain(
        task="Mobile manipulation",
        problem="Grasping in clutter",
        challenge="Partial observability",
        approach="Learned policy with tactile",
        one_sentence="We show tactile improves grasping under occlusion.",
        chain_complete=True,
        chain_coherent=True,
    )


def _make_review(
    findings: list[Finding] | None = None,
    verdict: Verdict = Verdict.WEAK_REJECT,
    steel_man: str = (
        "The paper identifies a real gap in tactile grasping under occlusion. "
        "The proposed approach is grounded in a principled formulation. "
        "The real-robot experiments are more extensive than most prior work. "
        "The ablation isolates the tactile contribution convincingly."
    ),
) -> Review:
    if findings is None:
        findings = [_make_finding()]

    fatal = [f for f in findings if f.severity == Severity.FATAL]
    serious = [f for f in findings if f.severity == Severity.SERIOUS]
    minor = [f for f in findings if f.severity == Severity.MINOR]

    return Review(
        version=1,
        summary="The paper proposes a tactile grasping policy for cluttered scenes.",
        chain_extraction=_make_chain(),
        steel_man=steel_man,
        fatal_flaws=fatal,
        serious_weaknesses=serious,
        minor_issues=minor,
        verdict=verdict,
        confidence=3,
    )


# ===================================================================
# compute_actionability
# ===================================================================

class TestComputeActionability:
    def test_all_actionable(self):
        findings = [_make_finding(what_would_fix="Do X"), _make_finding(what_would_fix="Do Y")]
        review = _make_review(findings=findings)
        assert compute_actionability(review) == 1.0

    def test_half_actionable(self):
        findings = [
            _make_finding(what_would_fix="Do X"),
            _make_finding(what_would_fix=""),
        ]
        review = _make_review(findings=findings)
        assert compute_actionability(review) == 0.5

    def test_none_actionable(self):
        findings = [_make_finding(what_would_fix=""), _make_finding(what_would_fix="")]
        review = _make_review(findings=findings)
        assert compute_actionability(review) == 0.0

    def test_empty_review(self):
        review = _make_review(findings=[])
        assert compute_actionability(review) == 1.0


# ===================================================================
# compute_grounding
# ===================================================================

class TestComputeGrounding:
    def test_all_serious_grounded(self):
        findings = [
            _make_finding(severity=Severity.SERIOUS, grounding="Section 3"),
            _make_finding(severity=Severity.FATAL, grounding="Table 1"),
        ]
        review = _make_review(findings=findings)
        assert compute_grounding(review) == 1.0

    def test_minor_not_grounded_doesnt_count(self):
        """Minor findings without grounding should NOT reduce the score."""
        findings = [
            _make_finding(severity=Severity.SERIOUS, grounding="Section 3"),
            _make_finding(severity=Severity.MINOR, grounding=""),
        ]
        review = _make_review(findings=findings)
        assert compute_grounding(review) == 1.0

    def test_mixed_grounding(self):
        findings = [
            _make_finding(severity=Severity.SERIOUS, grounding="Section 3"),
            _make_finding(severity=Severity.SERIOUS, grounding=""),
        ]
        review = _make_review(findings=findings)
        assert compute_grounding(review) == 0.5

    def test_no_serious_findings(self):
        findings = [_make_finding(severity=Severity.MINOR, grounding="")]
        review = _make_review(findings=findings)
        assert compute_grounding(review) == 1.0


# ===================================================================
# compute_falsifiability
# ===================================================================

class TestComputeFalsifiability:
    def test_all_falsifiable(self):
        findings = [
            _make_finding(severity=Severity.SERIOUS, falsification="Show X"),
            _make_finding(severity=Severity.FATAL, falsification="Show Y"),
        ]
        review = _make_review(findings=findings)
        assert compute_falsifiability(review) == 1.0

    def test_minor_not_falsifiable_doesnt_count(self):
        findings = [
            _make_finding(severity=Severity.SERIOUS, falsification="Show X"),
            _make_finding(severity=Severity.MINOR, falsification=""),
        ]
        review = _make_review(findings=findings)
        assert compute_falsifiability(review) == 1.0

    def test_mixed(self):
        findings = [
            _make_finding(severity=Severity.SERIOUS, falsification="Show X"),
            _make_finding(severity=Severity.FATAL, falsification=""),
        ]
        review = _make_review(findings=findings)
        assert compute_falsifiability(review) == 0.5

    def test_no_serious_findings(self):
        findings = [_make_finding(severity=Severity.MINOR, falsification="")]
        review = _make_review(findings=findings)
        assert compute_falsifiability(review) == 1.0


# ===================================================================
# count_vague_critiques
# ===================================================================

class TestCountVagueCritiques:
    def test_vague_weak(self):
        f = _make_finding(what_is_wrong="the evaluation is weak")
        review = _make_review(findings=[f])
        assert count_vague_critiques(review) == 1

    def test_specific_with_evidence(self):
        f = _make_finding(
            what_is_wrong="the evaluation only has 5 trials (Table 2)"
        )
        review = _make_review(findings=[f])
        assert count_vague_critiques(review) == 0

    def test_vague_limited_novelty(self):
        f = _make_finding(what_is_wrong="limited novelty")
        review = _make_review(findings=[f])
        assert count_vague_critiques(review) == 1

    def test_limited_novelty_with_citation(self):
        f = _make_finding(
            what_is_wrong=(
                "limited novelty because method X already does this "
                "(Smith 2023, Section 3)"
            )
        )
        review = _make_review(findings=[f])
        assert count_vague_critiques(review) == 0

    def test_not_vague_without_keywords(self):
        f = _make_finding(
            what_is_wrong="The loss function ignores contact forces"
        )
        review = _make_review(findings=[f])
        assert count_vague_critiques(review) == 0

    def test_vague_insufficient(self):
        f = _make_finding(what_is_wrong="insufficient analysis")
        review = _make_review(findings=[f])
        assert count_vague_critiques(review) == 1

    def test_insufficient_with_specifics(self):
        f = _make_finding(
            what_is_wrong="insufficient analysis — only 3 ablation conditions in Table 4"
        )
        review = _make_review(findings=[f])
        assert count_vague_critiques(review) == 0


# ===================================================================
# check_steel_man
# ===================================================================

class TestCheckSteelMan:
    def test_four_sentences(self):
        review = _make_review()  # default has 4 sentences
        assert check_steel_man(review) == 4

    def test_one_sentence(self):
        review = _make_review(steel_man="This paper is good.")
        assert check_steel_man(review) == 1

    def test_empty(self):
        review = _make_review(steel_man="")
        assert check_steel_man(review) == 0

    def test_three_sentences(self):
        review = _make_review(
            steel_man="First point. Second point. Third point."
        )
        assert check_steel_man(review) == 3


# ===================================================================
# check_anti_patterns
# ===================================================================

class TestCheckAntiPatterns:
    def test_dimension_averaging_detected(self):
        """3 serious findings + Accept verdict should trigger."""
        findings = [
            _make_finding(severity=Severity.SERIOUS),
            _make_finding(severity=Severity.SERIOUS),
            _make_finding(severity=Severity.SERIOUS),
        ]
        review = _make_review(findings=findings, verdict=Verdict.ACCEPT)
        checks = check_anti_patterns(review)
        dim_avg = next(c for c in checks if c.pattern == "dimension_averaging")
        assert dim_avg.detected is True

    def test_dimension_averaging_not_detected(self):
        """0 serious + Accept should NOT trigger."""
        findings = [_make_finding(severity=Severity.MINOR)]
        review = _make_review(findings=findings, verdict=Verdict.ACCEPT)
        checks = check_anti_patterns(review)
        dim_avg = next(c for c in checks if c.pattern == "dimension_averaging")
        assert dim_avg.detected is False

    def test_severity_regression_detected(self):
        """Previous fatal finding downgraded to minor should trigger."""
        prev_finding = _make_finding(
            severity=Severity.FATAL, finding_id="f1"
        )
        prev_review = _make_review(findings=[prev_finding])

        cur_finding = _make_finding(
            severity=Severity.MINOR, finding_id="f1"
        )
        cur_review = _make_review(findings=[cur_finding])

        checks = check_anti_patterns(cur_review, review_history=[prev_review])
        regression = next(c for c in checks if c.pattern == "severity_regression")
        assert regression.detected is True

    def test_severity_regression_not_detected_no_history(self):
        review = _make_review()
        checks = check_anti_patterns(review, review_history=[])
        regression = next(c for c in checks if c.pattern == "severity_regression")
        assert regression.detected is False

    def test_declining_specificity_detected(self):
        """Grounding length decreasing across 3 reviews should trigger."""
        f1 = _make_finding(
            severity=Severity.SERIOUS,
            grounding="Section 4.2, Table 2, Figure 3 shows the issue clearly",
        )
        f2 = _make_finding(
            severity=Severity.SERIOUS,
            grounding="Section 4, Table 2",
        )
        f3 = _make_finding(
            severity=Severity.SERIOUS,
            grounding="Section 4",
        )

        r1 = _make_review(findings=[f1])
        r2 = _make_review(findings=[f2])
        r3 = _make_review(findings=[f3])

        checks = check_anti_patterns(r3, review_history=[r1, r2])
        declining = next(c for c in checks if c.pattern == "declining_specificity")
        assert declining.detected is True

    def test_declining_specificity_not_detected_no_history(self):
        review = _make_review()
        checks = check_anti_patterns(review)
        declining = next(c for c in checks if c.pattern == "declining_specificity")
        assert declining.detected is False


# ===================================================================
# evaluate_review
# ===================================================================

class TestEvaluateReview:
    def test_good_review_passes(self):
        """A well-formed review should pass all checks."""
        findings = [
            _make_finding(
                severity=Severity.SERIOUS,
                what_is_wrong="Only 5 trials in Table 2",
                what_would_fix="Run 30 trials",
                grounding="Section 4.2, Table 2",
                falsification="If 30 trials confirm, critique invalid",
            ),
        ]
        review = _make_review(findings=findings, verdict=Verdict.WEAK_REJECT)
        report = evaluate_review(review)
        assert report.passes is True
        assert report.recommendation == "pass"

    def test_vague_critiques_fail(self):
        findings = [
            _make_finding(
                what_is_wrong="the evaluation is weak",
            ),
        ]
        review = _make_review(findings=findings)
        report = evaluate_review(review)
        assert report.passes is False
        spec = next(c for c in report.metric_checks if c.name == "specificity")
        assert spec.passed is False

    def test_low_actionability_fails(self):
        findings = [
            _make_finding(what_would_fix=""),
            _make_finding(what_would_fix=""),
        ]
        review = _make_review(findings=findings)
        report = evaluate_review(review)
        assert report.passes is False
        act = next(c for c in report.metric_checks if c.name == "actionability")
        assert act.passed is False

    def test_short_steel_man_fails(self):
        review = _make_review(steel_man="Short.")
        report = evaluate_review(review)
        assert report.passes is False
        sm = next(c for c in report.metric_checks if c.name == "steel_man_quality")
        assert sm.passed is False

    def test_custom_thresholds(self):
        """Custom lower thresholds should make a borderline review pass."""
        findings = [
            _make_finding(what_would_fix=""),
            _make_finding(what_would_fix="Do X"),
        ]
        review = _make_review(findings=findings)
        # Default actionability threshold 0.80 would fail (0.5),
        # but lowering to 0.40 should pass.
        report = evaluate_review(review, thresholds={"actionability": 0.40})
        act = next(c for c in report.metric_checks if c.name == "actionability")
        assert act.passed is True


# ===================================================================
# MetaReviewer integration
# ===================================================================

class TestMetaReviewer:
    def test_check_returns_report(self):
        mr = MetaReviewer()
        review = _make_review()
        report = mr.check(review)
        assert isinstance(report, ReviewQualityReport)
        assert isinstance(report.passes, bool)
        assert len(report.metric_checks) == 5

    def test_check_with_custom_thresholds(self):
        mr = MetaReviewer(thresholds={"actionability": 0.0})
        findings = [_make_finding(what_would_fix="")]
        review = _make_review(findings=findings)
        report = mr.check(review)
        act = next(c for c in report.metric_checks if c.name == "actionability")
        assert act.passed is True

    def test_check_with_history(self):
        mr = MetaReviewer()
        prev = _make_review()
        current = _make_review()
        report = mr.check(current, review_history=[prev])
        assert isinstance(report, ReviewQualityReport)
        assert any(
            ap.pattern == "severity_regression"
            for ap in report.anti_pattern_checks
        )

    def test_build_prompt(self):
        mr = MetaReviewer()
        review = _make_review()
        prompt = mr._build_prompt(review)
        assert "area chair" in prompt
        assert "Review Under Evaluation" in prompt

    def test_build_prompt_with_history(self):
        mr = MetaReviewer()
        review = _make_review()
        prev = _make_review()
        prompt = mr._build_prompt(review, review_history=[prev])
        assert "Previous Review Iterations" in prompt
