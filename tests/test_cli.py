"""Tests for the post-R6/R7 alpha-research CLI.

The old agent-centric CLI (``research``/``review``/``loop``) has been replaced
by skill-invoking and pipeline-driven commands:

    survey | evaluate | review | significance | loop | status

These tests verify the command surface, argument parsing, and output-directory
handling. End-to-end tests that actually hit Claude or alpha_review live in
``tests/test_integration/`` (Phase R8) and are marked ``@pytest.mark.integration``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from alpha_research.main import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Basic command surface
# ---------------------------------------------------------------------------

def test_cli_has_all_commands():
    """The CLI should expose the six post-refactor commands + project subtree."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("survey", "evaluate", "review", "significance", "loop", "status", "project"):
        assert cmd in result.output, f"missing command: {cmd}"


def test_project_subtree_exists():
    """After Phase 0 of the integrated-state-machine plan the old
    ``create/list/show/status/snapshot/resume`` subcommands are gone; the
    new ``init/stage/advance/backward/log/status`` verbs land in Phase 2.
    For now the ``project`` group just exists with a placeholder callback.
    """
    result = runner.invoke(app, ["project", "--help"])
    assert result.exit_code == 0
    # Just check the subtree is registered — no subcommands yet.
    assert "project" in result.output.lower()


# ---------------------------------------------------------------------------
# survey command
# ---------------------------------------------------------------------------

def test_survey_command_calls_pipeline(tmp_path, monkeypatch):
    """survey should delegate to run_literature_survey with the query."""
    monkeypatch.chdir(tmp_path)

    from alpha_research.pipelines.literature_survey import LiteratureSurveyResult

    fake_result = LiteratureSurveyResult(
        output_dir=tmp_path / "output" / "test_topic",
        papers_total=5,
        papers_included=3,
        evaluations_written=3,
    )
    with patch(
        "alpha_research.pipelines.literature_survey.run_literature_survey",
        new=AsyncMock(return_value=fake_result),
    ):
        result = runner.invoke(app, ["survey", "test topic", "-o", str(tmp_path / "out")])

    assert result.exit_code == 0
    assert "Survey complete" in result.output
    assert "3" in result.output  # papers_included


def test_survey_command_sanitizes_default_output_dir(tmp_path, monkeypatch):
    """Default output dir is derived from the query slug."""
    monkeypatch.chdir(tmp_path)

    from alpha_research.pipelines.literature_survey import LiteratureSurveyResult

    fake_result = LiteratureSurveyResult(output_dir=tmp_path / "output" / "some_query")
    mock_run = AsyncMock(return_value=fake_result)
    with patch(
        "alpha_research.pipelines.literature_survey.run_literature_survey",
        new=mock_run,
    ):
        result = runner.invoke(app, ["survey", "Some Query!"])

    assert result.exit_code == 0
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs["query"] == "Some Query!"
    assert "output" in str(call_kwargs["output_dir"])


def test_survey_command_propagates_errors(tmp_path, monkeypatch):
    """Pipeline exceptions bubble up as typer.Exit(1)."""
    monkeypatch.chdir(tmp_path)

    with patch(
        "alpha_research.pipelines.literature_survey.run_literature_survey",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        result = runner.invoke(app, ["survey", "q", "-o", str(tmp_path / "out")])

    assert result.exit_code == 1
    assert "boom" in result.output


# ---------------------------------------------------------------------------
# evaluate / review / significance commands (skill invocations)
# ---------------------------------------------------------------------------

def test_evaluate_command_requires_claude_cli(tmp_path, monkeypatch):
    """When `claude` CLI is missing, evaluate should report a friendly error."""
    monkeypatch.chdir(tmp_path)

    fake_invoker = AsyncMock(side_effect=FileNotFoundError("no claude"))
    with patch("alpha_research.main._default_skill_invoker", return_value=fake_invoker):
        result = runner.invoke(app, ["evaluate", "arxiv:2501.12345", "-o", str(tmp_path / "ev")])

    assert result.exit_code == 1
    assert "claude" in result.output.lower()


def test_evaluate_command_happy_path(tmp_path, monkeypatch):
    """evaluate should invoke the paper-evaluate skill and echo the result."""
    monkeypatch.chdir(tmp_path)

    fake_invoker = AsyncMock(return_value={"rubric_scores": {"B.1": 4}, "task_chain": {}})
    with patch("alpha_research.main._default_skill_invoker", return_value=fake_invoker):
        result = runner.invoke(app, ["evaluate", "arxiv:2501.12345", "-o", str(tmp_path / "ev")])

    assert result.exit_code == 0
    fake_invoker.assert_called_once()
    call_args = fake_invoker.call_args
    assert call_args.args[0] == "paper-evaluate"
    assert call_args.args[1]["paper_id"] == "arxiv:2501.12345"


def test_review_command_happy_path(tmp_path, monkeypatch):
    """review should invoke the adversarial-review skill."""
    monkeypatch.chdir(tmp_path)

    fake_invoker = AsyncMock(return_value={"verdict": "weak_reject", "findings": []})
    with patch("alpha_research.main._default_skill_invoker", return_value=fake_invoker):
        result = runner.invoke(app, ["review", "artifact.md", "--venue", "RSS", "-o", str(tmp_path / "rv")])

    assert result.exit_code == 0
    assert fake_invoker.call_args.args[0] == "adversarial-review"
    assert fake_invoker.call_args.args[1]["venue"] == "RSS"
    assert fake_invoker.call_args.args[1]["iteration"] == 2  # default


def test_significance_command_happy_path(tmp_path, monkeypatch):
    """significance should invoke the significance-screen skill."""
    monkeypatch.chdir(tmp_path)

    fake_invoker = AsyncMock(return_value={
        "hamming": {"score": 4, "human_flag": True},
        "overall_recommendation": "proceed with caveats",
    })
    with patch("alpha_research.main._default_skill_invoker", return_value=fake_invoker):
        result = runner.invoke(app, [
            "significance", "tactile manipulation of deformable objects",
            "-o", str(tmp_path / "sig"),
        ])

    assert result.exit_code == 0
    assert fake_invoker.call_args.args[0] == "significance-screen"


# ---------------------------------------------------------------------------
# loop command
# ---------------------------------------------------------------------------

def test_loop_command_missing_project_dir(tmp_path):
    """loop should fail cleanly when the project dir doesn't exist."""
    result = runner.invoke(app, ["loop", str(tmp_path / "nonexistent")])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_loop_command_happy_path(tmp_path):
    """loop should delegate to run_research_review_loop and print a summary."""
    from alpha_research.pipelines.research_review_loop import LoopResult

    fake_result = LoopResult(
        iterations_run=2,
        converged=True,
        submit_ready=False,
        final_verdict="weak_accept",
        final_findings=[],
        backward_triggers_fired=[],
        stagnation_detected=False,
    )
    project_dir = tmp_path / "proj"
    project_dir.mkdir()

    with patch(
        "alpha_research.pipelines.research_review_loop.run_research_review_loop",
        new=AsyncMock(return_value=fake_result),
    ):
        result = runner.invoke(app, ["loop", str(project_dir)])

    assert result.exit_code == 0
    assert "Converged" in result.output
    assert "weak_accept" in result.output


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------

def test_status_no_project_dir(tmp_path, monkeypatch):
    """status with no project dir and no output/ should print a friendly message."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "No project directory" in result.output or "Project" in result.output


def test_status_with_records(tmp_path):
    """status should count JSONL records in the given directory."""
    from alpha_research.records.jsonl import append_record

    append_record(tmp_path, "evaluation", {"paper_id": "p1", "rubric_scores": {}})
    append_record(tmp_path, "evaluation", {"paper_id": "p2", "rubric_scores": {}})
    append_record(tmp_path, "review", {"paper_id": "p1", "verdict": "accept"})

    result = runner.invoke(app, ["status", str(tmp_path)])
    assert result.exit_code == 0
    assert "evaluation" in result.output
    assert "2" in result.output
    assert "review" in result.output
