"""Unit tests for ``alpha_research.config``.

Writes ``tests/reports/test_config.md``.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from alpha_research.config import (
    ConstitutionConfig,
    ReviewConfig,
    load_constitution,
    load_review_config,
)
from alpha_research.models.blackboard import Venue


def test_constitution_defaults(report) -> None:
    c = ConstitutionConfig()
    passed = (
        "mobile manipulation" in c.focus_areas
        and c.max_papers_per_cycle == 50
        and c.name == "Robotics Research"
    )
    report.record(
        name="ConstitutionConfig defaults encode the robotics focus",
        purpose="Default constitution must contain the standard focus areas and sensible limits.",
        inputs={},
        expected={
            "name": "Robotics Research",
            "max_papers_per_cycle": 50,
            "mobile manipulation in focus": True,
        },
        actual={
            "name": c.name,
            "max_papers_per_cycle": c.max_papers_per_cycle,
            "mobile manipulation in focus": "mobile manipulation" in c.focus_areas,
        },
        passed=passed,
        conclusion="Defaults make the tool usable out-of-the-box without a YAML file.",
    )
    assert passed


def test_review_config_defaults(report) -> None:
    rc = ReviewConfig()
    passed = (
        rc.target_venue == "RSS"
        and rc.max_iterations == 5
        and rc.quality_threshold.max_serious == 1
        and rc.review_quality_thresholds.min_actionability == 0.80
    )
    report.record(
        name="ReviewConfig defaults match review_plan §4.4",
        purpose="Verify the baseline iteration budget, quality thresholds, and venue defaults.",
        inputs={},
        expected={
            "target_venue": "RSS",
            "max_iterations": 5,
            "max_serious": 1,
            "min_actionability": 0.80,
        },
        actual={
            "target_venue": rc.target_venue,
            "max_iterations": rc.max_iterations,
            "max_serious": rc.quality_threshold.max_serious,
            "min_actionability": rc.review_quality_thresholds.min_actionability,
        },
        passed=passed,
        conclusion="A caller with no YAML file still gets a well-defined review loop.",
    )
    assert passed


def test_review_depth_per_iteration(report) -> None:
    rc = ReviewConfig()
    depths = {
        1: rc.get_review_depth(1),
        2: rc.get_review_depth(2),
        3: rc.get_review_depth(3),
        5: rc.get_review_depth(5),
    }
    passed = (
        depths[1] == "structural_scan"
        and depths[2] == "full_review"
        and depths[3] == "focused_rereview"
        and depths[5] == "focused_rereview"
    )
    report.record(
        name="graduated pressure schedule per iteration",
        purpose="ReviewConfig.get_review_depth returns the correct mode for each iteration number.",
        inputs={"iterations": [1, 2, 3, 5]},
        expected={1: "structural_scan", 2: "full_review", 3: "focused_rereview", 5: "focused_rereview"},
        actual=depths,
        passed=passed,
        conclusion="Iterations 3+ collapse to focused rereview — the pressure schedule is bounded.",
    )
    assert passed


def test_resolve_venue_matches_enum(report) -> None:
    rc = ReviewConfig(target_venue="RSS")
    rc2 = ReviewConfig(target_venue="T-RO")
    passed = rc.resolve_venue() == Venue.RSS and rc2.resolve_venue() == Venue.T_RO
    report.record(
        name="resolve_venue handles value and name variants",
        purpose="target_venue strings 'RSS' and 'T-RO' must resolve to the correct Venue enum members.",
        inputs={"targets": ["RSS", "T-RO"]},
        expected={"RSS": "RSS", "T-RO": "T-RO"},
        actual={"RSS": rc.resolve_venue().value, "T-RO": rc2.resolve_venue().value},
        passed=passed,
        conclusion="String resolution tolerates the hyphen in T-RO — important because YAML quotes vary.",
    )
    assert passed


def test_load_constitution_missing_file(tmp_path: Path, report) -> None:
    missing = tmp_path / "nope.yaml"
    c = load_constitution(str(missing))
    passed = c.name == ConstitutionConfig().name
    report.record(
        name="load_constitution returns defaults when file is missing",
        purpose="A non-existent file should return a ConstitutionConfig with default values, not raise.",
        inputs={"path": str(missing)},
        expected={"name": "Robotics Research"},
        actual={"name": c.name},
        passed=passed,
        conclusion="Missing config file is handled gracefully so the tool works in minimal setups.",
    )
    assert passed


def test_load_review_config_from_yaml(tmp_path: Path, report) -> None:
    path = tmp_path / "review.yaml"
    data = {
        "target_venue": "CoRL",
        "max_iterations": 3,
        "review_quality_thresholds": {
            "min_actionability": 0.9,
            "min_grounding": 0.95,
            "max_vague_critiques": 0,
            "min_falsifiability": 0.80,
            "min_steel_man_sentences": 4,
        },
    }
    path.write_text(yaml.safe_dump(data))
    rc = load_review_config(str(path))
    passed = (
        rc.target_venue == "CoRL"
        and rc.max_iterations == 3
        and rc.review_quality_thresholds.min_actionability == 0.9
        and rc.review_quality_thresholds.min_grounding == 0.95
    )
    report.record(
        name="load_review_config reads overrides from YAML",
        purpose="Override venue, iterations, and quality thresholds via YAML and verify each takes effect.",
        inputs=data,
        expected={
            "target_venue": "CoRL",
            "max_iterations": 3,
            "min_actionability": 0.9,
            "min_grounding": 0.95,
        },
        actual={
            "target_venue": rc.target_venue,
            "max_iterations": rc.max_iterations,
            "min_actionability": rc.review_quality_thresholds.min_actionability,
            "min_grounding": rc.review_quality_thresholds.min_grounding,
        },
        passed=passed,
        conclusion="YAML overrides flow through to the runtime config with no lossy parsing.",
    )
    assert passed
