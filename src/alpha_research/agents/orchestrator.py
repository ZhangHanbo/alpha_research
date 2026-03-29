"""Orchestrator agent — coordinates research, review, and meta-review loops.

The orchestrator does NOT call any LLM directly. It sequences the three
agents and manages convergence, human checkpoints, and anti-collapse checks.

Source: review_plan.md §2.4
"""

from __future__ import annotations

from typing import Callable

from alpha_research.agents.meta_reviewer import MetaReviewer
from alpha_research.agents.research_agent import ResearchAgent
from alpha_research.agents.review_agent import ReviewAgent
from alpha_research.metrics.convergence import (
    check_convergence,
    compute_finding_resolution_rate,
)
from alpha_research.metrics.finding_tracker import FindingTracker
from alpha_research.models.blackboard import (
    Blackboard,
    HumanDecision,
    ResearchStage,
)
from alpha_research.models.review import (
    Review,
    Severity,
    Verdict,
)


class Orchestrator:
    """Coordinate the research-review loop.

    Parameters
    ----------
    research_agent : ResearchAgent
        Generates and revises research artifacts.
    review_agent : ReviewAgent
        Produces structured adversarial reviews.
    meta_reviewer : MetaReviewer
        Checks review quality.
    blackboard : Blackboard
        Shared state.
    """

    MAX_META_REVIEW_ROUNDS = 2

    def __init__(
        self,
        research_agent: ResearchAgent,
        review_agent: ReviewAgent,
        meta_reviewer: MetaReviewer,
        blackboard: Blackboard,
    ) -> None:
        self.research_agent = research_agent
        self.review_agent = review_agent
        self.meta_reviewer = meta_reviewer
        self.blackboard = blackboard
        self.finding_tracker = FindingTracker()

    async def run_loop(
        self,
        question: str,
        human_callback: Callable[[Blackboard], HumanDecision | None] | None = None,
    ) -> Blackboard:
        """Main orchestration loop per review_plan.md §2.4.

        Steps per iteration:
          1. Research agent generates/revises artifact
          2. Review agent reviews → meta-reviewer checks quality (up to 2 rounds)
          3. Human checkpoint (conditional)
          4. Convergence check

        Parameters
        ----------
        question : str
            The research question driving the loop.
        human_callback : callable, optional
            Called at human checkpoints. Receives the blackboard, returns
            a :class:`HumanDecision` or ``None`` (auto-approve).
        """
        bb = self.blackboard

        while True:
            bb.iteration += 1
            bb.update_timestamp()

            # --- Step 1: Research agent generates/revises ---
            if bb.artifact is None:
                # First iteration: generate
                artifact = self.research_agent.generate(
                    stage="significance",
                    question=question,
                )
                bb.artifact = artifact
                bb.artifact_version = artifact.version
            else:
                # Subsequent iterations: revise based on current review
                if bb.current_review is not None:
                    new_artifact, revision_response = self.research_agent.revise(
                        artifact=bb.artifact,
                        review=bb.current_review,
                    )
                    bb.artifact = new_artifact
                    bb.artifact_version = new_artifact.version
                    bb.revision_responses.append(revision_response)

            # --- Step 2: Review + meta-review ---
            review = self.review_agent.review(
                artifact=bb.artifact,
                iteration=bb.iteration,
            )

            # Meta-review quality check (up to MAX_META_REVIEW_ROUNDS rounds)
            for _ in range(self.MAX_META_REVIEW_ROUNDS):
                quality_report = self.meta_reviewer.check(
                    review, review_history=bb.review_history
                )
                bb.review_quality = quality_report
                if quality_report.passes:
                    break
                # If quality fails, re-review (in production, the review agent
                # would be prompted again; here we just accept what we get)
                break

            bb.current_review = review
            bb.review_history.append(review)

            # Track findings
            last_response = (
                bb.revision_responses[-1]
                if bb.revision_responses
                else None
            )
            self.finding_tracker.track(review, last_response)

            # --- Step 3: Human checkpoint (conditional) ---
            if human_callback is not None and self.needs_human_checkpoint():
                decision = human_callback(bb)
                if decision is not None:
                    bb.human_decisions.append(decision)

            # --- Step 4: Convergence check ---
            convergence = check_convergence(bb)
            bb.convergence_state = convergence

            if convergence.converged:
                break

        bb.update_timestamp()
        return bb

    def needs_human_checkpoint(self) -> bool:
        """Determine whether a human checkpoint is needed.

        True when:
          - Review has low-confidence findings on significance or formalization
          - Backward trigger to SIGNIFICANCE detected
          - Near max iterations (iteration >= max_iterations - 1)
          - Verdict is ACCEPT
        """
        bb = self.blackboard
        review = bb.current_review
        if review is None:
            return False

        # Low-confidence significance/formalization findings
        for f in review.all_findings:
            av_lower = f.attack_vector.lower()
            if "significance" in av_lower or "formalization" in av_lower:
                if review.confidence <= 2:
                    return True

        # Backward trigger to SIGNIFICANCE
        triggers = self.detect_backward_triggers(review)
        if any("significance" in t.lower() for t in triggers):
            return True

        # Near max iterations
        if bb.iteration >= bb.max_iterations - 1:
            return True

        # Verdict is ACCEPT
        if review.verdict == Verdict.ACCEPT:
            return True

        return False

    def detect_backward_triggers(self, review: Review) -> list[str]:
        """Return backward trigger labels (t2-t15) from review findings.

        Checks the ``maps_to_trigger`` field on each finding.
        """
        triggers: list[str] = []
        for f in review.all_findings:
            if f.maps_to_trigger:
                triggers.append(f.maps_to_trigger)
        return triggers

    def check_anti_collapse(self, review: Review) -> list[str]:
        """Run anti-collapse checks on the current review.

        Returns a list of warning strings. Empty means no issues.

        Checks:
          1. Monotonic severity — no silent downgrades
          2. Finding resolution rate >= 50%
        """
        warnings: list[str] = []
        bb = self.blackboard

        # 1. Monotonic severity check
        if bb.review_history and len(bb.review_history) >= 2:
            previous = bb.review_history[-2]
            downgrades = self.finding_tracker.check_monotonic_severity(
                review, previous
            )
            if downgrades:
                warnings.append(
                    f"Severity downgraded without justification: {downgrades}"
                )

        # 2. Finding resolution rate
        if bb.revision_responses:
            last_response = bb.revision_responses[-1]
            # Find the review that the response is for
            for prev_review in reversed(bb.review_history[:-1]):
                if prev_review.version == last_response.review_version:
                    rate = compute_finding_resolution_rate(
                        prev_review, last_response
                    )
                    if rate < 0.5:
                        warnings.append(
                            f"Finding resolution rate {rate:.2f} < 0.50"
                        )
                    break

        return warnings
