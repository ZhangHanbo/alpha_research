"""Adversarial research-review loop pipeline.

Extracted from :mod:`alpha_research.agents.orchestrator`. The loop drives
the outer convergence between a research artifact and the
``adversarial-review`` skill:

1. Load (or construct) a :class:`ResearchArtifact` from the blackboard.
2. For each iteration up to ``max_iterations``:

   a. Invoke the ``adversarial-review`` skill via ``skill_invoker``.
   b. Parse the response into a :class:`Review`.
   c. Compute the mechanical verdict via
      :func:`alpha_research.metrics.verdict.compute_verdict`.
   d. Evaluate convergence via
      :func:`alpha_research.metrics.convergence.check_convergence`.
   e. If converged, return.
   f. Otherwise, for each finding, classify via
      :func:`alpha_research.pipelines.state_machine.backward_trigger_from_finding`.
   g. If any trigger points back to SIGNIFICANCE, pause for human judgment.
   h. Otherwise, revise via ``paper-evaluate`` in revision mode.

3. Apply an anti-collapse check via
   :class:`alpha_research.metrics.finding_tracker.FindingTracker`.
4. Persist the final review to ``reviews.jsonl``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from alpha_research.metrics.convergence import check_convergence
from alpha_research.metrics.finding_tracker import FindingTracker
from alpha_research.metrics.verdict import compute_verdict
from alpha_research.models.blackboard import (
    Blackboard,
    ResearchArtifact,
    ResearchStage,
    Venue,
)
from alpha_research.models.review import Review, Verdict
from alpha_research.pipelines.state_machine import (
    backward_trigger_from_finding,
)
from alpha_research.records.jsonl import append_record

SkillInvoker = Callable[[str, dict], Awaitable[Optional[dict]]]


@dataclass
class LoopResult:
    """Structured output from :func:`run_research_review_loop`."""

    iterations_run: int
    converged: bool
    submit_ready: bool
    final_verdict: str
    final_findings: list[dict] = field(default_factory=list)
    backward_triggers_fired: list[str] = field(default_factory=list)
    stagnation_detected: bool = False
    paused_for_human: bool = False
    anti_collapse_warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_blackboard(project_dir: Path) -> Blackboard:
    bb_path = project_dir / "blackboard.json"
    if bb_path.exists():
        try:
            return Blackboard.load(bb_path)
        except Exception:
            pass
    return Blackboard(
        artifact=ResearchArtifact(
            stage=ResearchStage.SIGNIFICANCE,
            content="",
        )
    )


def _parse_review_payload(payload: Any) -> Optional[Review]:
    """Normalise a skill's result into a :class:`Review` instance."""
    if payload is None:
        return None
    if isinstance(payload, Review):
        return payload
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return None
    if isinstance(payload, dict):
        try:
            return Review.model_validate(payload)
        except Exception:
            return None
    return None


def _resolve_venue(venue: str | Venue) -> Venue:
    if isinstance(venue, Venue):
        return venue
    try:
        return Venue(venue)
    except Exception:
        return Venue.RSS


def _is_submit_ready(review: Review, verdict: Verdict) -> bool:
    """A review is submit-ready iff no fatal, zero serious, and verdict is ACCEPT."""
    return (
        verdict == Verdict.ACCEPT
        and not review.fatal_flaws
        and not review.serious_weaknesses
    )


def _trigger_needs_human(trigger: str | None) -> bool:
    """Backward triggers to SIGNIFICANCE require a human sign-off.

    Per ``research_plan.md §2.4``, triggers t5, t9, t13 regress to the
    significance stage and cannot be resolved autonomously.
    """
    return trigger in {"t5", "t9", "t13"}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_research_review_loop(
    project_dir: Path,
    max_iterations: int = 5,
    venue: str | Venue = "RSS",
    skill_invoker: Optional[SkillInvoker] = None,
) -> LoopResult:
    """Run the adversarial research-review loop to convergence or limit."""
    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)

    if skill_invoker is None:
        from alpha_research.pipelines.literature_survey import _default_skill_invoker

        skill_invoker = _default_skill_invoker

    venue_enum = _resolve_venue(venue)
    blackboard = _load_blackboard(project_dir)
    blackboard.target_venue = venue_enum
    blackboard.max_iterations = max_iterations

    tracker = FindingTracker()
    result = LoopResult(
        iterations_run=0,
        converged=False,
        submit_ready=False,
        final_verdict=Verdict.REJECT.value,
    )

    last_review: Optional[Review] = None

    for iteration in range(1, max_iterations + 1):
        blackboard.iteration = iteration
        result.iterations_run = iteration

        # a. adversarial-review skill
        try:
            raw = await skill_invoker(
                "adversarial-review",
                {
                    "artifact": blackboard.artifact.model_dump(mode="json")
                    if blackboard.artifact
                    else {},
                    "iteration": iteration,
                    "venue": venue_enum.value,
                },
            )
        except Exception as exc:
            result.errors.append(f"adversarial-review failed: {exc}")
            break

        review = _parse_review_payload(raw)
        if review is None:
            result.errors.append(
                f"iteration {iteration}: could not parse review payload"
            )
            break

        # b/c. verdict
        verdict = compute_verdict(review.all_findings, venue=venue_enum)
        review.verdict = verdict

        blackboard.current_review = review
        blackboard.review_history.append(review)
        tracker.track(review, None)
        last_review = review
        result.final_verdict = verdict.value
        result.final_findings = [f.model_dump() for f in review.all_findings]

        # d. convergence
        convergence = check_convergence(blackboard)
        blackboard.convergence_state = convergence
        if convergence.converged:
            result.converged = True
            result.submit_ready = _is_submit_ready(review, verdict)
            result.stagnation_detected = convergence.reason.value == "stagnated"
            break

        # f. backward triggers
        triggers_this_round: list[str] = []
        for finding in review.all_findings:
            trig = backward_trigger_from_finding(finding)
            if trig:
                triggers_this_round.append(trig)
        result.backward_triggers_fired.extend(triggers_this_round)

        # g. human checkpoint?
        if any(_trigger_needs_human(t) for t in triggers_this_round):
            result.paused_for_human = True
            break

        # h. revise via paper-evaluate in revision mode
        try:
            revision_raw = await skill_invoker(
                "paper-evaluate",
                {
                    "mode": "revision",
                    "artifact": blackboard.artifact.model_dump(mode="json")
                    if blackboard.artifact
                    else {},
                    "findings": [f.model_dump() for f in review.all_findings],
                    "triggers": triggers_this_round,
                },
            )
        except Exception as exc:
            result.errors.append(f"paper-evaluate (revision) failed: {exc}")
            break

        if isinstance(revision_raw, dict):
            new_content = revision_raw.get("content") or revision_raw.get("artifact")
            if isinstance(new_content, str) and blackboard.artifact is not None:
                blackboard.artifact.content = new_content
                blackboard.artifact.version += 1
            elif isinstance(new_content, dict):
                try:
                    blackboard.artifact = ResearchArtifact.model_validate(new_content)
                except Exception:
                    pass

    # 3. Anti-collapse check
    if last_review is not None and len(blackboard.review_history) >= 2:
        downgrades = tracker.check_monotonic_severity(
            last_review, blackboard.review_history[-2]
        )
        if downgrades:
            result.anti_collapse_warnings.append(
                f"Severity downgraded without justification: {downgrades}"
            )

    # 4. Persist final review
    if last_review is not None:
        try:
            append_record(
                project_dir,
                "review",
                {
                    "iteration": result.iterations_run,
                    "verdict": result.final_verdict,
                    "findings": result.final_findings,
                    "converged": result.converged,
                    "submit_ready": result.submit_ready,
                    "backward_triggers": result.backward_triggers_fired,
                },
            )
        except Exception as exc:
            result.errors.append(f"append_record(review) failed: {exc}")

    # Persist blackboard for caller
    try:
        blackboard.save(project_dir / "blackboard.json")
    except Exception as exc:
        result.errors.append(f"blackboard save failed: {exc}")

    return result
