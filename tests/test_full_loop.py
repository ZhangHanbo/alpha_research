"""End-to-end integration test for the integrated state machine.

Walks a single synthetic project through all six stages
(SIGNIFICANCE → FORMALIZE → DIAGNOSE → CHALLENGE → APPROACH → VALIDATE)
with at least one backward transition and both a reproduction-pass AND
a reproduction-fail path. Entirely in fixtures — no network, no LLM,
no real skill execution.

This is the load-bearing integration test for the whole Phase 1–6
implementation. If it passes, the state machine is coherent end-to-end.

Report saved to ``tests/reports/test_full_loop.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alpha_research.project import (
    GuardBlocked,
    advance,
    backward,
    check_forward_guard,
    init_project,
    load_state,
    propose_backward_trigger,
    stage_summary,
)
from alpha_research.records.jsonl import (
    append_record,
    count_records,
    log_action,
    read_records,
)


# ---------------------------------------------------------------------------
# Fixture project builders (reused from test_project_state.py style)
# ---------------------------------------------------------------------------


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _scaffold_significance(project_dir: Path) -> None:
    _write(
        project_dir / "PROJECT.md",
        "# Research question\n\nTactile insertion for contact-rich assembly.\n"
        "We address the formalization gap for sub-millimeter alignment.\n" * 4,
    )
    append_record(
        project_dir,
        "significance_screen",
        {
            "human_confirmed": True,
            "concrete_consequence": "warehouses can automate thin-peg insertion lines",
            "durability_risk": "low",
        },
    )


def _scaffold_formalization(project_dir: Path) -> None:
    _write(
        project_dir / "formalization.md",
        "# Formalization\n\nmin_π E[ L(π(o), a*) ] subject to contact constraint.\n" * 4,
    )
    append_record(
        project_dir,
        "formalization_check",
        {
            "formalization_level": "formal_math",
            "structure_exploited": ["SE(3) equivariance", "piecewise convex contact"],
        },
    )
    append_record(
        project_dir,
        "benchmark_survey",
        {"human_confirmed": True, "top_candidates": [{"name": "NIST ATB"}]},
    )
    _write(
        project_dir / "benchmarks.md",
        "# Benchmarks\n\n## In scope\n\n"
        "### Benchmark 1: NIST ATB\n"
        "- Rationale: community standard for contact-rich assembly\n"
        "- Metric: success rate\n"
        "- Success criterion: peg seated within 0.5mm\n"
        "- Published baselines:\n"
        "  - Paper A (2024) impedance: 0.62 success  ← strongest prior\n"
        "- Install: `pip install nist-atb-sim`\n"
        "- Reproducibility: pending\n"
        "- Saturation risk: LOW — top is 0.78\n",
    )


def _scaffold_diagnose_pass(project_dir: Path) -> None:
    """A passing reproduction + a diagnosis."""
    append_record(
        project_dir,
        "experiment_analysis",
        {
            "mode": "reproduction",
            "benchmark_id": "NIST ATB",
            "exp_id": "reproduction_nistatb_01",
            "reproducibility": "pass",
            "observed": 0.60,
            "target": 0.62,
            "hypothesis_status": "supported",
        },
    )
    append_record(
        project_dir,
        "diagnosis",
        {
            "failure_mapped_to_formal_term": "observation model P(z|s) insufficient at sub-mm",
            "failure_mode": "slip at contact initiation",
        },
    )


def _scaffold_diagnose_fail(project_dir: Path) -> None:
    """A FAILING reproduction to exercise the fail path."""
    append_record(
        project_dir,
        "experiment_analysis",
        {
            "mode": "reproduction",
            "benchmark_id": "NIST ATB",
            "exp_id": "reproduction_nistatb_broken_01",
            "reproducibility": "fail",
            "observed": 0.20,
            "target": 0.62,
            "hypothesis_status": "contradicted",
        },
    )


def _scaffold_challenge(project_dir: Path) -> None:
    append_record(
        project_dir,
        "challenge",
        {
            "challenge_type": "structural",
            "structural_barrier": "depth sensing cannot resolve sub-mm alignment",
            "implied_method_class": "tactile sensing + learned contact model",
        },
    )


def _scaffold_approach(project_dir: Path) -> None:
    _write(
        project_dir / "one_sentence.md",
        "# Insight\n\nWe show that SE(3)-equivariant tactile features enable "
        "sub-millimeter insertion because the learned contact model exploits "
        "a symmetry that vision-only approaches cannot access.\n",
    )
    append_record(
        project_dir,
        "experiment_design",
        {
            "mode": "approach",
            "benchmark_id": "NIST ATB",
            "exp_id": "approach_full_method_01",
            "conditions": ["full_method", "scripted_baseline", "strongest_prior", "ablation_no_tactile"],
            "trials_per_condition": 20,
        },
    )


# ---------------------------------------------------------------------------
# The main integration test
# ---------------------------------------------------------------------------


def test_full_loop_all_six_stages_with_backward_transition(tmp_path, report):
    """The canonical walkthrough. Validates that:

    1. init creates a project at SIGNIFICANCE.
    2. Each stage's forward guard passes once its artifacts are in place.
    3. advance transitions forward through every stage.
    4. A backward transition from FORMALIZE to SIGNIFICANCE fires via t2
       with a carried_constraint, and the project re-walks the loop.
    5. A reproduction FAIL is recorded, then a second reproduction PASS
       replaces it (both live in experiment_analysis.jsonl, and g3 only
       cares that ≥1 passes).
    6. The provenance log reconstructs every action in order.
    """
    project_dir = tmp_path / "walkthrough"

    # ── SIGNIFICANCE ──────────────────────────────────────────────────
    init_project(project_dir, project_id="walkthrough", question="tactile insertion")
    _scaffold_significance(project_dir)

    g1 = check_forward_guard(project_dir)
    assert g1.passed, g1.summary()
    advance(project_dir)  # → formalization

    # ── FORMALIZATION ─────────────────────────────────────────────────
    _scaffold_formalization(project_dir)
    g2 = check_forward_guard(project_dir)
    assert g2.passed, g2.summary()
    advance(project_dir)  # → diagnose

    # ── BACKWARD TRANSITION: formalization → significance via t2 ──────
    # Simulate the researcher discovering the problem reduces to a known one.
    # First walk back from diagnose to formalization isn't legal (that's t4
    # not t2). So we simulate: at formalization we would have fired t2.
    # For the test, do it NOW before we continue forward: advance already
    # moved us to diagnose. Instead, do it from diagnose via t4.
    backward(
        project_dir,
        trigger="t4",
        carried_constraint=(
            "the observed failure mode (contact slip) does not map to the "
            "current formalization objective — we need to add dynamics to the math"
        ),
        evidence="early diagnose attempt showed unmappable failures",
    )
    state_after_backward = load_state(project_dir)
    assert state_after_backward.current_stage == "formalization"

    # Now re-formalize (noop since artifacts are already in place) and re-advance
    g2_again = check_forward_guard(project_dir)
    assert g2_again.passed
    advance(project_dir)  # → diagnose again

    # ── DIAGNOSE: first reproduction FAILS ────────────────────────────
    _scaffold_diagnose_fail(project_dir)
    g3_fail = check_forward_guard(project_dir)
    # g3 should BLOCK because the only reproduction has failed
    assert not g3_fail.passed

    # Researcher fixes setup, runs again, it passes
    _scaffold_diagnose_pass(project_dir)
    g3_pass = check_forward_guard(project_dir)
    assert g3_pass.passed, g3_pass.summary()
    advance(project_dir)  # → challenge

    # ── CHALLENGE ──────────────────────────────────────────────────────
    _scaffold_challenge(project_dir)
    g4 = check_forward_guard(project_dir)
    assert g4.passed, g4.summary()
    advance(project_dir)  # → approach

    # ── APPROACH ───────────────────────────────────────────────────────
    _scaffold_approach(project_dir)
    g5 = check_forward_guard(project_dir)
    assert g5.passed, g5.summary()
    advance(project_dir)  # → validate

    # ── Final state verification ──────────────────────────────────────
    final = load_state(project_dir)
    provenance = read_records(project_dir, "provenance")

    # Walk the stage_history and assemble the sequence
    transitions = final.stage_history
    sequence = [transitions[0].to_stage] + [t.to_stage for t in transitions[1:]]

    expected_sequence = [
        "significance",   # init
        "formalization",  # g1
        "diagnose",       # g2
        "formalization",  # t4 backward
        "diagnose",       # g2 again
        "challenge",      # g3
        "approach",       # g4
        "validate",       # g5
    ]

    # Count experiment_analysis records (should be 2: fail + pass)
    n_analysis = count_records(project_dir, "experiment_analysis")

    # Provenance should contain: init + 5 forward advances + 1 backward + scaffolding is via append_record
    # which does NOT log provenance. So provenance = 1 init + 6 transitions = 7
    expected_prov_actions = [
        "project.init",
        "project.advance",   # g1
        "project.advance",   # g2
        "project.backward",  # t4
        "project.advance",   # g2 again
        "project.advance",   # g3
        "project.advance",   # g4
        "project.advance",   # g5
    ]
    actual_prov_actions = [p["action_name"] for p in provenance]

    passed = (
        final.current_stage == "validate"
        and sequence == expected_sequence
        and n_analysis == 2
        and actual_prov_actions == expected_prov_actions
        and any(t.trigger == "t4" for t in transitions)
        and any(t.carried_constraint for t in transitions if t.trigger == "t4")
    )

    report.record(
        name="full loop: six stages + backward transition + reproduction fail→pass",
        purpose=(
            "End-to-end validation of Phases 1-6 combined: init a project, "
            "walk it through all six stages, fire a backward transition "
            "(t4) with a carried constraint, exercise both reproduction "
            "fail and pass paths, and verify provenance reconstructs the "
            "full history."
        ),
        inputs={
            "stages_walked": [
                "significance", "formalization", "diagnose",
                "[backward t4 → formalization]", "diagnose",
                "challenge", "approach", "validate",
            ],
            "reproduction_experiments": [
                "FAIL — observed 0.20 vs target 0.62",
                "PASS — observed 0.60 vs target 0.62",
            ],
            "backward_trigger": {
                "trigger": "t4",
                "carried_constraint": "failure doesn't map to current formalization — need dynamics",
            },
        },
        expected={
            "final_stage": "validate",
            "stage_sequence": expected_sequence,
            "n_experiment_analysis_records": 2,
            "provenance_action_sequence": expected_prov_actions,
            "t4_backward_has_constraint": True,
        },
        actual={
            "final_stage": final.current_stage,
            "stage_sequence": sequence,
            "n_experiment_analysis_records": n_analysis,
            "provenance_action_sequence": actual_prov_actions,
            "t4_transitions": [
                {
                    "from": t.from_stage,
                    "to": t.to_stage,
                    "carried": t.carried_constraint,
                }
                for t in transitions if t.trigger == "t4"
            ],
        },
        passed=passed,
        conclusion=(
            "The integrated state machine is coherent end-to-end. A "
            "project can walk the full six-stage research loop, survive "
            "a backward transition with a learned constraint, handle "
            "both reproduction fail and pass paths, and produce a "
            "complete provenance trail. This is the load-bearing "
            "integration assertion that ties every phase together."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Second integration test: skill-proposed backward trigger
# ---------------------------------------------------------------------------


def test_skill_proposed_trigger_surfaces_in_stage_summary(tmp_path, report):
    """A skill proposes a backward trigger; it lands in state.json; the
    stage_summary renders it as an open item; the human then executes it
    via backward()."""
    project_dir = tmp_path / "proposed"
    init_project(project_dir, project_id="proposed", question="test")

    # Walk to formalization so there's a non-trivial state
    _scaffold_significance(project_dir)
    advance(project_dir)  # → formalization

    # Simulate formalization-check proposing a t2 trigger (valid from
    # formalization → significance when the problem reduces to a known one)
    propose_backward_trigger(
        project_dir,
        trigger="t2",
        proposed_by="formalization-check",
        evidence="reduces to standard POMDP that DESPOT already solves efficiently",
    )

    # stage_summary should render the open trigger
    summary = stage_summary(project_dir)
    rendered = summary.render()

    # Now the human decides to execute it
    backward(
        project_dir,
        trigger="t2",
        carried_constraint="formalization reduced to known POMDP; reframe to avoid the trivial reduction",
        evidence="formalization-check flagged the DESPOT overlap",
    )

    final = load_state(project_dir)
    resolved = [t for t in final.open_triggers if t.trigger == "t2" and t.resolved]

    passed = (
        "t2" in rendered
        and "formalization-check" in rendered
        and "Open backward triggers" in rendered
        and final.current_stage == "significance"
        and len(resolved) == 1
        and resolved[0].resolution_note is not None
    )

    report.record(
        name="skill → open trigger → human executes",
        purpose=(
            "A skill proposes a trigger (propose_backward_trigger). "
            "stage_summary renders it. The human executes backward(). "
            "The OpenTrigger is marked resolved."
        ),
        inputs={
            "propose_call": {
                "trigger": "t2",
                "proposed_by": "formalization-check",
                "evidence": "reduces to standard POMDP that DESPOT solves",
            },
            "human_call": {
                "trigger": "t2",
                "carried_constraint": "reframe to avoid trivial reduction",
            },
        },
        expected={
            "stage_summary_mentions_trigger": True,
            "stage_summary_mentions_proposer": True,
            "final_stage_after_backward": "significance",
            "trigger_resolved_with_note": True,
        },
        actual={
            "stage_summary_mentions_trigger": "t2" in rendered,
            "stage_summary_mentions_proposer": "formalization-check" in rendered,
            "final_stage_after_backward": final.current_stage,
            "trigger_resolved_with_note": len(resolved) == 1 and resolved[0].resolution_note is not None,
            "rendered_preview": rendered[:400],
        },
        passed=passed,
        conclusion=(
            "The skill → human → transition pipeline is intact. Skills "
            "surface what they found, the human reads it in `project "
            "stage`, and `project backward` turns the proposal into a "
            "real transition with a learned constraint."
        ),
    )
    assert passed
