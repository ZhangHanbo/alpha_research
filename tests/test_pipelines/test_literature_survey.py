"""Tests for the literature-survey pipeline."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from alpha_research.pipelines import literature_survey as ls


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

class _FakePaper:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _make_invoker(recorder: list[tuple[str, dict]]):
    async def invoker(skill_name: str, inputs: dict):
        recorder.append((skill_name, inputs))
        if skill_name == "paper-evaluate":
            return {
                "rubric_scores": {"B1": 4},
                "task_chain": {"task": "robot manip"},
            }
        if skill_name == "gap-analysis":
            return {"gaps": ["gap A"]}
        if skill_name == "classify-capability":
            return {"tier": "sometimes", "capability": inputs["evaluation"].get("title")}
        return {}
    return invoker


def _fake_completed(returncode=0, stdout="", stderr=""):
    mock = MagicMock()
    mock.returncode = returncode
    mock.stdout = stdout
    mock.stderr = stderr
    return mock


def _seed_alpha_review_outputs(tmp_path: Path, papers):
    """Create fake tex/bib + a fake ReviewState shim with included papers."""
    (tmp_path / "review_grounded.tex").write_text("\\documentclass{article}")
    (tmp_path / "references.bib").write_text("% bib")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_phase_a_subprocess_failure_returns_errors(tmp_path):
    recorder: list = []
    with patch.object(ls.subprocess, "run", return_value=_fake_completed(returncode=1, stderr="boom")):
        result = await ls.run_literature_survey(
            query="robot grasp",
            output_dir=tmp_path,
            skill_invoker=_make_invoker(recorder),
        )
    assert result.errors
    assert result.papers_included == 0
    # No skill calls should have happened.
    assert recorder == []


@pytest.mark.asyncio
async def test_phase_a_missing_tex_triggers_error(tmp_path):
    recorder: list = []
    with patch.object(ls.subprocess, "run", return_value=_fake_completed(returncode=0)):
        result = await ls.run_literature_survey(
            query="q",
            output_dir=tmp_path,
            skill_invoker=_make_invoker(recorder),
        )
    assert any("review_grounded.tex" in e for e in result.errors)
    assert result.tex_path is None


@pytest.mark.asyncio
async def test_apply_rubric_false_skips_phase_b_and_c(tmp_path):
    _seed_alpha_review_outputs(tmp_path, [])
    recorder: list = []
    with patch.object(ls.subprocess, "run", return_value=_fake_completed()):
        result = await ls.run_literature_survey(
            query="q",
            output_dir=tmp_path,
            apply_rubric=False,
            skill_invoker=_make_invoker(recorder),
        )
    assert result.tex_path == tmp_path / "review_grounded.tex"
    assert result.bib_path == tmp_path / "references.bib"
    assert result.evaluations_written == 0
    assert result.report_path is None
    assert recorder == []  # no skill calls


@pytest.mark.asyncio
async def test_full_pipeline_writes_evaluations_and_report(tmp_path):
    _seed_alpha_review_outputs(tmp_path, [])
    papers = [
        {"id": "p1", "title": "Robot paper 1", "authors": ["A"], "year": 2024,
         "venue": "RSS", "abstract": "abs1", "url": "", "doi": ""},
        {"id": "p2", "title": "Robot paper 2", "authors": ["B"], "year": 2023,
         "venue": "CoRL", "abstract": "abs2", "url": "", "doi": ""},
    ]
    recorder: list = []
    with patch.object(ls.subprocess, "run", return_value=_fake_completed()), \
         patch.object(ls, "_load_included_papers", return_value=papers):
        result = await ls.run_literature_survey(
            query="robot grasp",
            output_dir=tmp_path,
            skill_invoker=_make_invoker(recorder),
        )
    assert result.papers_included == 2
    assert result.evaluations_written == 2
    assert result.report_path is not None and result.report_path.exists()
    # evaluations.jsonl created
    assert (tmp_path / "evaluation.jsonl").exists()
    # skill invocations: 2 paper-evaluate + 1 gap-analysis + 2 classify-capability
    skills_called = [name for name, _ in recorder]
    assert skills_called.count("paper-evaluate") == 2
    assert "gap-analysis" in skills_called
    assert skills_called.count("classify-capability") == 2


@pytest.mark.asyncio
async def test_pipeline_no_included_papers(tmp_path):
    _seed_alpha_review_outputs(tmp_path, [])
    recorder: list = []
    with patch.object(ls.subprocess, "run", return_value=_fake_completed()), \
         patch.object(ls, "_load_included_papers", return_value=[]):
        result = await ls.run_literature_survey(
            query="q",
            output_dir=tmp_path,
            skill_invoker=_make_invoker(recorder),
        )
    assert result.papers_included == 0
    assert result.evaluations_written == 0
    # No rubric skill calls when no papers
    assert not any(s == "paper-evaluate" for s, _ in recorder)


@pytest.mark.asyncio
async def test_skill_invoker_exception_is_logged_not_fatal(tmp_path):
    _seed_alpha_review_outputs(tmp_path, [])
    papers = [{"id": "p1", "title": "T", "authors": [], "year": 2024,
               "venue": "", "abstract": "", "url": "", "doi": ""}]

    async def failing_invoker(skill, inp):
        if skill == "paper-evaluate":
            raise RuntimeError("boom")
        return {}

    with patch.object(ls.subprocess, "run", return_value=_fake_completed()), \
         patch.object(ls, "_load_included_papers", return_value=papers):
        result = await ls.run_literature_survey(
            query="q",
            output_dir=tmp_path,
            skill_invoker=failing_invoker,
        )
    assert result.evaluations_written == 0
    assert any("paper-evaluate failed" in e for e in result.errors)


@pytest.mark.asyncio
async def test_parallelism_respects_semaphore(tmp_path):
    _seed_alpha_review_outputs(tmp_path, [])
    papers = [
        {"id": f"p{i}", "title": f"T{i}", "authors": [], "year": 2024,
         "venue": "", "abstract": "", "url": "", "doi": ""}
        for i in range(5)
    ]
    concurrent = 0
    max_concurrent = 0

    async def slow_invoker(skill, inputs):
        nonlocal concurrent, max_concurrent
        if skill == "paper-evaluate":
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
            await asyncio.sleep(0.01)
            concurrent -= 1
            return {"rubric_scores": {}, "task_chain": {"task": "x"}}
        return {}

    with patch.object(ls.subprocess, "run", return_value=_fake_completed()), \
         patch.object(ls, "_load_included_papers", return_value=papers):
        await ls.run_literature_survey(
            query="q",
            output_dir=tmp_path,
            parallel_evaluations=2,
            skill_invoker=slow_invoker,
        )
    assert max_concurrent <= 2


@pytest.mark.asyncio
async def test_report_contains_query_and_counts(tmp_path):
    _seed_alpha_review_outputs(tmp_path, [])
    papers = [{"id": "p1", "title": "T", "authors": [], "year": 2024,
               "venue": "", "abstract": "", "url": "", "doi": ""}]
    recorder: list = []
    with patch.object(ls.subprocess, "run", return_value=_fake_completed()), \
         patch.object(ls, "_load_included_papers", return_value=papers):
        result = await ls.run_literature_survey(
            query="my unique query",
            output_dir=tmp_path,
            skill_invoker=_make_invoker(recorder),
        )
    body = result.report_path.read_text()
    assert "my unique query" in body
    assert "Papers evaluated" in body
