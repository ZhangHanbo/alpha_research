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
# Project lifecycle subcommands — Phase 2 of the integrated plan
# ---------------------------------------------------------------------------

project_app = typer.Typer(
    help=(
        "Project lifecycle commands. A project is a directory under "
        "output/<name>/ holding three canonical docs — PROJECT.md, "
        "DISCUSSION.md, LOGS.md — plus stage artifacts (hamming.md, "
        "formalization.md, benchmarks.md, one_sentence.md), state.json, "
        "and the JSONL record streams. See "
        "guidelines/spec/implementation_plan.md Part IV."
    )
)
app.add_typer(project_app, name="project")


@project_app.command("init")
def project_init(
    name: str = typer.Argument(..., help="Project name (directory basename)"),
    code: str = typer.Option(None, "--code", "-c", help="Absolute path to the method code directory"),
    question: str = typer.Option("", "--question", "-q", help="Primary research question"),
    venue: str = typer.Option("RSS", "--venue", help="Target venue"),
    output_dir: str = typer.Option(None, "-o", "--output", help="Parent directory (default: output/)"),
) -> None:
    """Scaffold a new project directory.

    Creates ``<parent>/<name>/`` with the three canonical docs
    (PROJECT.md, DISCUSSION.md, LOGS.md), the stage artifact templates
    (hamming.md, formalization.md, benchmarks.md, one_sentence.md),
    an initial ``state.json`` at SIGNIFICANCE stage, and the first
    provenance record. Does nothing if the directory already contains
    a ``state.json``.
    """
    from alpha_research.project import init_project
    from alpha_research.templates import scaffold_project_markdown

    parent = Path(output_dir) if output_dir else Path("output")
    project_dir = parent / name
    if (project_dir / "state.json").exists():
        typer.echo(f"Project already exists at {project_dir}", err=True)
        raise typer.Exit(code=1)

    # Initialize state first (this creates the dir + state.json + provenance).
    state = init_project(
        project_dir,
        project_id=name,
        question=question,
        code_dir=code,
        target_venue=venue,
    )
    # Then scaffold the human-owned markdown templates.
    written = scaffold_project_markdown(
        project_dir,
        project_id=name,
        question=question or "<fill in your research question>",
        created_at=state.created_at,
    )

    typer.echo(f"Project initialized: {project_dir}")
    typer.echo(f"  Stage:   {state.current_stage}")
    typer.echo(f"  Venue:   {state.target_venue}")
    if code:
        typer.echo(f"  Code:    {code}")
    typer.echo(f"  Templates written: {len(written)}")
    typer.echo("")
    typer.echo("Required docs: PROJECT.md, DISCUSSION.md, LOGS.md")
    typer.echo("Next: edit PROJECT.md + hamming.md, then run skills to")
    typer.echo("populate significance_screens.jsonl, then `project advance`.")


@project_app.command("stage")
def project_stage_cmd(
    project_dir: str = typer.Argument(None, help="Project directory (default: most recent under output/)"),
) -> None:
    """Show the current stage and forward-guard status."""
    from alpha_research.project import stage_summary

    target = _resolve_project_dir(project_dir)
    summary = stage_summary(target)
    typer.echo(summary.render())


@project_app.command("advance")
def project_advance_cmd(
    project_dir: str = typer.Argument(None, help="Project directory"),
    force: bool = typer.Option(False, "--force", help="Force advance even if the guard fails"),
    note: str = typer.Option("", "--note", help="Optional note recorded with the transition"),
) -> None:
    """Advance to the next stage if the forward guard passes."""
    from alpha_research.project import GuardBlocked, advance

    target = _resolve_project_dir(project_dir)
    try:
        transition = advance(target, force=force, note=note)
    except GuardBlocked as exc:
        typer.echo(exc.check.summary(), err=True)
        typer.echo("", err=True)
        typer.echo("Advance refused. Add the missing artifacts or pass --force (with a --note).", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"✓ advanced {transition.from_stage} → {transition.to_stage}  ({transition.trigger})")
    if transition.note:
        typer.echo(f"  note: {transition.note}")


@project_app.command("backward")
def project_backward_cmd(
    trigger: str = typer.Argument(..., help="One of t2..t15"),
    project_dir: str = typer.Argument(None, help="Project directory"),
    constraint: str = typer.Option(..., "--constraint", "-c", help="What did you learn? (mandatory)"),
    evidence: str = typer.Option("", "--evidence", "-e", help="Pointer to the record that motivated this"),
    note: str = typer.Option("", "--note", help="Extra notes"),
) -> None:
    """Execute a backward transition, recording the carried constraint."""
    from alpha_research.project import backward

    target = _resolve_project_dir(project_dir)
    try:
        transition = backward(
            target,
            trigger=trigger,
            carried_constraint=constraint,
            evidence=evidence,
            note=note,
        )
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(
        f"↩ backward {transition.from_stage} → {transition.to_stage}  "
        f"({transition.trigger})"
    )
    typer.echo(f"  carried: {transition.carried_constraint}")


@project_app.command("log")
def project_log_cmd(
    project_dir: str = typer.Argument(None, help="Project directory"),
) -> None:
    """Append a weekly log entry template to LOGS.md.

    Does NOT open $EDITOR automatically — instead, it appends the template
    and prints the path so the researcher can open it in whatever editor
    they prefer. This keeps the CLI scriptable.
    """
    from datetime import datetime, timezone

    target = _resolve_project_dir(project_dir)
    log_path = target / "LOGS.md"
    if not log_path.exists():
        typer.echo(f"No LOGS.md in {target} — run `project init` first", err=True)
        raise typer.Exit(code=1)

    week_header = datetime.now(timezone.utc).strftime("### Week of %Y-%m-%d")
    entry = (
        f"\n{week_header}\n\n"
        "- **Tried**:\n"
        "- **Expected**:\n"
        "- **Observed**:\n"
        "- **Concluded**:\n"
        "- **Next**:\n"
    )
    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(entry)
    typer.echo(f"Appended weekly template to {log_path}")
    typer.echo("Edit it in your preferred editor.")


@project_app.command("status")
def project_status_cmd(
    project_dir: str = typer.Argument(None, help="Project directory"),
) -> None:
    """Show a one-screen summary of a project.

    Includes: stage, days in stage, record counts, latest review verdict,
    open backward triggers. Safe on projects that don't have a state.json
    yet — falls back to the legacy JSONL-only ``status`` behaviour.
    """
    from alpha_research.records.jsonl import count_records, read_records, SUPPORTED_RECORD_TYPES

    target = _resolve_project_dir(project_dir)

    # Try to load state.json; if it's absent, fall back to counts only.
    state_loaded = None
    try:
        from alpha_research.project import load_state, stage_summary
        state_loaded = load_state(target)
        summary = stage_summary(target)
        typer.echo(summary.render())
        typer.echo("")
    except FileNotFoundError:
        typer.echo(f"Project: {target}  (no state.json — legacy layout)")

    for record_type in sorted(SUPPORTED_RECORD_TYPES):
        try:
            n = count_records(target, record_type)
        except Exception:
            n = 0
        if n > 0:
            typer.echo(f"  {record_type:22}: {n}")

    try:
        reviews = read_records(target, "review", limit=5)
    except Exception:
        reviews = []
    if reviews:
        latest = reviews[-1]
        verdict = latest.get("verdict", "unknown")
        typer.echo(f"\nLatest verdict: {verdict}")


def _resolve_project_dir(project_dir: str | None) -> Path:
    """Resolve an explicit project_dir or pick the most-recent under output/."""
    if project_dir:
        target = Path(project_dir)
        if not target.exists():
            typer.echo(f"No such directory: {target}", err=True)
            raise typer.Exit(code=1)
        return target

    output_root = Path("output")
    if not output_root.exists():
        typer.echo("No project specified and no output/ directory found.", err=True)
        raise typer.Exit(code=1)
    subdirs = [p for p in output_root.iterdir() if p.is_dir()]
    if not subdirs:
        typer.echo("No projects found under output/.", err=True)
        raise typer.Exit(code=1)
    return max(subdirs, key=lambda p: p.stat().st_mtime)


if __name__ == "__main__":
    app()
