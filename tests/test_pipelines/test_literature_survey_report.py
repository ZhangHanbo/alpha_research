"""Report-emitting tests for ``alpha_research.pipelines.literature_survey``.

Complements ``test_literature_survey.py`` by routing the core behaviours
through the ``report`` fixture so a human-readable record lands at
``tests/reports/test_literature_survey_report.md``.

Mock skill_invoker is used; subprocess/alpha_review.ReviewState are patched.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from alpha_research.pipelines import literature_survey as ls


def _make_mock_invoker(recorder: list[tuple[str, dict]]):
    async def invoker(skill: str, inputs: dict):
        recorder.append((skill, inputs))
        if skill == "paper-evaluate":
            return {"rubric_scores": {"B1": 4}, "task_chain": {"task": "grasp"}}
        if skill == "gap-analysis":
            return {"gaps": ["gap A"]}
        if skill == "classify-capability":
            return {"tier": "sometimes", "capability": inputs["evaluation"].get("title")}
        return {}
    return invoker


def _fake_completed(returncode: int = 0, stdout: str = "", stderr: str = ""):
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def _seed_alpha_review_outputs(path: Path) -> None:
    (path / "review_grounded.tex").write_text("\\documentclass{article}")
    (path / "references.bib").write_text("% bib")


@pytest.mark.asyncio
async def test_phase_a_subprocess_failure(tmp_path: Path, report) -> None:
    recorder: list = []
    with patch.object(ls.subprocess, "run", return_value=_fake_completed(returncode=1, stderr="boom")):
        result = await ls.run_literature_survey(
            query="robot grasp",
            output_dir=tmp_path,
            skill_invoker=_make_mock_invoker(recorder),
        )

    passed = bool(result.errors) and result.papers_included == 0 and recorder == []
    report.record(
        name="phase A failure aborts before any skill call",
        purpose="When alpha-review CLI returns non-zero, no skills should run.",
        inputs={"returncode": 1, "stderr": "boom"},
        expected={"errors": ">=1", "papers_included": 0, "skill_calls": 0},
        actual={"errors": result.errors, "papers_included": result.papers_included, "skill_calls": len(recorder)},
        passed=passed,
        conclusion="The pipeline short-circuits on phase-A failure to save cost and stay consistent.",
    )
    assert passed


@pytest.mark.asyncio
async def test_apply_rubric_false_skips_b_and_c(tmp_path: Path, report) -> None:
    _seed_alpha_review_outputs(tmp_path)
    recorder: list = []
    with patch.object(ls.subprocess, "run", return_value=_fake_completed()):
        result = await ls.run_literature_survey(
            query="q",
            output_dir=tmp_path,
            apply_rubric=False,
            skill_invoker=_make_mock_invoker(recorder),
        )

    passed = (
        result.tex_path == tmp_path / "review_grounded.tex"
        and result.bib_path == tmp_path / "references.bib"
        and result.evaluations_written == 0
        and recorder == []
    )
    report.record(
        name="apply_rubric=False runs Phase A only",
        purpose="Skip rubric and synthesis when only a LaTeX survey is needed.",
        inputs={"apply_rubric": False},
        expected={"tex_present": True, "bib_present": True, "evaluations_written": 0, "skill_calls": 0},
        actual={
            "tex_present": result.tex_path is not None,
            "bib_present": result.bib_path is not None,
            "evaluations_written": result.evaluations_written,
            "skill_calls": len(recorder),
        },
        passed=passed,
        conclusion="Phase A alone is a cheap mode for quick literature pulls.",
    )
    assert passed


@pytest.mark.asyncio
async def test_full_pipeline_writes_evaluations_and_report(tmp_path: Path, report) -> None:
    _seed_alpha_review_outputs(tmp_path)
    papers = [
        {"id": "p1", "title": "Robot paper 1", "authors": ["A"], "year": 2024, "venue": "RSS", "abstract": "", "url": "", "doi": ""},
        {"id": "p2", "title": "Robot paper 2", "authors": ["B"], "year": 2023, "venue": "CoRL", "abstract": "", "url": "", "doi": ""},
    ]
    recorder: list = []
    with patch.object(ls.subprocess, "run", return_value=_fake_completed()), patch.object(
        ls, "_load_included_papers", return_value=papers
    ):
        result = await ls.run_literature_survey(
            query="robot grasp",
            output_dir=tmp_path,
            skill_invoker=_make_mock_invoker(recorder),
        )

    skills = [s for s, _ in recorder]
    passed = (
        result.papers_included == 2
        and result.evaluations_written == 2
        and result.report_path is not None
        and result.report_path.exists()
        and skills.count("paper-evaluate") == 2
        and "gap-analysis" in skills
    )
    report.record(
        name="full pipeline produces evaluations + synthesis report",
        purpose="Phase A → B → C with two included papers should yield two evaluation records plus a synthesis report.",
        inputs={"papers": [p["title"] for p in papers]},
        expected={
            "papers_included": 2,
            "evaluations_written": 2,
            "report_exists": True,
            "paper_evaluate_calls": 2,
            "gap_analysis_called": True,
        },
        actual={
            "papers_included": result.papers_included,
            "evaluations_written": result.evaluations_written,
            "report_exists": bool(result.report_path and result.report_path.exists()),
            "paper_evaluate_calls": skills.count("paper-evaluate"),
            "gap_analysis_called": "gap-analysis" in skills,
        },
        passed=passed,
        conclusion="End-to-end run with a mock invoker verifies the three-phase orchestration shape.",
    )
    assert passed
