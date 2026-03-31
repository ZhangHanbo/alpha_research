"""Understanding agent system prompt builder.

Builds a system prompt that instructs the agent to produce a structured
UnderstandingSnapshot from source material.  Parameterized by project
type (codebase, literature, hybrid) and whether this is a fresh
understanding or a refresh after source changes.

Source: project_lifecycle_revision_plan.md §128-135, §808-820
"""

from __future__ import annotations


def build_understanding_prompt(
    project_type: str,
    project_name: str = "",
    primary_question: str = "",
    source_summary: str = "",
    previous_understanding: str | None = None,
    source_delta: str | None = None,
) -> str:
    """Build the system prompt for the understanding agent.

    Args:
        project_type: "codebase", "literature", or "hybrid".
        project_name: Human-readable project name.
        primary_question: The driving research question.
        source_summary: Summary of available source material
            (file listing, paper titles, etc.).
        previous_understanding: JSON of the prior UnderstandingSnapshot
            (for refresh mode).
        source_delta: Human-readable description of what changed since
            the last understanding (for refresh mode).

    Returns:
        Complete system prompt string.
    """
    sections: list[str] = []

    sections.append(_identity_section(project_type, project_name))
    sections.append(_type_specific_section(project_type))

    if primary_question:
        sections.append(f"# Research Question\n\n{primary_question}")

    if source_summary:
        sections.append(f"# Available Source Material\n\n{source_summary}")

    if previous_understanding and source_delta:
        sections.append(_refresh_section(previous_understanding, source_delta))

    sections.append(_output_format_section())

    return "\n\n".join(sections)


def _identity_section(project_type: str, project_name: str) -> str:
    return f"""\
# Identity

You are a **project understanding agent** analyzing the project \
"{project_name or 'unnamed'}".

Your task is to produce a structured understanding of the project's \
current state. This understanding will be used by research and review \
agents as context. It must be accurate, specific, and honest about \
uncertainty.

Project type: **{project_type}**

## Rules

1. **Be specific.** Name files, modules, classes, papers, and methods \
by their actual names. Do not generalize.
2. **Flag uncertainty.** If you cannot determine something from the \
provided material, say so explicitly in the ``warnings`` field.
3. **Identify open questions.** What would a researcher need to \
investigate next? What is unclear or under-specified?
4. **State assumptions.** What are you assuming about the project \
that is not explicitly confirmed by the source material?"""


def _type_specific_section(project_type: str) -> str:
    if project_type == "codebase":
        return """\
# Codebase Understanding Requirements

For a codebase project, your understanding must cover:

1. **Architecture map:** Top-level modules and their responsibilities. \
Key entry points. Data flow between components.
2. **Important paths:** Files and directories that are most relevant \
to the research question.  Configuration files. Test directories.
3. **Dependencies:** Key external libraries and frameworks. \
Language and runtime versions.
4. **Open questions:** What is unclear about the codebase? \
What needs human clarification? What might be technical debt vs. \
intentional design?
5. **Assumptions:** What are you assuming about the project's \
conventions, patterns, and intended behavior?"""

    elif project_type == "literature":
        return """\
# Literature Understanding Requirements

For a literature project, your understanding must cover:

1. **Research landscape:** Key themes, subfields, and methodological \
approaches relevant to the research question.
2. **Important references:** Papers, authors, and groups that appear \
central to the topic.  Known landmark results.
3. **Open questions:** What gaps exist in the current literature? \
What is contentious or unresolved?
4. **Assumptions:** What scope boundaries are you assuming? \
What fields are you including or excluding?
5. **Methodology notes:** What evaluation criteria, venues, or \
standards are relevant?"""

    else:  # hybrid
        return """\
# Hybrid Understanding Requirements

For a hybrid project (codebase + literature), your understanding \
must cover BOTH:

**Codebase side:**
1. Architecture map, important paths, dependencies
2. How the code relates to the research question
3. What the code currently implements vs. what is planned

**Literature side:**
1. Research landscape, key references, methodological approaches
2. How the literature informs the codebase design
3. Gaps between the code and the state of the art

**Connections:**
1. Which papers informed which code modules?
2. Where does the code diverge from published approaches?
3. What literature gaps does the code attempt to address?"""


def _refresh_section(previous_understanding: str, source_delta: str) -> str:
    return f"""\
# Refresh Mode — Source Has Changed

You are REFRESHING an existing understanding, not creating one from \
scratch.  The source material has changed since the last understanding.

## Previous Understanding

```json
{previous_understanding}
```

## What Changed

{source_delta}

## Refresh Instructions

1. Start from the previous understanding.
2. Identify which parts are still valid and which are invalidated \
by the changes.
3. Update the understanding to reflect the current state.
4. In ``warnings``, note any assumptions from the previous \
understanding that may no longer hold.
5. In ``open_questions``, add new questions raised by the changes.
6. Do NOT discard valid prior understanding — refine it."""


def _output_format_section() -> str:
    return """\
# Output Format

You MUST produce your output as valid JSON matching this schema:

```json
{
  "summary": "<2-4 sentence overview of the project's current state>",
  "architecture_map": {
    "<component_name>": "<one-line description of responsibility>",
    ...
  },
  "important_paths": [
    "<path/to/important/file_or_dir>",
    ...
  ],
  "open_questions": [
    "<specific question that needs investigation>",
    ...
  ],
  "assumptions": [
    "<assumption you are making about the project>",
    ...
  ],
  "warnings": [
    "<anything you are uncertain about or that may be wrong>",
    ...
  ],
  "confidence": "high|medium|low"
}
```

Rules:
- ``summary`` must be concrete and specific to THIS project.
- ``architecture_map`` keys should be actual module/component names.
- ``important_paths`` should be real file or directory paths from the source.
- ``open_questions`` should be answerable with more investigation.
- ``confidence`` reflects your overall confidence in this understanding.
- Minimum 3 items each in ``important_paths`` and ``open_questions``."""
