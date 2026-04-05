"""Method-survey pipeline.

Given a challenge record (from ``challenges.jsonl``), find the strongest
existing methods that attempt that challenge, evaluate each with the
rubric, and identify method-class gaps the project could fill.

Flow:

1. Load the challenge from ``challenges.jsonl`` via ``read_records``.
2. Build a handful of search queries from ``challenge_type`` using the
   §2.7 mapping baked into :data:`_CHALLENGE_QUERY_TEMPLATES`.
3. Search with :func:`alpha_review.apis.search_all` — merge and dedupe.
4. Take the top 3 by citation count and expand via ``s2_references`` /
   ``s2_citations`` to find influential neighbours.
5. Invoke ``paper-evaluate`` on each candidate in parallel.
6. Assemble a comparison table from the evaluation records.
7. Invoke ``identify-method-gaps`` on the comparison table.
8. Persist a ``method_survey`` record via :func:`append_record`.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from alpha_research.records.jsonl import append_record, read_records

SkillInvoker = Callable[[str, dict], Awaitable[Optional[dict]]]


# ---------------------------------------------------------------------------
# Challenge → query mapping (research_guideline §2.7 — condensed)
# ---------------------------------------------------------------------------

_CHALLENGE_QUERY_TEMPLATES: dict[str, list[str]] = {
    "structural": [
        "{name} structural method",
        "{name} formalization",
        "{name} theoretical guarantees",
    ],
    "resource_complaint": [
        "{name} data efficient",
        "{name} sample efficient",
    ],
    "absent": [
        "{name}",
    ],
}


@dataclass
class MethodSurveyResult:
    """Structured output from :func:`run_method_survey`."""

    output_dir: Path
    challenge_id: str
    methods_surveyed: int = 0
    comparison_table: list[dict] = field(default_factory=list)
    gaps_in_class: list[str] = field(default_factory=list)
    suggested_direction: str = ""
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_challenge(project_dir: Path, challenge_id: str) -> Optional[dict]:
    records = read_records(project_dir, "challenge")
    for rec in records:
        if rec.get("id") == challenge_id or rec.get("challenge_id") == challenge_id:
            return rec
    return None


def _build_queries(challenge: dict) -> list[str]:
    ctype = (challenge.get("challenge_type") or "absent").lower()
    name = challenge.get("name") or challenge.get("statement") or challenge_name_fallback(challenge)
    templates = _CHALLENGE_QUERY_TEMPLATES.get(ctype, _CHALLENGE_QUERY_TEMPLATES["absent"])
    return [tmpl.format(name=name) for tmpl in templates]


def challenge_name_fallback(challenge: dict) -> str:
    for key in ("what_is_wrong", "title", "description"):
        val = challenge.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip().split("\n", 1)[0][:80]
    return "challenge"


def _merge_search_results(batches: list[list[dict]]) -> list[dict]:
    """Deduplicate by paperId/id/title, preserving first occurrence."""
    seen: set[str] = set()
    merged: list[dict] = []
    for batch in batches:
        if not batch:
            continue
        for paper in batch:
            key = (
                paper.get("paperId")
                or paper.get("id")
                or paper.get("title", "")
            )
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(paper)
    return merged


def _top_by_citations(papers: list[dict], n: int) -> list[dict]:
    def _cites(p: dict) -> int:
        return int(p.get("citationCount") or p.get("citations") or 0)

    return sorted(papers, key=_cites, reverse=True)[:n]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_method_survey(
    challenge_id: str,
    project_dir: Path,
    max_methods: int = 15,
    skill_invoker: Optional[SkillInvoker] = None,
) -> MethodSurveyResult:
    """Survey the state of the art for the methods attempting ``challenge_id``.

    Parameters
    ----------
    challenge_id:
        ``id`` (or ``challenge_id``) field of a record in
        ``challenges.jsonl``.
    project_dir:
        Project directory containing the JSONL stores.
    max_methods:
        Upper bound on how many candidate methods we evaluate.
    skill_invoker:
        Test seam for mocking skill calls.
    """
    project_dir = Path(project_dir)
    result = MethodSurveyResult(output_dir=project_dir, challenge_id=challenge_id)

    if skill_invoker is None:
        # Same default as literature_survey — keep them in sync.
        from alpha_research.pipelines.literature_survey import _default_skill_invoker

        skill_invoker = _default_skill_invoker

    # 1. Load the challenge record.
    challenge = _load_challenge(project_dir, challenge_id)
    if challenge is None:
        result.errors.append(f"challenge {challenge_id!r} not found")
        return result

    # 2. Build queries.
    queries = _build_queries(challenge)

    # 3. Search each query via alpha_review.apis.search_all.
    try:
        from alpha_review.apis import search_all  # type: ignore
    except Exception as exc:
        result.errors.append(f"alpha_review.apis unavailable: {exc}")
        return result

    batches: list[list[dict]] = []
    for q in queries:
        try:
            raw = await asyncio.to_thread(search_all, q)
        except Exception as exc:
            result.errors.append(f"search_all({q!r}) failed: {exc}")
            continue
        if isinstance(raw, list):
            batches.append(raw)
        elif isinstance(raw, dict):
            batches.append(raw.get("results", []))

    merged = _merge_search_results(batches)
    if not merged:
        return result

    # 4. Expand the top-3 via references + citations.
    top3 = _top_by_citations(merged, 3)
    try:
        from alpha_review.apis import s2_citations, s2_references  # type: ignore
    except Exception:
        s2_references = None  # type: ignore
        s2_citations = None  # type: ignore

    expansion_batches: list[list[dict]] = []
    if s2_references is not None and s2_citations is not None:
        for paper in top3:
            pid = paper.get("paperId") or paper.get("id")
            if not pid:
                continue
            for fn in (s2_references, s2_citations):
                try:
                    raw = await asyncio.to_thread(fn, pid)
                except Exception as exc:
                    result.errors.append(f"{fn.__name__}({pid}) failed: {exc}")
                    continue
                if isinstance(raw, list):
                    expansion_batches.append(raw)

    candidates = _merge_search_results([merged, *expansion_batches])[:max_methods]

    # 5. Parallel paper-evaluate.
    async def _evaluate(paper: dict) -> Optional[dict]:
        try:
            res = await skill_invoker("paper-evaluate", {"paper": paper})
        except Exception as exc:
            result.errors.append(f"paper-evaluate failed: {exc}")
            return None
        if not isinstance(res, dict):
            return None
        res.setdefault("paper_id", paper.get("paperId") or paper.get("id"))
        res.setdefault("title", paper.get("title"))
        return res

    evaluations = [e for e in await asyncio.gather(*(_evaluate(p) for p in candidates)) if e]

    # 6. Comparison table.
    comparison_table: list[dict] = []
    for ev in evaluations:
        comparison_table.append(
            {
                "paper_id": ev.get("paper_id"),
                "title": ev.get("title"),
                "approach": ev.get("approach") or ev.get("method"),
                "scores": ev.get("rubric_scores", {}),
                "task_chain": ev.get("task_chain"),
            }
        )

    # 7. identify-method-gaps skill.
    gaps_in_class: list[str] = []
    suggested_direction = ""
    try:
        gap_res = await skill_invoker(
            "identify-method-gaps",
            {
                "challenge": challenge,
                "comparison_table": comparison_table,
            },
        )
        if isinstance(gap_res, dict):
            gaps_in_class = list(gap_res.get("gaps_in_class", []) or [])
            suggested_direction = str(gap_res.get("suggested_direction", "") or "")
    except Exception as exc:
        result.errors.append(f"identify-method-gaps failed: {exc}")

    # 8. Persist method_survey record.
    record_payload: dict[str, Any] = {
        "challenge_id": challenge_id,
        "methods_surveyed": len(comparison_table),
        "comparison_table": comparison_table,
        "gaps_in_class": gaps_in_class,
        "suggested_direction": suggested_direction,
    }
    try:
        append_record(project_dir, "method_survey", record_payload)
    except Exception as exc:
        result.errors.append(f"append_record failed: {exc}")

    result.methods_surveyed = len(comparison_table)
    result.comparison_table = comparison_table
    result.gaps_in_class = gaps_in_class
    result.suggested_direction = suggested_direction
    return result
