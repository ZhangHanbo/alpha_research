"""Tests for the alpha_research CLI (main.py)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from alpha_research.main import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Test: CLI app has all expected commands
# ---------------------------------------------------------------------------

def test_cli_has_all_commands():
    """The Typer app should register research, review, loop, and status."""
    command_names = {cmd.name for cmd in app.registered_commands}
    assert "research" in command_names
    assert "review" in command_names
    assert "loop" in command_names
    assert "status" in command_names


# ---------------------------------------------------------------------------
# Test: research command (digest mode)
# ---------------------------------------------------------------------------

def test_research_digest_mode(tmp_path, monkeypatch):
    """research command in digest mode should call run_digest and produce output."""
    monkeypatch.chdir(tmp_path)

    mock_report = "# Digest Report\n\nSome findings here."

    with patch("alpha_research.main.KnowledgeStore") as MockStore, \
         patch("alpha_research.main.ResearchAgent") as MockAgent, \
         patch("alpha_research.main.load_constitution") as mock_load:
        mock_load.return_value = MagicMock()
        agent_instance = MockAgent.return_value
        agent_instance.run_digest = AsyncMock(return_value=mock_report)

        # Create config dir so load_constitution path resolves
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "constitution.yaml").write_text("name: test")

        result = runner.invoke(app, ["research", "mobile manipulation", "--mode", "digest"])

    assert result.exit_code == 0
    assert "Digest Report" in result.output
    assert "Saved to" in result.output
    # Check output file was created
    output_dir = tmp_path / "output" / "reports"
    assert output_dir.exists()
    report_files = list(output_dir.glob("digest_*.md"))
    assert len(report_files) == 1
    assert "Digest Report" in report_files[0].read_text()


# ---------------------------------------------------------------------------
# Test: research command (deep mode)
# ---------------------------------------------------------------------------

def test_research_deep_mode(tmp_path, monkeypatch):
    """research command in deep mode should call run_deep and produce output."""
    monkeypatch.chdir(tmp_path)

    mock_report = "# Deep Analysis\n\nDetailed paper analysis."

    with patch("alpha_research.main.KnowledgeStore") as MockStore, \
         patch("alpha_research.main.ResearchAgent") as MockAgent, \
         patch("alpha_research.main.load_constitution") as mock_load:
        mock_load.return_value = MagicMock()
        agent_instance = MockAgent.return_value
        agent_instance.run_deep = AsyncMock(return_value=mock_report)

        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "constitution.yaml").write_text("name: test")

        result = runner.invoke(app, ["research", "2401.12345", "--mode", "deep"])

    assert result.exit_code == 0
    assert "Deep Analysis" in result.output


# ---------------------------------------------------------------------------
# Test: research command (unimplemented mode)
# ---------------------------------------------------------------------------

def test_research_unimplemented_mode(tmp_path, monkeypatch):
    """research command with unsupported mode should print 'not yet implemented'."""
    monkeypatch.chdir(tmp_path)

    with patch("alpha_research.main.KnowledgeStore"), \
         patch("alpha_research.main.ResearchAgent"), \
         patch("alpha_research.main.load_constitution"):
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "constitution.yaml").write_text("name: test")

        result = runner.invoke(app, ["research", "some question", "--mode", "survey"])

    assert result.exit_code == 0
    assert "not yet implemented" in result.output.lower()


# ---------------------------------------------------------------------------
# Test: review command with mocked agent
# ---------------------------------------------------------------------------

def test_review_command(tmp_path, monkeypatch):
    """review command should read artifact file and invoke ReviewAgent."""
    monkeypatch.chdir(tmp_path)

    # Create a temp artifact file
    artifact_file = tmp_path / "artifact.md"
    artifact_file.write_text("# My Research\n\nSome content here.")

    # Without ANTHROPIC_API_KEY, the CLI falls back to outputting the prompt.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = runner.invoke(app, ["review", str(artifact_file), "--venue", "RSS"])

    assert result.exit_code == 0
    assert "Review Prompt" in result.output or "Saved to" in result.output


def test_review_command_missing_file(tmp_path, monkeypatch):
    """review command with a missing file should exit with error."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["review", "nonexistent.md"])

    assert result.exit_code == 1
    assert "not found" in result.output


# ---------------------------------------------------------------------------
# Test: status command — no active loop
# ---------------------------------------------------------------------------

def test_status_no_active_loop(tmp_path, monkeypatch):
    """status command when no blackboard exists should print 'No active loop'."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "No active loop" in result.output


# ---------------------------------------------------------------------------
# Test: status command — with existing blackboard
# ---------------------------------------------------------------------------

def test_status_with_blackboard(tmp_path, monkeypatch):
    """status command should print summary from an existing blackboard."""
    monkeypatch.chdir(tmp_path)

    from alpha_research.models.blackboard import Blackboard

    bb = Blackboard(iteration=3, max_iterations=5)
    bb_path = tmp_path / "data" / "blackboard.json"
    bb.save(bb_path)

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "Iteration: 3" in result.output
    assert "Converged: False" in result.output


# ---------------------------------------------------------------------------
# Test: output directory creation
# ---------------------------------------------------------------------------

def test_output_directory_creation(tmp_path, monkeypatch):
    """_save_report should create the output/reports directory if missing."""
    monkeypatch.chdir(tmp_path)

    from alpha_research.main import _save_report

    path = _save_report("test content", "test")
    assert path.exists()
    assert path.read_text() == "test content"
    # _OUTPUT_DIR is relative, so resolve both sides for comparison
    assert path.parent.resolve() == (tmp_path / "output" / "reports").resolve()


# ---------------------------------------------------------------------------
# Test: integration — CLI wiring connects correct components
# ---------------------------------------------------------------------------

def test_loop_command_requires_api_key(tmp_path, monkeypatch):
    """loop command without API key should exit with error."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "constitution.yaml").write_text("name: test")
    (tmp_path / "config" / "review_config.yaml").write_text("target_venue: RSS")

    result = runner.invoke(app, ["loop", "mobile manipulation"])

    assert result.exit_code == 1
    assert "requires an LLM" in result.output or "ANTHROPIC_API_KEY" in result.output


def test_loop_command_wiring(tmp_path, monkeypatch):
    """loop command should wire up all agents and call orchestrator.run_loop."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-for-wiring")

    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "constitution.yaml").write_text("name: test")
    (tmp_path / "config" / "review_config.yaml").write_text("target_venue: RSS")

    from alpha_research.models.blackboard import Blackboard

    mock_bb = Blackboard(iteration=2, max_iterations=5)

    with patch("alpha_research.main.Orchestrator") as MockOrch, \
         patch("alpha_research.main.ResearchAgent"), \
         patch("alpha_research.main.ReviewAgent"), \
         patch("alpha_research.main.MetaReviewer"), \
         patch("alpha_research.main.KnowledgeStore"), \
         patch("alpha_research.main._make_llm") as mock_llm, \
         patch("alpha_research.main.load_constitution") as mock_lc, \
         patch("alpha_research.main.load_review_config") as mock_lr:

        mock_llm.return_value = MagicMock()
        mock_lc.return_value = MagicMock()
        mock_lr_inst = MagicMock()
        mock_lr_inst.resolve_venue.return_value = "RSS"
        mock_lr.return_value = mock_lr_inst

        orch_instance = MockOrch.return_value
        orch_instance.run_loop = AsyncMock(return_value=mock_bb)

        result = runner.invoke(app, ["loop", "mobile manipulation"])

    assert result.exit_code == 0
    orch_instance.run_loop.assert_called_once()
    # Verify blackboard was saved
    bb_path = tmp_path / "data" / "blackboard.json"
    assert bb_path.exists()
