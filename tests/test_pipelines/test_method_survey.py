"""Unit tests for ``alpha_research.pipelines.method_survey`` helpers.

The full ``run_method_survey`` pipeline calls ``alpha_review.apis`` for
search, which isn't available in isolated test environments. These
tests cover the pure helper functions and the error-path for a missing
challenge record. Writes ``tests/reports/test_method_survey.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alpha_research.pipelines.method_survey import (
    _build_queries,
    _merge_search_results,
    _top_by_citations,
    challenge_name_fallback,
    run_method_survey,
)
from alpha_research.records.jsonl import append_record


def test_build_queries_structural(report) -> None:
    challenge = {"challenge_type": "structural", "name": "contact-rich manipulation"}
    qs = _build_queries(challenge)
    passed = any("structural method" in q for q in qs) and all("contact-rich manipulation" in q for q in qs)
    report.record(
        name="structural challenges produce structural-method queries",
        purpose="For a structural challenge, _build_queries instantiates templates that emphasise formalization.",
        inputs=challenge,
        expected={"contains_structural_method": True, "all_contain_name": True},
        actual={"queries": qs},
        passed=passed,
        conclusion="Query templates are tuned to the challenge type per research_guideline §2.7.",
    )
    assert passed


def test_build_queries_resource_complaint(report) -> None:
    challenge = {"challenge_type": "resource_complaint", "name": "sim2real"}
    qs = _build_queries(challenge)
    passed = any("data efficient" in q for q in qs) and any("sample efficient" in q for q in qs)
    report.record(
        name="resource_complaint challenges produce efficiency queries",
        purpose="Data-/sample-efficient queries target the 'we just need more X' framing.",
        inputs=challenge,
        expected={"contains_data_efficient": True, "contains_sample_efficient": True},
        actual=qs,
        passed=passed,
        conclusion="Matching the query to the challenge class keeps survey recall high.",
    )
    assert passed


def test_challenge_name_fallback(report) -> None:
    # name/statement missing, what_is_wrong present
    name = challenge_name_fallback({"what_is_wrong": "Long description of the problem and all its nasty details."})
    passed = name.startswith("Long description") and len(name) <= 80
    report.record(
        name="fallback uses what_is_wrong when name is absent",
        purpose="challenge_name_fallback should pull a human-readable label from what_is_wrong.",
        inputs={"what_is_wrong": "Long description of the problem and all its nasty details."},
        expected={"starts_with": "Long description", "length <= 80": True},
        actual={"name": name, "length": len(name)},
        passed=passed,
        conclusion="Fallback keeps the pipeline usable even when record schemas vary.",
    )
    assert passed


def test_merge_search_results_dedupes(report) -> None:
    batch1 = [{"paperId": "a", "title": "A"}, {"paperId": "b", "title": "B"}]
    batch2 = [{"paperId": "b", "title": "B"}, {"paperId": "c", "title": "C"}]
    merged = _merge_search_results([batch1, batch2])
    ids = [p["paperId"] for p in merged]
    passed = ids == ["a", "b", "c"]
    report.record(
        name="duplicate paperId is dropped and order preserved",
        purpose="_merge_search_results keeps first occurrence of each key.",
        inputs={"batch1_ids": ["a", "b"], "batch2_ids": ["b", "c"]},
        expected={"merged_ids": ["a", "b", "c"]},
        actual={"merged_ids": ids},
        passed=passed,
        conclusion="Dedup keeps downstream evaluation counts stable across search backends.",
    )
    assert passed


def test_top_by_citations_sorts_desc(report) -> None:
    papers = [
        {"paperId": "low", "citationCount": 1},
        {"paperId": "high", "citationCount": 100},
        {"paperId": "mid", "citationCount": 20},
    ]
    top = _top_by_citations(papers, 2)
    ids = [p["paperId"] for p in top]
    passed = ids == ["high", "mid"]
    report.record(
        name="top-3 selection by citation count",
        purpose="_top_by_citations returns the N most-cited papers in descending order.",
        inputs={"papers": [{"id": p["paperId"], "cites": p["citationCount"]} for p in papers]},
        expected={"top2_ids": ["high", "mid"]},
        actual={"top2_ids": ids},
        passed=passed,
        conclusion="Citation-based seeds bias the expansion toward influential papers.",
    )
    assert passed


@pytest.mark.asyncio
async def test_missing_challenge_reports_error(tmp_path: Path, report) -> None:
    # Seed challenge.jsonl with an unrelated challenge
    append_record(tmp_path, "challenge", {"id": "other", "name": "unrelated"})

    async def invoker(skill: str, inputs: dict):
        return {}

    result = await run_method_survey("nonexistent", tmp_path, skill_invoker=invoker)
    passed = result.methods_surveyed == 0 and any("not found" in e for e in result.errors)
    report.record(
        name="missing challenge surfaces an error in the result",
        purpose="run_method_survey should short-circuit when the challenge_id doesn't exist.",
        inputs={"challenge_id": "nonexistent"},
        expected={"methods_surveyed": 0, "error_contains": "not found"},
        actual={"methods_surveyed": result.methods_surveyed, "errors": result.errors},
        passed=passed,
        conclusion="Typos in challenge_id are caught without hitting the search APIs.",
    )
    assert passed
