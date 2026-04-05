"""End-to-end calibration: agent B.1-B.7 scores vs. human gold labels.

Successor to the original T10 calibration test. Loads 10 fixture papers
with human-assigned rubric scores, runs paper-evaluate on each, and
verifies agreement within ±1 on ≥70% of dimensions (the T10 threshold).

The fixture file lives at ``tests/test_integration/fixtures/calibration.json``
and is PENDING: the user should curate the 10 papers + gold labels before
running this test. The test skips cleanly if the fixture is absent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from alpha_research.main import app


runner = CliRunner()

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "calibration.json"


@pytest.mark.integration
def test_calibration_against_human_gold(tmp_path, skip_if_no_claude):
    """Verify agent rubric scores match human labels within ±1 on ≥70% of dims.

    Acceptance (from refactor_plan.md Part V Phase R8.3):
    - 10 fixture papers evaluated
    - Agreement within ±1 on ≥70% of B.1-B.7 dimensions across the set
    """
    if not _FIXTURE_PATH.exists():
        pytest.skip(
            f"Calibration fixture missing: {_FIXTURE_PATH}. "
            "The user must curate 10 papers + human gold labels before this "
            "test can run. See guidelines/refactor_plan.md Part V Phase R8.3."
        )

    fixtures = json.loads(_FIXTURE_PATH.read_text())
    assert len(fixtures) >= 10, f"need ≥10 calibration papers, have {len(fixtures)}"

    dim_matches = 0
    dim_total = 0
    for entry in fixtures:
        paper_id = entry["paper_id"]
        human_scores = entry["scores"]

        result = runner.invoke(
            app,
            ["evaluate", paper_id, "-o", str(tmp_path / paper_id.replace(":", "_"))],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, f"evaluate failed for {paper_id}: {result.output}"

        eval_path = tmp_path / paper_id.replace(":", "_") / "evaluation.jsonl"
        assert eval_path.exists()
        with eval_path.open() as f:
            records = [json.loads(l) for l in f if l.strip()]
        agent_scores = records[-1].get("rubric_scores", {})

        for dim in ("B.1", "B.2", "B.3", "B.4", "B.5", "B.6", "B.7"):
            if dim not in human_scores or dim not in agent_scores:
                continue
            human = int(human_scores[dim])
            agent = int(agent_scores[dim].get("score", 0))
            dim_total += 1
            if abs(agent - human) <= 1:
                dim_matches += 1

    assert dim_total > 0, "no dimensions compared"
    agreement = dim_matches / dim_total
    assert agreement >= 0.70, (
        f"calibration failed: {agreement:.1%} agreement "
        f"({dim_matches}/{dim_total}) < 70% threshold"
    )
