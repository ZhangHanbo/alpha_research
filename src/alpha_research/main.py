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


def _make_llm(api_key: str | None = None, model: str | None = None):
    """Create an AnthropicLLM if an API key is available, else return None."""
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    from alpha_research.llm import AnthropicLLM
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


if __name__ == "__main__":
    app()
