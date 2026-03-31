"""CLI entry-point for alpha_research.

Provides four commands:
  - research: run the research agent standalone
  - review:   run the review agent on an existing artifact
  - loop:     run the full research-review loop
  - status:   show the current blackboard state
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path

import typer

from alpha_research.agents.meta_reviewer import MetaReviewer
from alpha_research.agents.orchestrator import Orchestrator
from alpha_research.agents.research_agent import ResearchAgent
from alpha_research.agents.review_agent import ReviewAgent
from alpha_research.config import load_constitution, load_review_config
from alpha_research.knowledge.store import KnowledgeStore
from alpha_research.models.blackboard import (
    Blackboard,
    HumanAction,
    HumanDecision,
    ResearchArtifact,
)

app = typer.Typer(help="Alpha Research — multi-agent research & review system")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OUTPUT_DIR = Path("output/reports")


def _ensure_output_dir() -> Path:
    """Create and return the output directory."""
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return _OUTPUT_DIR


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _save_report(content: str, prefix: str) -> Path:
    """Save *content* to output/reports/<prefix>_<timestamp>.md."""
    out_dir = _ensure_output_dir()
    path = out_dir / f"{prefix}_{_timestamp()}.md"
    path.write_text(content)
    return path


def _make_llm(api_key: str | None = None, model: str | None = None, config: str | None = None):
    """Create an LLM client.

    Prefers llmutils (config/llm.yaml) if available, falls back to
    direct Anthropic.  Returns None if no API key and no config.
    """
    from alpha_research.llm import make_llm, AnthropicLLM

    # Try llmutils config first
    cfg_path = config or "config/llm.yaml"
    if Path(cfg_path).exists():
        try:
            return make_llm(cfg_path, model=model)
        except Exception:
            pass  # fall through to direct Anthropic

    # Direct Anthropic fallback
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    return AnthropicLLM(api_key=key, model=model or "claude-sonnet-4-20250514")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command("research")
def research(
    question: str = typer.Argument(..., help="Research question or topic"),
    mode: str = typer.Option("digest", help="Mode: digest|deep|survey|gap|frontier|direction"),
    config_dir: str = typer.Option("config", help="Path to config directory"),
    api_key: str = typer.Option(None, envvar="ANTHROPIC_API_KEY", help="Anthropic API key"),
    model: str = typer.Option(None, help="Model to use (default: claude-sonnet-4-20250514)"),
) -> None:
    """Run the research agent standalone."""
    constitution = load_constitution(str(Path(config_dir) / "constitution.yaml"))
    store = KnowledgeStore(db_path="data/knowledge.db")
    llm = _make_llm(api_key, model)
    agent = ResearchAgent(knowledge_store=store, config=constitution, llm=llm)

    if mode == "digest":
        try:
            report = asyncio.run(agent.run_digest(question))
        except Exception as exc:
            typer.echo(f"Error running digest: {exc}", err=True)
            raise typer.Exit(code=1)
        typer.echo(report)
        path = _save_report(report, "digest")
        typer.echo(f"\nSaved to {path}")

    elif mode == "deep":
        try:
            report = asyncio.run(agent.run_deep(question))
        except Exception as exc:
            typer.echo(f"Error running deep analysis: {exc}", err=True)
            raise typer.Exit(code=1)
        typer.echo(report)
        path = _save_report(report, "deep")
        typer.echo(f"\nSaved to {path}")

    else:
        typer.echo(f"Mode '{mode}' not yet implemented. Available: digest, deep")


@app.command("review")
def review(
    artifact: str = typer.Argument(..., help="Path to markdown artifact file"),
    venue: str = typer.Option("RSS", help="Target venue (e.g. RSS, ICRA, IJRR)"),
    api_key: str = typer.Option(None, envvar="ANTHROPIC_API_KEY", help="Anthropic API key"),
    model: str = typer.Option(None, help="Model to use"),
) -> None:
    """Run the review agent on an existing artifact file."""
    artifact_path = Path(artifact)
    if not artifact_path.exists():
        typer.echo(f"Error: artifact file not found: {artifact}", err=True)
        raise typer.Exit(code=1)

    content = artifact_path.read_text()

    research_artifact = ResearchArtifact(
        stage="significance",
        content=content,
    )

    llm = _make_llm(api_key, model)
    agent = ReviewAgent(venue=venue, llm=llm)

    if llm is not None:
        # Use async LLM-backed review
        try:
            rev = asyncio.run(agent.areview(artifact=research_artifact))
        except Exception as exc:
            typer.echo(f"Error running review: {exc}", err=True)
            raise typer.Exit(code=1)
        output = rev.model_dump_json(indent=2)
        typer.echo(output)
        path = _save_report(output, "review")
        typer.echo(f"\nSaved to {path}")
    else:
        # No LLM — output the prompt for manual use
        prompt = agent._build_prompt(research_artifact, iteration=1)
        output = f"# Review Prompt (set ANTHROPIC_API_KEY for LLM review)\n\n{prompt}"
        typer.echo(output)
        path = _save_report(output, "review_prompt")
        typer.echo(f"\nSaved to {path}")


@app.command("loop")
def loop(
    question: str = typer.Argument(..., help="Research question"),
    venue: str = typer.Option("RSS", help="Target venue"),
    max_iterations: int = typer.Option(5, help="Maximum loop iterations"),
    config_dir: str = typer.Option("config", help="Path to config directory"),
    api_key: str = typer.Option(None, envvar="ANTHROPIC_API_KEY", help="Anthropic API key"),
    model: str = typer.Option(None, help="Model to use"),
) -> None:
    """Run the full research-review loop."""
    llm = _make_llm(api_key, model)
    if llm is None:
        typer.echo(
            "Error: the loop command requires an LLM. "
            "Set ANTHROPIC_API_KEY or pass --api-key.",
            err=True,
        )
        raise typer.Exit(code=1)

    constitution = load_constitution(str(Path(config_dir) / "constitution.yaml"))
    review_config = load_review_config(str(Path(config_dir) / "review_config.yaml"))

    store = KnowledgeStore(db_path="data/knowledge.db")
    research_agent = ResearchAgent(knowledge_store=store, config=constitution, llm=llm)
    review_agent = ReviewAgent(venue=venue, llm=llm)
    meta_reviewer = MetaReviewer(llm=llm)

    bb = Blackboard(
        target_venue=review_config.resolve_venue(),
        max_iterations=max_iterations,
    )

    orchestrator = Orchestrator(
        research_agent=research_agent,
        review_agent=review_agent,
        meta_reviewer=meta_reviewer,
        blackboard=bb,
    )

    def human_callback(blackboard: Blackboard) -> HumanDecision | None:
        typer.echo(f"\n--- Human checkpoint (iteration {blackboard.iteration}) ---")
        if blackboard.current_review:
            typer.echo(f"Current verdict: {blackboard.current_review.verdict.value}")
            typer.echo(f"Findings: {len(blackboard.current_review.all_findings)}")
        action = input("Action [approve/force/skip]: ").strip().lower()
        if action == "approve":
            return HumanDecision(
                iteration=blackboard.iteration,
                action=HumanAction.APPROVE,
            )
        elif action == "force":
            return HumanDecision(
                iteration=blackboard.iteration,
                action=HumanAction.FORCE_ITERATION,
            )
        return None

    try:
        result = asyncio.run(
            orchestrator.run_loop(question=question, human_callback=human_callback)
        )
    except Exception as exc:
        typer.echo(f"Error in research loop: {exc}", err=True)
        raise typer.Exit(code=1)

    # Save blackboard
    bb_path = Path("data/blackboard.json")
    result.save(bb_path)
    typer.echo(f"\nBlackboard saved to {bb_path}")

    if result.artifact:
        path = _save_report(result.artifact.content, "loop")
        typer.echo(f"Final artifact saved to {path}")


@app.command("status")
def status() -> None:
    """Show current blackboard state."""
    bb_path = Path("data/blackboard.json")
    if not bb_path.exists():
        typer.echo("No active loop")
        return

    try:
        bb = Blackboard.load(bb_path)
    except Exception as exc:
        typer.echo(f"Error loading blackboard: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Iteration: {bb.iteration}")
    if bb.current_review:
        typer.echo(f"Verdict: {bb.current_review.verdict.value}")
    typer.echo(f"Reviews: {len(bb.review_history)}")
    typer.echo(f"Converged: {bb.convergence_state.converged}")
    if bb.convergence_state.converged:
        typer.echo(f"Reason: {bb.convergence_state.reason.value}")


# ---------------------------------------------------------------------------
# Project subcommands
# ---------------------------------------------------------------------------

project_app = typer.Typer(help="Project lifecycle commands")
app.add_typer(project_app, name="project")


@project_app.command("create")
def project_create(
    name: str = typer.Argument(..., help="Project name"),
    project_type: str = typer.Option("literature", help="Type: literature|codebase|hybrid"),
    question: str = typer.Option("", help="Primary research question"),
    source_path: str = typer.Option(None, help="Path to source directory or repo"),
    description: str = typer.Option("", help="Project description"),
    domain: str = typer.Option("", help="Research domain"),
    api_key: str = typer.Option(None, envvar="ANTHROPIC_API_KEY", help="Anthropic API key"),
    model: str = typer.Option(None, help="Model to use"),
) -> None:
    """Create a new research project."""
    from alpha_research.projects.orchestrator import ProjectOrchestrator

    llm = _make_llm(api_key, model)
    orch = ProjectOrchestrator(llm=llm)

    try:
        manifest = asyncio.run(orch.create_and_understand(
            name=name,
            project_type=project_type,
            primary_question=question,
            source_path=source_path,
            description=description,
            domain=domain,
        ))
    except Exception as exc:
        typer.echo(f"Error creating project: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Project created: {manifest.name}")
    typer.echo(f"  ID:   {manifest.project_id}")
    typer.echo(f"  Slug: {manifest.slug}")
    typer.echo(f"  Type: {manifest.project_type.value}")
    typer.echo(f"  Dir:  data/projects/{manifest.slug}/")


@project_app.command("list")
def project_list() -> None:
    """List all projects."""
    from alpha_research.projects.orchestrator import ProjectOrchestrator

    orch = ProjectOrchestrator()
    projects = orch.list_projects()

    if not projects:
        typer.echo("No projects found.")
        return

    typer.echo(f"{'ID':<14} {'Status':<10} {'Type':<12} {'Name'}")
    typer.echo("-" * 60)
    for m in projects:
        typer.echo(
            f"{m.project_id:<14} {m.status.value:<10} "
            f"{m.project_type.value:<12} {m.name}"
        )


@project_app.command("show")
def project_show(
    project_id: str = typer.Argument(..., help="Project ID"),
) -> None:
    """Show project details."""
    from alpha_research.projects.orchestrator import ProjectOrchestrator

    orch = ProjectOrchestrator()
    try:
        manifest, state = orch.get_project(project_id)
    except ValueError:
        typer.echo(f"Project not found: {project_id}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Name:     {manifest.name}")
    typer.echo(f"ID:       {manifest.project_id}")
    typer.echo(f"Type:     {manifest.project_type.value}")
    typer.echo(f"Status:   {manifest.status.value}")
    typer.echo(f"Question: {manifest.primary_question}")
    typer.echo(f"State:    {state.current_status.value}")
    if state.current_snapshot_id:
        typer.echo(f"Snapshot: {state.current_snapshot_id}")
    if state.last_completed_run_id:
        typer.echo(f"Last run: {state.last_completed_run_id}")

    # Show source bindings
    if manifest.source_bindings:
        typer.echo(f"\nSource bindings:")
        for b in manifest.source_bindings:
            typer.echo(f"  [{b.binding_type.value}] {b.root_path}")

    # Show snapshots count
    snapshots = orch.list_snapshots(project_id)
    typer.echo(f"\nSnapshots: {len(snapshots)}")

    # Show runs count
    runs = orch.list_runs(project_id)
    typer.echo(f"Runs:      {len(runs)}")


@project_app.command("status")
def project_status(
    project_id: str = typer.Argument(..., help="Project ID"),
) -> None:
    """Show project operational status."""
    from alpha_research.projects.orchestrator import ProjectOrchestrator

    orch = ProjectOrchestrator()
    try:
        _, state = orch.get_project(project_id)
    except ValueError:
        typer.echo(f"Project not found: {project_id}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Status:   {state.current_status.value}")
    typer.echo(f"Resume:   {'required' if state.resume_required else 'not required'}")
    typer.echo(f"Changed:  {'yes' if state.source_changed_since_last_snapshot else 'no'}")
    if state.active_run_id:
        typer.echo(f"Active:   {state.active_run_id}")
    if state.last_completed_run_id:
        typer.echo(f"Last run: {state.last_completed_run_id}")
    if state.last_resumed_at:
        typer.echo(f"Resumed:  {state.last_resumed_at}")


@project_app.command("snapshot")
def project_snapshot(
    project_id: str = typer.Argument(..., help="Project ID"),
    note: str = typer.Option("", help="Snapshot note"),
    milestone: bool = typer.Option(False, help="Mark as milestone"),
    milestone_name: str = typer.Option(None, help="Milestone name (for git tag)"),
) -> None:
    """Create a manual project snapshot."""
    from alpha_research.projects.orchestrator import ProjectOrchestrator

    orch = ProjectOrchestrator()
    try:
        snap = asyncio.run(orch.create_manual_snapshot(
            project_id,
            note=note,
            milestone=milestone,
            milestone_name=milestone_name,
        ))
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)

    kind = snap.snapshot_kind.value
    typer.echo(f"Snapshot created: {snap.snapshot_id} ({kind})")
    if note:
        typer.echo(f"  Note: {note}")


@project_app.command("resume")
def project_resume(
    project_id: str = typer.Argument(..., help="Project ID"),
    mode: str = typer.Option("current_workspace", help="Mode: current_workspace|exact_snapshot|milestone"),
    snapshot_id: str = typer.Option(None, help="Snapshot ID (for exact_snapshot/milestone mode)"),
    api_key: str = typer.Option(None, envvar="ANTHROPIC_API_KEY", help="Anthropic API key"),
    model: str = typer.Option(None, help="Model to use"),
) -> None:
    """Resume a project."""
    from alpha_research.projects.orchestrator import ProjectOrchestrator

    llm = _make_llm(api_key, model)
    orch = ProjectOrchestrator(llm=llm)

    try:
        state = asyncio.run(orch.resume_and_continue(
            project_id, mode=mode, snapshot_id=snapshot_id,
        ))
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    except Exception as exc:
        typer.echo(f"Error resuming: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Project resumed successfully.")
    typer.echo(f"  Status:   {state.current_status.value}")
    typer.echo(f"  Snapshot: {state.current_snapshot_id}")


if __name__ == "__main__":
    app()
