"""Unit tests for ``alpha_research.pipelines.research_review_loop``.

Uses a mock ``skill_invoker`` to simulate the adversarial-review loop
without any LLM calls. Writes ``tests/reports/test_research_review_loop.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alpha_research.pipelines.research_review_loop import run_research_review_loop
from alpha_research.records.jsonl import read_records


def _review_payload(
    *,
    fatal: int = 0,
    serious: int = 0,
    minor: int = 0,
    verdict: str = "accept",
    iteration: int = 1,
    fixable: bool = True,
) -> dict:
    def _finding(i: int, sev: str) -> dict:
        return {
            "id": f"{sev[:1]}{iteration}_{i}",
            "severity": sev,
            "attack_vector": "baseline",
            "what_is_wrong": "missing baseline",
            "why_it_matters": "SOTA baseline missing",
            "what_would_fix": "add baseline",
            "falsification": "beat it",
            "grounding": "Table 2",
            "fixable": fixable,
            "maps_to_trigger": None,
        }

    return {
        "version": 1,
        "iteration": iteration,
        "summary": "s",
        "chain_extraction": {"task": "t", "problem": "p", "challenge": "c", "approach": "a", "one_sentence": "x"},
        "steel_man": "One. Two. Three.",
        "fatal_flaws": [_finding(i, "fatal") for i in range(fatal)],
        "serious_weaknesses": [_finding(i, "serious") for i in range(serious)],
        "minor_issues": [_finding(i, "minor") for i in range(minor)],
        "questions": [],
        "verdict": verdict,
        "confidence": 3,
    }


@pytest.mark.asyncio
async def test_converges_on_clean_review(tmp_path: Path, report) -> None:
    calls: list[str] = []

    async def invoker(skill: str, inputs: dict):
        calls.append(skill)
        if skill == "adversarial-review":
            return _review_payload(verdict="accept")
        return {}

    result = await run_research_review_loop(
        project_dir=tmp_path,
        max_iterations=3,
        venue="RSS",
        skill_invoker=invoker,
    )

    passed = (
        result.converged is True
        and result.submit_ready is True
        and result.iterations_run == 1
        and result.final_verdict == "accept"
    )
    report.record(
        name="clean review converges in one iteration",
        purpose="A first-iteration review with 0 fatal, 0 serious and ACCEPT verdict should converge and mark submit_ready.",
        inputs={"mock_review": "accept, 0 fatal, 0 serious"},
        expected={"converged": True, "submit_ready": True, "iterations": 1, "verdict": "accept"},
        actual={
            "converged": result.converged,
            "submit_ready": result.submit_ready,
            "iterations": result.iterations_run,
            "verdict": result.final_verdict,
        },
        passed=passed,
        conclusion="Single-pass success is the happy path; the loop exits as soon as the review is clean.",
    )
    assert passed


@pytest.mark.asyncio
async def test_hits_iteration_limit(tmp_path: Path, report) -> None:
    async def invoker(skill: str, inputs: dict):
        if skill == "adversarial-review":
            # Always return 2 serious fixable at RSS → WEAK_ACCEPT (but ACCEPT required for submit)
            return _review_payload(serious=2, verdict="weak_accept", iteration=inputs.get("iteration", 1))
        # paper-evaluate revision returns unchanged artifact
        return {}

    result = await run_research_review_loop(
        project_dir=tmp_path,
        max_iterations=2,
        venue="IJRR",  # IJRR treats 2 serious as REJECT
        skill_invoker=invoker,
    )

    passed = result.iterations_run == 2 and result.converged is True and result.submit_ready is False
    report.record(
        name="loop terminates at iteration limit when unconverged",
        purpose="If the review never passes the quality bar, the loop runs to max_iterations and marks ITERATION_LIMIT.",
        inputs={"max_iterations": 2, "venue": "IJRR", "serious_per_review": 2},
        expected={"iterations_run": 2, "converged": True, "submit_ready": False},
        actual={
            "iterations_run": result.iterations_run,
            "converged": result.converged,
            "submit_ready": result.submit_ready,
        },
        passed=passed,
        conclusion="Iteration-limit convergence signals the loop stopped trying, not that the paper is ready.",
    )
    assert passed


@pytest.mark.asyncio
async def test_persist_review_record(tmp_path: Path, report) -> None:
    async def invoker(skill: str, inputs: dict):
        if skill == "adversarial-review":
            return _review_payload(verdict="accept")
        return {}

    await run_research_review_loop(tmp_path, max_iterations=1, venue="RSS", skill_invoker=invoker)

    recs = read_records(tmp_path, "review")
    passed = len(recs) == 1 and recs[0]["verdict"] == "accept" and recs[0]["submit_ready"] is True
    report.record(
        name="final review is persisted to review.jsonl",
        purpose="run_research_review_loop should append a JSONL review record at the end.",
        inputs={"max_iterations": 1},
        expected={"records": 1, "verdict": "accept", "submit_ready": True},
        actual={
            "records": len(recs),
            "verdict": recs[0]["verdict"] if recs else None,
            "submit_ready": recs[0]["submit_ready"] if recs else None,
        },
        passed=passed,
        conclusion="Persistence guarantees the dashboard and follow-up pipelines can read the final verdict.",
    )
    assert passed


@pytest.mark.asyncio
async def test_backward_to_significance_pauses_for_human(tmp_path: Path, report) -> None:
    async def invoker(skill: str, inputs: dict):
        if skill == "adversarial-review":
            # 1 serious NON-fixable keeps the review below the quality bar
            payload = _review_payload(serious=1, verdict="weak_reject", fixable=False)
            # Mark the finding as t13 (validate → significance, hamming fail)
            payload["serious_weaknesses"][0]["maps_to_trigger"] = "t13"
            return payload
        return {}

    result = await run_research_review_loop(tmp_path, max_iterations=3, venue="RSS", skill_invoker=invoker)

    passed = result.paused_for_human is True and "t13" in result.backward_triggers_fired
    report.record(
        name="t13 backward trigger pauses loop for human sign-off",
        purpose="Triggers that regress to SIGNIFICANCE cannot be resolved autonomously.",
        inputs={"trigger": "t13"},
        expected={"paused_for_human": True, "fired_triggers_contains": "t13"},
        actual={"paused_for_human": result.paused_for_human, "backward_triggers": result.backward_triggers_fired},
        passed=passed,
        conclusion="The researcher must decide whether to abandon or rescope the problem when hamming-test fails.",
    )
    assert passed
