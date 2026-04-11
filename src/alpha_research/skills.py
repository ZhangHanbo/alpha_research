"""Skill discovery and stage-awareness helpers.

This module is *not* where skills are executed — that happens in Claude
Code via progressive disclosure of the SKILL.md files. This module
provides:

1. **Frontmatter parsing** — read a SKILL.md's YAML frontmatter and
   extract its ``name``, ``description``, ``model``, and
   ``research_stages`` fields. No external YAML dependency; the
   frontmatter is small and regular enough to parse with stdlib.

2. **Stage checking** — given a skill name and a project's current stage,
   decide whether invoking the skill is in-stage, out-of-stage (warn),
   or unknown (warn).

3. **Discovery** — walk the ``skills/`` directory tree (or ``.claude/skills``)
   and return a dict keyed by slug. The runtime skill invoker uses this
   to look up the frontmatter when an invocation arrives.

The test suite exercises all three concerns via ``tests/test_skills.py``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from alpha_research.models.blackboard import ResearchStage

SkillStageCheckVerdict = Literal["in_stage", "out_of_stage", "unknown_stage", "unknown_skill"]


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


@dataclass
class SkillFrontmatter:
    """Parsed frontmatter of a ``SKILL.md`` file.

    Only fields we actually use are parsed — the SKILL.md body and any
    unknown frontmatter keys are ignored.
    """

    name: str
    description: str = ""
    model: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    research_stages: list[str] = field(default_factory=list)
    raw: dict[str, str] = field(default_factory=dict)


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_value(raw: str) -> str | list[str]:
    """Parse a frontmatter value — either a plain string or a bracketed list."""
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1]
        return [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]
    return raw


def parse_frontmatter(text: str) -> SkillFrontmatter | None:
    """Parse the YAML-like frontmatter at the top of ``text``.

    Returns ``None`` if no frontmatter is present. The parser is
    deliberately simple: one ``key: value`` per line, values may be
    strings or bracketed lists. No nested mappings, no multi-line scalars,
    no anchors.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    block = match.group(1)

    raw: dict[str, str] = {}
    parsed_lists: dict[str, list[str]] = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        parsed = _parse_value(value)
        if isinstance(parsed, list):
            parsed_lists[key] = parsed
            raw[key] = value.strip()
        else:
            raw[key] = parsed

    name = raw.get("name", "")
    if not name:
        return None

    return SkillFrontmatter(
        name=name,
        description=raw.get("description", ""),
        model=raw.get("model", ""),
        allowed_tools=parsed_lists.get("allowed-tools", []),
        research_stages=parsed_lists.get("research_stages", []),
        raw=raw,
    )


def load_skill(path: Path) -> SkillFrontmatter | None:
    """Load and parse the frontmatter at ``path`` (a SKILL.md file)."""
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return parse_frontmatter(text)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


DEFAULT_SKILL_ROOTS: tuple[Path, ...] = (
    Path("skills"),
    Path(".claude/skills"),
)


def discover_skills(roots: tuple[Path, ...] | None = None) -> dict[str, SkillFrontmatter]:
    """Return a ``{slug: SkillFrontmatter}`` mapping.

    Slug is the SKILL.md's parent directory name (e.g. ``paper-evaluate``).
    On conflict, the earliest root wins.
    """
    roots = roots if roots is not None else DEFAULT_SKILL_ROOTS
    found: dict[str, SkillFrontmatter] = {}
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for skill_md in sorted(root.glob("*/SKILL.md")):
            slug = skill_md.parent.name
            if slug in found:
                continue
            fm = load_skill(skill_md)
            if fm is not None:
                found[slug] = fm
    return found


# ---------------------------------------------------------------------------
# Stage checking
# ---------------------------------------------------------------------------


def _normalize_stage(stage: str | ResearchStage) -> str:
    if isinstance(stage, ResearchStage):
        return stage.value
    return str(stage).strip().lower()


@dataclass
class StageCheckResult:
    verdict: SkillStageCheckVerdict
    skill_name: str
    project_stage: str
    valid_stages: list[str]
    message: str


def check_skill_stage(
    skill_name: str,
    project_stage: str | ResearchStage,
    *,
    skills: dict[str, SkillFrontmatter] | None = None,
) -> StageCheckResult:
    """Check whether ``skill_name`` is valid in ``project_stage``.

    Verdicts:

    - ``"in_stage"``: the skill's ``research_stages`` contains the current stage.
    - ``"out_of_stage"``: the skill exists and declares stages, but the
      current stage is not in the list. Caller should warn the human.
    - ``"unknown_stage"``: the skill exists but does not declare
      ``research_stages`` (legacy). Caller may warn or proceed.
    - ``"unknown_skill"``: no such skill in the discovered set. Caller
      should treat this as an error (probably a typo).
    """
    skills = skills if skills is not None else discover_skills()
    normalized = _normalize_stage(project_stage)

    fm = skills.get(skill_name)
    if fm is None:
        return StageCheckResult(
            verdict="unknown_skill",
            skill_name=skill_name,
            project_stage=normalized,
            valid_stages=[],
            message=f"Unknown skill {skill_name!r}; did you mean one of {sorted(skills.keys())}?",
        )

    if not fm.research_stages:
        return StageCheckResult(
            verdict="unknown_stage",
            skill_name=skill_name,
            project_stage=normalized,
            valid_stages=[],
            message=(
                f"Skill {skill_name!r} does not declare research_stages; "
                f"cannot confirm it's valid in {normalized!r}."
            ),
        )

    valid = [_normalize_stage(s) for s in fm.research_stages]
    if normalized in valid:
        return StageCheckResult(
            verdict="in_stage",
            skill_name=skill_name,
            project_stage=normalized,
            valid_stages=valid,
            message=f"{skill_name} is valid in {normalized}",
        )

    return StageCheckResult(
        verdict="out_of_stage",
        skill_name=skill_name,
        project_stage=normalized,
        valid_stages=valid,
        message=(
            f"⚠ {skill_name} is declared valid in stages {valid} but "
            f"the project is currently in {normalized!r}. "
            f"Pass --force to invoke anyway; the override will be logged."
        ),
    )
