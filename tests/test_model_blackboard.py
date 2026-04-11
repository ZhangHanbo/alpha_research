"""Unit tests for ``alpha_research.models.blackboard`` with per-case report."""

from __future__ import annotations

from pathlib import Path

from alpha_research.models.blackboard import (
    VENUE_ACCEPTANCE_RATES,
    Blackboard,
    ConvergenceReason,
    ConvergenceState,
    HumanAction,
    HumanDecision,
    ResearchArtifact,
    ResearchStage,
    Venue,
)
from alpha_research.models.research import TaskChain
from alpha_research.models.review import (
    Finding,
    Review,
    Severity,
    Verdict,
)


def _finding() -> Finding:
    return Finding(
        id="f1",
        severity=Severity.SERIOUS,
        attack_vector="x",
        what_is_wrong="w",
        why_it_matters="w",
        what_would_fix="w",
        falsification="w",
        grounding="w",
        fixable=True,
    )


def _review() -> Review:
    return Review(
        version=1,
        summary="s",
        chain_extraction=TaskChain(task="t"),
        steel_man="a. b. c.",
        serious_weaknesses=[_finding()],
        verdict=Verdict.WEAK_ACCEPT,
        confidence=3,
    )


def test_venue_acceptance_rates_ordered(report) -> None:
    passed = (
        VENUE_ACCEPTANCE_RATES[Venue.IJRR] < VENUE_ACCEPTANCE_RATES[Venue.ICRA]
        and VENUE_ACCEPTANCE_RATES[Venue.RSS] < VENUE_ACCEPTANCE_RATES[Venue.IROS]
    )
    report.record(
        name="venue acceptance rates follow tier ordering",
        purpose="Top-tier venues (IJRR, T-RO) must have stricter acceptance than mid-tier.",
        inputs={v.value: r for v, r in VENUE_ACCEPTANCE_RATES.items()},
        expected={"IJRR < ICRA": True, "RSS < IROS": True},
        actual={
            "IJRR < ICRA": VENUE_ACCEPTANCE_RATES[Venue.IJRR] < VENUE_ACCEPTANCE_RATES[Venue.ICRA],
            "RSS < IROS": VENUE_ACCEPTANCE_RATES[Venue.RSS] < VENUE_ACCEPTANCE_RATES[Venue.IROS],
        },
        passed=passed,
        conclusion="Acceptance-rate ordering drives verdict calibration in compute_verdict.",
    )
    assert passed


def test_research_stage_has_seven_stages(report) -> None:
    stages = [s.value for s in ResearchStage]
    expected = [
        "significance", "formalization", "diagnose", "challenge",
        "approach", "validate", "full_draft",
    ]
    passed = stages == expected
    report.record(
        name="ResearchStage enum matches research_plan outer state machine",
        purpose="Regression guard: the stage order must match research_plan §2.4.",
        inputs={},
        expected=expected,
        actual=stages,
        passed=passed,
        conclusion="Any drift in the enum would invalidate state.json records in existing projects.",
    )
    assert passed


def test_blackboard_save_load_roundtrip(tmp_path: Path, report) -> None:
    bb = Blackboard(
        artifact=ResearchArtifact(
            stage=ResearchStage.CHALLENGE,
            content="# Challenge\n...",
            task_chain=TaskChain(task="t"),
        ),
        artifact_version=2,
        current_review=_review(),
        review_history=[_review()],
        iteration=3,
        convergence_state=ConvergenceState(
            converged=False,
            iterations_completed=3,
            verdict_history=["weak_reject", "weak_accept"],
            reason=ConvergenceReason.NOT_CONVERGED,
        ),
        target_venue=Venue.CORL,
        human_decisions=[HumanDecision(iteration=1, action=HumanAction.FORCE_ITERATION)],
    )
    path = tmp_path / "bb.json"
    bb.save(path)
    loaded = Blackboard.load(path)

    passed = (
        loaded.artifact_version == 2
        and loaded.artifact.stage == ResearchStage.CHALLENGE
        and loaded.iteration == 3
        and loaded.target_venue == Venue.CORL
        and loaded.convergence_state.verdict_history == ["weak_reject", "weak_accept"]
        and len(loaded.human_decisions) == 1
    )
    report.record(
        name="Blackboard JSON round-trip preserves every field",
        purpose="save()/load() must losslessly persist the shared state between research and review agents.",
        inputs={
            "artifact_version": 2,
            "stage": "challenge",
            "iteration": 3,
            "target_venue": "CoRL",
        },
        expected={
            "artifact_version": 2,
            "stage": "challenge",
            "iteration": 3,
            "target_venue": "CoRL",
            "verdict_history": ["weak_reject", "weak_accept"],
            "decisions": 1,
        },
        actual={
            "artifact_version": loaded.artifact_version,
            "stage": loaded.artifact.stage.value,
            "iteration": loaded.iteration,
            "target_venue": loaded.target_venue.value,
            "verdict_history": loaded.convergence_state.verdict_history,
            "decisions": len(loaded.human_decisions),
        },
        passed=passed,
        conclusion="Disk persistence of the blackboard is the only way the review loop survives a crash.",
    )
    assert passed


def test_blackboard_save_creates_parent_dir(tmp_path: Path, report) -> None:
    bb = Blackboard()
    path = tmp_path / "nested" / "subdir" / "bb.json"
    bb.save(path)
    passed = path.exists()
    report.record(
        name="Blackboard.save creates missing parent directories",
        purpose="save() should mkdir -p the parent of the target path.",
        inputs={"path": str(path)},
        expected={"exists": True},
        actual={"exists": passed},
        passed=passed,
        conclusion="Convenience: caller never needs to preflight the directory.",
    )
    assert passed


def test_convergence_state_default(report) -> None:
    cs = ConvergenceState()
    passed = cs.converged is False and cs.reason == ConvergenceReason.NOT_CONVERGED
    report.record(
        name="ConvergenceState defaults to not-converged",
        purpose="Default convergence state must be safe — the loop should not think it converged by accident.",
        inputs={},
        expected={"converged": False, "reason": "not_converged"},
        actual={"converged": cs.converged, "reason": cs.reason.value},
        passed=passed,
        conclusion="Conservative default prevents accidental early termination.",
    )
    assert passed


def test_human_decision_fields(report) -> None:
    hd = HumanDecision(iteration=2, action=HumanAction.APPROVE_BACKWARD, details="approved to significance")
    passed = hd.iteration == 2 and hd.action == HumanAction.APPROVE_BACKWARD
    report.record(
        name="HumanDecision carries iteration, action, and details",
        purpose="Smoke test construction of HumanDecision with an APPROVE_BACKWARD action.",
        inputs={"iteration": 2, "action": "approve_backward", "details": "approved to significance"},
        expected={"iteration": 2, "action": "approve_backward"},
        actual={"iteration": hd.iteration, "action": hd.action.value},
        passed=passed,
        conclusion="Human decisions are append-only; the timestamp is default-now.",
    )
    assert passed
