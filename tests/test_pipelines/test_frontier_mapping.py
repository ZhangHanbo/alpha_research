"""Unit tests for ``alpha_research.pipelines.frontier_mapping``.

Uses a mock ``skill_invoker`` to avoid real LLM calls. Writes
``tests/reports/test_frontier_mapping.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alpha_research.pipelines.frontier_mapping import run_frontier_mapping
from alpha_research.records.jsonl import append_record, read_records


def _make_mock_invoker(tier_map: dict[str, str]):
    """Return a mock skill_invoker that classifies each evaluation by title."""

    async def _invoker(skill_name: str, inputs: dict):
        assert skill_name == "classify-capability"
        ev = inputs["evaluation"]
        title = ev.get("title", "")
        tier = tier_map.get(title, "cant_yet")
        return {
            "tier": tier,
            "capability": f"capability({title})",
            "justification": f"mock classification: {tier}",
        }

    return _invoker


@pytest.mark.asyncio
async def test_frontier_mapping_three_tiers(tmp_path: Path, report) -> None:
    # Seed three evaluations in the project
    append_record(tmp_path, "evaluation", {"title": "Paper A", "paper_id": "pA", "task_chain": {"task": "robot grasping"}})
    append_record(tmp_path, "evaluation", {"title": "Paper B", "paper_id": "pB", "task_chain": {"task": "robot manipulation"}})
    append_record(tmp_path, "evaluation", {"title": "Paper C", "paper_id": "pC", "task_chain": {"task": "robot planning"}})

    invoker = _make_mock_invoker({"Paper A": "reliable", "Paper B": "sometimes", "Paper C": "cant_yet"})

    result = await run_frontier_mapping(tmp_path, domain="robot grasp", skill_invoker=invoker)

    passed = (
        len(result.reliable) == 1
        and len(result.sometimes) == 1
        and len(result.cant_yet) == 1
        and result.reliable[0]["capability"] == "capability(Paper A)"
    )
    report.record(
        name="three-tier classification aggregates correctly",
        purpose="run_frontier_mapping partitions mocked classifications into reliable/sometimes/cant_yet.",
        inputs={"papers": ["Paper A", "Paper B", "Paper C"], "tier_map": {"Paper A": "reliable", "Paper B": "sometimes", "Paper C": "cant_yet"}},
        expected={"reliable": 1, "sometimes": 1, "cant_yet": 1},
        actual={"reliable": len(result.reliable), "sometimes": len(result.sometimes), "cant_yet": len(result.cant_yet)},
        passed=passed,
        conclusion="The tier partition is the core observable output of frontier_mapping.",
    )
    assert passed


@pytest.mark.asyncio
async def test_frontier_snapshot_persisted(tmp_path: Path, report) -> None:
    append_record(tmp_path, "evaluation", {"title": "P1", "paper_id": "p1", "task_chain": {"task": "grasp"}})
    invoker = _make_mock_invoker({"P1": "reliable"})

    await run_frontier_mapping(tmp_path, domain="grasp", skill_invoker=invoker)

    recs = read_records(tmp_path, "frontier")
    passed = len(recs) == 1 and recs[0]["domain"] == "grasp" and len(recs[0]["reliable"]) == 1
    report.record(
        name="frontier snapshot appended to frontier.jsonl",
        purpose="Each run should append one frontier record with the full tier partition.",
        inputs={"domain": "grasp"},
        expected={"records": 1, "domain": "grasp", "reliable_count": 1},
        actual={"records": len(recs), "domain": recs[0]["domain"] if recs else None, "reliable_count": len(recs[0]["reliable"]) if recs else 0},
        passed=passed,
        conclusion="Persistence gives the dashboard and downstream diff logic a stable store.",
    )
    assert passed


@pytest.mark.asyncio
async def test_frontier_diff_detects_shifts(tmp_path: Path, report) -> None:
    append_record(tmp_path, "evaluation", {"title": "Shifter", "paper_id": "ps", "task_chain": {"task": "grasp"}})

    # First run: classify as cant_yet
    await run_frontier_mapping(tmp_path, domain="grasp", skill_invoker=_make_mock_invoker({"Shifter": "cant_yet"}))
    # Second run: classify as reliable
    result = await run_frontier_mapping(tmp_path, domain="grasp", skill_invoker=_make_mock_invoker({"Shifter": "reliable"}))

    passed = any(shift.get("to") == "reliable" and shift.get("from") == "cant_yet" for shift in result.shifts_since_last)
    report.record(
        name="shift from cant_yet → reliable detected",
        purpose="A second run that promotes a capability should emit a shift record.",
        inputs={"first_run_tier": "cant_yet", "second_run_tier": "reliable"},
        expected={"shift_observed": True},
        actual={"shifts": result.shifts_since_last},
        passed=passed,
        conclusion="The diff drives narrative signal in the dashboard: 'capability X moved up a tier'.",
    )
    assert passed


@pytest.mark.asyncio
async def test_domain_word_matching(tmp_path: Path, report) -> None:
    # Only the first evaluation mentions "grasp" in its task
    append_record(tmp_path, "evaluation", {"title": "Grasp Paper", "paper_id": "g1", "task_chain": {"task": "robot grasping"}})
    append_record(tmp_path, "evaluation", {"title": "Other", "paper_id": "o1", "task_chain": {"task": "legged locomotion"}})

    invoker = _make_mock_invoker({"Grasp Paper": "reliable", "Other": "reliable"})
    result = await run_frontier_mapping(tmp_path, domain="robot grasp", skill_invoker=invoker)

    titles_in_report = [e.get("title") for e in result.reliable]
    passed = titles_in_report == ["Grasp Paper"]
    report.record(
        name="domain word-match filters irrelevant evaluations",
        purpose="Papers whose task chain doesn't share a significant word with the query should be skipped.",
        inputs={"query": "robot grasp", "titles": ["Grasp Paper", "Other"]},
        expected={"included_titles": ["Grasp Paper"]},
        actual={"included_titles": titles_in_report},
        passed=passed,
        conclusion="Word-level matching is how frontier scoping stays on-topic.",
    )
    assert passed
