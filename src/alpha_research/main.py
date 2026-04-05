"""CLI entry-point for alpha_research.

Post-R6/R7 command surface (the old agent-centric commands are replaced by
pipeline-invoking and skill-invoking commands):

    alpha-research survey      <query> -o <dir>         # literature_survey pipeline
    alpha-research evaluate    <paper_id> -o <dir>      # paper-evaluate skill
    alpha-research review      <artifact> -o <dir>      # adversarial-review skill
    alpha-research significance <problem>               # significance-screen skill
    alpha-research loop        <project_dir>            # research_review_loop pipeline
    alpha-research status      [<project_dir>]          # summarize JSONL records

Project lifecycle subcommands (``alpha-research project ...``) are
unchanged — they still drive :class:`ProjectOrchestrator`, which has been
updated internally to call the new pipelines.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import typer

from alpha_research.config import load_constitution, load_review_config

app = typer.Typer(help="Alpha Research — skills-first research & review system")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OUTPUT_DIR = Path("output/reports")


def _ensure_output_dir() -> Path:
    """Create and return the default output directory."""
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return _OUTPUT_DIR


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _save_report(content: str, prefix: str) -> Path:
    """Save ``content`` to ``output/reports/<prefix>_<timestamp>.md``."""
    out_dir = _ensure_output_dir()
    path = out_dir / f"{prefix}_{_timestamp()}.md"
    path.write_text(content)
    return path


def _sanitize_query(query: str) -> str:
    """Convert a free-text query into a filesystem-safe directory name."""
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in query)
    return safe.strip().replace(" ", "_").lower()[:60] or "untitled"


def _default_skill_invoker():
    """Return a default skill_invoker that calls ``claude -p`` via subprocess.

    The default invoker is used by pipelines that need to invoke Claude Code
    skills. If the ``claude`` CLI is not on PATH, the pipelines accept a
    caller-provided mock invoker instead — the CLI tests patch this.
    """
    from alpha_research.pipelines.literature_survey import _default_skill_invoker as _d
    return _d


# ---------------------------------------------------------------------------
# Core commands — pipeline and skill driven
# ---------------------------------------------------------------------------

@app.command("survey")
def survey(
    query: str = typer.Argument(..., help="Research topic or question"),
    output_dir: str = typer.Option(
        None, "-o", "--output",
        help="Output directory (default: output/<sanitized_query>)",
    ),
    apply_rubric: bool = typer.Option(
        True, help="Apply the alpha_research rubric after alpha_review survey",
    ),
) -> None:
    """Run a full literature survey via the ``literature_survey`` pipeline.

    Internally delegates Phase A (search + scope + read loop + LaTeX write)
    to the ``alpha-review`` CLI, then Phase B applies the Appendix B rubric
    via the ``paper-evaluate`` skill on each included paper, then Phase C
    synthesizes via ``gap-analysis`` and ``frontier-mapping``.
    """
    from alpha_research.pipelines.literature_survey import run_literature_survey

    target = Path(output_dir) if output_dir else Path("output") / _sanitize_query(query)
    target.mkdir(parents=True, exist_ok=True)

    try:
        result = asyncio.run(
            run_literature_survey(
                query=query,
                output_dir=target,
                apply_rubric=apply_rubric,
            )
        )
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Error running survey: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Survey complete: {target}")
    typer.echo(f"  Papers total:    {result.papers_total}")
    typer.echo(f"  Papers included: {result.papers_included}")
    typer.echo(f"  Evaluations:     {result.evaluations_written}")
    if result.tex_path:
        typer.echo(f"  LaTeX:           {result.tex_path}")
    if result.report_path:
        typer.echo(f"  Report:          {result.report_path}")
    for err in result.errors:
        typer.echo(f"  [warn] {err}", err=True)


@app.command("evaluate")
def evaluate(
    paper_id: str = typer.Argument(..., help="ArXiv ID, DOI, or URL"),
    output_dir: str = typer.Option(
        None, "-o", "--output",
        help="Project directory for the evaluations.jsonl record",
    ),
) -> None:
    """Invoke the ``paper-evaluate`` skill on a single paper.

    Writes the structured evaluation (rubric scores B.1-B.7, task chain,
    significance assessment) as a JSONL record under
    ``<output_dir>/evaluation.jsonl``.

    Requires the ``claude`` CLI to be installed and in PATH.
    """
    target = Path(output_dir) if output_dir else _ensure_output_dir().parent / "single"
    target.mkdir(parents=True, exist_ok=True)

    # The paper-evaluate skill expects a claude -p invocation that mentions
    # the paper id. We build a prompt that will trigger keyword-discovery on
    # the skill description.
    prompt = (
        f"Use the paper-evaluate skill to evaluate the paper {paper_id}. "
        f"Write the evaluation record to {target}/evaluation.jsonl."
    )

    try:
        invoker = _default_skill_invoker()
        result = asyncio.run(invoker("paper-evaluate", {
            "paper_id": paper_id,
            "project_dir": str(target),
            "prompt": prompt,
        }))
    except FileNotFoundError:
        typer.echo(
            "Error: `claude` CLI not found. Install Claude Code "
            "(https://claude.ai/claude-code) to use the evaluate command.",
            err=True,
        )
        raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Error running evaluate: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Evaluation written to {target}/evaluation.jsonl")
    if isinstance(result, dict):
        typer.echo(json.dumps(result, indent=2, default=str))


@app.command("review")
def review(
    artifact: str = typer.Argument(..., help="Path to the artifact file (markdown, tex, or paper id)"),
    venue: str = typer.Option("RSS", help="Target venue (RSS, CoRL, IJRR, T-RO, ICRA, IROS, RA-L)"),
    output_dir: str = typer.Option(
        None, "-o", "--output",
        help="Project directory for the review.jsonl record",
    ),
    iteration: int = typer.Option(
        2, help="Iteration number (1=structural scan, 2=full review, 3+=focused re-review)",
    ),
) -> None:
    """Invoke the ``adversarial-review`` skill on an artifact.

    Runs graduated-pressure adversarial review at the target venue's standard
    with all six attack vectors. Verdict is computed mechanically via
    ``alpha_research.metrics.verdict.compute_verdict``.

    Requires the ``claude`` CLI.
    """
    target = Path(output_dir) if output_dir else _ensure_output_dir().parent / "reviews"
    target.mkdir(parents=True, exist_ok=True)

    prompt = (
        f"Use the adversarial-review skill on the artifact at {artifact}. "
        f"Target venue: {venue}. Iteration: {iteration}. "
        f"Write the review record to {target}/review.jsonl."
    )

    try:
        invoker = _default_skill_invoker()
        result = asyncio.run(invoker("adversarial-review", {
            "artifact": artifact,
            "venue": venue,
            "iteration": iteration,
            "project_dir": str(target),
            "prompt": prompt,
        }))
    except FileNotFoundError:
        typer.echo(
            "Error: `claude` CLI not found. Install Claude Code to use the review command.",
            err=True,
        )
        raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Error running review: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Review written to {target}/review.jsonl")
    if isinstance(result, dict):
        typer.echo(json.dumps(result, indent=2, default=str))


@app.command("significance")
def significance(
    problem: str = typer.Argument(..., help="The candidate research problem"),
    output_dir: str = typer.Option(
        None, "-o", "--output",
        help="Project directory for the significance_screen.jsonl record",
    ),
) -> None:
    """Invoke the ``significance-screen`` skill on a candidate problem.

    Applies the Hamming, Consequence, Durability, and Compounding tests
    from ``research_guideline.md`` §2.2. Writes a structured report as a
    JSONL record and always flags the Hamming test for human confirmation.

    Requires the ``claude`` CLI.
    """
    target = Path(output_dir) if output_dir else _ensure_output_dir().parent / "screens"
    target.mkdir(parents=True, exist_ok=True)

    prompt = (
        f"Use the significance-screen skill on the research problem: \"{problem}\". "
        f"Write the result record to {target}/significance_screen.jsonl."
    )

    try:
        invoker = _default_skill_invoker()
        result = asyncio.run(invoker("significance-screen", {
            "problem": problem,
            "project_dir": str(target),
            "prompt": prompt,
        }))
    except FileNotFoundError:
        typer.echo(
            "Error: `claude` CLI not found. Install Claude Code to use the significance command.",
            err=True,
        )
        raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Error running significance screen: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Significance screen written to {target}/significance_screen.jsonl")
    if isinstance(result, dict):
        typer.echo(json.dumps(result, indent=2, default=str))


@app.command("loop")
def loop(
    project_dir: str = typer.Argument(..., help="Project directory (must contain blackboard.json or similar)"),
    venue: str = typer.Option("RSS", help="Target venue"),
    max_iterations: int = typer.Option(5, help="Maximum loop iterations"),
) -> None:
    """Run the adversarial research-review loop via the
    ``research_review_loop`` pipeline.

    Loads the current ``ResearchArtifact`` from the project directory, then
    alternates between the ``adversarial-review`` skill and revision via
    ``paper-evaluate`` until convergence, submit-ready state, or
    ``max_iterations`` exhaustion. Verdict is computed mechanically.

    Requires the ``claude`` CLI.
    """
    from alpha_research.pipelines.research_review_loop import run_research_review_loop

    target = Path(project_dir)
    if not target.exists():
        typer.echo(f"Error: project directory not found: {project_dir}", err=True)
        raise typer.Exit(code=1)

    try:
        result = asyncio.run(
            run_research_review_loop(
                project_dir=target,
                max_iterations=max_iterations,
                venue=venue,
            )
        )
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Error in research-review loop: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Loop complete.")
    typer.echo(f"  Iterations run:      {result.iterations_run}")
    typer.echo(f"  Converged:           {result.converged}")
    typer.echo(f"  Submit-ready:        {result.submit_ready}")
    typer.echo(f"  Final verdict:       {result.final_verdict}")
    typer.echo(f"  Backward triggers:   {', '.join(result.backward_triggers_fired) or 'none'}")
    if result.stagnation_detected:
        typer.echo(f"  [warn] Stagnation detected")


@app.command("status")
def status(
    project_dir: str = typer.Argument(
        None, help="Project directory (default: most-recent under output/)",
    ),
) -> None:
    """Summarize the state of a project from its JSONL records.

    Counts evaluations, findings, reviews, and frontier snapshots under
    the project directory. If no directory is given, picks the most
    recently-modified subdirectory under ``output/``.
    """
    from alpha_research.records.jsonl import count_records, read_records, SUPPORTED_RECORD_TYPES

    target: Path | None = None
    if project_dir:
        target = Path(project_dir)
    else:
        output_root = Path("output")
        if output_root.exists():
            subdirs = [p for p in output_root.iterdir() if p.is_dir()]
            if subdirs:
                target = max(subdirs, key=lambda p: p.stat().st_mtime)

    if target is None or not target.exists():
        typer.echo("No project directory found. Run a survey or review first, or pass --output-dir.")
        return

    typer.echo(f"Project: {target}")
    for record_type in sorted(SUPPORTED_RECORD_TYPES):
        try:
            n = count_records(target, record_type)
        except Exception:
            n = 0
        if n > 0:
            typer.echo(f"  {record_type:22}: {n}")

    # If there's a review history, show the most recent verdict
    try:
        reviews = read_records(target, "review", limit=5)
    except Exception:
        reviews = []
    if reviews:
        latest = reviews[-1]
        verdict = latest.get("verdict", "unknown")
        typer.echo(f"\nLatest verdict: {verdict}")


# ---------------------------------------------------------------------------
# Project lifecycle subcommands (unchanged — use ProjectOrchestrator)
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

    if manifest.source_bindings:
        typer.echo(f"\nSource bindings:")
        for b in manifest.source_bindings:
            typer.echo(f"  [{b.binding_type.value}] {b.root_path}")

    snapshots = orch.list_snapshots(project_id)
    typer.echo(f"\nSnapshots: {len(snapshots)}")

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
    snapshot_id: str = typer.Option(None, help="Snapshot ID"),
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


# ---------------------------------------------------------------------------
# LLM helper (retained for project subcommands that need an LLM client)
# ---------------------------------------------------------------------------

def _make_llm(api_key: str | None = None, model: str | None = None):
    """Create an LLM client for the project subcommands.

    Projects use :class:`alpha_research.projects.understanding.UnderstandingAgent`
    which accepts an optional ``LLMCallable``. The core research/review
    commands do NOT go through this path — they invoke Claude Code skills
    via the ``claude`` CLI (see ``_default_skill_invoker``).
    """
    from alpha_research.llm import AnthropicLLM

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    return AnthropicLLM(api_key=key, model=model or "claude-sonnet-4-20250514")


if __name__ == "__main__":
    app()
