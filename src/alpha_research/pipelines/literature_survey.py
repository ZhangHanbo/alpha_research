"""Literature-survey pipeline.

Three-phase orchestration:

**Phase A — delegate to alpha_review.** Run the ``alpha-review`` CLI on the
user query to produce a grounded LaTeX survey, a BibTeX file, and a
SQLite-backed :class:`alpha_review.models.ReviewState`. This phase does
all of the search, scoring, and draft synthesis for us.

**Phase B — apply the alpha_research rubric.** For every included paper in
the ReviewState, invoke the ``paper-evaluate`` skill to score the paper
against Appendix B of the research guideline. Results are appended to
``evaluations.jsonl`` via :func:`alpha_research.records.jsonl.append_record`.

**Phase C — synthesize.** Call the ``gap-analysis`` skill over the
aggregated evaluations, then run :func:`run_frontier_mapping` to produce
a capability-tier map, and finally write ``alpha_research_report.md`` as
the synthesis artifact.

Every skill invocation goes through an injected ``skill_invoker`` callable
so tests can supply a mock. The production default calls
:func:`alpha_review.llm.claude_call` with a prompt that names the target
skill; Claude Code's skill matcher then picks up the correct SKILL.md.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from alpha_research.records.jsonl import append_record

SkillInvoker = Callable[[str, dict], Awaitable[Optional[dict]]]


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class LiteratureSurveyResult:
    """Structured result from :func:`run_literature_survey`."""

    output_dir: Path
    tex_path: Optional[Path] = None
    bib_path: Optional[Path] = None
    pdf_path: Optional[Path] = None
    report_path: Optional[Path] = None
    papers_total: int = 0
    papers_included: int = 0
    evaluations_written: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Default skill invoker
# ---------------------------------------------------------------------------

async def _default_skill_invoker(skill_name: str, inputs: dict) -> Optional[dict]:
    """Default production skill invoker using ``alpha_review.llm.claude_call``.

    Builds a short instruction that names the target skill; Claude Code's
    skill matcher is expected to pick up the correct ``SKILL.md`` from
    the project's ``.claude/skills/`` directory. Tests should always
    supply their own mock instead of relying on this path.
    """
    try:
        from alpha_review.llm import claude_call  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised via tests using mocks
        raise RuntimeError(
            "alpha_review.llm.claude_call is required when no skill_invoker "
            "is provided"
        ) from exc

    prompt = (
        f"Use the `{skill_name}` skill on the following JSON input and "
        f"return a JSON result.\n\n{json.dumps(inputs, default=str)}"
    )
    raw = await asyncio.to_thread(claude_call, prompt)
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {"raw": raw}


# ---------------------------------------------------------------------------
# Phase helpers
# ---------------------------------------------------------------------------

def _run_alpha_review_cli(query: str, output_dir: Path) -> tuple[bool, str]:
    """Phase A: invoke ``alpha-review`` CLI, return (success, stderr)."""
    try:
        completed = subprocess.run(
            ["alpha-review", query, "-o", str(output_dir), "--yes"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        return False, f"alpha-review CLI not found: {exc}"
    except Exception as exc:  # pragma: no cover
        return False, f"alpha-review CLI failed: {exc}"

    if completed.returncode != 0:
        return False, completed.stderr or "alpha-review exited non-zero"
    return True, completed.stdout or ""


def _load_included_papers(output_dir: Path) -> list[dict]:
    """Load included papers from the alpha_review SQLite store.

    Returns a list of plain dict payloads so that the pipeline remains
    decoupled from the alpha_review dataclass layout for downstream tests.
    """
    try:
        from alpha_review.models import PaperStatus, ReviewState  # type: ignore
    except Exception:
        return []

    db_path = output_dir / "review.db"
    if not db_path.exists():
        return []

    state = ReviewState(db_path)
    try:
        state.load()
        papers: list[dict] = []
        for paper in getattr(state, "papers", {}).values():
            status = getattr(paper, "status", None)
            if status == PaperStatus.INCLUDED:
                papers.append(
                    {
                        "id": paper.id,
                        "title": paper.title,
                        "authors": list(paper.authors),
                        "year": paper.year,
                        "venue": paper.venue,
                        "abstract": paper.abstract,
                        "url": paper.url,
                        "doi": paper.doi,
                    }
                )
        return papers
    finally:
        close = getattr(state, "close", None)
        if callable(close):
            try:
                close()
            except Exception:  # pragma: no cover
                pass


async def _evaluate_papers(
    papers: list[dict],
    project_dir: Path,
    skill_invoker: SkillInvoker,
    parallel_evaluations: int,
) -> tuple[int, list[dict], list[str]]:
    """Phase B: run paper-evaluate in parallel, persist to evaluations.jsonl."""
    semaphore = asyncio.Semaphore(max(1, parallel_evaluations))
    errors: list[str] = []
    evaluations: list[dict] = []

    async def _eval_one(paper: dict) -> Optional[dict]:
        async with semaphore:
            try:
                result = await skill_invoker("paper-evaluate", {"paper": paper})
            except Exception as exc:
                errors.append(f"paper-evaluate failed for {paper.get('id')}: {exc}")
                return None
            if not isinstance(result, dict):
                return None
            # Stamp with paper identity for downstream consumers
            result.setdefault("paper_id", paper.get("id"))
            result.setdefault("title", paper.get("title"))
            return result

    raw_results = await asyncio.gather(*(_eval_one(p) for p in papers))
    written = 0
    for res in raw_results:
        if res is None:
            continue
        try:
            append_record(project_dir, "evaluation", res)
            evaluations.append(res)
            written += 1
        except Exception as exc:
            errors.append(f"append_record failed: {exc}")
    return written, evaluations, errors


async def _synthesize(
    project_dir: Path,
    query: str,
    evaluations: list[dict],
    skill_invoker: SkillInvoker,
) -> tuple[Optional[Path], list[str]]:
    """Phase C: gap-analysis + frontier mapping + write report."""
    errors: list[str] = []

    # Gap analysis
    gap_result: dict[str, Any] = {}
    try:
        res = await skill_invoker(
            "gap-analysis",
            {"evaluations": evaluations, "query": query},
        )
        if isinstance(res, dict):
            gap_result = res
    except Exception as exc:
        errors.append(f"gap-analysis failed: {exc}")

    # Frontier mapping (lazy import to avoid a circular dependency)
    frontier_payload: dict[str, Any] = {}
    try:
        from alpha_research.pipelines.frontier_mapping import run_frontier_mapping

        report = await run_frontier_mapping(
            project_dir=project_dir,
            domain=query,
            skill_invoker=skill_invoker,
        )
        frontier_payload = {
            "reliable": report.reliable,
            "sometimes": report.sometimes,
            "cant_yet": report.cant_yet,
            "shifts_since_last": report.shifts_since_last,
        }
    except Exception as exc:
        errors.append(f"frontier-mapping failed: {exc}")

    # Write the synthesis report
    report_path = project_dir / "alpha_research_report.md"
    lines: list[str] = [
        f"# Alpha Research Report: {query}",
        "",
        f"- Papers evaluated: **{len(evaluations)}**",
        "",
        "## Gap analysis",
        "",
        "```json",
        json.dumps(gap_result, indent=2, default=str),
        "```",
        "",
        "## Capability frontier",
        "",
        "```json",
        json.dumps(frontier_payload, indent=2, default=str),
        "```",
        "",
    ]
    try:
        project_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines), encoding="utf-8")
    except Exception as exc:
        errors.append(f"report write failed: {exc}")
        return None, errors

    return report_path, errors


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_literature_survey(
    query: str,
    output_dir: Path,
    apply_rubric: bool = True,
    parallel_evaluations: int = 4,
    skill_invoker: Optional[SkillInvoker] = None,
) -> LiteratureSurveyResult:
    """Orchestrate a full literature survey for ``query``.

    Parameters
    ----------
    query:
        Natural-language research topic.
    output_dir:
        Directory where alpha_review artifacts and rubric outputs live.
    apply_rubric:
        If ``False``, skip Phase B (paper-evaluate) and Phase C (synthesis).
    parallel_evaluations:
        Max number of concurrent ``paper-evaluate`` skill invocations.
    skill_invoker:
        Async callable ``(skill_name, inputs) -> dict | None``. Tests must
        supply a mock; production uses :func:`_default_skill_invoker`.
    """
    output_dir = Path(output_dir)
    invoker: SkillInvoker = skill_invoker or _default_skill_invoker
    result = LiteratureSurveyResult(output_dir=output_dir)

    # --- Phase A: alpha-review CLI -----------------------------------------
    ok, detail = _run_alpha_review_cli(query, output_dir)
    if not ok:
        result.errors.append(detail)
        return result

    # Verify expected outputs
    tex = output_dir / "review_grounded.tex"
    if tex.exists():
        result.tex_path = tex
    else:
        result.errors.append("alpha-review did not produce review_grounded.tex")
        # Phase A "succeeded" per CLI but outputs missing — bail early.
        return result

    bib = output_dir / "references.bib"
    if bib.exists():
        result.bib_path = bib
    pdf = output_dir / "review_grounded.pdf"
    if pdf.exists():
        result.pdf_path = pdf

    # --- Phase B: rubric application ---------------------------------------
    if not apply_rubric:
        return result

    papers = _load_included_papers(output_dir)
    result.papers_total = len(papers)
    result.papers_included = len(papers)
    if not papers:
        return result

    written, evaluations, phase_b_errors = await _evaluate_papers(
        papers,
        project_dir=output_dir,
        skill_invoker=invoker,
        parallel_evaluations=parallel_evaluations,
    )
    result.evaluations_written = written
    result.errors.extend(phase_b_errors)

    # --- Phase C: synthesis ------------------------------------------------
    report_path, phase_c_errors = await _synthesize(
        project_dir=output_dir,
        query=query,
        evaluations=evaluations,
        skill_invoker=invoker,
    )
    result.report_path = report_path
    result.errors.extend(phase_c_errors)

    return result
