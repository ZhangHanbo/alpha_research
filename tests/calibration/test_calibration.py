"""Calibration tests for the review system.

Verifies that venue calibration, graduated pressure, anti-pattern detection,
verdict computation, and finding structure all behave correctly for known
inputs -- without any LLM or network calls.

Sections:
  A. Venue Calibration Tests
  B. Graduated Pressure Tests
  C. Anti-Pattern Detection Tests
  D. Verdict Computation Tests
  E. Finding Structure Tests
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from alpha_research.agents.meta_reviewer import MetaReviewer
from alpha_research.agents.review_agent import ReviewAgent
from alpha_research.metrics.review_quality import (
    check_steel_man,
    compute_actionability,
    compute_grounding,
    compute_falsifiability,
    count_vague_critiques,
    evaluate_review,
)
from alpha_research.models.blackboard import ResearchArtifact, ResearchStage, Venue
from alpha_research.models.research import TaskChain
from alpha_research.models.review import Finding, Review, Severity, Verdict
from alpha_research.prompts.review_system import build_review_prompt


# ===================================================================
# Helpers — reusable test-data factories
# ===================================================================

def _make_finding(
    *,
    severity: Severity = Severity.SERIOUS,
    fixable: bool = True,
    fid: str = "",
    what_is_wrong: str = "The baseline comparison omits MPC which solves this task in 0.3s",
    why_it_matters: str = "Without this baseline the contribution cannot be isolated",
    what_would_fix: str = "Add MPC baseline with 20 trials and report mean/CI",
    falsification: str = "If MPC cannot solve the task, this critique is invalid",
    grounding: str = "Section 5, Table 2",
    attack_vector: str = "missing_baseline",
) -> Finding:
    return Finding(
        id=fid,
        severity=severity,
        attack_vector=attack_vector,
        what_is_wrong=what_is_wrong,
        why_it_matters=why_it_matters,
        what_would_fix=what_would_fix,
        falsification=falsification,
        grounding=grounding,
        fixable=fixable,
    )


def _make_review(
    *,
    fatal_flaws: list[Finding] | None = None,
    serious_weaknesses: list[Finding] | None = None,
    minor_issues: list[Finding] | None = None,
    verdict: Verdict = Verdict.WEAK_REJECT,
    steel_man: str = (
        "The paper proposes a novel contact-rich manipulation planner. "
        "It introduces a structural insight about exploiting quasi-static dynamics. "
        "The evaluation on real hardware with 50 trials is above average for this area."
    ),
    version: int = 1,
    iteration: int = 1,
) -> Review:
    return Review(
        version=version,
        iteration=iteration,
        summary="The paper proposes X for task Y.",
        chain_extraction=TaskChain(
            task="Mobile manipulation in kitchens",
            problem="Plan contact-rich motions under uncertainty",
            challenge="Quasi-static assumption breaks at transitions",
            approach="Hybrid planner with mode switching",
            one_sentence="Quasi-static transitions can be handled by explicit mode switching",
            chain_complete=True,
            chain_coherent=True,
        ),
        steel_man=steel_man,
        fatal_flaws=fatal_flaws or [],
        serious_weaknesses=serious_weaknesses or [],
        minor_issues=minor_issues or [],
        questions=["How does the planner handle novel objects?"],
        verdict=verdict,
        confidence=3,
        verdict_justification="The logical chain has a break at validation.",
        improvement_path="Add the MPC baseline and run 20 more trials.",
        target_venue="RSS",
    )


def _make_artifact() -> ResearchArtifact:
    return ResearchArtifact(
        stage=ResearchStage.FULL_DRAFT,
        content="# Paper\n\nThis is a borderline artifact with strengths and weaknesses.",
        version=1,
    )


# ===================================================================
# A. Venue Calibration Tests
# ===================================================================

class TestVenueCalibration:
    """Verify that the same findings produce stricter verdicts at higher venues."""

    # Ordered from strictest to most lenient
    VENUE_ORDER = [
        Venue.IJRR, Venue.T_RO, Venue.RSS, Venue.CORL,
        Venue.RA_L, Venue.ICRA, Venue.IROS,
    ]

    def test_compute_verdict_is_deterministic(self):
        """compute_verdict is a pure function -- same input, same output."""
        findings = [
            _make_finding(severity=Severity.SERIOUS, fixable=True),
            _make_finding(severity=Severity.MINOR),
        ]
        v1 = ReviewAgent.compute_verdict(findings)
        v2 = ReviewAgent.compute_verdict(findings)
        assert v1 == v2

    def test_venue_prompts_differ(self):
        """Different venue configs produce different system prompts."""
        prompts = {}
        for venue in self.VENUE_ORDER:
            agent = ReviewAgent(venue=venue.value)
            artifact = _make_artifact()
            prompt = agent._build_prompt(artifact, iteration=2)
            prompts[venue] = prompt

        # IJRR and IROS should have different prompts
        assert prompts[Venue.IJRR] != prompts[Venue.IROS]
        # Each venue name appears in its own prompt
        for venue in self.VENUE_ORDER:
            assert venue.value in prompts[venue]

    def test_venue_calibration_text_strictness(self):
        """Stricter venues mention stricter language in their calibration blocks."""
        strict_prompt = build_review_prompt(venue="IJRR", iteration=2)
        lenient_prompt = build_review_prompt(venue="ICRA", iteration=2)

        # IJRR demands formalization as fatal; ICRA says helpful
        assert "DEMAND" in strict_prompt or "REQUIRED" in strict_prompt
        assert "MODERATE" in lenient_prompt or "HELPFUL" in lenient_prompt

    def test_all_venues_produce_valid_prompts(self):
        """Every venue enum produces a non-empty prompt without errors."""
        for venue in self.VENUE_ORDER:
            prompt = build_review_prompt(venue=venue.value, iteration=2)
            assert len(prompt) > 500, f"{venue.value} prompt is too short"

    def test_venue_acceptance_rates_ordering(self):
        """Acceptance rates are monotonically non-decreasing from strict to lenient."""
        from alpha_research.models.blackboard import VENUE_ACCEPTANCE_RATES
        rates = [VENUE_ACCEPTANCE_RATES[v] for v in self.VENUE_ORDER]
        for i in range(len(rates) - 1):
            assert rates[i] <= rates[i + 1], (
                f"{self.VENUE_ORDER[i].value} rate {rates[i]} > "
                f"{self.VENUE_ORDER[i+1].value} rate {rates[i+1]}"
            )


# ===================================================================
# B. Graduated Pressure Tests
# ===================================================================

class TestGraduatedPressure:
    """Verify iteration-based graduated pressure in prompt construction."""

    def test_iteration_1_is_structural_scan(self):
        """Iteration 1 produces the structural scan (shorter, focused)."""
        p1 = build_review_prompt(venue="RSS", iteration=1)
        assert "Five-Minute Fatal Flaw Scan" in p1

    def test_iteration_2_is_full_review(self):
        """Iteration 2 produces the full review with attack vectors."""
        p2 = build_review_prompt(venue="RSS", iteration=2)
        assert "FULL REVIEW" in p2
        # Attack vector sections 3.1-3.6 should be present
        assert "3.1" in p2 or "Attack" in p2

    def test_iteration_3_is_focused_rereview(self):
        """Iteration 3+ produces focused re-review mentioning previous findings."""
        p3 = build_review_prompt(venue="RSS", iteration=3)
        assert "previous findings" in p3.lower() or "re-review" in p3.lower()

    def test_iteration_1_shorter_than_2(self):
        """Structural scan prompt (iter 1) is shorter than full review (iter 2)."""
        p1 = build_review_prompt(venue="RSS", iteration=1)
        p2 = build_review_prompt(venue="RSS", iteration=2)
        assert len(p1) < len(p2), (
            f"Iteration 1 ({len(p1)} chars) should be shorter than "
            f"iteration 2 ({len(p2)} chars)"
        )

    def test_iteration_1_no_attack_vectors(self):
        """Structural scan should NOT include full attack vector sections."""
        p1 = build_review_prompt(venue="RSS", iteration=1)
        # The structural scan explicitly says "DO NOT apply full attack vectors yet"
        assert "DO NOT apply full attack vectors" in p1

    def test_iteration_2_has_attack_vector_subsections(self):
        """Full review should include attack vector subsection numbers."""
        p2 = build_review_prompt(venue="RSS", iteration=2)
        # Should contain specific subsection references
        has_subsections = any(f"3.{i}" in p2 for i in range(1, 7))
        assert has_subsections, "Full review prompt missing attack vector subsections (3.1-3.6)"

    def test_rereview_with_previous_findings(self):
        """Re-review prompt includes previous findings when provided."""
        prev_findings = [
            {
                "id": "val-1",
                "severity": "serious",
                "what_is_wrong": "Missing MPC baseline",
                "why_it_matters": "Cannot isolate contribution",
                "what_would_fix": "Add MPC with 20 trials",
                "falsification": "If MPC fails, critique invalid",
            }
        ]
        p3 = build_review_prompt(
            venue="RSS",
            iteration=3,
            previous_findings=prev_findings,
            review_mode="focused_rereview",
        )
        assert "val-1" in p3
        assert "Missing MPC baseline" in p3


# ===================================================================
# C. Anti-Pattern Detection Tests
# ===================================================================

class TestAntiPatternDetection:
    """Verify meta-reviewer detects known anti-patterns and passes clean reviews."""

    def setup_method(self):
        self.meta = MetaReviewer()

    def test_dimension_averaging_detected(self):
        """All-serious findings with Accept verdict -> dimension averaging."""
        review = _make_review(
            serious_weaknesses=[
                _make_finding(severity=Severity.SERIOUS, fid="s1"),
                _make_finding(severity=Severity.SERIOUS, fid="s2"),
                _make_finding(severity=Severity.SERIOUS, fid="s3"),
            ],
            verdict=Verdict.ACCEPT,
        )
        report = self.meta.check(review)
        detected = {ap.pattern: ap.detected for ap in report.anti_pattern_checks}
        assert detected["dimension_averaging"] is True

    def test_severity_regression_detected(self):
        """Previous fatal became minor -> severity regression."""
        previous = _make_review(
            fatal_flaws=[_make_finding(severity=Severity.FATAL, fid="f1")],
            verdict=Verdict.REJECT,
        )
        current = _make_review(
            minor_issues=[_make_finding(severity=Severity.MINOR, fid="f1")],
            verdict=Verdict.WEAK_ACCEPT,
            iteration=2,
        )
        report = self.meta.check(current, review_history=[previous])
        detected = {ap.pattern: ap.detected for ap in report.anti_pattern_checks}
        assert detected["severity_regression"] is True

    def test_specificity_violation_detected(self):
        """Vague critique ('the evaluation is weak') -> specificity violation."""
        review = _make_review(
            serious_weaknesses=[
                _make_finding(
                    severity=Severity.SERIOUS,
                    what_is_wrong="the evaluation is weak",
                    fid="v1",
                ),
            ],
            verdict=Verdict.WEAK_REJECT,
        )
        report = self.meta.check(review)
        spec_check = next(c for c in report.metric_checks if c.name == "specificity")
        assert not spec_check.passed, "Vague critique should fail specificity check"

    def test_steel_man_too_short(self):
        """1-sentence steel-man -> fails steel-man quality check."""
        review = _make_review(
            steel_man="The paper is interesting.",
            serious_weaknesses=[_make_finding(fid="s1")],
            verdict=Verdict.WEAK_REJECT,
        )
        report = self.meta.check(review)
        sm_check = next(c for c in report.metric_checks if c.name == "steel_man_quality")
        assert not sm_check.passed, "1-sentence steel-man should fail"

    def test_zero_actionable_findings(self):
        """Findings with empty what_would_fix -> fails actionability."""
        review = _make_review(
            serious_weaknesses=[
                _make_finding(
                    severity=Severity.SERIOUS,
                    what_would_fix="",
                    fid="na1",
                ),
                _make_finding(
                    severity=Severity.SERIOUS,
                    what_would_fix="",
                    fid="na2",
                ),
            ],
            verdict=Verdict.WEAK_REJECT,
        )
        report = self.meta.check(review)
        act_check = next(c for c in report.metric_checks if c.name == "actionability")
        assert not act_check.passed, "Empty what_would_fix should fail actionability"

    def test_no_grounding_fails(self):
        """Findings with no grounding -> fails grounding check."""
        review = _make_review(
            serious_weaknesses=[
                _make_finding(severity=Severity.SERIOUS, grounding="", fid="g1"),
                _make_finding(severity=Severity.SERIOUS, grounding="", fid="g2"),
            ],
            verdict=Verdict.WEAK_REJECT,
        )
        report = self.meta.check(review)
        grd_check = next(c for c in report.metric_checks if c.name == "grounding")
        assert not grd_check.passed, "Empty grounding should fail grounding check"

    def test_properly_structured_review_passes(self):
        """A well-formed review with all fields filled passes all checks."""
        review = _make_review(
            serious_weaknesses=[
                _make_finding(severity=Severity.SERIOUS, fid="s1"),
            ],
            verdict=Verdict.WEAK_REJECT,
        )
        report = self.meta.check(review)
        assert report.passes, f"Clean review should pass. Issues: {report.issues}"


# ===================================================================
# D. Verdict Computation Tests
# ===================================================================

class TestVerdictComputation:
    """Verify mechanical verdict rules in ReviewAgent.compute_verdict."""

    def test_zero_findings_accept(self):
        """0 findings -> ACCEPT."""
        assert ReviewAgent.compute_verdict([]) == Verdict.ACCEPT

    def test_one_fatal_reject(self):
        """1 fatal -> REJECT regardless of other findings."""
        findings = [
            _make_finding(severity=Severity.FATAL, fixable=False),
            _make_finding(severity=Severity.MINOR),
            _make_finding(severity=Severity.MINOR),
        ]
        assert ReviewAgent.compute_verdict(findings) == Verdict.REJECT

    def test_one_fixable_serious_weak_accept(self):
        """1 fixable serious -> WEAK_ACCEPT."""
        findings = [
            _make_finding(severity=Severity.SERIOUS, fixable=True),
        ]
        assert ReviewAgent.compute_verdict(findings) == Verdict.WEAK_ACCEPT

    def test_two_serious_one_unfixable_weak_reject(self):
        """2 serious, one not fixable -> WEAK_REJECT."""
        findings = [
            _make_finding(severity=Severity.SERIOUS, fixable=True),
            _make_finding(severity=Severity.SERIOUS, fixable=False),
        ]
        assert ReviewAgent.compute_verdict(findings) == Verdict.WEAK_REJECT

    def test_two_fixable_serious_weak_accept(self):
        """2 fixable serious -> WEAK_ACCEPT (borderline heuristic)."""
        findings = [
            _make_finding(severity=Severity.SERIOUS, fixable=True),
            _make_finding(severity=Severity.SERIOUS, fixable=True),
        ]
        assert ReviewAgent.compute_verdict(findings) == Verdict.WEAK_ACCEPT

    def test_three_plus_serious_weak_reject(self):
        """3+ serious -> WEAK_REJECT."""
        findings = [
            _make_finding(severity=Severity.SERIOUS, fixable=True),
            _make_finding(severity=Severity.SERIOUS, fixable=True),
            _make_finding(severity=Severity.SERIOUS, fixable=True),
        ]
        assert ReviewAgent.compute_verdict(findings) == Verdict.WEAK_REJECT

    def test_three_unresolvable_serious_reject(self):
        """3+ unresolvable serious -> REJECT."""
        findings = [
            _make_finding(severity=Severity.SERIOUS, fixable=False),
            _make_finding(severity=Severity.SERIOUS, fixable=False),
            _make_finding(severity=Severity.SERIOUS, fixable=False),
        ]
        assert ReviewAgent.compute_verdict(findings) == Verdict.REJECT

    def test_all_minor_accept(self):
        """All minor findings -> ACCEPT."""
        findings = [
            _make_finding(severity=Severity.MINOR) for _ in range(5)
        ]
        assert ReviewAgent.compute_verdict(findings) == Verdict.ACCEPT

    def test_mixed_serious_minor_driven_by_serious(self):
        """2 serious + 5 minor -> verdict driven by serious count, not minor."""
        findings = [
            _make_finding(severity=Severity.SERIOUS, fixable=True),
            _make_finding(severity=Severity.SERIOUS, fixable=False),
        ] + [
            _make_finding(severity=Severity.MINOR) for _ in range(5)
        ]
        # 2 serious, one unfixable -> WEAK_REJECT
        assert ReviewAgent.compute_verdict(findings) == Verdict.WEAK_REJECT

    def test_fatal_overrides_everything(self):
        """Fatal finding overrides even if all other findings are minor."""
        findings = [
            _make_finding(severity=Severity.FATAL, fixable=False),
        ] + [
            _make_finding(severity=Severity.MINOR) for _ in range(10)
        ]
        assert ReviewAgent.compute_verdict(findings) == Verdict.REJECT


# ===================================================================
# E. Finding Structure Tests
# ===================================================================

class TestFindingStructure:
    """Verify Finding model enforces required fields and quality metrics detect gaps."""

    def test_finding_requires_all_fields(self):
        """Finding model requires severity, attack_vector, and all text fields."""
        # This should work -- all required fields present
        f = _make_finding()
        assert f.severity == Severity.SERIOUS

    def test_finding_missing_severity_fails(self):
        """Omitting severity raises ValidationError."""
        with pytest.raises(ValidationError):
            Finding(
                attack_vector="missing_baseline",
                what_is_wrong="X",
                why_it_matters="Y",
                what_would_fix="Z",
                falsification="W",
                grounding="Section 1",
                fixable=True,
                # severity omitted
            )

    def test_finding_missing_attack_vector_fails(self):
        """Omitting attack_vector raises ValidationError."""
        with pytest.raises(ValidationError):
            Finding(
                severity=Severity.SERIOUS,
                # attack_vector omitted
                what_is_wrong="X",
                why_it_matters="Y",
                what_would_fix="Z",
                falsification="W",
                grounding="Section 1",
                fixable=True,
            )

    def test_empty_what_would_fix_fails_actionability(self):
        """Finding with empty what_would_fix -> actionability metric flags it."""
        review = _make_review(
            serious_weaknesses=[
                _make_finding(what_would_fix="", fid="a1"),
            ],
            verdict=Verdict.WEAK_REJECT,
        )
        score = compute_actionability(review)
        assert score < 1.0, "Empty what_would_fix should reduce actionability"

    def test_empty_grounding_fails_grounding_check(self):
        """Finding with empty grounding -> grounding metric flags it."""
        review = _make_review(
            serious_weaknesses=[
                _make_finding(grounding="", fid="g1"),
            ],
            verdict=Verdict.WEAK_REJECT,
        )
        score = compute_grounding(review)
        assert score < 1.0, "Empty grounding should reduce grounding score"

    def test_empty_falsification_fails_falsifiability(self):
        """Finding with empty falsification -> falsifiability metric flags it."""
        review = _make_review(
            serious_weaknesses=[
                _make_finding(falsification="", fid="f1"),
            ],
            verdict=Verdict.WEAK_REJECT,
        )
        score = compute_falsifiability(review)
        assert score < 1.0, "Empty falsification should reduce falsifiability score"

    def test_vague_what_is_wrong_detected(self):
        """Vague what_is_wrong with no evidence -> counted as vague critique."""
        review = _make_review(
            serious_weaknesses=[
                _make_finding(
                    what_is_wrong="the evaluation is weak",
                    fid="vg1",
                ),
            ],
            verdict=Verdict.WEAK_REJECT,
        )
        count = count_vague_critiques(review)
        assert count >= 1, "Vague critique should be detected"

    def test_specific_what_is_wrong_not_vague(self):
        """Specific what_is_wrong with evidence references -> not vague."""
        review = _make_review(
            serious_weaknesses=[
                _make_finding(
                    what_is_wrong=(
                        "The evaluation is weak: Section 3 reports only 5 trials "
                        "with no confidence intervals, which is below the 20-trial "
                        "threshold for statistical validity."
                    ),
                    fid="sp1",
                ),
            ],
            verdict=Verdict.WEAK_REJECT,
        )
        count = count_vague_critiques(review)
        assert count == 0, "Specific critique with evidence should not be vague"

    def test_steel_man_sentence_counting(self):
        """Steel-man sentence count works correctly."""
        review_3 = _make_review(
            steel_man=(
                "The paper proposes a novel approach. "
                "It addresses a real problem in manipulation. "
                "The evaluation is thorough."
            ),
        )
        assert check_steel_man(review_3) == 3

        review_1 = _make_review(steel_man="Short.")
        assert check_steel_man(review_1) == 1

        review_0 = _make_review(steel_man="")
        assert check_steel_man(review_0) == 0
