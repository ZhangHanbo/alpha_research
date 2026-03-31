"""Understanding agent — produces structured project understanding.

LLM-based agent that reads source material and produces an
UnderstandingSnapshot.  Supports both fresh understanding (on project
create) and refreshed understanding (on resume with source changes).

Source: project_lifecycle_revision_plan.md §128-135, §808-820
"""

from __future__ import annotations

import json
from typing import Any

from alpha_research.models.project import ProjectManifest
from alpha_research.models.snapshot import SourceSnapshot, UnderstandingSnapshot
from alpha_research.prompts.understanding_system import build_understanding_prompt

# Type alias for LLM callable: async (system, user) -> str
LLMCallable = Any


class UnderstandingAgent:
    """Produces structured understanding of a project's source material.

    Parameters
    ----------
    llm : LLMCallable | None
        Async callable ``(system_prompt, user_message) -> str``.
        If None, returns a stub understanding (for testing).
    """

    def __init__(self, llm: LLMCallable | None = None) -> None:
        self.llm = llm

    async def understand(
        self,
        project: ProjectManifest,
        source_snapshot: SourceSnapshot,
        file_contents: dict[str, str],
    ) -> UnderstandingSnapshot:
        """Produce a fresh understanding of the project.

        Parameters
        ----------
        project : ProjectManifest
            The project being understood.
        source_snapshot : SourceSnapshot
            The captured source state.
        file_contents : dict[str, str]
            Mapping of file paths to their contents.  The caller is
            responsible for selecting files and enforcing token limits.
        """
        source_summary = _build_source_summary(file_contents)

        system = build_understanding_prompt(
            project_type=project.project_type.value,
            project_name=project.name,
            primary_question=project.primary_question,
            source_summary=source_summary,
        )

        if self.llm is None:
            return _stub_understanding(project, source_snapshot, file_contents)

        user_msg = (
            "Analyze the source material and produce a structured "
            "understanding of this project."
        )
        response = await self.llm(system, user_msg)
        return _parse_response(response, project, source_snapshot)

    async def refresh_understanding(
        self,
        project: ProjectManifest,
        previous: UnderstandingSnapshot,
        source_snapshot: SourceSnapshot,
        source_delta: str,
        file_contents: dict[str, str],
    ) -> UnderstandingSnapshot:
        """Refresh understanding after source changes.

        Parameters
        ----------
        previous : UnderstandingSnapshot
            The last understanding snapshot.
        source_delta : str
            Human-readable description of what changed.
        """
        source_summary = _build_source_summary(file_contents)

        system = build_understanding_prompt(
            project_type=project.project_type.value,
            project_name=project.name,
            primary_question=project.primary_question,
            source_summary=source_summary,
            previous_understanding=previous.model_dump_json(indent=2),
            source_delta=source_delta,
        )

        if self.llm is None:
            return _stub_understanding(
                project, source_snapshot, file_contents,
                note="Refreshed (stub — no LLM)",
            )

        user_msg = (
            "The source has changed since the last understanding. "
            "Refresh the understanding to reflect the current state."
        )
        response = await self.llm(system, user_msg)
        return _parse_response(response, project, source_snapshot)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_source_summary(file_contents: dict[str, str]) -> str:
    """Build a summary of available files for the prompt."""
    if not file_contents:
        return "No source files provided."

    lines = [f"**{len(file_contents)} files provided:**\n"]
    for path in sorted(file_contents.keys()):
        size = len(file_contents[path])
        lines.append(f"- `{path}` ({size:,} chars)")

    lines.append("\n---\n")
    for path, content in sorted(file_contents.items()):
        lines.append(f"### `{path}`\n```\n{content}\n```\n")

    return "\n".join(lines)


def _stub_understanding(
    project: ProjectManifest,
    source_snapshot: SourceSnapshot,
    file_contents: dict[str, str],
    note: str = "Stub — no LLM available",
) -> UnderstandingSnapshot:
    """Return a minimal understanding when no LLM is available."""
    return UnderstandingSnapshot(
        project_id=project.project_id,
        source_snapshot_id=source_snapshot.source_snapshot_id,
        summary=f"Project '{project.name}': {note}",
        important_paths=sorted(file_contents.keys())[:10],
        open_questions=[
            "What is the primary research contribution?",
            "What is the current implementation status?",
            "What are the key open problems?",
        ],
        warnings=[note],
        confidence="low",
    )


def _parse_response(
    response_text: str,
    project: ProjectManifest,
    source_snapshot: SourceSnapshot,
) -> UnderstandingSnapshot:
    """Parse LLM response into an UnderstandingSnapshot."""
    text = response_text.strip()

    # Extract JSON from markdown fences if present
    if "```json" in text:
        start = text.index("```json") + len("```json")
        end = text.index("```", start)
        text = text[start:end].strip()
    elif text.startswith("```"):
        start = text.index("\n") + 1
        end = text.rindex("```")
        text = text[start:end].strip()

    # Find outermost braces
    first = text.find("{")
    if first != -1:
        depth = 0
        for i in range(first, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    text = text[first:i + 1]
                    break

    data = json.loads(text)

    return UnderstandingSnapshot(
        project_id=project.project_id,
        source_snapshot_id=source_snapshot.source_snapshot_id,
        summary=data.get("summary", ""),
        architecture_map=data.get("architecture_map", {}),
        important_paths=data.get("important_paths", []),
        open_questions=data.get("open_questions", []),
        assumptions=data.get("assumptions", []),
        warnings=data.get("warnings", []),
        confidence=data.get("confidence", "low"),
    )
