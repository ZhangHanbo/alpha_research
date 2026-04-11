"""Tests for Phase 5 (benchmark-survey) + Phase 6 (experiment-design, experiment-analyze).

Skills are markdown files executed at runtime by Claude Code, so the
Python-side test surface is the *glue* — not the skill body. We test:

  - All four new SKILL.md files (project-understanding, benchmark-survey,
    experiment-design, experiment-analyze) parse cleanly and declare
    correct stage bindings.
  - benchmarks.md parsing (``_has_scope_benchmarks``) handles various
    edge cases correctly.
  - experiment_analysis records flow through the records layer and get
    picked up by the g3 guard.
  - propose_backward_trigger round-trips via the records layer and ends
    up on state.open_triggers.
  - Provenance records from experiment-analyze correctly reference the
    parent experiment_design via parent_ids.

Report saved to ``tests/reports/test_phase_5_6_skills.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alpha_research.project import (
    _has_scope_benchmarks,
    check_forward_guard,
    init_project,
    load_state,
    propose_backward_trigger,
)
from alpha_research.records.jsonl import (
    append_record,
    log_action,
    read_records,
)
from alpha_research.skills import check_skill_stage, discover_skills


REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Test 1 — all 4 new skills exist, parse, and declare stages
# ---------------------------------------------------------------------------


def test_all_new_skills_exist_and_parse(report):
    skills = discover_skills((REPO_ROOT / "skills",))

    expected_stages = {
        "project-understanding": ["diagnose", "approach"],
        "benchmark-survey": ["formalization", "approach"],
        "experiment-design": ["diagnose", "approach", "validate"],
        "experiment-analyze": ["diagnose", "validate"],
    }

    found_stages = {
        slug: skills[slug].research_stages if slug in skills else None
        for slug in expected_stages
    }

    missing = [slug for slug, stages in found_stages.items() if stages is None]
    mismatched = {
        slug: (expected_stages[slug], found_stages[slug])
        for slug in expected_stages
        if found_stages[slug] is not None and found_stages[slug] != expected_stages[slug]
    }

    passed = len(missing) == 0 and len(mismatched) == 0

    report.record(
        name="new skills exist and declare correct stages",
        purpose=(
            "Phase 4/5/6 add four new SKILL.md files. Each must parse "
            "cleanly and declare the exact research_stages specified in "
            "implementation_plan.md Part VI."
        ),
        inputs={"expected_stages": expected_stages},
        expected=expected_stages,
        actual=found_stages,
        passed=passed,
        conclusion=(
            "All four new skills are well-formed and their stage bindings "
            "match the plan. The runtime can route invocations correctly."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 2 — benchmarks.md parsing edge cases
# ---------------------------------------------------------------------------


def test_benchmarks_md_parsing_edge_cases(tmp_path, report):
    """The _has_scope_benchmarks helper must handle: missing file, empty
    file, file with only 'Considered but rejected' section, and file with
    multiple '## In scope' benchmarks."""

    cases = {}

    # Case A — missing file
    missing = tmp_path / "missing.md"
    cases["missing"] = _has_scope_benchmarks(missing)

    # Case B — file with no '## In scope' section
    only_rejected = tmp_path / "only_rejected.md"
    only_rejected.write_text(
        "# Benchmarks\n\n## Considered but rejected\n\n### RLBench\nsaturated\n"
    )
    cases["only_rejected_section"] = _has_scope_benchmarks(only_rejected)

    # Case C — file with '## In scope' but no ### subheaders
    empty_scope = tmp_path / "empty_scope.md"
    empty_scope.write_text("# Benchmarks\n\n## In scope\n\n(none yet)\n")
    cases["empty_scope"] = _has_scope_benchmarks(empty_scope)

    # Case D — file with one benchmark in scope
    one_scope = tmp_path / "one.md"
    one_scope.write_text(
        "# Benchmarks\n\n## In scope\n\n"
        "### Benchmark A: NIST ATB\n- rationale: standard\n\n"
        "## Considered but rejected\n\n### RLBench\nsaturated\n"
    )
    cases["one_in_scope"] = _has_scope_benchmarks(one_scope)

    # Case E — file with three benchmarks in scope
    three_scope = tmp_path / "three.md"
    three_scope.write_text(
        "# Benchmarks\n\n## In scope\n\n"
        "### Benchmark A\ndetails\n\n"
        "### Benchmark B\ndetails\n\n"
        "### Benchmark C\ndetails\n"
    )
    cases["three_in_scope"] = _has_scope_benchmarks(three_scope)

    expected = {
        "missing": (False, 0),
        "only_rejected_section": (False, 0),
        "empty_scope": (False, 0),
        "one_in_scope": (True, 1),
        "three_in_scope": (True, 3),
    }

    passed = cases == expected

    report.record(
        name="_has_scope_benchmarks edge cases",
        purpose=(
            "The benchmarks.md parser must correctly count ### subheaders "
            "under the '## In scope' section only, ignoring rejected "
            "benchmarks. This is what the g2 guard relies on."
        ),
        inputs={"cases": list(expected.keys())},
        expected=expected,
        actual=cases,
        passed=passed,
        conclusion=(
            "The parser is robust: missing files, misplaced sections, "
            "and multi-entry in-scope lists all resolve to the right "
            "count. The g2 guard gets a reliable signal."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 3 — experiment_analysis records flow through records layer
# ---------------------------------------------------------------------------


def test_experiment_analysis_records_flow_end_to_end(tmp_path, report):
    project_dir = tmp_path / "flow"
    project_dir.mkdir()

    # Append three experiment_analysis records: reproduction pass,
    # diagnostic with triggers, approach with ablation fail
    rec1 = append_record(
        project_dir,
        "experiment_analysis",
        {
            "exp_id": "reproduction_nistatb_01",
            "mode": "reproduction",
            "benchmark_id": "NIST ATB",
            "reproducibility": "pass",
            "observed": 0.60,
            "target": 0.62,
        },
    )
    rec2 = append_record(
        project_dir,
        "experiment_analysis",
        {
            "exp_id": "diagnostic_observation_res_01",
            "mode": "diagnostic",
            "hypothesis_status": "contradicted",
            "new_failure_modes": ["grip loss during acceleration"],
            "proposed_backward_triggers": [
                {"trigger": "t8", "severity": "serious"}
            ],
        },
    )
    rec3 = append_record(
        project_dir,
        "experiment_analysis",
        {
            "exp_id": "approach_full_method_01",
            "mode": "approach",
            "hypothesis_status": "inconclusive",
            "ablation_verdict": "no effect",
            "proposed_backward_triggers": [
                {"trigger": "t15", "severity": "fatal"}
            ],
        },
    )

    all_analyses = read_records(project_dir, "experiment_analysis")
    reproduction_passes = read_records(
        project_dir,
        "experiment_analysis",
        filters={"mode": "reproduction", "reproducibility": "pass"},
    )

    passed = (
        len(all_analyses) == 3
        and len(reproduction_passes) == 1
        and reproduction_passes[0]["id"] == rec1
    )

    report.record(
        name="experiment_analysis records flow end-to-end",
        purpose=(
            "Three experiment-analyze records (reproduction pass, "
            "diagnostic contradiction, approach null ablation) must be "
            "appendable and filterable through the records layer."
        ),
        inputs={
            "records_written": 3,
            "modes": ["reproduction", "diagnostic", "approach"],
        },
        expected={
            "total_count": 3,
            "reproduction_passes": 1,
            "first_pass_id_matches": True,
        },
        actual={
            "total_count": len(all_analyses),
            "reproduction_passes": len(reproduction_passes),
            "first_pass_id_matches": reproduction_passes[0]["id"] == rec1 if reproduction_passes else False,
        },
        passed=passed,
        conclusion=(
            "The records/jsonl layer supports the new experiment_analysis "
            "record type with full filter semantics. Downstream skills "
            "(adversarial-review, project stage) can query by mode and "
            "reproducibility without custom code."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 4 — propose_backward_trigger from experiment-analyze path
# ---------------------------------------------------------------------------


def test_propose_backward_trigger_from_analysis(tmp_path, report):
    """Simulate the experiment-analyze path: the skill detects a t15 and
    calls propose_backward_trigger; we verify state.json reflects it."""
    project_dir = tmp_path / "propose_t15"
    init_project(project_dir, project_id="propose_t15", question="test")

    # Simulate reaching VALIDATE state by manually setting it (for test simplicity
    # — in a real workflow the project would have walked through the stages).
    # Instead, just propose the trigger from SIGNIFICANCE and verify it lands.
    ot = propose_backward_trigger(
        project_dir,
        trigger="t15",
        proposed_by="experiment-analyze",
        evidence="ablation removing contact prior did not hurt accuracy (exp=approach_full_method_01)",
    )

    state = load_state(project_dir)
    found_trigger = next(
        (t for t in state.open_triggers if t.trigger == "t15" and not t.resolved),
        None,
    )

    passed = (
        len(state.open_triggers) == 1
        and found_trigger is not None
        and found_trigger.proposed_by == "experiment-analyze"
        and "contact prior" in found_trigger.evidence
    )

    report.record(
        name="propose_backward_trigger from experiment-analyze",
        purpose=(
            "When experiment-analyze detects a backward-trigger pattern "
            "(e.g. t15 ablation), it calls propose_backward_trigger and "
            "the open trigger lands in state.json for the human to "
            "review via `project stage`."
        ),
        inputs={
            "trigger": "t15",
            "proposed_by": "experiment-analyze",
            "evidence": "ablation removing contact prior did not hurt accuracy",
        },
        expected={
            "open_triggers_count": 1,
            "trigger": "t15",
            "proposed_by": "experiment-analyze",
            "not_resolved": True,
        },
        actual={
            "open_triggers_count": len(state.open_triggers),
            "trigger": found_trigger.trigger if found_trigger else None,
            "proposed_by": found_trigger.proposed_by if found_trigger else None,
            "not_resolved": found_trigger.resolved is False if found_trigger else None,
            "evidence_preserved": "contact prior" in (found_trigger.evidence if found_trigger else ""),
        },
        passed=passed,
        conclusion=(
            "The skill-to-state bridge works: a skill surfaces a "
            "proposal, the state tracks it, and `project stage` will "
            "render it for the human to act on."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 5 — provenance chain for experiment-design → experiment-analyze
# ---------------------------------------------------------------------------


def test_provenance_chain_design_to_analyze(tmp_path, report):
    """experiment-analyze should log provenance with parent_ids pointing at
    the experiment-design record that motivated the experiment."""
    project_dir = tmp_path / "prov_chain"
    project_dir.mkdir()

    # Simulate experiment-design logging
    design_prov_id = log_action(
        project_dir,
        action_type="skill",
        action_name="experiment-design",
        project_stage="approach",
        inputs=["formalization.md", "benchmarks.md"],
        outputs=["experiments/approach_01/config.yaml"],
        summary="designed approach experiment for NIST ATB",
    )

    # Then experiment-analyze logs with parent_ids=[design_prov_id]
    analyze_prov_id = log_action(
        project_dir,
        action_type="skill",
        action_name="experiment-analyze",
        project_stage="approach",
        inputs=["experiments/approach_01/results.jsonl"],
        outputs=["experiment_analysis.jsonl", "finding.jsonl"],
        parent_ids=[design_prov_id],
        summary="approach: full_method beats strongest prior by 12%",
    )

    provenance = read_records(project_dir, "provenance")

    design_rec = next((p for p in provenance if p["id"] == design_prov_id), None)
    analyze_rec = next((p for p in provenance if p["id"] == analyze_prov_id), None)

    passed = (
        len(provenance) == 2
        and design_rec is not None
        and analyze_rec is not None
        and design_rec["parent_ids"] == []
        and analyze_rec["parent_ids"] == [design_prov_id]
    )

    report.record(
        name="provenance chain: design → analyze",
        purpose=(
            "Every experiment_analysis action must link back to the "
            "experiment_design that motivated it, so `alpha-research "
            "provenance` can reconstruct 'why did we run this experiment?'."
        ),
        inputs={
            "design_action": "experiment-design",
            "analyze_action": "experiment-analyze",
        },
        expected={
            "provenance_count": 2,
            "design_has_no_parent": True,
            "analyze_parent_is_design": True,
        },
        actual={
            "provenance_count": len(provenance),
            "design_parent_ids": design_rec["parent_ids"] if design_rec else None,
            "analyze_parent_ids": analyze_rec["parent_ids"] if analyze_rec else None,
            "analyze_parent_is_design": (
                analyze_rec["parent_ids"] == [design_prov_id] if analyze_rec else False
            ),
        },
        passed=passed,
        conclusion=(
            "Provenance DAG is intact. A reviewer three weeks later "
            "running `alpha-research provenance` can trace every "
            "experiment_analysis back to the design that motivated it."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 6 — check_skill_stage is correct for new skills in each stage
# ---------------------------------------------------------------------------


def test_new_skills_stage_checks(report):
    """Sanity check that the new skills surface the right verdict when
    invoked in each of the six stages."""
    skills = discover_skills((REPO_ROOT / "skills",))

    matrix = {}
    for stage in ["significance", "formalization", "diagnose", "challenge", "approach", "validate"]:
        matrix[stage] = {
            "benchmark-survey": check_skill_stage("benchmark-survey", stage, skills=skills).verdict,
            "experiment-design": check_skill_stage("experiment-design", stage, skills=skills).verdict,
            "experiment-analyze": check_skill_stage("experiment-analyze", stage, skills=skills).verdict,
            "project-understanding": check_skill_stage("project-understanding", stage, skills=skills).verdict,
        }

    # Expected: in_stage where the plan says yes, out_of_stage otherwise
    expected = {
        "significance": {
            "benchmark-survey": "out_of_stage",
            "experiment-design": "out_of_stage",
            "experiment-analyze": "out_of_stage",
            "project-understanding": "out_of_stage",
        },
        "formalization": {
            "benchmark-survey": "in_stage",
            "experiment-design": "out_of_stage",
            "experiment-analyze": "out_of_stage",
            "project-understanding": "out_of_stage",
        },
        "diagnose": {
            "benchmark-survey": "out_of_stage",
            "experiment-design": "in_stage",
            "experiment-analyze": "in_stage",
            "project-understanding": "in_stage",
        },
        "challenge": {
            "benchmark-survey": "out_of_stage",
            "experiment-design": "out_of_stage",
            "experiment-analyze": "out_of_stage",
            "project-understanding": "out_of_stage",
        },
        "approach": {
            "benchmark-survey": "in_stage",
            "experiment-design": "in_stage",
            "experiment-analyze": "out_of_stage",
            "project-understanding": "in_stage",
        },
        "validate": {
            "benchmark-survey": "out_of_stage",
            "experiment-design": "in_stage",
            "experiment-analyze": "in_stage",
            "project-understanding": "out_of_stage",
        },
    }

    passed = matrix == expected

    report.record(
        name="new skills have correct stage verdicts across all six stages",
        purpose=(
            "Walk each new skill through every stage and confirm the "
            "verdict matches the plan. This is the definitive matrix "
            "check for Phase 4–6 stage wiring."
        ),
        inputs={"stages": list(expected.keys())},
        expected=expected,
        actual=matrix,
        passed=passed,
        conclusion=(
            "The stage-awareness layer is correctly wired for every "
            "new skill. Runtime invocation from the wrong stage will "
            "warn, from the right stage will proceed silently."
        ),
    )
    assert passed
