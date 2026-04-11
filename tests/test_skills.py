"""Tests for the Phase 3 skill stage-awareness layer.

Covers:
  - parse_frontmatter extracts name / description / model / allowed-tools /
    research_stages
  - parse_frontmatter returns None on files without frontmatter
  - discover_skills walks the skills/ directory and returns all 11
  - All 11 skills now declare research_stages
  - check_skill_stage returns in_stage / out_of_stage / unknown_* correctly

Report saved to ``tests/reports/test_skills.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alpha_research.skills import (
    SkillFrontmatter,
    check_skill_stage,
    discover_skills,
    load_skill,
    parse_frontmatter,
)


REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Test 1 — frontmatter parser
# ---------------------------------------------------------------------------


def test_parse_frontmatter_extracts_all_fields(report):
    text = (
        "---\n"
        "name: paper-evaluate\n"
        "description: Evaluate a robotics paper against the Appendix B rubric.\n"
        "allowed-tools: [Bash, Read, Write, Grep]\n"
        "model: claude-sonnet-4-6\n"
        "research_stages: [significance, approach]\n"
        "---\n\n"
        "# Paper Evaluate\n\n"
        "Body content goes here.\n"
    )
    fm = parse_frontmatter(text)

    passed = (
        fm is not None
        and fm.name == "paper-evaluate"
        and "Appendix B" in fm.description
        and fm.model == "claude-sonnet-4-6"
        and fm.allowed_tools == ["Bash", "Read", "Write", "Grep"]
        and fm.research_stages == ["significance", "approach"]
    )

    report.record(
        name="parse_frontmatter extracts all fields",
        purpose=(
            "The frontmatter parser is a stdlib-only implementation "
            "(no PyYAML dependency) that extracts the five fields the "
            "runtime cares about: name, description, model, allowed-tools, "
            "research_stages."
        ),
        inputs={"text_preview": text[:200]},
        expected={
            "name": "paper-evaluate",
            "model": "claude-sonnet-4-6",
            "allowed_tools": ["Bash", "Read", "Write", "Grep"],
            "research_stages": ["significance", "approach"],
        },
        actual={
            "name": fm.name if fm else None,
            "model": fm.model if fm else None,
            "allowed_tools": fm.allowed_tools if fm else None,
            "research_stages": fm.research_stages if fm else None,
        },
        passed=passed,
        conclusion=(
            "Parsing SKILL.md frontmatter requires no external dependency. "
            "All bracketed-list fields are split correctly and plain "
            "strings are preserved verbatim."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 2 — parse_frontmatter returns None on missing frontmatter
# ---------------------------------------------------------------------------


def test_parse_frontmatter_returns_none_without_frontmatter(report):
    text = "# Just a markdown file\n\nNo frontmatter here.\n"
    fm = parse_frontmatter(text)

    passed = fm is None

    report.record(
        name="parse_frontmatter returns None on missing frontmatter",
        purpose=(
            "Files without a ``---``-delimited frontmatter header are "
            "treated as 'not a skill file' and return None."
        ),
        inputs={"text": text},
        expected=None,
        actual=fm,
        passed=passed,
        conclusion=(
            "The parser degrades cleanly: any non-skill markdown file "
            "returns None rather than raising. Callers can treat None "
            "as 'not a skill'."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 3 — all 11 skills now declare research_stages
# ---------------------------------------------------------------------------


def test_all_skills_declare_research_stages(report):
    skills_dir = REPO_ROOT / "skills"
    skills = discover_skills((skills_dir,))

    expected_skills = {
        "significance-screen",
        "gap-analysis",
        "paper-evaluate",
        "formalization-check",
        "diagnose-system",
        "challenge-articulate",
        "concurrent-work-check",
        "identify-method-gaps",
        "experiment-audit",
        "adversarial-review",
        "classify-capability",
    }

    found = set(skills.keys())
    missing_skill = expected_skills - found
    no_stages = {
        slug for slug, fm in skills.items() if not fm.research_stages
    }

    passed = len(missing_skill) == 0 and len(no_stages) == 0

    report.record(
        name="all 11 skills declare research_stages",
        purpose=(
            "Phase 3 adds a research_stages frontmatter field to every "
            "SKILL.md so the runtime can warn on out-of-stage invocation. "
            "This test ensures the migration is complete."
        ),
        inputs={"skills_dir": str(skills_dir)},
        expected={
            "discovered_slugs_superset_of": sorted(expected_skills),
            "all_have_research_stages": True,
        },
        actual={
            "discovered_slugs": sorted(found),
            "missing_expected": sorted(missing_skill),
            "slugs_without_research_stages": sorted(no_stages),
            "stages_per_skill": {
                slug: fm.research_stages for slug, fm in sorted(skills.items())
            },
        },
        passed=passed,
        conclusion=(
            "Every skill now knows which research stage(s) it's valid in. "
            "The check_skill_stage function can give a meaningful verdict "
            "for every skill, with no 'unknown_stage' fallback."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 4 — check_skill_stage returns in_stage
# ---------------------------------------------------------------------------


def test_check_skill_stage_in_stage(report):
    skills = discover_skills((REPO_ROOT / "skills",))
    result = check_skill_stage("significance-screen", "significance", skills=skills)

    passed = (
        result.verdict == "in_stage"
        and result.skill_name == "significance-screen"
        and result.project_stage == "significance"
    )

    report.record(
        name="check_skill_stage returns in_stage",
        purpose=(
            "Invoking significance-screen while the project is in the "
            "SIGNIFICANCE stage must return verdict='in_stage'."
        ),
        inputs={
            "skill_name": "significance-screen",
            "project_stage": "significance",
        },
        expected={"verdict": "in_stage"},
        actual={
            "verdict": result.verdict,
            "valid_stages": result.valid_stages,
            "message": result.message,
        },
        passed=passed,
        conclusion=(
            "The happy path: a stage-bound skill in its declared stage "
            "reports in_stage and the CLI proceeds without warning."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 5 — check_skill_stage returns out_of_stage
# ---------------------------------------------------------------------------


def test_check_skill_stage_out_of_stage_warns(report):
    skills = discover_skills((REPO_ROOT / "skills",))
    result = check_skill_stage("adversarial-review", "significance", skills=skills)

    passed = (
        result.verdict == "out_of_stage"
        and "validate" in result.valid_stages
        and "significance" not in result.valid_stages
        and "force" in result.message.lower()
    )

    report.record(
        name="check_skill_stage returns out_of_stage with force-override hint",
        purpose=(
            "Invoking adversarial-review (valid in VALIDATE only) from "
            "SIGNIFICANCE must return out_of_stage AND include a hint "
            "about the --force override path."
        ),
        inputs={
            "skill_name": "adversarial-review",
            "project_stage": "significance",
        },
        expected={
            "verdict": "out_of_stage",
            "valid_stages_include": "validate",
            "message_mentions_force": True,
        },
        actual={
            "verdict": result.verdict,
            "valid_stages": result.valid_stages,
            "message": result.message,
        },
        passed=passed,
        conclusion=(
            "Out-of-stage invocation is warned, not blocked. The CLI "
            "surfaces the warning and explains how to override — the "
            "researcher keeps full control."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 6 — check_skill_stage returns unknown_skill
# ---------------------------------------------------------------------------


def test_check_skill_stage_unknown_skill(report):
    skills = discover_skills((REPO_ROOT / "skills",))
    result = check_skill_stage("nonexistent-skill", "significance", skills=skills)

    passed = result.verdict == "unknown_skill" and "nonexistent-skill" in result.message

    report.record(
        name="check_skill_stage flags unknown skill",
        purpose=(
            "A typo'd skill name must return unknown_skill so the CLI "
            "can surface a typo-style error rather than silently doing "
            "nothing."
        ),
        inputs={
            "skill_name": "nonexistent-skill",
            "project_stage": "significance",
        },
        expected={"verdict": "unknown_skill"},
        actual={
            "verdict": result.verdict,
            "message": result.message,
        },
        passed=passed,
        conclusion=(
            "Unknown skills are flagged with the available set, so the "
            "researcher can see at a glance what they could have meant."
        ),
    )
    assert passed


# ---------------------------------------------------------------------------
# Test 7 — every skill's stage assignment matches the plan
# ---------------------------------------------------------------------------


def test_stage_assignments_match_implementation_plan(report):
    """Sanity-check each skill's stages match Part VI of the plan."""
    skills = discover_skills((REPO_ROOT / "skills",))

    expected = {
        "significance-screen":   ["significance"],
        "gap-analysis":          ["significance"],
        "paper-evaluate":        ["significance", "approach"],
        "formalization-check":   ["formalization", "approach"],
        "diagnose-system":       ["diagnose"],
        "challenge-articulate":  ["challenge"],
        "concurrent-work-check": ["challenge", "approach", "validate"],
        "identify-method-gaps":  ["approach"],
        "experiment-audit":      ["validate"],
        "adversarial-review":    ["validate"],
        "classify-capability":   ["significance", "validate"],
    }

    actual = {
        slug: skills[slug].research_stages
        for slug in expected
        if slug in skills
    }

    mismatches = {
        slug: (expected[slug], actual.get(slug))
        for slug in expected
        if actual.get(slug) != expected[slug]
    }

    passed = len(mismatches) == 0

    report.record(
        name="skill stage assignments match implementation_plan.md Part VI",
        purpose=(
            "Each of the 11 skills must declare exactly the stages the "
            "plan assigns them. This is the single-source-of-truth check."
        ),
        inputs={"expected_stage_map": expected},
        expected=expected,
        actual=actual,
        passed=passed,
        conclusion=(
            "Stage bindings are faithful to the plan — invoking "
            "adversarial-review from SIGNIFICANCE will warn, invoking "
            "paper-evaluate from SIGNIFICANCE will not, etc."
        ),
    )
    assert passed
