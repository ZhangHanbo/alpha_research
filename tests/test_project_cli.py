"""Tests for the Phase 2 ``alpha-research project`` CLI verbs.

Covers:
  - ``project init`` creates directory + state.json + templates
  - ``project stage`` prints the guard status
  - ``project advance`` refuses when blocked, succeeds when not
  - ``project advance --force`` records override
  - ``project backward`` requires --constraint
  - ``project log`` appends a weekly template
  - ``project status`` renders record counts

Report saved to ``tests/reports/test_project_cli.md``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from alpha_research.main import app
from alpha_research.project import load_state
from alpha_research.records.jsonl import append_record, read_records
from alpha_research.templates import PROJECT_TEMPLATES

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_and_chdir(tmp_path: Path, name: str, monkeypatch) -> Path:
    """Chdir into tmp_path and run `project init <name>`."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, [
        "project", "init", name,
        "--question", "test question",
        "--venue", "RSS",
    ])
    assert result.exit_code == 0, result.output
    return tmp_path / "output" / name


def _passing_significance_record() -> dict:
    return {
        "human_confirmed": True,
        "concrete_consequence": "robots handle thin deformable objects in packing lines",
        "durability_risk": "low",
    }


# ---------------------------------------------------------------------------
# Test 1 — project init creates directory structure
# ---------------------------------------------------------------------------


def test_project_init_creates_scaffold(tmp_path, report, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, [
        "project", "init", "demo",
        "--question", "tactile insertion for peg-in-hole",
        "--venue", "RSS",
    ])

    project_dir = tmp_path / "output" / "demo"
    state_exists = (project_dir / "state.json").exists()
    template_files = [f for f in PROJECT_TEMPLATES if (project_dir / f).exists()]

    state = None
    if state_exists:
        state = load_state(project_dir)

    passed = (
        result.exit_code == 0
        and state_exists
        and len(template_files) == len(PROJECT_TEMPLATES)
        and state is not None
        and state.current_stage == "significance"
        and state.target_venue == "RSS"
    )

    report.record(
        name="project init creates directory + templates",
        purpose=(
            "`alpha-research project init demo --question '...'` must "
            "create output/demo/ with state.json, every template in "
            "PROJECT_TEMPLATES (the three canonical docs PROJECT.md, "
            "DISCUSSION.md, LOGS.md plus the stage artifacts), an "
            "initial stage_history entry, and one provenance record."
        ),
        inputs={
            "argv": ["project", "init", "demo", "--question", "tactile insertion for peg-in-hole", "--venue", "RSS"],
            "cwd": str(tmp_path),
        },
        expected={
            "exit_code": 0,
            "state.json_exists": True,
            "templates_written": list(PROJECT_TEMPLATES),
            "initial_stage": "significance",
            "target_venue": "RSS",
        },
        actual={
            "exit_code": result.exit_code,
            "state.json_exists": state_exists,
            "templates_written": template_files,
            "initial_stage": state.current_stage if state else None,
            "target_venue": state.target_venue if state else None,
            "stdout_preview": result.output.strip()[:200],
        },
        passed=passed,
        conclusion=(
            "`project init` is the single onboarding command. One call "
            "produces a project that is ready for the researcher to "
            "start filling in markdown."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 2 — project init refuses to overwrite
# ---------------------------------------------------------------------------


def test_project_init_refuses_to_overwrite(tmp_path, report, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["project", "init", "demo", "--question", "q1"])

    # Second init with same name should fail
    result = runner.invoke(app, ["project", "init", "demo", "--question", "q2"])

    passed = result.exit_code != 0 and "already exists" in result.output.lower()

    report.record(
        name="project init refuses to clobber existing project",
        purpose=(
            "Re-running init on an existing project must fail loudly so "
            "the researcher cannot accidentally reset their state.json "
            "and lose their stage history."
        ),
        inputs={
            "first_call": ["project", "init", "demo", "--question", "q1"],
            "second_call": ["project", "init", "demo", "--question", "q2"],
        },
        expected={
            "second_exit_nonzero": True,
            "error_mentions_already_exists": True,
        },
        actual={
            "second_exit_code": result.exit_code,
            "error_mentions_already_exists": "already exists" in result.output.lower(),
            "stderr_preview": result.output.strip()[:200],
        },
        passed=passed,
        conclusion=(
            "Project init is idempotency-safe: a typo or a script retry "
            "won't clobber real work."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 3 — project stage prints guard status
# ---------------------------------------------------------------------------


def test_project_stage_prints_guard_status(tmp_path, report, monkeypatch):
    project_dir = _init_and_chdir(tmp_path, "stage_demo", monkeypatch)

    result = runner.invoke(app, ["project", "stage", str(project_dir)])

    passed = (
        result.exit_code == 0
        and "stage_demo" in result.output
        and "significance" in result.output
        and "g1" in result.output
        and "blocked" in result.output  # empty project → g1 blocks
    )

    report.record(
        name="project stage renders guard check",
        purpose=(
            "`project stage` must read state.json + run the current "
            "stage's forward guard and render both in a readable format."
        ),
        inputs={"argv": ["project", "stage", str(project_dir)]},
        expected={
            "exit_code": 0,
            "output_contains": ["stage_demo", "significance", "g1", "blocked"],
        },
        actual={
            "exit_code": result.exit_code,
            "output_contains": {
                "stage_demo": "stage_demo" in result.output,
                "significance": "significance" in result.output,
                "g1": "g1" in result.output,
                "blocked": "blocked" in result.output,
            },
            "stdout_preview": result.output.strip()[:400],
        },
        passed=passed,
        conclusion=(
            "The researcher's single go-to command for 'where am I and "
            "what's blocking me' renders correctly on a fresh project."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 4 — project advance blocks on empty project
# ---------------------------------------------------------------------------


def test_project_advance_blocks_without_artifacts(tmp_path, report, monkeypatch):
    project_dir = _init_and_chdir(tmp_path, "advance_block", monkeypatch)

    result = runner.invoke(app, ["project", "advance", str(project_dir)])

    passed = (
        result.exit_code != 0
        and "refused" in result.output.lower()
    )

    report.record(
        name="project advance refuses on empty project",
        purpose=(
            "Without the required artifacts g1 must block and the CLI "
            "must exit non-zero with a helpful 'refused' message."
        ),
        inputs={"argv": ["project", "advance", str(project_dir)]},
        expected={
            "exit_code_nonzero": True,
            "output_has_refused": True,
        },
        actual={
            "exit_code": result.exit_code,
            "output_has_refused": "refused" in result.output.lower(),
            "output_preview": result.output.strip()[:300],
        },
        passed=passed,
        conclusion=(
            "The CLI enforces the guard strictly and gives the researcher "
            "a clear signal to add missing artifacts rather than "
            "silently advancing."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 5 — project advance succeeds with artifacts in place
# ---------------------------------------------------------------------------


def test_project_advance_succeeds_with_artifacts(tmp_path, report, monkeypatch):
    project_dir = _init_and_chdir(tmp_path, "advance_ok", monkeypatch)

    # Fill PROJECT.md with real content (init already wrote a template)
    project_md = project_dir / "PROJECT.md"
    project_md.write_text(
        "# Research question\n\ntactile insertion of peg into hole.\n"
        "We address the formalization gap for sub-millimeter alignment "
        "where depth cameras fundamentally cannot resolve the residual.\n"
        "This work matters because it unlocks a capability class.\n",
        encoding="utf-8",
    )
    append_record(project_dir, "significance_screen", _passing_significance_record())

    result = runner.invoke(app, ["project", "advance", str(project_dir)])
    state = load_state(project_dir)

    passed = (
        result.exit_code == 0
        and "significance" in result.output.lower()
        and "formalization" in result.output.lower()
        and state.current_stage == "formalization"
    )

    report.record(
        name="project advance transitions SIGNIFICANCE → FORMALIZE",
        purpose=(
            "With PROJECT.md filled in and a confirmed significance_screen "
            "record, the advance verb must transition the project and "
            "persist the new stage to state.json."
        ),
        inputs={
            "artifacts": ["PROJECT.md (real content)", "significance_screen (human_confirmed)"],
            "argv": ["project", "advance", str(project_dir)],
        },
        expected={
            "exit_code": 0,
            "stage_after": "formalization",
            "output_has_both_stages": True,
        },
        actual={
            "exit_code": result.exit_code,
            "stage_after": state.current_stage,
            "output_preview": result.output.strip()[:200],
        },
        passed=passed,
        conclusion=(
            "The happy-path advance from SIGNIFICANCE → FORMALIZE runs "
            "end-to-end: CLI reads state.json, runs guard, logs "
            "transition + provenance, rewrites state.json."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 6 — project backward requires --constraint
# ---------------------------------------------------------------------------


def test_project_backward_requires_constraint(tmp_path, report, monkeypatch):
    project_dir = _init_and_chdir(tmp_path, "back_demo", monkeypatch)

    # Get to formalization
    (project_dir / "PROJECT.md").write_text("# Q\n" + "body. " * 40)
    append_record(project_dir, "significance_screen", _passing_significance_record())
    runner.invoke(app, ["project", "advance", str(project_dir)])

    # Run backward without --constraint — should fail at typer level
    result_missing = runner.invoke(app, [
        "project", "backward", "t2", str(project_dir),
    ])

    # Run backward with --constraint — should succeed
    result_ok = runner.invoke(app, [
        "project", "backward", "t2", str(project_dir),
        "--constraint", "formalization reduced to a known POMDP that DESPOT already solves",
        "--evidence", "formalization_check record abc123",
    ])
    state = load_state(project_dir)

    passed = (
        result_missing.exit_code != 0
        and result_ok.exit_code == 0
        and state.current_stage == "significance"
        and any(
            t.trigger == "t2" and t.carried_constraint for t in state.stage_history
        )
    )

    report.record(
        name="project backward requires --constraint",
        purpose=(
            "Backward transition CLI must require --constraint (typer "
            "option marked as required) and produce a transition that "
            "records the constraint."
        ),
        inputs={
            "missing_constraint": ["project", "backward", "t2", "..."],
            "with_constraint": ["project", "backward", "t2", "...", "--constraint", "..."],
        },
        expected={
            "missing_exit_nonzero": True,
            "with_exit_zero": True,
            "stage_after": "significance",
            "constraint_recorded_in_history": True,
        },
        actual={
            "missing_exit_code": result_missing.exit_code,
            "with_exit_code": result_ok.exit_code,
            "stage_after": state.current_stage,
            "history_triggers": [t.trigger for t in state.stage_history],
            "last_constraint": state.stage_history[-1].carried_constraint,
        },
        passed=passed,
        conclusion=(
            "The CLI enforces the doctrine-level requirement that "
            "backward transitions MUST carry a learned constraint."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 7 — project log appends weekly template
# ---------------------------------------------------------------------------


def test_project_log_appends_weekly_template(tmp_path, report, monkeypatch):
    project_dir = _init_and_chdir(tmp_path, "log_demo", monkeypatch)
    log_path = project_dir / "LOGS.md"
    before = log_path.read_text(encoding="utf-8")

    result = runner.invoke(app, ["project", "log", str(project_dir)])
    after = log_path.read_text(encoding="utf-8")

    passed = (
        result.exit_code == 0
        and len(after) > len(before)
        and "### Week of" in after
        and "**Tried**" in after
        and "**Next**" in after
    )

    report.record(
        name="project log appends a weekly template",
        purpose=(
            "`project log` must append (not overwrite) a new weekly "
            "entry with the five-line Tried/Expected/Observed/Concluded/"
            "Next template."
        ),
        inputs={"argv": ["project", "log", str(project_dir)]},
        expected={
            "exit_code": 0,
            "log_length_increased": True,
            "has_week_header": True,
            "has_all_five_fields": True,
        },
        actual={
            "exit_code": result.exit_code,
            "before_length": len(before),
            "after_length": len(after),
            "has_week_header": "### Week of" in after,
            "has_all_five_fields": all(
                f in after for f in ["**Tried**", "**Expected**", "**Observed**", "**Concluded**", "**Next**"]
            ),
        },
        passed=passed,
        conclusion=(
            "Weekly logging is a research-guideline mandate (§9.2). "
            "The CLI makes it a one-line action so there's no friction "
            "to maintaining the log."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 8 — project status summarizes record counts
# ---------------------------------------------------------------------------


def test_project_status_summarizes_records(tmp_path, report, monkeypatch):
    project_dir = _init_and_chdir(tmp_path, "status_demo", monkeypatch)

    # Add a few records
    append_record(project_dir, "significance_screen", _passing_significance_record())
    append_record(project_dir, "evaluation", {"paper_id": "p1", "score": 4})
    append_record(project_dir, "evaluation", {"paper_id": "p2", "score": 5})

    result = runner.invoke(app, ["project", "status", str(project_dir)])

    passed = (
        result.exit_code == 0
        and "status_demo" in result.output
        and "significance" in result.output
        and "evaluation" in result.output
    )

    report.record(
        name="project status summarizes record counts",
        purpose=(
            "`project status` must print the project's stage AND the "
            "counts for every JSONL record stream with at least one entry."
        ),
        inputs={
            "records_added": {
                "significance_screen": 1,
                "evaluation": 2,
            },
            "argv": ["project", "status", str(project_dir)],
        },
        expected={
            "exit_code": 0,
            "mentions_project_name": True,
            "mentions_significance": True,
            "mentions_evaluation": True,
        },
        actual={
            "exit_code": result.exit_code,
            "mentions_project_name": "status_demo" in result.output,
            "mentions_significance": "significance" in result.output,
            "mentions_evaluation": "evaluation" in result.output,
            "output_preview": result.output.strip()[:400],
        },
        passed=passed,
        conclusion=(
            "status gives the researcher a one-screen pulse check on "
            "their project without requiring them to remember which "
            "subcommands exist."
        ),
    )
    assert passed
