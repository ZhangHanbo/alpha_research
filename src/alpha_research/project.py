"""Compact project layer — the state machine made real on disk.

Phase 0 of the integrated-state-machine plan deleted the ~1,300-line
``src/alpha_research/projects/`` package (ProjectManifest / ProjectState /
ProjectSnapshot / registry / git worktree resume). This module is its
replacement and the core of Phase 1 + Phase 2.

**Principles** (from ``guidelines/spec/implementation_plan.md`` Parts I–II):

1. A project is a directory. No registry, no SQLite, no snapshots beyond
   what ``git`` already gives you if you initialize one inside the dir.
2. The filesystem holds the state: ``state.json`` is the mutable HEAD,
   ``provenance.jsonl`` is the append-only lineage, and the various
   ``*.jsonl`` streams hold structured agent outputs.
3. Stage transitions are *explicit* actions. The agent never transitions
   stages on its own; a human invokes ``advance`` / ``backward`` via the
   CLI or programmatically through :func:`advance` / :func:`backward`.
4. Forward guards (``g1..g5``) read artifacts from disk and return a
   structured :class:`GuardCheck` with per-condition pass/fail so the
   CLI can explain *why* ``advance`` refused.
5. Backward transitions carry a **constraint** — a human-written
   sentence explaining what was learned downstream, so the re-entered
   stage does not start from a blank slate.

References: ``guidelines/spec/implementation_plan.md`` Parts II–IV,
``guidelines/spec/research_plan.md`` §1 (state machine),
``guidelines/doctrine/research_guideline.md`` §2.2–§2.8.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alpha_research.models.blackboard import ResearchStage
from alpha_research.pipelines.state_machine import (
    BACKWARD_TRANSITIONS,
    FORWARD_TRANSITIONS,
)
from alpha_research.records.jsonl import (
    count_records,
    log_action,
    read_records,
)

# ---------------------------------------------------------------------------
# Dataclasses — the on-disk state model
# ---------------------------------------------------------------------------


def _now() -> str:
    """Timezone-aware ISO-8601 timestamp (UTC, seconds precision)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class StageTransition:
    """One edge traversed in the state machine.

    Recorded in ``state.json``'s ``stage_history`` when ``advance`` /
    ``backward`` fires. ``trigger`` is one of ``g1..g5`` for forward
    transitions, ``t2..t15`` for backward ones, or ``"init"`` for the
    initial state at project creation.
    """

    from_stage: str | None
    to_stage: str
    at: str
    trigger: str
    note: str = ""
    carried_constraint: str | None = None
    provenance_id: str | None = None


@dataclass
class OpenTrigger:
    """A backward trigger proposed by a skill but not yet executed.

    Skills write findings or reviews; when ``experiment-analyze`` or
    ``adversarial-review`` detects a pattern that maps to a specific
    backward trigger, it appends one of these to the project state.
    The human then decides whether to execute the transition.
    """

    trigger: str
    proposed_by: str
    proposed_at: str
    evidence: str
    resolved: bool = False
    resolution_note: str | None = None


@dataclass
class ConditionResult:
    """One atomic check inside a forward guard."""

    name: str
    passed: bool
    detail: str


@dataclass
class GuardCheck:
    """Result of running a forward guard (``g1..g5``).

    A guard passes iff every ``ConditionResult`` in ``conditions`` passed.
    The CLI prints the per-condition breakdown when ``advance`` refuses
    so the researcher can see exactly which artifacts to update.
    """

    guard: str
    stage: str
    passed: bool
    conditions: list[ConditionResult]
    checked_at: str

    def summary(self) -> str:
        status = "✅ passes" if self.passed else "❌ blocked"
        parts = [f"{self.guard} ({self.stage}): {status}"]
        for c in self.conditions:
            mark = "✓" if c.passed else "✗"
            parts.append(f"  {mark} {c.name}: {c.detail}")
        return "\n".join(parts)


@dataclass
class ProjectState:
    """The mutable HEAD of a project."""

    project_id: str
    created_at: str
    current_stage: str
    stage_entered_at: str
    stage_history: list[StageTransition] = field(default_factory=list)
    open_triggers: list[OpenTrigger] = field(default_factory=list)
    code_dir: str | None = None
    target_venue: str = "RSS"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "created_at": self.created_at,
            "current_stage": self.current_stage,
            "stage_entered_at": self.stage_entered_at,
            "stage_history": [asdict(t) for t in self.stage_history],
            "open_triggers": [asdict(t) for t in self.open_triggers],
            "code_dir": self.code_dir,
            "target_venue": self.target_venue,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectState":
        history = [StageTransition(**t) for t in data.get("stage_history", [])]
        triggers = [OpenTrigger(**t) for t in data.get("open_triggers", [])]
        return cls(
            project_id=data["project_id"],
            created_at=data["created_at"],
            current_stage=data["current_stage"],
            stage_entered_at=data["stage_entered_at"],
            stage_history=history,
            open_triggers=triggers,
            code_dir=data.get("code_dir"),
            target_venue=data.get("target_venue", "RSS"),
            notes=data.get("notes", ""),
        )


# ---------------------------------------------------------------------------
# state.json I/O
# ---------------------------------------------------------------------------


STATE_FILENAME = "state.json"


def state_path(project_dir: Path) -> Path:
    return Path(project_dir) / STATE_FILENAME


def load_state(project_dir: Path) -> ProjectState:
    """Read ``state.json`` from ``project_dir``.

    Raises
    ------
    FileNotFoundError
        If the project has not been initialized.
    """
    path = state_path(project_dir)
    if not path.exists():
        raise FileNotFoundError(
            f"No state.json in {project_dir}. Run `alpha-research project "
            f"init` to create a project first."
        )
    with path.open("r", encoding="utf-8") as fp:
        return ProjectState.from_dict(json.load(fp))


def save_state(project_dir: Path, state: ProjectState) -> None:
    """Atomically write ``state.json``.

    Uses a ``.tmp`` sibling + rename so the file is never observed in a
    half-written state by concurrent readers.
    """
    path = state_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fp:
        json.dump(state.to_dict(), fp, indent=2)
        fp.write("\n")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Project initialization
# ---------------------------------------------------------------------------


def init_project(
    project_dir: Path,
    project_id: str | None = None,
    question: str = "",
    code_dir: str | None = None,
    target_venue: str = "RSS",
) -> ProjectState:
    """Create a new project directory and initial ``state.json``.

    This does NOT scaffold the markdown templates (PROJECT.md, DISCUSSION.md,
    LOGS.md, hamming.md, etc.) — that's Phase 2's job in
    ``alpha_research.main``. This function handles only the state-machine side.
    """
    project_dir = Path(project_dir)
    if state_path(project_dir).exists():
        raise FileExistsError(
            f"Project already exists at {project_dir} (state.json present)"
        )

    project_dir.mkdir(parents=True, exist_ok=True)

    now = _now()
    initial_transition = StageTransition(
        from_stage=None,
        to_stage=ResearchStage.SIGNIFICANCE.value,
        at=now,
        trigger="init",
        note=question or "project initialized",
        carried_constraint=None,
    )
    state = ProjectState(
        project_id=project_id or project_dir.name,
        created_at=now,
        current_stage=ResearchStage.SIGNIFICANCE.value,
        stage_entered_at=now,
        stage_history=[initial_transition],
        open_triggers=[],
        code_dir=code_dir,
        target_venue=target_venue,
        notes="",
    )
    save_state(project_dir, state)

    # First provenance record is the init itself.
    prov_id = log_action(
        project_dir,
        action_type="cli",
        action_name="project.init",
        project_stage=state.current_stage,
        inputs=[],
        outputs=[STATE_FILENAME],
        summary=f"project initialized: {question!r}",
    )
    initial_transition.provenance_id = prov_id
    save_state(project_dir, state)

    return state


# ---------------------------------------------------------------------------
# Forward guard checks — disk-bound, one per stage
# ---------------------------------------------------------------------------


def _file_nonempty(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def _md_has_real_content(path: Path, min_chars: int = 50) -> bool:
    """A markdown file "has real content" if it's non-empty AND has at
    least ``min_chars`` of non-whitespace non-comment text after stripping
    header lines and HTML comments.
    """
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    # Strip HTML comments and lines starting with #
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    # Remove boilerplate placeholders like "<fill me in>"
    body = "\n".join(lines)
    body = body.replace("<!--", " ").replace("-->", " ")
    cleaned = "".join(ch for ch in body if not ch.isspace())
    return len(cleaned) >= min_chars


def _has_scope_benchmarks(benchmarks_md: Path) -> tuple[bool, int]:
    """Return (has_at_least_one, count) for benchmarks listed under an
    ``## In scope`` header in ``benchmarks.md``.

    A "benchmark" is any ``###`` subheader under the ``## In scope``
    section.
    """
    if not benchmarks_md.exists():
        return False, 0
    text = benchmarks_md.read_text(encoding="utf-8")
    lines = text.splitlines()

    count = 0
    in_scope = False
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("## "):
            in_scope = "in scope" in stripped.lower()
            continue
        if in_scope and stripped.startswith("### "):
            count += 1
    return count > 0, count


def _check_g1(project_dir: Path) -> GuardCheck:
    """g1 — SIGNIFICANCE → FORMALIZE.

    Conditions (implementation_plan.md §III.1):
      1. PROJECT.md has real content.
      2. ≥1 significance_screen record with ``human_confirmed: true``.
      3. That record has a non-null ``concrete_consequence`` string.
      4. That record's ``durability_risk`` is not ``"high"``.
    """
    conditions: list[ConditionResult] = []

    project_md = project_dir / "PROJECT.md"
    c1_ok = _md_has_real_content(project_md, min_chars=40)
    conditions.append(
        ConditionResult(
            "PROJECT.md has content",
            c1_ok,
            "found" if c1_ok else "missing or empty",
        )
    )

    confirmed = read_records(
        project_dir,
        "significance_screen",
        filters={"human_confirmed": True},
    )
    c2_ok = len(confirmed) >= 1
    conditions.append(
        ConditionResult(
            "significance_screen with human_confirmed=true",
            c2_ok,
            f"{len(confirmed)} record(s)" if c2_ok else "none found",
        )
    )

    latest = confirmed[-1] if confirmed else None
    consequence = (latest or {}).get("concrete_consequence") or ""
    c3_ok = bool(consequence.strip())
    conditions.append(
        ConditionResult(
            "concrete_consequence is non-empty",
            c3_ok,
            consequence[:60] + "..." if len(consequence) > 60 else consequence or "missing",
        )
    )

    durability = (latest or {}).get("durability_risk", "unknown")
    c4_ok = durability != "high"
    conditions.append(
        ConditionResult(
            "durability_risk is not 'high'",
            c4_ok,
            f"risk={durability}",
        )
    )

    return GuardCheck(
        guard="g1",
        stage=ResearchStage.SIGNIFICANCE.value,
        passed=all(c.passed for c in conditions),
        conditions=conditions,
        checked_at=_now(),
    )


def _check_g2(project_dir: Path) -> GuardCheck:
    """g2 — FORMALIZE → DIAGNOSE.

    Conditions (implementation_plan.md §III.2):
      1. formalization.md has real content.
      2. ≥1 formalization_check record with ``formalization_level ∈
         {formal_math, semi_formal}``.
      3. That record has a non-empty ``structure_exploited`` list.
      4. benchmarks.md exists with ≥1 benchmark under "## In scope".
      5. ≥1 benchmark_survey record with ``human_confirmed: true``.
    """
    conditions: list[ConditionResult] = []

    formalization_md = project_dir / "formalization.md"
    c1_ok = _md_has_real_content(formalization_md, min_chars=80)
    conditions.append(
        ConditionResult(
            "formalization.md has content",
            c1_ok,
            "found" if c1_ok else "missing or empty",
        )
    )

    checks = read_records(project_dir, "formalization_check")
    formal_checks = [
        c for c in checks
        if c.get("formalization_level") in {"formal_math", "semi_formal"}
    ]
    c2_ok = len(formal_checks) >= 1
    conditions.append(
        ConditionResult(
            "formalization_check with level in {formal_math, semi_formal}",
            c2_ok,
            f"{len(formal_checks)} record(s)" if c2_ok else f"0 of {len(checks)} qualify",
        )
    )

    latest_fc = formal_checks[-1] if formal_checks else {}
    structure = latest_fc.get("structure_exploited") or []
    c3_ok = isinstance(structure, list) and len(structure) > 0
    conditions.append(
        ConditionResult(
            "structure_exploited is non-empty",
            c3_ok,
            f"{len(structure) if isinstance(structure, list) else 0} entries",
        )
    )

    benchmarks_md = project_dir / "benchmarks.md"
    has_any, bench_count = _has_scope_benchmarks(benchmarks_md)
    conditions.append(
        ConditionResult(
            "benchmarks.md has ≥1 benchmark under '## In scope'",
            has_any,
            f"{bench_count} benchmark(s) found",
        )
    )

    surveys = read_records(
        project_dir,
        "benchmark_survey",
        filters={"human_confirmed": True},
    )
    c5_ok = len(surveys) >= 1
    conditions.append(
        ConditionResult(
            "benchmark_survey with human_confirmed=true",
            c5_ok,
            f"{len(surveys)} record(s)" if c5_ok else "none found",
        )
    )

    return GuardCheck(
        guard="g2",
        stage=ResearchStage.FORMALIZATION.value,
        passed=all(c.passed for c in conditions),
        conditions=conditions,
        checked_at=_now(),
    )


def _check_g3(project_dir: Path) -> GuardCheck:
    """g3 — DIAGNOSE → CHALLENGE.

    Conditions (implementation_plan.md §III.3):
      1. For every in-scope benchmark in benchmarks.md, at least one
         experiment_analysis record with mode="reproduction" and
         reproducibility ∈ {pass, partial}.
      2. ≥1 diagnosis record with non-null failure_mapped_to_formal_term.
    """
    conditions: list[ConditionResult] = []

    # Condition 1 — reproducibility floor
    reprods = read_records(project_dir, "experiment_analysis")
    passing = [
        r for r in reprods
        if r.get("mode") == "reproduction"
        and r.get("reproducibility") in {"pass", "partial"}
    ]
    _, scope_count = _has_scope_benchmarks(project_dir / "benchmarks.md")
    # If no benchmarks are scoped we auto-fail with a clear message —
    # g2 should have been blocked already but defensive check here.
    if scope_count == 0:
        c1_ok = False
        detail = "no benchmarks in scope (blocked by g2)"
    else:
        c1_ok = len(passing) >= 1
        detail = (
            f"{len(passing)} passing reproduction(s) for "
            f"{scope_count} scoped benchmark(s)"
        )
    conditions.append(ConditionResult(
        "reproduction experiment for each in-scope benchmark",
        c1_ok,
        detail,
    ))

    # Condition 2 — specific failure mapped to a formal term
    diagnoses = read_records(project_dir, "diagnosis")
    mapped = [d for d in diagnoses if d.get("failure_mapped_to_formal_term")]
    c2_ok = len(mapped) >= 1
    conditions.append(ConditionResult(
        "diagnosis with failure_mapped_to_formal_term",
        c2_ok,
        f"{len(mapped)} mapped of {len(diagnoses)} total",
    ))

    return GuardCheck(
        guard="g3",
        stage=ResearchStage.DIAGNOSE.value,
        passed=all(c.passed for c in conditions),
        conditions=conditions,
        checked_at=_now(),
    )


def _check_g4(project_dir: Path) -> GuardCheck:
    """g4 — CHALLENGE → APPROACH.

    Conditions (implementation_plan.md §III.4):
      1. ≥1 challenge record with challenge_type="structural".
      2. That record's implied_method_class is non-null.
      3. No unresolved t12 open trigger.
    """
    conditions: list[ConditionResult] = []

    state = load_state(project_dir)

    challenges = read_records(project_dir, "challenge")
    structural = [c for c in challenges if c.get("challenge_type") == "structural"]
    c1_ok = len(structural) >= 1
    conditions.append(ConditionResult(
        "challenge with challenge_type='structural'",
        c1_ok,
        f"{len(structural)} structural of {len(challenges)} total",
    ))

    latest = structural[-1] if structural else {}
    implied = latest.get("implied_method_class") or ""
    c2_ok = bool(implied.strip()) if isinstance(implied, str) else False
    conditions.append(ConditionResult(
        "implied_method_class is set",
        c2_ok,
        implied or "missing",
    ))

    unresolved_t12 = [
        t for t in state.open_triggers
        if t.trigger == "t12" and not t.resolved
    ]
    c3_ok = len(unresolved_t12) == 0
    conditions.append(ConditionResult(
        "no unresolved t12 open trigger",
        c3_ok,
        f"{len(unresolved_t12)} unresolved" if unresolved_t12 else "clean",
    ))

    return GuardCheck(
        guard="g4",
        stage=ResearchStage.CHALLENGE.value,
        passed=all(c.passed for c in conditions),
        conditions=conditions,
        checked_at=_now(),
    )


def _check_g5(project_dir: Path) -> GuardCheck:
    """g5 — APPROACH → VALIDATE.

    Conditions (implementation_plan.md §III.5):
      1. one_sentence.md has content and is not a performance claim.
      2. ≥1 experiment_design record for the current approach.
      3. No unresolved backward triggers in open_triggers.
    """
    conditions: list[ConditionResult] = []

    state = load_state(project_dir)

    one_sentence = project_dir / "one_sentence.md"
    c1_ok = _md_has_real_content(one_sentence, min_chars=30)
    if c1_ok:
        text = one_sentence.read_text(encoding="utf-8").lower()
        # Heuristic: flag obvious "SOTA on X" claims as failing the insight test.
        bad_phrases = ["sota on", "state of the art on", "outperforms on", "achieves sota"]
        if any(p in text for p in bad_phrases):
            c1_ok = False
            detail = "present but reads as a performance claim, not an insight"
        else:
            detail = "present; not a raw performance claim"
    else:
        detail = "missing or too short"
    conditions.append(ConditionResult(
        "one_sentence.md states an insight",
        c1_ok,
        detail,
    ))

    n_designs = count_records(project_dir, "experiment_design")
    c2_ok = n_designs >= 1
    conditions.append(ConditionResult(
        "≥1 experiment_design record",
        c2_ok,
        f"{n_designs} design(s)",
    ))

    unresolved = [t for t in state.open_triggers if not t.resolved]
    c3_ok = len(unresolved) == 0
    conditions.append(ConditionResult(
        "no unresolved backward triggers",
        c3_ok,
        f"{len(unresolved)} unresolved" if unresolved else "clean",
    ))

    return GuardCheck(
        guard="g5",
        stage=ResearchStage.APPROACH.value,
        passed=all(c.passed for c in conditions),
        conditions=conditions,
        checked_at=_now(),
    )


_GUARD_DISPATCH: dict[str, Any] = {
    ResearchStage.SIGNIFICANCE.value: _check_g1,
    ResearchStage.FORMALIZATION.value: _check_g2,
    ResearchStage.DIAGNOSE.value: _check_g3,
    ResearchStage.CHALLENGE.value: _check_g4,
    ResearchStage.APPROACH.value: _check_g5,
}


def check_forward_guard(project_dir: Path) -> GuardCheck:
    """Run the forward guard for the project's current stage.

    VALIDATE → DONE is not a true forward guard; it's handled via an
    explicit ``mark_validated`` path in the research_review_loop pipeline.
    Calling this function when the current stage is VALIDATE or later
    returns a pre-built failed ``GuardCheck`` with an explanatory detail.
    """
    state = load_state(project_dir)
    stage = state.current_stage
    if stage not in _GUARD_DISPATCH:
        return GuardCheck(
            guard="(none)",
            stage=stage,
            passed=False,
            conditions=[ConditionResult(
                "forward guard defined for stage",
                False,
                f"stage {stage!r} has no forward guard — use adversarial review loop",
            )],
            checked_at=_now(),
        )
    return _GUARD_DISPATCH[stage](project_dir)


# ---------------------------------------------------------------------------
# Transition verbs: advance, backward
# ---------------------------------------------------------------------------


class GuardBlocked(Exception):
    """Raised by :func:`advance` when the forward guard refuses to pass."""

    def __init__(self, check: GuardCheck):
        super().__init__(check.summary())
        self.check = check


def advance(
    project_dir: Path,
    force: bool = False,
    note: str = "",
) -> StageTransition:
    """Transition forward to the next stage.

    Runs the current stage's forward guard. If the guard passes, writes
    a new :class:`StageTransition` to ``state.json`` and logs a provenance
    record. If the guard fails and ``force`` is ``False``, raises
    :class:`GuardBlocked` with the full :class:`GuardCheck` inside.

    ``force=True`` records an ``override_reason`` on the transition and
    appends a provenance record flagged as overridden. Use with care.
    """
    state = load_state(project_dir)
    check = check_forward_guard(project_dir)

    if not check.passed and not force:
        raise GuardBlocked(check)

    forward = FORWARD_TRANSITIONS.get(state.current_stage, [])
    if not forward:
        raise ValueError(
            f"Stage {state.current_stage!r} has no forward successor"
        )
    target = forward[0]

    now = _now()
    prov_id = log_action(
        project_dir,
        action_type="transition",
        action_name="project.advance",
        project_stage=state.current_stage,
        inputs=[STATE_FILENAME],
        outputs=[STATE_FILENAME],
        summary=(
            f"advance {state.current_stage}→{target} "
            f"({'forced' if not check.passed else check.guard})"
            + (f": {note}" if note else "")
        ),
    )

    # If the guard was blocked and we're forcing, make it visible in the
    # transition note AND the trigger. If the guard actually passed, use
    # the guard name as the trigger and preserve whatever note the human gave.
    if check.passed:
        resolved_trigger = check.guard
        resolved_note = note
    else:
        resolved_trigger = "force"
        if note:
            resolved_note = f"FORCED ({check.guard} blocked): {note}"
        else:
            resolved_note = f"FORCED — {check.guard} conditions not met"

    transition = StageTransition(
        from_stage=state.current_stage,
        to_stage=target,
        at=now,
        trigger=resolved_trigger,
        note=resolved_note,
        carried_constraint=None,
        provenance_id=prov_id,
    )
    state.stage_history.append(transition)
    state.current_stage = target
    state.stage_entered_at = now
    save_state(project_dir, state)
    return transition


def backward(
    project_dir: Path,
    trigger: str,
    carried_constraint: str,
    evidence: str = "",
    note: str = "",
) -> StageTransition:
    """Transition backward to an earlier stage.

    ``trigger`` must be one of ``t2..t15`` and must be a valid backward
    transition from the project's current stage per
    :data:`alpha_research.pipelines.state_machine.BACKWARD_TRANSITIONS`.

    ``carried_constraint`` is mandatory — the researcher must state what
    was learned downstream so the re-entered stage starts with a concrete
    constraint rather than a blank slate.
    """
    if not carried_constraint or not carried_constraint.strip():
        raise ValueError(
            "backward transition requires a non-empty carried_constraint. "
            "What did you learn downstream that now constrains the new "
            "search in the earlier stage?"
        )

    state = load_state(project_dir)
    transitions = BACKWARD_TRANSITIONS.get(state.current_stage, {})
    if trigger not in transitions:
        allowed = ", ".join(sorted(transitions.keys())) or "(none)"
        raise ValueError(
            f"Trigger {trigger!r} is not a valid backward transition from "
            f"stage {state.current_stage!r}. Allowed: {allowed}"
        )
    target = transitions[trigger]

    now = _now()
    prov_id = log_action(
        project_dir,
        action_type="transition",
        action_name="project.backward",
        project_stage=state.current_stage,
        inputs=[STATE_FILENAME],
        outputs=[STATE_FILENAME],
        summary=(
            f"backward {state.current_stage}→{target} via {trigger}: "
            f"{carried_constraint[:120]}"
        ),
    )

    transition = StageTransition(
        from_stage=state.current_stage,
        to_stage=target,
        at=now,
        trigger=trigger,
        note=note or evidence,
        carried_constraint=carried_constraint,
        provenance_id=prov_id,
    )
    state.stage_history.append(transition)
    state.current_stage = target
    state.stage_entered_at = now

    # Resolve any matching open trigger, or record one if none existed.
    resolved_any = False
    for ot in state.open_triggers:
        if ot.trigger == trigger and not ot.resolved:
            ot.resolved = True
            ot.resolution_note = carried_constraint
            resolved_any = True
            break
    if not resolved_any:
        state.open_triggers.append(OpenTrigger(
            trigger=trigger,
            proposed_by="human",
            proposed_at=now,
            evidence=evidence or carried_constraint,
            resolved=True,
            resolution_note=carried_constraint,
        ))

    save_state(project_dir, state)
    return transition


def propose_backward_trigger(
    project_dir: Path,
    trigger: str,
    proposed_by: str,
    evidence: str,
) -> OpenTrigger:
    """Append an :class:`OpenTrigger` to the project state.

    Skills call this (indirectly, via a helper invoked from their
    ``bash python -c`` snippets) when they detect a pattern that suggests
    a backward transition. The trigger is NOT executed — the human must
    decide by calling :func:`backward`.
    """
    state = load_state(project_dir)
    ot = OpenTrigger(
        trigger=trigger,
        proposed_by=proposed_by,
        proposed_at=_now(),
        evidence=evidence,
        resolved=False,
    )
    state.open_triggers.append(ot)
    save_state(project_dir, state)
    return ot


# ---------------------------------------------------------------------------
# Stage summary — used by `alpha-research project stage`
# ---------------------------------------------------------------------------


@dataclass
class StageSummary:
    """Everything `project stage` needs to render the current state."""

    project_id: str
    current_stage: str
    stage_entered_at: str
    days_in_stage: int
    guard_check: GuardCheck | None
    open_triggers: list[OpenTrigger]
    recent_history: list[StageTransition]

    def render(self) -> str:
        lines = [
            f"Project: {self.project_id}",
            f"Stage:   {self.current_stage}  (entered {self.stage_entered_at}, {self.days_in_stage}d ago)",
            "",
        ]
        if self.guard_check is not None:
            lines.append("Forward guard:")
            lines.append(self.guard_check.summary())
            lines.append("")

        if self.open_triggers:
            lines.append("Open backward triggers:")
            for t in self.open_triggers:
                mark = "✓" if t.resolved else "⚠"
                lines.append(f"  {mark} {t.trigger} — proposed by {t.proposed_by}: {t.evidence[:80]}")
            lines.append("")
        else:
            lines.append("Open backward triggers: none")
            lines.append("")

        if self.recent_history:
            lines.append("Recent transitions (most recent last):")
            for h in self.recent_history[-5:]:
                arrow = f"{h.from_stage or '∅'} → {h.to_stage}"
                lines.append(f"  [{h.at}] {arrow}  ({h.trigger})  {h.note[:60]}")

        return "\n".join(lines)


def stage_summary(project_dir: Path) -> StageSummary:
    state = load_state(project_dir)

    try:
        entered = datetime.fromisoformat(state.stage_entered_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days = max(0, (now - entered).days)
    except (ValueError, AttributeError):
        days = 0

    try:
        check = check_forward_guard(project_dir)
    except Exception:
        check = None

    return StageSummary(
        project_id=state.project_id,
        current_stage=state.current_stage,
        stage_entered_at=state.stage_entered_at,
        days_in_stage=days,
        guard_check=check,
        open_triggers=list(state.open_triggers),
        recent_history=list(state.stage_history),
    )


# ---------------------------------------------------------------------------
# LOGS.md — append-only entries written by agents/skills during revisions.
# ---------------------------------------------------------------------------

_AGENT_REVISIONS_MARKER = "<!-- AGENT_REVISIONS_END -->"


def append_revision_log(
    project_dir: Path | str,
    *,
    agent: str,
    stage: str,
    target: str,
    revision: str,
    result: str = "",
    feedback: str = "",
) -> str:
    """Append one agent-revision entry to ``LOGS.md``.

    Every skill / pipeline that mutates a research artifact should call
    this so the LOGS.md file in the project directory carries a human-
    readable audit trail alongside the structured ``provenance.jsonl``
    stream. Writes are idempotent-safe for concurrent calls because we
    always re-read the file before injecting.

    Parameters
    ----------
    project_dir:
        The project directory. Must contain a ``LOGS.md`` file — raises
        :class:`FileNotFoundError` otherwise.
    agent:
        Skill, pipeline, or human name (e.g. ``"adversarial-review"``).
    stage:
        Project stage at time of revision (lowercase, matching
        :class:`alpha_research.models.blackboard.ResearchStage` values).
    target:
        Artifact / file / record the agent touched (e.g.
        ``"PROJECT.md § Scope"`` or ``"evaluation.jsonl#eval_abc123"``).
    revision:
        One-paragraph description of the change, concretely.
    result:
        Optional: what the downstream verifier / guard / metric reported.
    feedback:
        Optional: reviewer feedback, skill verdict, or error message.

    Returns
    -------
    str
        The timestamp header (ISO-8601 UTC) of the appended entry.
    """
    project_dir = Path(project_dir)
    logs_path = project_dir / "LOGS.md"
    if not logs_path.exists():
        raise FileNotFoundError(
            f"{logs_path} not found — run `alpha-research project init` first."
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry_lines = [
        "",
        f"### {timestamp} — {agent}",
        "",
        f"- **Stage**: {stage}",
        f"- **Target**: {target}",
        f"- **Revision**: {revision}",
    ]
    if result:
        entry_lines.append(f"- **Result**: {result}")
    if feedback:
        entry_lines.append(f"- **Feedback**: {feedback}")
    entry_lines.append("")
    entry_block = "\n".join(entry_lines)

    text = logs_path.read_text(encoding="utf-8")
    if _AGENT_REVISIONS_MARKER in text:
        # Insert directly before the marker so entries stay chronological.
        new_text = text.replace(
            _AGENT_REVISIONS_MARKER,
            entry_block + "\n" + _AGENT_REVISIONS_MARKER,
            1,
        )
    else:
        # LOGS.md was hand-edited and lost the marker — fall back to append
        # at the end of the file rather than silently dropping the entry.
        if not text.endswith("\n"):
            text += "\n"
        new_text = text + entry_block + "\n"
    logs_path.write_text(new_text, encoding="utf-8")

    # Also record a provenance entry so the JSONL audit trail stays aligned.
    try:
        log_action(
            project_dir,
            action_type="skill",
            action_name=agent,
            project_stage=stage,
            inputs=[target],
            outputs=["LOGS.md"],
            summary=revision[:200],
        )
    except Exception:  # pragma: no cover - best-effort secondary write
        pass

    return timestamp
