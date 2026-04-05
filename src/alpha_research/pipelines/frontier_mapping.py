"""Frontier-mapping pipeline.

Aggregates per-paper evaluations in a project into a 3-tier capability
frontier:

- **reliable** — capability works consistently (``tier == "reliable"``)
- **sometimes** — capability works in constrained conditions
- **cant_yet** — capability does not yet work

The pipeline also diffs the new snapshot against the previous ``frontier``
record in the project (if any) and reports any capabilities that moved
between tiers.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from alpha_research.records.jsonl import append_record, read_records

SkillInvoker = Callable[[str, dict], Awaitable[Optional[dict]]]

TIERS: tuple[str, ...] = ("reliable", "sometimes", "cant_yet")


@dataclass
class FrontierReport:
    """Structured output from :func:`run_frontier_mapping`."""

    domain: str
    reliable: list[dict] = field(default_factory=list)
    sometimes: list[dict] = field(default_factory=list)
    cant_yet: list[dict] = field(default_factory=list)
    shifts_since_last: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _domain_matches(evaluation: dict, domain: str) -> bool:
    """Return True if the evaluation mentions any significant word of ``domain``.

    Empty or whitespace-only ``domain`` matches everything. Otherwise, splits
    ``domain`` into words and returns True when at least one word (≥ 3 chars,
    not a stopword) appears in any of: ``task_chain.task``, title, abstract,
    or ``domain`` field — case-insensitive.

    Word-level matching is used instead of substring matching so that a
    survey query like "robot grasp" matches a paper whose task is phrased
    as "robot grasping" (shared word "robot"). Pure substring match would
    miss this.
    """
    needle = (domain or "").lower().strip()
    if not needle:
        return True

    _STOPWORDS = {
        "a", "an", "the", "of", "in", "on", "for", "to", "and", "with",
        "is", "are", "by", "at", "from", "or",
    }
    query_words = {
        w for w in needle.split()
        if len(w) >= 3 and w not in _STOPWORDS
    }
    if not query_words:
        # All query words filtered out — match everything to be safe.
        return True

    haystacks: list[str] = []
    chain = evaluation.get("task_chain") or {}
    if isinstance(chain, dict):
        task = chain.get("task")
        if isinstance(task, str):
            haystacks.append(task)
    for key in ("title", "abstract", "domain"):
        val = evaluation.get(key)
        if isinstance(val, str):
            haystacks.append(val)

    combined = " ".join(haystacks).lower()
    return any(word in combined for word in query_words)


def _normalize_tier(tier: Optional[str]) -> Optional[str]:
    if not tier:
        return None
    t = tier.strip().lower().replace("-", "_").replace(" ", "_")
    if t in TIERS:
        return t
    # Accept some common synonyms
    if t in {"works", "ok", "reliably"}:
        return "reliable"
    if t in {"partial", "limited", "sometimes_works"}:
        return "sometimes"
    if t in {"cannot", "fails", "broken", "not_yet"}:
        return "cant_yet"
    return None


def _capability_key(entry: dict) -> str:
    return (
        entry.get("capability")
        or entry.get("title")
        or entry.get("paper_id")
        or ""
    )


def _diff_tiers(previous: dict, current: dict) -> list[dict]:
    """Compare capability → tier mappings and return movement records."""
    shifts: list[dict] = []
    all_caps = set(previous.keys()) | set(current.keys())
    for cap in all_caps:
        prev_tier = previous.get(cap)
        curr_tier = current.get(cap)
        if prev_tier != curr_tier:
            shifts.append(
                {
                    "capability": cap,
                    "from": prev_tier,
                    "to": curr_tier,
                }
            )
    return shifts


async def run_frontier_mapping(
    project_dir: Path,
    domain: str,
    skill_invoker: Optional[SkillInvoker] = None,
) -> FrontierReport:
    """Build a capability-frontier snapshot for ``domain``.

    Every evaluation in the project that mentions ``domain`` is fed to
    the ``classify-capability`` skill. The skill is expected to return a
    dict with keys ``tier`` (one of :data:`TIERS`) and ``capability``
    (a short human-readable label).
    """
    project_dir = Path(project_dir)
    report = FrontierReport(domain=domain)

    if skill_invoker is None:
        from alpha_research.pipelines.literature_survey import _default_skill_invoker

        skill_invoker = _default_skill_invoker

    # 1. Load evaluations touching this domain.
    try:
        evaluations = read_records(project_dir, "evaluation")
    except Exception as exc:
        report.errors.append(f"read_records(evaluation) failed: {exc}")
        return report
    evaluations = [e for e in evaluations if _domain_matches(e, domain)]

    # 2. classify each evaluation.
    current_map: dict[str, str] = {}
    for ev in evaluations:
        try:
            res = await skill_invoker("classify-capability", {"evaluation": ev})
        except Exception as exc:
            report.errors.append(f"classify-capability failed: {exc}")
            continue
        if not isinstance(res, dict):
            continue
        tier = _normalize_tier(res.get("tier"))
        if tier is None:
            continue
        capability = (
            res.get("capability")
            or ev.get("title")
            or ev.get("paper_id")
            or "unknown"
        )
        entry = {
            "capability": capability,
            "paper_id": ev.get("paper_id") or ev.get("id"),
            "title": ev.get("title"),
            "justification": res.get("justification", ""),
        }
        if tier == "reliable":
            report.reliable.append(entry)
        elif tier == "sometimes":
            report.sometimes.append(entry)
        else:
            report.cant_yet.append(entry)
        current_map[capability] = tier

    # 3. Diff against previous frontier snapshot for this domain, if any.
    try:
        prev_records = read_records(
            project_dir,
            "frontier",
            filters={"domain": domain},
        )
    except Exception as exc:
        report.errors.append(f"read_records(frontier) failed: {exc}")
        prev_records = []

    if prev_records:
        # Use the most recent snapshot (last appended).
        last = prev_records[-1]
        prev_map: dict[str, str] = {}
        for tier in TIERS:
            for entry in last.get(tier, []) or []:
                cap = _capability_key(entry)
                if cap:
                    prev_map[cap] = tier
        report.shifts_since_last = _diff_tiers(prev_map, current_map)

    # 4. Persist the new snapshot.
    try:
        append_record(
            project_dir,
            "frontier",
            {
                "domain": domain,
                "reliable": report.reliable,
                "sometimes": report.sometimes,
                "cant_yet": report.cant_yet,
                "shifts_since_last": report.shifts_since_last,
                "snapshot_time": time.time(),
            },
        )
    except Exception as exc:
        report.errors.append(f"append_record(frontier) failed: {exc}")

    return report
