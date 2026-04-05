"""Pure state-machine logic for the research workflow.

Extracted from :mod:`alpha_research.agents.research_agent`. This module has
**no I/O, no LLM calls, and no side effects** — every function is a pure
mapping from inputs to outputs, which makes the state machine exhaustively
testable.

References:
  - ``guidelines/research_plan.md`` — the outer state machine (stages
    SIGNIFICANCE → FULL_DRAFT) with forward guards ``g1..g5`` and
    backward triggers ``t2..t15``.
  - ``guidelines/review_guideline.md`` §3.1-§3.4 — attack vectors that
    justify each backward trigger.
"""

from __future__ import annotations

from typing import Literal

from alpha_research.models.blackboard import ResearchArtifact, ResearchStage
from alpha_research.models.review import Finding

# ---------------------------------------------------------------------------
# Trigger type alias — one of the 13 backward triggers defined in
# research_plan.md §2.4.
# ---------------------------------------------------------------------------

BackwardTrigger = Literal[
    "t2", "t4", "t5", "t6", "t7", "t8", "t9", "t10",
    "t11", "t12", "t13", "t14", "t15",
]


# ---------------------------------------------------------------------------
# Transition tables
# ---------------------------------------------------------------------------

# Forward transitions: each stage has exactly one successor per the outer
# state machine in ``research_plan.md``. ``full_draft`` is terminal.
FORWARD_TRANSITIONS: dict[str, list[str]] = {
    "significance": ["formalization"],
    "formalization": ["diagnose"],
    "diagnose": ["challenge"],
    "challenge": ["approach"],
    "approach": ["validate"],
    "validate": ["full_draft"],
    "full_draft": [],
}


# Backward transitions: from a given stage, which earlier stages can we
# regress to and which trigger justifies the regression. Keys at the outer
# level are the *current* stage; values map trigger → target stage.
#
# Derived from research_plan.md §2.4 (the t2..t15 table):
#   t2  (formalize→significance)  : trivial special case of known problem
#   t4  (diagnose→formalize)      : failure doesn't map to math
#   t5  (approach→significance)   : problem turned out to be low-impact
#   t6  (challenge→diagnose)      : wrong challenge identified
#   t7  (challenge→formalize)     : wrong mathematical framework
#   t8  (approach→diagnose)       : approach exposes wrong failure analysis
#   t9  (validate→significance)   : concurrent work nullifies novelty
#   t10 (approach→formalize)      : formalization-reality gap
#   t11 (approach→diagnose)       : approach contradicts diagnosed failure
#   t12 (approach→challenge)      : pre-solved challenge
#   t13 (validate→significance)   : incremental contribution (Hamming fail)
#   t14 (validate→formalize)      : theoretical justification gap
#   t15 (validate→diagnose)       : wrong mechanism hypothesis
BACKWARD_TRANSITIONS: dict[str, dict[str, str]] = {
    "formalization": {"t2": "significance"},
    "diagnose": {"t4": "formalization"},
    "challenge": {"t6": "diagnose", "t7": "formalization"},
    "approach": {
        "t5": "significance",
        "t8": "diagnose",
        "t10": "formalization",
        "t11": "diagnose",
        "t12": "challenge",
    },
    "validate": {
        "t9": "significance",
        "t13": "significance",
        "t14": "formalization",
        "t15": "diagnose",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stage_key(stage: ResearchStage | str) -> str:
    """Normalise a :class:`ResearchStage` or raw string to its value."""
    if isinstance(stage, ResearchStage):
        return stage.value
    return str(stage)


def valid_transitions(stage: ResearchStage | str) -> list[ResearchStage]:
    """Return every stage reachable from ``stage`` in one step.

    The returned list is the union of the forward successor (if any) and
    all backward targets declared in :data:`BACKWARD_TRANSITIONS`.

    The result contains no duplicates and is ordered as
    ``[forward, *backward...]`` where ``backward...`` preserves the trigger
    order from :data:`BACKWARD_TRANSITIONS`.
    """
    key = _stage_key(stage)

    forward = list(FORWARD_TRANSITIONS.get(key, []))
    backward = list(BACKWARD_TRANSITIONS.get(key, {}).values())

    seen: set[str] = set()
    ordered: list[str] = []
    for s in (*forward, *backward):
        if s not in seen:
            seen.add(s)
            ordered.append(s)

    return [ResearchStage(s) for s in ordered]


# ---------------------------------------------------------------------------
# Forward guards (g1..g5)
# ---------------------------------------------------------------------------

def _content_has(artifact: ResearchArtifact, *needles: str) -> bool:
    """Case-insensitive substring search across the artifact content."""
    body = (artifact.content or "").lower()
    return any(n.lower() in body for n in needles)


def _task_chain_field(artifact: ResearchArtifact, field: str) -> str | None:
    chain = getattr(artifact, "task_chain", None)
    if chain is None:
        return None
    return getattr(chain, field, None)


def stage_guard_satisfied(
    stage: ResearchStage | str,
    artifact: ResearchArtifact,
) -> bool:
    """Return ``True`` iff ``artifact`` satisfies the forward guard for ``stage``.

    The guards implement the §2.4 research-plan rules:

    - **g1** ``significance → formalization``: artifact contains an explicit
      significance assessment (any of the four tests) *or* declares a
      significance score in its metadata.
    - **g2** ``formalization → diagnose``: artifact has a formal problem
      definition (task chain has a non-empty ``problem`` field, or content
      mentions a mathematical object).
    - **g3** ``diagnose → challenge``: artifact cites a specific failure
      (task chain ``challenge`` set, or content references a failure mode).
    - **g4** ``challenge → approach``: artifact's challenge constrains a
      solution class (task chain ``challenge`` and ``approach`` both set,
      or content states the implied approach class).
    - **g5** ``approach → validate``: artifact has an approach and a
      one-sentence contribution linking back to the challenge.

    Stages without an outgoing forward edge (``validate``, ``full_draft``)
    always return ``False``.
    """
    key = _stage_key(stage)

    # Only stages with a forward transition can satisfy a forward guard.
    # ``full_draft`` is terminal and has no outgoing edge.
    if not FORWARD_TRANSITIONS.get(key):
        return False

    if key == "significance":
        # g1: any significance signal present
        meta_has_sig = (
            isinstance(artifact.metadata, dict)
            and "significance" in {k.lower() for k in artifact.metadata.keys()}
        )
        return meta_has_sig or _content_has(
            artifact,
            "significance",
            "impact",
            "why this matters",
            "one-sentence test",
            "hamming",
            "concrete consequence",
        )

    if key == "formalization":
        # g2: formal problem definition
        problem = _task_chain_field(artifact, "problem")
        if problem:
            return True
        return _content_has(
            artifact,
            "formal problem",
            "problem definition",
            "\\mathcal",
            "$",  # inline math
            "argmin",
            "argmax",
            "∀",
            "∃",
        )

    if key == "diagnose":
        # g3: specific failure mapped to term/assumption
        challenge = _task_chain_field(artifact, "challenge")
        if challenge:
            return True
        return _content_has(
            artifact,
            "failure mode",
            "fails when",
            "breaks down",
            "diagnosed",
            "root cause",
        )

    if key == "challenge":
        # g4: structural challenge constrains solution class
        challenge = _task_chain_field(artifact, "challenge")
        approach = _task_chain_field(artifact, "approach")
        if challenge and approach:
            return True
        return _content_has(
            artifact,
            "structural challenge",
            "constrains the solution",
            "implied solution class",
            "must handle",
        )

    if key == "approach":
        # g5: approach addresses challenge with formal structure
        approach = _task_chain_field(artifact, "approach")
        one_sentence = _task_chain_field(artifact, "one_sentence")
        if approach and one_sentence:
            return True
        return _content_has(
            artifact,
            "our approach",
            "we propose",
            "key insight",
            "addresses the challenge",
        )

    if key == "validate":
        # g6: artifact has an approach and a one-sentence contribution
        # linking back to the challenge (proxy for "validated").
        approach = _task_chain_field(artifact, "approach")
        one_sentence = _task_chain_field(artifact, "one_sentence")
        if approach and one_sentence:
            return True
        return _content_has(
            artifact,
            "validated",
            "experiments show",
            "results demonstrate",
        )

    return False


# ---------------------------------------------------------------------------
# Backward trigger mapping
# ---------------------------------------------------------------------------

# Which stages each trigger is allowed to fire from. This lets
# ``backward_trigger_from_finding`` return triggers that are syntactically
# valid backward transitions.
_ALL_TRIGGERS: set[str] = {
    trigger
    for targets in BACKWARD_TRANSITIONS.values()
    for trigger in targets.keys()
}


def _infer_trigger_from_text(text: str) -> BackwardTrigger | None:
    """Keyword-heuristic fallback for mapping an attack_vector to a trigger."""
    t = text.lower()

    # §3.1 novelty: concurrent work or incremental contribution
    if "concurrent" in t or "scooped" in t or "prior art" in t:
        return "t9"
    if "incremental" in t or "hamming" in t:
        return "t13"
    if "low impact" in t or "trivial significance" in t:
        return "t5"

    # §3.2 formalization attacks
    if "trivial special case" in t or "known problem" in t:
        return "t2"
    if "wrong framework" in t or "wrong mathematical framework" in t:
        return "t7"
    if (
        "formalization-reality gap" in t
        or "formalization reality gap" in t
        or "reality gap" in t
    ):
        return "t10"
    if "does not map to" in t or "failure doesn't map" in t:
        return "t4"

    # §3.3 challenge attacks
    if "wrong challenge" in t:
        return "t6"
    if "pre-solved" in t or "already solved" in t:
        return "t12"
    if "approach contradicts" in t:
        return "t11"
    if "approach exposes" in t:
        return "t8"

    # §3.4 mechanism / theoretical
    if "wrong mechanism" in t:
        return "t15"
    if "theoretical justification" in t or "justification gap" in t:
        return "t14"

    return None


def backward_trigger_from_finding(finding: Finding) -> BackwardTrigger | None:
    """Map a :class:`Finding` to a backward trigger (``t2..t15``).

    Resolution order:

    1. If ``finding.maps_to_trigger`` is set and names a known trigger,
       return it verbatim.
    2. Otherwise inspect ``finding.attack_vector`` and pattern-match on
       the keywords listed in research_plan.md §2.4 / review_guideline §3.
    3. If no rule matches, return ``None``.

    Only triggers whose severity warrants backward motion are returned.
    Minor findings are always mapped to ``None`` regardless of wording.
    """
    # Minor findings don't justify backward movement.
    from alpha_research.models.review import Severity

    if finding.severity == Severity.MINOR:
        return None

    # 1. Explicit maps_to_trigger field wins.
    explicit = (finding.maps_to_trigger or "").strip().lower()
    if explicit in _ALL_TRIGGERS:
        return explicit  # type: ignore[return-value]

    # 2. Infer from attack_vector text.
    return _infer_trigger_from_text(finding.attack_vector or "")
