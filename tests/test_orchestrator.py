"""Tests for convergence, finding tracker, and orchestrator.

All agents are mocked — no LLM calls. Convergence logic is pure Python.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from alpha_research.agents.orchestrator import Orchestrator
from alpha_research.agents.meta_reviewer import MetaReviewer
from alpha_research.agents.research_agent import ResearchAgent
from alpha_research.agents.review_agent import ReviewAgent
from alpha_research.metrics.convergence import (
    check_convergence,
    compute_finding_resolution_rate,
    detect_stagnation,
)
from alpha_research.metrics.finding_tracker import FindingTracker
from alpha_research.models.blackboard import (
    Blackboard,
    ConvergenceReason,
    HumanAction,
    HumanDecision,
    ResearchArtifact,
    ResearchStage,
)
from alpha_research.models.research import TaskChain
from alpha_research.models.review import (
    Finding,
    FindingDeferral,
    FindingDispute,
    FindingResponse,
    Review,
    ReviewQualityReport,
    RevisionResponse,
    Severity,
    Verdict,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_finding(
    id: str = "f1",
    severity: Severity = Severity.MINOR,
    attack_vector: str = "av1",
    fixable: bool = True,
    maps_to_trigger: str | None = None,
) -> Finding:
    return Finding(
        id=id,
        severity=severity,
        attack_vector=attack_vector,
        what_is_wrong="something wrong",
        why_it_matters="matters",
        what_would_fix="fix it",
        falsification="would show otherwise",
        grounding="Section 3",
        fixable=fixable,
        maps_to_trigger=maps_to_trigger,
    )


def _make_review(
    verdict: Verdict = Verdict.ACCEPT,
    fatal_flaws: list[Finding] | None = None,
    serious_weaknesses: list[Finding] | None = None,
    minor_issues: list[Finding] | None = None,
    version: int = 1,
    iteration: int = 1,
    confidence: int = 4,
) -> Review:
    return Review(
        version=version,
        iteration=iteration,
        summary="Test summary.",
        chain_extraction=TaskChain(),
        steel_man="This paper makes a strong case. It argues well. The evidence supports it.",
        fatal_flaws=fatal_flaws or [],
        serious_weaknesses=serious_weaknesses or [],
        minor_issues=minor_issues or [],
        verdict=verdict,
        confidence=confidence,
        verdict_justification="Test justification",
    )


def _make_artifact(stage: ResearchStage = ResearchStage.SIGNIFICANCE, version: int = 1) -> ResearchArtifact:
    return ResearchArtifact(
        stage=stage,
        content="Test artifact content",
        version=version,
    )


def _make_blackboard(**kwargs) -> Blackboard:
    defaults = dict(max_iterations=5)
    defaults.update(kwargs)
    return Blackboard(**defaults)


# ===========================================================================
# Convergence tests
# ===========================================================================

class TestCheckConvergence:
    def test_quality_threshold_met(self):
        """0 fatal, ≤1 serious (fixable), ACCEPT verdict → converges."""
        review = _make_review(
            verdict=Verdict.ACCEPT,
            serious_weaknesses=[_make_finding(severity=Severity.SERIOUS, fixable=True)],
        )
        bb = _make_blackboard(
            current_review=review,
            review_history=[review],
            iteration=1,
        )
        state = check_convergence(bb)
        assert state.converged is True
        assert state.reason == ConvergenceReason.QUALITY_MET

    def test_quality_threshold_weak_accept(self):
        """WEAK_ACCEPT with 0 fatal, 0 serious → converges."""
        review = _make_review(verdict=Verdict.WEAK_ACCEPT)
        bb = _make_blackboard(
            current_review=review,
            review_history=[review],
            iteration=1,
        )
        state = check_convergence(bb)
        assert state.converged is True
        assert state.reason == ConvergenceReason.QUALITY_MET

    def test_iteration_limit(self):
        """iteration >= max_iterations → converges."""
        review = _make_review(
            verdict=Verdict.WEAK_REJECT,
            serious_weaknesses=[
                _make_finding(id="s1", severity=Severity.SERIOUS),
                _make_finding(id="s2", severity=Severity.SERIOUS),
            ],
        )
        bb = _make_blackboard(
            current_review=review,
            review_history=[review],
            iteration=5,
            max_iterations=5,
        )
        state = check_convergence(bb)
        assert state.converged is True
        assert state.reason == ConvergenceReason.ITERATION_LIMIT

    def test_stagnation(self):
        """2 identical consecutive reviews → stagnation."""
        review1 = _make_review(
            verdict=Verdict.WEAK_REJECT,
            serious_weaknesses=[_make_finding(id="s1", severity=Severity.SERIOUS, attack_vector="av_sig")],
            iteration=1,
        )
        review2 = _make_review(
            verdict=Verdict.WEAK_REJECT,
            serious_weaknesses=[_make_finding(id="s1", severity=Severity.SERIOUS, attack_vector="av_sig")],
            iteration=2,
        )
        bb = _make_blackboard(
            current_review=review2,
            review_history=[review1, review2],
            iteration=2,
        )
        state = check_convergence(bb)
        assert state.converged is True
        assert state.reason == ConvergenceReason.STAGNATED

    def test_not_converged(self):
        """Findings remain, not at limit, no stagnation → not converged."""
        review = _make_review(
            verdict=Verdict.WEAK_REJECT,
            serious_weaknesses=[
                _make_finding(id="s1", severity=Severity.SERIOUS),
                _make_finding(id="s2", severity=Severity.SERIOUS),
            ],
        )
        bb = _make_blackboard(
            current_review=review,
            review_history=[review],
            iteration=1,
        )
        state = check_convergence(bb)
        assert state.converged is False
        assert state.reason == ConvergenceReason.NOT_CONVERGED

    def test_human_approved(self):
        """Human APPROVE action → converges."""
        review = _make_review(verdict=Verdict.WEAK_REJECT)
        bb = _make_blackboard(
            current_review=review,
            review_history=[review],
            iteration=2,
            human_decisions=[
                HumanDecision(iteration=2, action=HumanAction.APPROVE),
            ],
        )
        state = check_convergence(bb)
        assert state.converged is True
        assert state.reason == ConvergenceReason.HUMAN_APPROVED


# ===========================================================================
# Stagnation detection
# ===========================================================================

class TestDetectStagnation:
    def test_same_verdict_same_findings(self):
        r1 = _make_review(
            verdict=Verdict.WEAK_REJECT,
            serious_weaknesses=[_make_finding(attack_vector="av_x")],
        )
        r2 = _make_review(
            verdict=Verdict.WEAK_REJECT,
            serious_weaknesses=[_make_finding(attack_vector="av_x")],
        )
        assert detect_stagnation([r1, r2]) is True

    def test_different_verdict(self):
        r1 = _make_review(verdict=Verdict.WEAK_REJECT)
        r2 = _make_review(verdict=Verdict.WEAK_ACCEPT)
        assert detect_stagnation([r1, r2]) is False

    def test_different_findings(self):
        r1 = _make_review(
            verdict=Verdict.WEAK_REJECT,
            serious_weaknesses=[_make_finding(attack_vector="av_a")],
        )
        r2 = _make_review(
            verdict=Verdict.WEAK_REJECT,
            serious_weaknesses=[_make_finding(attack_vector="av_b")],
        )
        assert detect_stagnation([r1, r2]) is False

    def test_insufficient_history(self):
        r1 = _make_review()
        assert detect_stagnation([r1]) is False
        assert detect_stagnation([]) is False


# ===========================================================================
# Finding resolution rate
# ===========================================================================

class TestFindingResolutionRate:
    def test_all_addressed(self):
        review = _make_review(
            minor_issues=[
                _make_finding(id="f1"),
                _make_finding(id="f2"),
            ],
        )
        response = RevisionResponse(
            review_version=1,
            addressed=[
                FindingResponse(finding_id="f1", action_taken="fixed", evidence="Section 3"),
                FindingResponse(finding_id="f2", action_taken="fixed", evidence="Section 4"),
            ],
        )
        assert compute_finding_resolution_rate(review, response) == 1.0

    def test_partial_addressed(self):
        review = _make_review(
            minor_issues=[
                _make_finding(id="f1"),
                _make_finding(id="f2"),
            ],
        )
        response = RevisionResponse(
            review_version=1,
            addressed=[
                FindingResponse(finding_id="f1", action_taken="fixed", evidence="Section 3"),
            ],
            deferred=[
                FindingDeferral(finding_id="f2", reason="future work", plan="v2"),
            ],
        )
        assert compute_finding_resolution_rate(review, response) == 0.5

    def test_no_findings(self):
        review = _make_review()
        response = RevisionResponse(review_version=1)
        assert compute_finding_resolution_rate(review, response) == 1.0


# ===========================================================================
# FindingTracker
# ===========================================================================

class TestFindingTracker:
    def test_track_across_iterations(self):
        tracker = FindingTracker()

        # Iteration 1: two findings
        review1 = _make_review(
            minor_issues=[_make_finding(id="f1"), _make_finding(id="f2")],
        )
        tracker.track(review1)

        # Iteration 2: f1 addressed, f2 persists, f3 new
        review2 = _make_review(
            minor_issues=[_make_finding(id="f2"), _make_finding(id="f3")],
        )
        response2 = RevisionResponse(
            review_version=1,
            addressed=[FindingResponse(finding_id="f1", action_taken="fixed", evidence="s3")],
        )
        tracker.track(review2, response2)

        summary = tracker.get_summary()
        assert summary["f1"] == "addressed"
        assert summary["f2"] == "persistent"
        assert summary["f3"] == "new"

    def test_deferred_and_disputed(self):
        tracker = FindingTracker()
        review = _make_review(
            minor_issues=[
                _make_finding(id="d1"),
                _make_finding(id="d2"),
            ],
        )
        response = RevisionResponse(
            review_version=1,
            deferred=[FindingDeferral(finding_id="d1", reason="later", plan="v2")],
            disputed=[FindingDispute(finding_id="d2", argument="wrong", evidence="proof")],
        )
        tracker.track(review, response)

        summary = tracker.get_summary()
        assert summary["d1"] == "deferred"
        assert summary["d2"] == "disputed"

    def test_severity_monotonicity(self):
        tracker = FindingTracker()

        prev = _make_review(
            serious_weaknesses=[_make_finding(id="f1", severity=Severity.SERIOUS)],
        )
        current = _make_review(
            minor_issues=[_make_finding(id="f1", severity=Severity.MINOR)],
        )
        tracker.track(prev)
        tracker.track(current)

        downgrades = tracker.check_monotonic_severity(current, prev)
        assert "f1" in downgrades

    def test_severity_monotonicity_addressed_ok(self):
        """Downgrade is OK if finding was addressed."""
        tracker = FindingTracker()

        prev = _make_review(
            serious_weaknesses=[_make_finding(id="f1", severity=Severity.SERIOUS)],
        )
        response = RevisionResponse(
            review_version=1,
            addressed=[FindingResponse(finding_id="f1", action_taken="fixed", evidence="s3")],
        )
        current = _make_review(
            minor_issues=[_make_finding(id="f1", severity=Severity.MINOR)],
        )
        tracker.track(prev, response)
        tracker.track(current)

        downgrades = tracker.check_monotonic_severity(current, prev)
        assert "f1" not in downgrades

    def test_resolution_history(self):
        tracker = FindingTracker()

        review1 = _make_review(
            minor_issues=[_make_finding(id="f1"), _make_finding(id="f2")],
        )
        response1 = RevisionResponse(
            review_version=1,
            addressed=[
                FindingResponse(finding_id="f1", action_taken="fixed", evidence="s3"),
            ],
        )
        tracker.track(review1, response1)

        review2 = _make_review(
            minor_issues=[_make_finding(id="f2")],
        )
        response2 = RevisionResponse(
            review_version=2,
            addressed=[
                FindingResponse(finding_id="f2", action_taken="fixed", evidence="s4"),
            ],
        )
        tracker.track(review2, response2)

        history = tracker.get_resolution_history()
        assert len(history) == 2
        assert history[0] == 0.5  # 1 of 2 addressed
        assert history[1] == 1.0  # 1 of 1 addressed


# ===========================================================================
# Orchestrator unit tests
# ===========================================================================

class TestOrchestratorUnit:
    def _make_orchestrator(self, bb: Blackboard | None = None) -> Orchestrator:
        research_agent = MagicMock(spec=ResearchAgent)
        review_agent = MagicMock(spec=ReviewAgent)
        meta_reviewer = MagicMock(spec=MetaReviewer)
        bb = bb or _make_blackboard()
        return Orchestrator(research_agent, review_agent, meta_reviewer, bb)

    def test_needs_human_checkpoint_accept(self):
        """ACCEPT verdict triggers human checkpoint."""
        bb = _make_blackboard(
            current_review=_make_review(verdict=Verdict.ACCEPT),
            iteration=1,
        )
        orch = self._make_orchestrator(bb)
        assert orch.needs_human_checkpoint() is True

    def test_needs_human_checkpoint_near_limit(self):
        """iteration >= max_iterations - 1 triggers checkpoint."""
        bb = _make_blackboard(
            current_review=_make_review(verdict=Verdict.WEAK_REJECT),
            iteration=4,
            max_iterations=5,
        )
        orch = self._make_orchestrator(bb)
        assert orch.needs_human_checkpoint() is True

    def test_needs_human_checkpoint_low_confidence_significance(self):
        """Low confidence on significance finding triggers checkpoint."""
        review = _make_review(
            verdict=Verdict.WEAK_REJECT,
            serious_weaknesses=[
                _make_finding(attack_vector="significance_gap"),
            ],
            confidence=2,
        )
        bb = _make_blackboard(current_review=review, iteration=1)
        orch = self._make_orchestrator(bb)
        assert orch.needs_human_checkpoint() is True

    def test_needs_human_checkpoint_backward_significance(self):
        """Backward trigger to significance triggers checkpoint."""
        review = _make_review(
            verdict=Verdict.WEAK_REJECT,
            serious_weaknesses=[
                _make_finding(maps_to_trigger="t2-significance-gap"),
            ],
        )
        bb = _make_blackboard(current_review=review, iteration=1)
        orch = self._make_orchestrator(bb)
        assert orch.needs_human_checkpoint() is True

    def test_needs_human_checkpoint_false(self):
        """Normal review mid-loop — no checkpoint needed."""
        review = _make_review(
            verdict=Verdict.WEAK_REJECT,
            serious_weaknesses=[_make_finding(attack_vector="validation")],
            confidence=4,
        )
        bb = _make_blackboard(current_review=review, iteration=1)
        orch = self._make_orchestrator(bb)
        assert orch.needs_human_checkpoint() is False

    def test_detect_backward_triggers(self):
        """Finds t2-t15 triggers from findings."""
        review = _make_review(
            serious_weaknesses=[
                _make_finding(id="f1", maps_to_trigger="t2-significance-gap"),
                _make_finding(id="f2", maps_to_trigger="t7-validation-mismatch"),
                _make_finding(id="f3"),  # no trigger
            ],
        )
        orch = self._make_orchestrator()
        triggers = orch.detect_backward_triggers(review)
        assert "t2-significance-gap" in triggers
        assert "t7-validation-mismatch" in triggers
        assert len(triggers) == 2

    def test_check_anti_collapse_severity_downgrade(self):
        """Catches severity downgrade across iterations."""
        prev_review = _make_review(
            version=1,
            serious_weaknesses=[_make_finding(id="f1", severity=Severity.SERIOUS)],
        )
        curr_review = _make_review(
            version=2,
            minor_issues=[_make_finding(id="f1", severity=Severity.MINOR)],
        )
        bb = _make_blackboard(
            current_review=curr_review,
            review_history=[prev_review, curr_review],
            iteration=2,
        )
        orch = self._make_orchestrator(bb)
        # Track the reviews in the finding tracker
        orch.finding_tracker.track(prev_review)
        orch.finding_tracker.track(curr_review)

        warnings = orch.check_anti_collapse(curr_review)
        assert any("downgrade" in w.lower() for w in warnings)

    def test_check_anti_collapse_low_resolution(self):
        """Catches low finding resolution rate."""
        prev_review = _make_review(
            version=1,
            minor_issues=[
                _make_finding(id="f1"),
                _make_finding(id="f2"),
                _make_finding(id="f3"),
                _make_finding(id="f4"),
            ],
        )
        response = RevisionResponse(
            review_version=1,
            addressed=[
                FindingResponse(finding_id="f1", action_taken="fixed", evidence="s3"),
            ],
            deferred=[
                FindingDeferral(finding_id="f2", reason="later", plan="v2"),
                FindingDeferral(finding_id="f3", reason="later", plan="v2"),
                FindingDeferral(finding_id="f4", reason="later", plan="v2"),
            ],
        )
        curr_review = _make_review(version=2)
        bb = _make_blackboard(
            current_review=curr_review,
            review_history=[prev_review, curr_review],
            revision_responses=[response],
            iteration=2,
        )
        orch = self._make_orchestrator(bb)
        warnings = orch.check_anti_collapse(curr_review)
        assert any("resolution rate" in w.lower() for w in warnings)


# ===========================================================================
# Orchestrator run_loop integration test (mocked agents)
# ===========================================================================

class TestOrchestratorRunLoop:
    @pytest.mark.asyncio
    async def test_run_loop_converges_on_accept(self):
        """Mock agents: converges when review verdict is ACCEPT with no serious findings."""
        research_agent = MagicMock(spec=ResearchAgent)
        review_agent = MagicMock(spec=ReviewAgent)
        meta_reviewer = MagicMock(spec=MetaReviewer)
        bb = _make_blackboard(max_iterations=5)

        # Research agent returns an artifact on generate
        artifact = _make_artifact()
        research_agent.generate.return_value = artifact

        # Review agent returns ACCEPT on first review
        good_review = _make_review(verdict=Verdict.ACCEPT, confidence=4)
        review_agent.review.return_value = good_review

        # Meta-reviewer passes
        quality_report = ReviewQualityReport(passes=True, recommendation="pass")
        meta_reviewer.check.return_value = quality_report

        orch = Orchestrator(research_agent, review_agent, meta_reviewer, bb)
        result = await orch.run_loop("test question")

        assert result.convergence_state.converged is True
        assert result.convergence_state.reason == ConvergenceReason.QUALITY_MET
        assert result.iteration == 1
        research_agent.generate.assert_called_once()
        review_agent.review.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_loop_with_revision(self):
        """Mock agents: revision loop that converges after 2 iterations."""
        research_agent = MagicMock(spec=ResearchAgent)
        review_agent = MagicMock(spec=ReviewAgent)
        meta_reviewer = MagicMock(spec=MetaReviewer)
        bb = _make_blackboard(max_iterations=5)

        artifact_v1 = _make_artifact(version=1)
        artifact_v2 = _make_artifact(version=2)
        revision_response = RevisionResponse(
            review_version=1,
            addressed=[FindingResponse(finding_id="s1", action_taken="fixed", evidence="s3")],
        )

        research_agent.generate.return_value = artifact_v1
        research_agent.revise.return_value = (artifact_v2, revision_response)

        # First review: serious finding → not converged
        review1 = _make_review(
            verdict=Verdict.WEAK_REJECT,
            version=1,
            iteration=1,
            serious_weaknesses=[
                _make_finding(id="s1", severity=Severity.SERIOUS, attack_vector="av_a"),
                _make_finding(id="s2", severity=Severity.SERIOUS, attack_vector="av_b"),
            ],
        )
        # Second review: all clear
        review2 = _make_review(verdict=Verdict.ACCEPT, version=2, iteration=2)

        review_agent.review.side_effect = [review1, review2]

        quality_report = ReviewQualityReport(passes=True, recommendation="pass")
        meta_reviewer.check.return_value = quality_report

        orch = Orchestrator(research_agent, review_agent, meta_reviewer, bb)
        result = await orch.run_loop("test question")

        assert result.convergence_state.converged is True
        assert result.iteration == 2
        research_agent.revise.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_loop_hits_iteration_limit(self):
        """Mock agents: hits iteration limit and converges."""
        research_agent = MagicMock(spec=ResearchAgent)
        review_agent = MagicMock(spec=ReviewAgent)
        meta_reviewer = MagicMock(spec=MetaReviewer)
        bb = _make_blackboard(max_iterations=3)

        artifact = _make_artifact()
        research_agent.generate.return_value = artifact
        revision_response = RevisionResponse(review_version=1)
        research_agent.revise.return_value = (artifact, revision_response)

        # Always return a weak_reject review with varying attack vectors
        def make_bad_review(artifact, iteration=1):
            return _make_review(
                verdict=Verdict.WEAK_REJECT,
                version=artifact.version,
                iteration=iteration,
                serious_weaknesses=[
                    _make_finding(id=f"s{iteration}", severity=Severity.SERIOUS, attack_vector=f"av_{iteration}"),
                    _make_finding(id=f"s{iteration}b", severity=Severity.SERIOUS, attack_vector=f"av_{iteration}b"),
                ],
            )

        review_agent.review.side_effect = [
            make_bad_review(artifact, 1),
            make_bad_review(artifact, 2),
            make_bad_review(artifact, 3),
        ]

        quality_report = ReviewQualityReport(passes=True, recommendation="pass")
        meta_reviewer.check.return_value = quality_report

        orch = Orchestrator(research_agent, review_agent, meta_reviewer, bb)
        result = await orch.run_loop("test question")

        assert result.convergence_state.converged is True
        assert result.convergence_state.reason == ConvergenceReason.ITERATION_LIMIT
        assert result.iteration == 3

    @pytest.mark.asyncio
    async def test_run_loop_human_callback(self):
        """Human callback is called at checkpoints and can approve."""
        research_agent = MagicMock(spec=ResearchAgent)
        review_agent = MagicMock(spec=ReviewAgent)
        meta_reviewer = MagicMock(spec=MetaReviewer)
        bb = _make_blackboard(max_iterations=5)

        artifact = _make_artifact()
        research_agent.generate.return_value = artifact

        # ACCEPT triggers human checkpoint
        review = _make_review(verdict=Verdict.ACCEPT)
        review_agent.review.return_value = review

        quality_report = ReviewQualityReport(passes=True, recommendation="pass")
        meta_reviewer.check.return_value = quality_report

        # Human approves
        human_cb = MagicMock(return_value=HumanDecision(
            iteration=1, action=HumanAction.APPROVE,
        ))

        orch = Orchestrator(research_agent, review_agent, meta_reviewer, bb)
        result = await orch.run_loop("test question", human_callback=human_cb)

        human_cb.assert_called_once()
        # Human approved takes priority over quality_met in check order
        assert result.convergence_state.converged is True
        assert result.convergence_state.reason in (
            ConvergenceReason.HUMAN_APPROVED,
            ConvergenceReason.QUALITY_MET,
        )


# ===========================================================================
# Blackboard save/load during loop
# ===========================================================================

class TestBlackboardPersistence:
    def test_save_load_roundtrip(self):
        """Blackboard with review data survives save/load."""
        review = _make_review(
            verdict=Verdict.WEAK_ACCEPT,
            minor_issues=[_make_finding(id="f1")],
        )
        bb = _make_blackboard(
            artifact=_make_artifact(),
            current_review=review,
            review_history=[review],
            iteration=2,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bb.json"
            bb.save(path)
            loaded = Blackboard.load(path)

        assert loaded.iteration == 2
        assert loaded.current_review is not None
        assert loaded.current_review.verdict == Verdict.WEAK_ACCEPT
        assert len(loaded.review_history) == 1
        assert loaded.artifact is not None
        assert loaded.artifact.version == 1
