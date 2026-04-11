"""Templates for project scaffolding.

The project-lifecycle CLI verbs (``project init`` in particular) copy
these templates into the new project directory. They're plain markdown
with simple ``{{placeholder}}`` string interpolation — no Jinja2 needed
for the small number of substitutions we actually make, and keeping them
as raw markdown means a human can read/edit them without running any
tooling.
"""

from __future__ import annotations

from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "project"

# The three canonical top-level docs that every project must carry:
#   PROJECT.md    — technical details, always kept up to date
#   DISCUSSION.md — append-only record of researcher ↔ agent discussions
#   LOGS.md       — append-only log (agent revisions + weekly entries)
#
# The remaining files are stage-specific artifacts used by the g2..g5
# forward guards and the research-plan §2.4 state machine.
REQUIRED_DOCS: tuple[str, ...] = (
    "PROJECT.md",
    "DISCUSSION.md",
    "LOGS.md",
)

PROJECT_TEMPLATES: tuple[str, ...] = (
    *REQUIRED_DOCS,
    "hamming.md",
    "formalization.md",
    "benchmarks.md",
    "one_sentence.md",
)


def render(name: str, **substitutions: str) -> str:
    """Return the rendered text of one project template.

    Substitutions are simple ``str.replace`` calls on ``{{key}}`` — no
    escape handling, no Jinja, no surprises. Unknown keys are left as-is.
    """
    path = TEMPLATES_DIR / name
    text = path.read_text(encoding="utf-8")
    for key, value in substitutions.items():
        text = text.replace(f"{{{{{key}}}}}", value or "")
    return text


def scaffold_project_markdown(
    project_dir: Path,
    *,
    project_id: str,
    question: str,
    created_at: str,
) -> list[Path]:
    """Write all project markdown templates into ``project_dir``.

    Returns the list of paths written. Existing files are NOT overwritten
    — a researcher who has already customized their project.md shouldn't
    have it clobbered by a re-run.
    """
    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name in PROJECT_TEMPLATES:
        dest = project_dir / name
        if dest.exists():
            continue
        text = render(
            name,
            project_id=project_id,
            question=question,
            created_at=created_at,
        )
        dest.write_text(text, encoding="utf-8")
        written.append(dest)
    return written
