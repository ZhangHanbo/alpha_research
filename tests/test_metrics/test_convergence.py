"""Unit tests for ``alpha_research.metrics.convergence`` with per-case report.

Covers :func:`check_convergence`, :func:`detect_stagnation`, and
:func:`compute_finding_resolution_rate`. Every case records a row via
the ``report`` fixture so ``tests/reports/test_convergence.md`` documents
the examples, inputs, outputs, expected results, and conclusions.
"""

from __future__ import annotations

from alpha_research.metrics.convergence import (
    check_convergence,
    compute_finding_resolution_rate,
    detect_stagnation,
)
from alpha_research.models.blackboard import (
    Blackboard,
    ConvergenceReason,
    HumanAction,
    HumanDecision,
)
from alpha_research.models.research import TaskChain
from alpha_research.models.review import (
    Finding,
    FindingResponse,
    Review,
    RevisionResponse,
    Severity,
    Verdict,
)


# ---------------------------------------------------------------------------
# Small builders — keep the test bodies compact
# ---------------------------------------------------------------------------

def _finding(fid: str, severity: Severity, fixable: bool = True, vec: str = "baseline") -> Finding:
    return Finding(
        id=fid,
        severity=severity,
        attack_vector=vec,
        what_is_wrong="w",
        why_it_matters="w",
        what_would_fix="w",
        falsification="w",
        grounding="w",
        fixable=fixable,
    )


def _review(
    findings: list[Finding] | None = None,
    verdict: Verdict = Verdict.WEAK_ACCEPT,
    iteration: int = 1,
) -> Review:
    fatals = [f for f in (findings or []) if f.severity == Severity.FATAL]
    serious = [f for f in (findings or []) if f.severity == Severity.SERIOUS]
    minors = [f for f in (findings or []) if f.severity == Severity.MINOR]
    return Review(
        version=1,
        iteration=iteration,
        summary="s",
        chain_extraction=TaskChain(),
        steel_man="Sentence one. Sentence two. Sentence three.",
        fatal_flaws=fatals,
        serious_weaknesses=serious,
        minor_issues=minors,
        verdict=verdict,
        confidence=3,
    )


# ---------------------------------------------------------------------------
# check_convergence
# ---------------------------------------------------------------------------

def test_human_approved_trumps_everything(report) -> None:
    bb = Blackboard(
        max_iterations=5,
        iteration=1,
        human_decisions=[HumanDecision(iteration=1, action=HumanAction.APPROVE)],
    )
    bb.current_review = _review([_finding("f1", Severity.FATAL)])
    bb.review_history.append(bb.current_review)

    state = check_convergence(bb)

    passed = state.converged is True and state.reason == ConvergenceReason.HUMAN_APPROVED
    report.record(
        name="human approval wins over fatal findings",
        purpose="Verify that a HumanAction.APPROVE decision flips converged=True regardless of review quality.",
        inputs={"human_action": "APPROVE", "fatal_findings": 1},
        expected={"converged": True, "reason": "human_approved"},
        actual={"converged": state.converged, "reason": state.reason.value},
        passed=passed,
        conclusion=(
            "Human approval is priority 1 in check_convergence — research loops "
            "stop immediately when the researcher signs off."
        ),
    )
    assert passed


def test_quality_threshold_met(report) -> None:
    bb = Blackboard(max_iterations=5, iteration=2)
    bb.current_review = _review([_finding("f1", Severity.SERIOUS, fixable=True)], verdict=Verdict.WEAK_ACCEPT)
    bb.review_history.append(bb.current_review)

    state = check_convergence(bb)

    passed = state.converged is True and state.reason == ConvergenceReason.QUALITY_MET
    report.record(
        name="quality threshold met converges",
        purpose="0 fatal, 1 serious (fixable), verdict WEAK_ACCEPT should satisfy the quality gate.",
        inputs={"fatal": 0, "serious_fixable": 1, "verdict": "weak_accept"},
        expected={"converged": True, "reason": "quality_met"},
        actual={"converged": state.converged, "reason": state.reason.value},
        passed=passed,
        conclusion="Quality convergence fires when the review meets the review_plan §2.5 quality thresholds.",
    )
    assert passed


def test_iteration_limit(report) -> None:
    bb = Blackboard(max_iterations=3, iteration=3)
    bb.current_review = _review([_finding("f1", Severity.SERIOUS, fixable=False)], verdict=Verdict.WEAK_REJECT)
    bb.review_history.append(bb.current_review)

    state = check_convergence(bb)

    passed = state.converged is True and state.reason == ConvergenceReason.ITERATION_LIMIT
    report.record(
        name="iteration limit terminates loop",
        purpose="iteration == max_iterations with an unconverged review triggers ITERATION_LIMIT.",
        inputs={"iteration": 3, "max_iterations": 3, "verdict": "weak_reject"},
        expected={"converged": True, "reason": "iteration_limit"},
        actual={"converged": state.converged, "reason": state.reason.value},
        passed=passed,
        conclusion="Loops are bounded — research cannot iterate forever without progress.",
    )
    assert passed


def test_not_converged_mid_loop(report) -> None:
    bb = Blackboard(max_iterations=5, iteration=1)
    bb.current_review = _review(
        [_finding("f1", Severity.FATAL), _finding("f2", Severity.SERIOUS)],
        verdict=Verdict.REJECT,
    )
    bb.review_history.append(bb.current_review)

    state = check_convergence(bb)

    passed = state.converged is False and state.reason == ConvergenceReason.NOT_CONVERGED
    report.record(
        name="ongoing loop reports not_converged",
        purpose="A reject-verdict review mid-loop should not converge.",
        inputs={"iteration": 1, "max_iterations": 5, "verdict": "reject", "fatal": 1},
        expected={"converged": False, "reason": "not_converged"},
        actual={"converged": state.converged, "reason": state.reason.value},
        passed=passed,
        conclusion="The loop continues as long as none of the four convergence conditions fire.",
    )
    assert passed


# ---------------------------------------------------------------------------
# detect_stagnation
# ---------------------------------------------------------------------------

def test_stagnation_detected_on_identical_verdicts(report) -> None:
    rv1 = _review([_finding("f1", Severity.SERIOUS, vec="baseline_strength")], verdict=Verdict.WEAK_REJECT)
    rv2 = _review([_finding("f1", Severity.SERIOUS, vec="baseline_strength")], verdict=Verdict.WEAK_REJECT, iteration=2)

    stagnated = detect_stagnation([rv1, rv2])

    passed = stagnated is True
    report.record(
        name="two identical reviews detect stagnation",
        purpose="Same verdict + same attack vectors across 2 reviews = stagnation.",
        inputs={
            "review_1": {"verdict": "weak_reject", "vectors": ["baseline_strength"]},
            "review_2": {"verdict": "weak_reject", "vectors": ["baseline_strength"]},
        },
        expected={"stagnated": True},
        actual={"stagnated": stagnated},
        passed=passed,
        conclusion=(
            "Stagnation guards against the loop wasting iterations on the same finding. "
            "When the reviewer says the same thing twice, the loop must escape."
        ),
    )
    assert passed


def test_no_stagnation_when_findings_differ(report) -> None:
    rv1 = _review([_finding("f1", Severity.SERIOUS, vec="baseline_strength")], verdict=Verdict.WEAK_REJECT)
    rv2 = _review([_finding("f2", Severity.SERIOUS, vec="experimental_rigor")], verdict=Verdict.WEAK_REJECT, iteration=2)

    stagnated = detect_stagnation([rv1, rv2])

    passed = stagnated is False
    report.record(
        name="different findings do not stagnate",
        purpose="Same verdict but a different attack vector indicates genuine progress.",
        inputs={
            "review_1_vectors": ["baseline_strength"],
            "review_2_vectors": ["experimental_rigor"],
        },
        expected={"stagnated": False},
        actual={"stagnated": stagnated},
        passed=passed,
        conclusion="Stagnation is only flagged when BOTH verdict AND attack vectors repeat.",
    )
    assert passed


def test_stagnation_needs_two_reviews(report) -> None:
    stagnated = detect_stagnation([_review([], verdict=Verdict.ACCEPT)])
    passed = stagnated is False
    report.record(
        name="one review is not enough to stagnate",
        purpose="detect_stagnation returns False when fewer than 2 reviews exist.",
        inputs={"review_history_length": 1},
        expected={"stagnated": False},
        actual={"stagnated": stagnated},
        passed=passed,
        conclusion="Single-sample history can't support a stagnation signal.",
    )
    assert passed


# ---------------------------------------------------------------------------
# compute_finding_resolution_rate
# ---------------------------------------------------------------------------

def test_resolution_rate_all_addressed(report) -> None:
    review = _review([
        _finding("f1", Severity.SERIOUS),
        _finding("f2", Severity.SERIOUS),
    ])
    response = RevisionResponse(
        review_version=1,
        addressed=[
            FindingResponse(finding_id="f1", action_taken="added baseline", evidence="Table 2"),
            FindingResponse(finding_id="f2", action_taken="added trials", evidence="Sec 5"),
        ],
    )

    rate = compute_finding_resolution_rate(review, response)

    passed = rate == 1.0
    report.record(
        name="all findings addressed gives rate 1.0",
        purpose="compute_finding_resolution_rate returns addressed/total.",
        inputs={"findings": 2, "addressed_ids": ["f1", "f2"]},
        expected={"rate": 1.0},
        actual={"rate": rate},
        passed=passed,
        conclusion="A revision that addresses every finding has full resolution.",
    )
    assert passed


def test_resolution_rate_no_findings_returns_one(report) -> None:
    review = _review([])
    response = RevisionResponse(review_version=1)
    rate = compute_finding_resolution_rate(review, response)
    passed = rate == 1.0
    report.record(
        name="empty review yields rate 1.0",
        purpose="An empty set of findings is vacuously fully resolved.",
        inputs={"findings": 0},
        expected={"rate": 1.0},
        actual={"rate": rate},
        passed=passed,
        conclusion="Avoids a divide-by-zero and matches the convention used by FindingTracker.",
    )
    assert passed
