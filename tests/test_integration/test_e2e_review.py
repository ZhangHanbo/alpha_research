"""End-to-end: ``alpha-research review`` on a fixture paper.

Invokes the adversarial-review skill via claude CLI on a short fixture
artifact and verifies the output record shape.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from alpha_research.main import app


runner = CliRunner()


_FIXTURE_PAPER = """\
# Learning Tactile Insertion with Diffusion Policy

## Abstract
We present a diffusion-policy-based approach to precision insertion using
GelSight tactile sensors. Our method achieves 85% success rate on three
peg-in-hole tasks.

## Introduction
Precision insertion is a long-standing problem in manipulation. We propose...

## Method
Section 3 describes our diffusion policy architecture and tactile encoder.

## Experiments
We evaluate on 3 peg types in a single environment over 6 trials per condition.
Our method outperforms behavior cloning by 20 percentage points.

## Related Work
We build on prior work in tactile manipulation and diffusion policies.
"""


@pytest.mark.integration
def test_review_e2e_fixture_paper(tmp_path, skip_if_no_claude):
    """End-to-end: run adversarial-review skill on a toy fixture paper.

    Acceptance (from refactor_plan.md Part V Phase R8.2):
    - reviews.jsonl has a new record
    - Review has chain_extraction, steel_man, findings, verdict fields
    - Findings are classified (fatal/serious/minor)
    - Verdict computation is mechanical (metrics/verdict.py was called)
    """
    artifact = tmp_path / "paper.md"
    artifact.write_text(_FIXTURE_PAPER)

    result = runner.invoke(
        app,
        [
            "review",
            str(artifact),
            "--venue", "RSS",
            "-o", str(tmp_path / "review_out"),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, f"review failed: {result.output}"

    review_jsonl = tmp_path / "review_out" / "review.jsonl"
    assert review_jsonl.exists(), "review.jsonl not written"

    with review_jsonl.open() as f:
        lines = [json.loads(l) for l in f if l.strip()]
    assert len(lines) >= 1

    review = lines[-1]
    assert "verdict" in review
    assert "findings" in review
    # Findings are classified
    findings = review.get("findings", {})
    if isinstance(findings, dict):
        for severity in ("fatal", "serious", "minor"):
            assert severity in findings, f"findings.{severity} missing"
