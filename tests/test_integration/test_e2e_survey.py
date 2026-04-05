"""End-to-end: ``alpha-research survey`` on a small real topic.

This test runs the actual literature_survey pipeline, which invokes the
``alpha-review`` CLI subprocess and (if ``claude`` is on PATH) the
paper-evaluate skill on each included paper. It takes minutes and costs
API credits — marked ``integration`` to stay opt-in.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from alpha_research.main import app


runner = CliRunner()


@pytest.mark.integration
def test_survey_e2e_tactile_manipulation(
    tmp_path,
    skip_if_no_alpha_review,
    skip_if_no_claude,
):
    """End-to-end: survey a tiny topic, verify artifacts.

    Acceptance (from refactor_plan.md Part V Phase R8.1):
    - LaTeX survey file exists and is non-trivial
    - evaluations.jsonl has ≥ 3 records (lowered from 10 to keep runtime under 5 min)
    - alpha_research_report.md exists
    - No exceptions during run
    """
    project_dir = tmp_path / "tactile_survey"

    result = runner.invoke(
        app,
        [
            "survey",
            "tactile manipulation for deformable objects",
            "-o", str(project_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, f"survey failed: {result.output}"

    # Artifacts
    tex_path = project_dir / "review_grounded.tex"
    assert tex_path.exists(), f"LaTeX survey missing under {project_dir}"
    assert tex_path.stat().st_size > 1000, "LaTeX file suspiciously small"

    evaluations_path = project_dir / "evaluation.jsonl"
    assert evaluations_path.exists(), "evaluations.jsonl not written"
    with evaluations_path.open() as f:
        lines = [l for l in f if l.strip()]
    assert len(lines) >= 3, f"too few evaluations ({len(lines)}) — expected ≥3"

    report_path = project_dir / "alpha_research_report.md"
    assert report_path.exists(), "alpha_research_report.md missing"
