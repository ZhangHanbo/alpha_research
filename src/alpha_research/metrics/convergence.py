"""Convergence detection for the review loop.

Pure-Python logic — no LLM calls. Checks four conditions from
review_plan.md §2.5:
  1. Quality threshold met
  2. Human approved
  3. Iteration limit reached
  4. Stagnation (repeated identical reviews)

Source: review_plan.md §2.4-2.5
"""

from __future__ import annotations

from alpha_research.models.blackboard import (
    Blackboard,
    ConvergenceReason,
    ConvergenceState,
    HumanAction,
)
from alpha_research.models.review import (
    Review,
    RevisionResponse,
    Severity,
    Verdict,
)


def check_convergence(blackboard: Blackboard) -> ConvergenceState:
    """Evaluate whether the review loop should terminate.

    Checks four conditions in priority order:
      1. Human approved
      2. Quality threshold met (0 fatal, ≤1 serious all fixable, ACCEPT/WEAK_ACCEPT)
      3. Stagnation (2+ consecutive identical verdicts with same findings)
      4. Iteration limit reached

    Returns a :class:`ConvergenceState` with the reason.
    """
    # Build verdict history from review_history
    verdict_history = [r.verdict.value for r in blackboard.review_history]

    base = ConvergenceState(
        iterations_completed=blackboard.iteration,
        verdict_history=verdict_history,
    )

    # 1. Human approved
    for decision in blackboard.human_decisions:
        if decision.action == HumanAction.APPROVE:
            base.converged = True
            base.reason = ConvergenceReason.HUMAN_APPROVED
            return base

    # 2. Quality threshold met
    review = blackboard.current_review
    if review is not None:
        fatal_count = len(review.fatal_flaws)
        serious = review.serious_weaknesses
        serious_count = len(serious)
        all_serious_fixable = all(f.fixable for f in serious)
        verdict_ok = review.verdict in (Verdict.ACCEPT, Verdict.WEAK_ACCEPT)

        if (
            fatal_count == 0
            and serious_count <= 1
            and all_serious_fixable
            and verdict_ok
        ):
            base.converged = True
            base.reason = ConvergenceReason.QUALITY_MET
            return base

    # 3. Stagnation
    if detect_stagnation(blackboard.review_history):
        base.converged = True
        base.reason = ConvergenceReason.STAGNATED
        return base

    # 4. Iteration limit
    if blackboard.iteration >= blackboard.max_iterations:
        base.converged = True
        base.reason = ConvergenceReason.ITERATION_LIMIT
        return base

    # Not converged
    base.converged = False
    base.reason = ConvergenceReason.NOT_CONVERGED
    return base


def detect_stagnation(review_history: list[Review]) -> bool:
    """Return True if the last 2 reviews have the same verdict and findings.

    Compares verdict and the set of ``attack_vector`` values across all
    findings in the last two reviews.
    """
    if len(review_history) < 2:
        return False

    last = review_history[-1]
    prev = review_history[-2]

    # Same verdict?
    if last.verdict != prev.verdict:
        return False

    # Same set of attack vectors in findings?
    last_vectors = {f.attack_vector for f in last.all_findings}
    prev_vectors = {f.attack_vector for f in prev.all_findings}

    return last_vectors == prev_vectors


def compute_finding_resolution_rate(
    prev_review: Review,
    response: RevisionResponse,
) -> float:
    """Fraction of previous findings that were addressed (not deferred/disputed).

    Parameters
    ----------
    prev_review : Review
        The review whose findings are being responded to.
    response : RevisionResponse
        The research agent's response.

    Returns
    -------
    float
        0.0–1.0 resolution rate. Returns 1.0 if there were no findings.
    """
    total = len(prev_review.all_findings)
    if total == 0:
        return 1.0

    addressed_ids = {fr.finding_id for fr in response.addressed}
    addressed_count = sum(
        1 for f in prev_review.all_findings if f.id in addressed_ids
    )
    return addressed_count / total
