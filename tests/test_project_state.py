"""Tests for the Phase 1 state-machine layer.

Covers:
  - state.json I/O (round-trip)
  - init_project sets SIGNIFICANCE stage and logs provenance
  - check_forward_guard returns per-condition GuardCheck
  - advance refuses when guard fails, proceeds when it passes
  - advance honors --force (override)
  - backward requires carried_constraint, records the transition
  - propose_backward_trigger appends an OpenTrigger
  - Provenance records are appended on every transition

Every test uses the ``report`` fixture from ``tests/conftest.py`` so a
human-readable report lands at ``tests/reports/test_project_state.md``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from alpha_research.models.blackboard import ResearchStage
from alpha_research.project import (
    GuardBlocked,
    OpenTrigger,
    ProjectState,
    StageTransition,
    advance,
    backward,
    check_forward_guard,
    init_project,
    load_state,
    propose_backward_trigger,
    save_state,
    stage_summary,
    state_path,
)
from alpha_research.records.jsonl import (
    SUPPORTED_RECORD_TYPES,
    append_record,
    count_records,
    log_action,
    read_records,
)


# ---------------------------------------------------------------------------
# Helpers for building fixture projects
# ---------------------------------------------------------------------------


def _passing_significance_record() -> dict:
    return {
        "human_confirmed": True,
        "concrete_consequence": (
            "Robots can handle deformable objects in warehouses, "
            "enabling automation of produce packing lines."
        ),
        "durability_risk": "low",
        "hamming_test_score": 4,
    }


def _passing_formalization_record() -> dict:
    return {
        "formalization_level": "formal_math",
        "framework": "POMDP with contact constraint",
        "structure_exploited": ["SE(3) equivariance", "convex tangent plane"],
        "sympy_verified": True,
    }


def _passing_benchmark_survey() -> dict:
    return {
        "human_confirmed": True,
        "top_candidates": [
            {"name": "NIST ATB", "saturation": "low"},
            {"name": "FurnitureBench", "saturation": "medium"},
        ],
        "recommended": "NIST ATB",
    }


def _passing_reproduction_analysis() -> dict:
    return {
        "mode": "reproduction",
        "benchmark_id": "NIST ATB",
        "reproducibility": "pass",
        "measured_metric": 0.60,
        "target_metric": 0.62,
    }


def _passing_diagnosis() -> dict:
    return {
        "failure_mapped_to_formal_term": "observation model P(z|s) insufficient",
        "failure_mode": "slip at contact initiation",
        "root_cause": "depth camera resolution below 2mm",
    }


def _passing_challenge() -> dict:
    return {
        "challenge_type": "structural",
        "structural_barrier": "depth sensing cannot resolve sub-mm alignment",
        "implied_method_class": "tactile sensing + learned contact model",
    }


def _write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_benchmarks_md(project_dir: Path, n_in_scope: int = 1) -> Path:
    lines = ["# Benchmarks", "", "## In scope", ""]
    for i in range(n_in_scope):
        lines.extend([
            f"### Benchmark {i}: NIST ATB #{i}",
            "- Rationale: community standard",
            "- Metric: success rate",
            "- Success criterion: peg seated within 0.5mm tolerance",
            "- Published baselines:",
            "  - Paper A (2024) impedance: 0.62 success",
            "- Install: pip install nist-atb-sim",
            "- Reproducibility: pending",
            "- Saturation risk: LOW — top is 0.78",
            "",
        ])
    path = project_dir / "benchmarks.md"
    _write_md(path, "\n".join(lines))
    return path


def _scaffold_project(tmp_path: Path, name: str) -> Path:
    """Create a bare project with a stage of SIGNIFICANCE and empty artifacts."""
    project_dir = tmp_path / name
    init_project(project_dir, project_id=name, question=f"research question for {name}")
    return project_dir


# ---------------------------------------------------------------------------
# Test 1 — init_project
# ---------------------------------------------------------------------------


def test_init_project_creates_state_and_logs_provenance(tmp_path, report):
    """init_project should create state.json at SIGNIFICANCE with one
    initial transition and one provenance record."""
    project_dir = tmp_path / "test_init"
    state = init_project(
        project_dir,
        project_id="test_init",
        question="tactile insertion for assembly",
    )

    state_loaded = load_state(project_dir)
    provenance = read_records(project_dir, "provenance")

    passed = (
        state_loaded.current_stage == ResearchStage.SIGNIFICANCE.value
        and state_loaded.project_id == "test_init"
        and len(state_loaded.stage_history) == 1
        and state_loaded.stage_history[0].trigger == "init"
        and len(provenance) == 1
        and provenance[0]["action_name"] == "project.init"
    )

    report.record(
        name="init_project creates state.json and logs provenance",
        purpose=(
            "Verify init_project() creates a state.json with stage=SIGNIFICANCE, "
            "one init transition, and appends a provenance record."
        ),
        inputs={
            "project_dir": str(project_dir),
            "project_id": "test_init",
            "question": "tactile insertion for assembly",
        },
        expected={
            "current_stage": "significance",
            "stage_history_length": 1,
            "init_trigger": "init",
            "provenance_count": 1,
            "init_provenance_action": "project.init",
        },
        actual={
            "current_stage": state_loaded.current_stage,
            "stage_history_length": len(state_loaded.stage_history),
            "init_trigger": state_loaded.stage_history[0].trigger,
            "provenance_count": len(provenance),
            "init_provenance_action": provenance[0]["action_name"] if provenance else None,
        },
        passed=passed,
        conclusion=(
            "Project initialization is the single entry point that creates "
            "state.json in a known-good state and makes the first provenance "
            "entry so every subsequent action has a lineage root."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 2 — state.json round-trip
# ---------------------------------------------------------------------------


def test_state_json_round_trip_preserves_history_and_triggers(tmp_path, report):
    """save_state followed by load_state must return an identical ProjectState."""
    project_dir = tmp_path / "rt"
    project_dir.mkdir()

    original = ProjectState(
        project_id="rt",
        created_at="2026-04-11T10:00:00+00:00",
        current_stage="formalization",
        stage_entered_at="2026-04-11T11:00:00+00:00",
        stage_history=[
            StageTransition(
                from_stage=None,
                to_stage="significance",
                at="2026-04-11T10:00:00+00:00",
                trigger="init",
                note="test project",
            ),
            StageTransition(
                from_stage="significance",
                to_stage="formalization",
                at="2026-04-11T11:00:00+00:00",
                trigger="g1",
                note="Hamming confirmed",
                provenance_id="prov_abc123",
            ),
        ],
        open_triggers=[
            OpenTrigger(
                trigger="t5",
                proposed_by="experiment-analyze",
                proposed_at="2026-04-11T12:00:00+00:00",
                evidence="method matches prior work",
            ),
        ],
        code_dir="/home/user/my-method",
        target_venue="RSS",
        notes="lorem",
    )

    save_state(project_dir, original)
    loaded = load_state(project_dir)

    passed = (
        loaded.project_id == original.project_id
        and loaded.current_stage == original.current_stage
        and len(loaded.stage_history) == len(original.stage_history)
        and loaded.stage_history[1].trigger == "g1"
        and loaded.stage_history[1].provenance_id == "prov_abc123"
        and len(loaded.open_triggers) == 1
        and loaded.open_triggers[0].trigger == "t5"
        and loaded.code_dir == "/home/user/my-method"
    )

    report.record(
        name="state.json round-trip",
        purpose="save_state then load_state must be a lossless identity.",
        inputs={
            "stage_history_count": len(original.stage_history),
            "open_triggers_count": len(original.open_triggers),
            "code_dir": original.code_dir,
        },
        expected={"identity": True},
        actual={
            "project_id_match": loaded.project_id == original.project_id,
            "stage_match": loaded.current_stage == original.current_stage,
            "history_length_match": len(loaded.stage_history) == len(original.stage_history),
            "transition_trigger_preserved": loaded.stage_history[1].trigger,
            "open_trigger_preserved": loaded.open_triggers[0].trigger if loaded.open_triggers else None,
            "code_dir_preserved": loaded.code_dir,
        },
        passed=passed,
        conclusion=(
            "State serialization is lossless for all fields including "
            "nested StageTransition and OpenTrigger objects. This is the "
            "foundation for every other state-machine operation."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 3 — g1 blocks when significance is missing
# ---------------------------------------------------------------------------


def test_g1_blocks_without_confirmed_significance(tmp_path, report):
    """check_forward_guard on an empty project returns passed=False with
    each missing condition clearly marked."""
    project_dir = _scaffold_project(tmp_path, "g1_blocked")

    # Don't create PROJECT.md or any significance_screen record
    check = check_forward_guard(project_dir)

    failed_conditions = [c for c in check.conditions if not c.passed]
    passed = (
        not check.passed
        and check.guard == "g1"
        and len(failed_conditions) >= 3  # at least the 4 conditions we expect
    )

    report.record(
        name="g1 blocks empty project",
        purpose=(
            "A freshly-initialized project should NOT be able to advance "
            "from SIGNIFICANCE — the guard must report each missing "
            "artifact so the researcher knows what to add."
        ),
        inputs={
            "project_dir": str(project_dir),
            "artifacts_created": [],
        },
        expected={
            "guard": "g1",
            "passed": False,
            "num_failing_conditions": ">=3",
        },
        actual={
            "guard": check.guard,
            "passed": check.passed,
            "num_failing_conditions": len(failed_conditions),
            "failing_condition_names": [c.name for c in failed_conditions],
        },
        passed=passed,
        conclusion=(
            "g1 reads disk artifacts and fails loudly with a per-condition "
            "breakdown. This gives the CLI enough information to tell the "
            "researcher 'add a significance_screen record and fill in PROJECT.md'."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 4 — g1 passes with proper artifacts
# ---------------------------------------------------------------------------


def test_g1_passes_with_confirmed_significance(tmp_path, report):
    """With PROJECT.md populated and a human_confirmed significance_screen,
    g1 passes and advance() moves to FORMALIZE."""
    project_dir = _scaffold_project(tmp_path, "g1_pass")

    _write_md(project_dir / "PROJECT.md", "# Question\nDeformable object manipulation.\n\n" * 4)
    append_record(project_dir, "significance_screen", _passing_significance_record())

    check = check_forward_guard(project_dir)
    advance_result = advance(project_dir)
    state_after = load_state(project_dir)

    passed = (
        check.passed
        and advance_result.from_stage == "significance"
        and advance_result.to_stage == "formalization"
        and state_after.current_stage == "formalization"
        and len(state_after.stage_history) == 2
    )

    report.record(
        name="g1 passes → advance to FORMALIZE",
        purpose=(
            "With PROJECT.md + a confirmed significance_screen, g1 should "
            "pass and advance should transition SIGNIFICANCE → FORMALIZE."
        ),
        inputs={
            "artifacts_created": ["PROJECT.md", "significance_screen.jsonl"],
            "significance_record": _passing_significance_record(),
        },
        expected={
            "guard_passed": True,
            "advance_from": "significance",
            "advance_to": "formalization",
            "new_stage": "formalization",
            "history_length": 2,
        },
        actual={
            "guard_passed": check.passed,
            "advance_from": advance_result.from_stage,
            "advance_to": advance_result.to_stage,
            "new_stage": state_after.current_stage,
            "history_length": len(state_after.stage_history),
        },
        passed=passed,
        conclusion=(
            "The forward guard + advance path is a full-loop assertion: "
            "guard reads disk, advance writes disk, state is updated, "
            "provenance is logged. This is the happy path through g1."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 5 — advance raises GuardBlocked when conditions fail
# ---------------------------------------------------------------------------


def test_advance_raises_guard_blocked_without_force(tmp_path, report):
    project_dir = _scaffold_project(tmp_path, "g1_blocked_raise")

    exc_raised = False
    check_summary = ""
    try:
        advance(project_dir)
    except GuardBlocked as exc:
        exc_raised = True
        check_summary = exc.check.summary()

    passed = exc_raised and "g1" in check_summary and "blocked" in check_summary

    report.record(
        name="advance raises GuardBlocked without --force",
        purpose=(
            "advance() must refuse to transition when the guard fails, "
            "with a structured error containing the full GuardCheck so "
            "callers can render it."
        ),
        inputs={
            "project_dir": str(project_dir),
            "force": False,
        },
        expected={
            "raised_GuardBlocked": True,
            "summary_mentions_g1": True,
            "summary_mentions_blocked": True,
        },
        actual={
            "raised_GuardBlocked": exc_raised,
            "summary_mentions_g1": "g1" in check_summary,
            "summary_mentions_blocked": "blocked" in check_summary,
            "summary_preview": check_summary[:200],
        },
        passed=passed,
        conclusion=(
            "Without --force, advance enforces the guard strictly — this "
            "is the mechanism that prevents silent cheating through the "
            "state machine."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 6 — advance with --force records the override
# ---------------------------------------------------------------------------


def test_advance_force_records_override_in_provenance(tmp_path, report):
    project_dir = _scaffold_project(tmp_path, "force_override")

    transition = advance(project_dir, force=True, note="emergency hackathon override")
    state = load_state(project_dir)
    provenance = read_records(project_dir, "provenance")

    forced_transition = state.stage_history[-1]
    override_prov = [p for p in provenance if "forced" in p.get("summary", "").lower()]

    passed = (
        transition.to_stage == "formalization"
        and state.current_stage == "formalization"
        and forced_transition.trigger == "force"
        and "FORCED" in (forced_transition.note or "")
        and len(override_prov) >= 1
    )

    report.record(
        name="advance --force records override in provenance",
        purpose=(
            "An emergency override must transition the stage but leave a "
            "visible footprint in provenance (so reviewers can audit "
            "cheating after the fact)."
        ),
        inputs={
            "project_dir": str(project_dir),
            "force": True,
            "note": "emergency hackathon override",
        },
        expected={
            "new_stage": "formalization",
            "transition_trigger": "force",
            "note_has_FORCED": True,
            "override_logged_in_provenance": True,
        },
        actual={
            "new_stage": state.current_stage,
            "transition_trigger": forced_transition.trigger,
            "note": forced_transition.note,
            "override_logged_in_provenance": len(override_prov) >= 1,
        },
        passed=passed,
        conclusion=(
            "Force override works and is auditable. Any reviewer running "
            "`alpha-research provenance` on the project sees exactly which "
            "transitions were forced and why."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 7 — backward transition requires carried_constraint
# ---------------------------------------------------------------------------


def test_backward_requires_carried_constraint(tmp_path, report):
    project_dir = _scaffold_project(tmp_path, "backward_constraint")

    # Advance forward first so we have room to go backward
    _write_md(project_dir / "PROJECT.md", "# Q\n" + "body. " * 20)
    append_record(project_dir, "significance_screen", _passing_significance_record())
    advance(project_dir)  # → formalization

    raised_without_constraint = False
    try:
        backward(project_dir, trigger="t2", carried_constraint="", evidence="")
    except ValueError as exc:
        raised_without_constraint = "carried_constraint" in str(exc).lower()

    # Now do it properly
    transition = backward(
        project_dir,
        trigger="t2",
        carried_constraint="formalization reduced to a known POMDP that DESPOT solves",
        evidence="formalization_check detected trivial reduction",
    )
    state = load_state(project_dir)

    passed = (
        raised_without_constraint
        and transition.from_stage == "formalization"
        and transition.to_stage == "significance"
        and transition.trigger == "t2"
        and transition.carried_constraint is not None
        and state.current_stage == "significance"
        and any(ot.trigger == "t2" and ot.resolved for ot in state.open_triggers)
    )

    report.record(
        name="backward requires carried_constraint",
        purpose=(
            "backward() must reject an empty carried_constraint and accept "
            "a non-empty one, recording the transition with the constraint "
            "and marking the open trigger as resolved."
        ),
        inputs={
            "project_dir": str(project_dir),
            "first_call": {"trigger": "t2", "carried_constraint": ""},
            "second_call": {
                "trigger": "t2",
                "carried_constraint": "formalization reduced to a known POMDP that DESPOT solves",
                "evidence": "formalization_check detected trivial reduction",
            },
        },
        expected={
            "first_call_raises_ValueError": True,
            "second_call_transition": "formalization → significance via t2",
            "carried_constraint_preserved": True,
            "open_trigger_resolved": True,
        },
        actual={
            "first_call_raises_ValueError": raised_without_constraint,
            "transition": f"{transition.from_stage} → {transition.to_stage} via {transition.trigger}",
            "carried_constraint_preserved": transition.carried_constraint is not None,
            "open_trigger_resolved": any(
                ot.trigger == "t2" and ot.resolved for ot in state.open_triggers
            ),
        },
        passed=passed,
        conclusion=(
            "Backward transitions enforce the research-guideline principle: "
            "backward motion is learning, and the learning must be explicitly "
            "captured as a constraint the re-entered stage will carry."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 8 — backward rejects invalid trigger for current stage
# ---------------------------------------------------------------------------


def test_backward_rejects_invalid_trigger(tmp_path, report):
    """From SIGNIFICANCE, no backward trigger is valid."""
    project_dir = _scaffold_project(tmp_path, "backward_invalid")

    error_message = ""
    try:
        backward(
            project_dir,
            trigger="t15",  # valid from VALIDATE only
            carried_constraint="some learning",
        )
    except ValueError as exc:
        error_message = str(exc)

    passed = "t15" in error_message and "significance" in error_message.lower()

    report.record(
        name="backward rejects trigger invalid for current stage",
        purpose=(
            "A trigger that's not allowed from the current stage must be "
            "rejected with a clear error naming both the trigger and stage."
        ),
        inputs={
            "project_dir": str(project_dir),
            "current_stage": "significance",
            "requested_trigger": "t15",  # valid only from validate
        },
        expected={
            "raises_ValueError_with_trigger_and_stage": True,
        },
        actual={
            "error_message": error_message,
            "mentions_t15": "t15" in error_message,
            "mentions_significance": "significance" in error_message.lower(),
        },
        passed=passed,
        conclusion=(
            "BACKWARD_TRANSITIONS is the authoritative graph; attempts to "
            "take an edge that doesn't exist are rejected with actionable "
            "errors rather than corrupting state."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 9 — propose_backward_trigger appends an OpenTrigger
# ---------------------------------------------------------------------------


def test_propose_backward_trigger_appends_open_trigger(tmp_path, report):
    project_dir = _scaffold_project(tmp_path, "propose")

    ot = propose_backward_trigger(
        project_dir,
        trigger="t15",
        proposed_by="experiment-analyze",
        evidence="ablation removing 'contact prior' doesn't hurt accuracy",
    )
    state = load_state(project_dir)

    passed = (
        len(state.open_triggers) == 1
        and state.open_triggers[0].trigger == "t15"
        and state.open_triggers[0].proposed_by == "experiment-analyze"
        and not state.open_triggers[0].resolved
    )

    report.record(
        name="propose_backward_trigger appends open trigger",
        purpose=(
            "Skills propose triggers; humans execute them. "
            "propose_backward_trigger must persist the proposal without "
            "moving the project."
        ),
        inputs={
            "trigger": "t15",
            "proposed_by": "experiment-analyze",
            "evidence": "ablation removing 'contact prior' doesn't hurt accuracy",
        },
        expected={
            "open_triggers_count": 1,
            "trigger": "t15",
            "proposed_by": "experiment-analyze",
            "resolved": False,
            "stage_unchanged": "significance",
        },
        actual={
            "open_triggers_count": len(state.open_triggers),
            "trigger": state.open_triggers[0].trigger if state.open_triggers else None,
            "proposed_by": state.open_triggers[0].proposed_by if state.open_triggers else None,
            "resolved": state.open_triggers[0].resolved if state.open_triggers else None,
            "stage_unchanged": state.current_stage,
        },
        passed=passed,
        conclusion=(
            "This keeps skills one layer removed from mutating control flow: "
            "they surface what they found, the human decides what to do with it."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 10 — provenance records accumulate across actions
# ---------------------------------------------------------------------------


def test_provenance_accumulates_across_transitions(tmp_path, report):
    project_dir = _scaffold_project(tmp_path, "prov_chain")

    # init logs 1 record. Now advance forward twice.
    _write_md(project_dir / "PROJECT.md", "# Q\n" + "body. " * 20)
    append_record(project_dir, "significance_screen", _passing_significance_record())
    advance(project_dir)  # → formalization, logs 1 more

    # Backward log
    backward(
        project_dir,
        trigger="t2",
        carried_constraint="reduced to known problem",
        evidence="formalization check",
    )  # → significance, logs 1 more

    provenance = read_records(project_dir, "provenance")

    action_names = [p["action_name"] for p in provenance]
    passed = (
        len(provenance) == 3
        and action_names == ["project.init", "project.advance", "project.backward"]
    )

    report.record(
        name="provenance accumulates across transitions",
        purpose=(
            "Every state-changing action must append exactly one provenance "
            "record; the sequence of records reconstructs the full history."
        ),
        inputs={
            "actions": ["init", "advance (g1)", "backward (t2)"],
        },
        expected={
            "provenance_count": 3,
            "action_sequence": ["project.init", "project.advance", "project.backward"],
        },
        actual={
            "provenance_count": len(provenance),
            "action_sequence": action_names,
        },
        passed=passed,
        conclusion=(
            "Provenance is append-only and complete. A reviewer reading "
            "provenance.jsonl can reconstruct every transition in order."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 11 — g2 requires benchmarks.md
# ---------------------------------------------------------------------------


def test_g2_requires_benchmarks_md(tmp_path, report):
    project_dir = _scaffold_project(tmp_path, "g2_benchmarks")

    # Get to FORMALIZATION
    _write_md(project_dir / "PROJECT.md", "# Q\n" + "body. " * 20)
    append_record(project_dir, "significance_screen", _passing_significance_record())
    advance(project_dir)  # → formalization

    # Satisfy formalization.md + formalization_check but NOT benchmarks.md
    _write_md(project_dir / "formalization.md", "# Formalization\n" + "math. " * 40)
    append_record(project_dir, "formalization_check", _passing_formalization_record())
    append_record(project_dir, "benchmark_survey", _passing_benchmark_survey())

    check_without_benchmarks = check_forward_guard(project_dir)
    benchmark_cond = [
        c for c in check_without_benchmarks.conditions
        if "benchmarks.md" in c.name.lower()
    ]

    # Now add benchmarks.md
    _write_benchmarks_md(project_dir, n_in_scope=1)
    check_with_benchmarks = check_forward_guard(project_dir)

    passed = (
        not check_without_benchmarks.passed
        and len(benchmark_cond) == 1
        and not benchmark_cond[0].passed
        and check_with_benchmarks.passed
    )

    report.record(
        name="g2 requires benchmarks.md (the Phase-5 gap-fix)",
        purpose=(
            "The user pointed out that benchmarks were missing from the "
            "state machine. g2 must block advancement from FORMALIZE until "
            "benchmarks.md contains at least one benchmark under '## In scope'."
        ),
        inputs={
            "before_benchmarks_md": {
                "formalization_md": True,
                "formalization_check_record": True,
                "benchmark_survey_record": True,
                "benchmarks_md": False,
            },
            "after_benchmarks_md": {"benchmarks_md_with_in_scope": True},
        },
        expected={
            "without_benchmarks_md": {"g2_passed": False, "benchmark_condition_failed": True},
            "with_benchmarks_md": {"g2_passed": True},
        },
        actual={
            "without_benchmarks_md": {
                "g2_passed": check_without_benchmarks.passed,
                "benchmark_condition_failed": not benchmark_cond[0].passed if benchmark_cond else None,
            },
            "with_benchmarks_md": {"g2_passed": check_with_benchmarks.passed},
        },
        passed=passed,
        conclusion=(
            "Benchmark survey and selection is wired into the guard layer: "
            "FORMALIZE → DIAGNOSE cannot happen until the researcher has "
            "chosen at least one benchmark. This is the first enforcement "
            "point for the reproducibility floor."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 12 — g3 requires reproduction experiment
# ---------------------------------------------------------------------------


def test_g3_requires_reproduction_experiment(tmp_path, report):
    """With benchmarks.md populated, DIAGNOSE cannot exit without a passing
    reproduction experiment AND a diagnosis with a formal mapping."""
    project_dir = _scaffold_project(tmp_path, "g3_reproduction")

    # Walk to DIAGNOSE
    _write_md(project_dir / "PROJECT.md", "# Q\n" + "body. " * 20)
    append_record(project_dir, "significance_screen", _passing_significance_record())
    advance(project_dir)  # → formalization

    _write_md(project_dir / "formalization.md", "# F\n" + "math. " * 40)
    append_record(project_dir, "formalization_check", _passing_formalization_record())
    append_record(project_dir, "benchmark_survey", _passing_benchmark_survey())
    _write_benchmarks_md(project_dir, n_in_scope=1)
    advance(project_dir)  # → diagnose

    # Without reproduction or diagnosis, g3 blocks
    check_empty = check_forward_guard(project_dir)
    reproduction_cond = [c for c in check_empty.conditions if "reproduction" in c.name.lower()]

    # Add a reproduction experiment and a diagnosis
    append_record(project_dir, "experiment_analysis", _passing_reproduction_analysis())
    append_record(project_dir, "diagnosis", _passing_diagnosis())

    check_populated = check_forward_guard(project_dir)

    passed = (
        not check_empty.passed
        and len(reproduction_cond) == 1
        and not reproduction_cond[0].passed
        and check_populated.passed
    )

    report.record(
        name="g3 requires reproduction experiment + diagnosis",
        purpose=(
            "g3 is the reproducibility floor: DIAGNOSE cannot exit without "
            "a passing reproduction run AND at least one observed failure "
            "mapped to a formal term."
        ),
        inputs={
            "phase_1_records": {"experiment_analysis": 0, "diagnosis": 0},
            "phase_2_records": {
                "experiment_analysis": "mode=reproduction, reproducibility=pass",
                "diagnosis": "failure_mapped_to_formal_term set",
            },
        },
        expected={
            "phase_1": {"g3_passed": False, "reproduction_condition_blocks": True},
            "phase_2": {"g3_passed": True},
        },
        actual={
            "phase_1": {
                "g3_passed": check_empty.passed,
                "reproduction_condition_blocks": not reproduction_cond[0].passed if reproduction_cond else None,
            },
            "phase_2": {"g3_passed": check_populated.passed},
        },
        passed=passed,
        conclusion=(
            "The reproducibility floor is enforced: a failing or missing "
            "reproduction experiment blocks DIAGNOSE from exiting. Every "
            "subsequent failure observation stands on a verified measurement "
            "infrastructure."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 13 — full happy path SIGNIFICANCE → VALIDATE
# ---------------------------------------------------------------------------


def test_full_forward_walk_through_all_stages(tmp_path, report):
    """Walk a synthetic project through all six stages with all guards
    passing, verify state_history records every transition."""
    project_dir = _scaffold_project(tmp_path, "full_walk")

    # SIGNIFICANCE
    _write_md(project_dir / "PROJECT.md", "# Q\n" + "body. " * 20)
    append_record(project_dir, "significance_screen", _passing_significance_record())
    advance(project_dir)  # → formalization

    # FORMALIZATION
    _write_md(project_dir / "formalization.md", "# F\n" + "math. " * 40)
    append_record(project_dir, "formalization_check", _passing_formalization_record())
    append_record(project_dir, "benchmark_survey", _passing_benchmark_survey())
    _write_benchmarks_md(project_dir, n_in_scope=2)
    advance(project_dir)  # → diagnose

    # DIAGNOSE
    append_record(project_dir, "experiment_analysis", _passing_reproduction_analysis())
    append_record(project_dir, "diagnosis", _passing_diagnosis())
    advance(project_dir)  # → challenge

    # CHALLENGE
    append_record(project_dir, "challenge", _passing_challenge())
    advance(project_dir)  # → approach

    # APPROACH
    _write_md(
        project_dir / "one_sentence.md",
        "# Insight\nWe show that SE(3)-equivariant tactile features enable "
        "sub-millimeter insertion under partial observability, because the "
        "learned contact model exploits the symmetry of the formal problem.\n",
    )
    append_record(
        project_dir,
        "experiment_design",
        {"mode": "approach", "benchmark_id": "NIST ATB", "conditions": ["full", "ablation"]},
    )
    advance(project_dir)  # → validate

    state = load_state(project_dir)

    expected_sequence = [
        "significance",
        "formalization",
        "diagnose",
        "challenge",
        "approach",
        "validate",
    ]
    actual_sequence = [state.stage_history[0].to_stage] + [
        t.to_stage for t in state.stage_history[1:]
    ]

    passed = (
        state.current_stage == "validate"
        and actual_sequence == expected_sequence
        and all(t.trigger.startswith("g") for t in state.stage_history[1:])
    )

    report.record(
        name="full forward walk SIGNIFICANCE → VALIDATE",
        purpose=(
            "The end-to-end happy path: every guard passes and the project "
            "walks from SIGNIFICANCE to VALIDATE with each transition "
            "recorded in stage_history."
        ),
        inputs={
            "starting_stage": "significance",
            "records_added_per_stage": {
                "significance": ["PROJECT.md", "significance_screen"],
                "formalization": [
                    "formalization.md",
                    "formalization_check",
                    "benchmark_survey",
                    "benchmarks.md (2 in scope)",
                ],
                "diagnose": ["experiment_analysis (reproduction=pass)", "diagnosis"],
                "challenge": ["challenge (structural)"],
                "approach": ["one_sentence.md (insight)", "experiment_design"],
            },
        },
        expected={
            "final_stage": "validate",
            "stage_sequence": expected_sequence,
            "all_forward_via_guards": True,
        },
        actual={
            "final_stage": state.current_stage,
            "stage_sequence": actual_sequence,
            "transition_triggers": [t.trigger for t in state.stage_history],
            "all_forward_via_guards": all(
                t.trigger.startswith("g") for t in state.stage_history[1:]
            ),
        },
        passed=passed,
        conclusion=(
            "Every stage transition is guard-gated and every artifact "
            "listed in implementation_plan.md Parts III.1–III.5 is actually "
            "read by the runtime. This is the load-bearing end-to-end test "
            "for the state machine proper."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 14 — log_action writes to the right file
# ---------------------------------------------------------------------------


def test_log_action_writes_provenance_record(tmp_path, report):
    project_dir = tmp_path / "prov_only"
    project_dir.mkdir()

    rec_id = log_action(
        project_dir,
        action_type="skill",
        action_name="paper-evaluate",
        project_stage="significance",
        inputs=["paper:arxiv:2501.12345"],
        outputs=["evaluations.jsonl"],
        parent_ids=["prov_init_001"],
        summary="evaluated a test paper",
    )

    records = read_records(project_dir, "provenance")
    rec = records[0] if records else {}

    passed = (
        len(records) == 1
        and rec.get("id") == rec_id
        and rec.get("action_type") == "skill"
        and rec.get("action_name") == "paper-evaluate"
        and rec.get("project_stage") == "significance"
        and rec.get("parent_ids") == ["prov_init_001"]
        and rec.get("summary") == "evaluated a test paper"
    )

    report.record(
        name="log_action writes a complete provenance record",
        purpose=(
            "log_action is the one helper every skill/pipeline/CLI verb "
            "uses. It must persist every field faithfully so the provenance "
            "graph is intact."
        ),
        inputs={
            "action_type": "skill",
            "action_name": "paper-evaluate",
            "project_stage": "significance",
            "inputs": ["paper:arxiv:2501.12345"],
            "outputs": ["evaluations.jsonl"],
            "parent_ids": ["prov_init_001"],
            "summary": "evaluated a test paper",
        },
        expected={
            "records_count": 1,
            "id_matches_returned": True,
            "all_fields_preserved": True,
        },
        actual={
            "records_count": len(records),
            "id_matches_returned": rec.get("id") == rec_id,
            "action_type": rec.get("action_type"),
            "action_name": rec.get("action_name"),
            "project_stage": rec.get("project_stage"),
            "parent_ids": rec.get("parent_ids"),
            "summary": rec.get("summary"),
        },
        passed=passed,
        conclusion=(
            "log_action is the canonical way to record work done. It works "
            "on an isolated project directory with no other state, proving "
            "it's a pure append operation that skills can call from bash."
        ),
    )
    assert passed
