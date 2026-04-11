"""Tests for the three-canonical-docs invariant.

Every project scaffolded by ``alpha-research project init`` MUST contain
PROJECT.md, DISCUSSION.md, and LOGS.md. Additionally, ``append_revision_log``
must write agent revision entries into LOGS.md above the
``AGENT_REVISIONS_END`` marker so they stay chronological.

Writes ``tests/reports/test_project_docs_invariant.md``.
"""

from __future__ import annotations

from pathlib import Path

from alpha_research.project import (
    append_revision_log,
    init_project,
)
from alpha_research.records.jsonl import read_records
from alpha_research.templates import REQUIRED_DOCS, scaffold_project_markdown


def _scaffold(tmp_path: Path, name: str) -> Path:
    project_dir = tmp_path / name
    state = init_project(project_dir, project_id=name, question="tactile peg-in-hole")
    scaffold_project_markdown(
        project_dir,
        project_id=name,
        question="tactile peg-in-hole",
        created_at=state.created_at,
    )
    return project_dir


def test_init_creates_three_canonical_docs(tmp_path: Path, report) -> None:
    project_dir = _scaffold(tmp_path, "canonical_docs_demo")

    present = {doc: (project_dir / doc).exists() for doc in REQUIRED_DOCS}
    passed = all(present.values()) and set(REQUIRED_DOCS) == {
        "PROJECT.md", "DISCUSSION.md", "LOGS.md",
    }

    report.record(
        name="project init scaffolds PROJECT.md + DISCUSSION.md + LOGS.md",
        purpose=(
            "Every research project must carry the three canonical docs so "
            "agents always have a stable place to record technical details, "
            "discussions, and revision history."
        ),
        inputs={"project_dir": str(project_dir), "required_docs": list(REQUIRED_DOCS)},
        expected={doc: True for doc in REQUIRED_DOCS},
        actual=present,
        passed=passed,
        conclusion=(
            "Three-doc invariant is enforced at init time. REQUIRED_DOCS is "
            "the single source of truth and the test asserts both the exact "
            "set of names and their presence on disk."
        ),
    )
    assert passed


def test_canonical_docs_have_meaningful_content(tmp_path: Path, report) -> None:
    project_dir = _scaffold(tmp_path, "content_demo")

    sizes = {doc: (project_dir / doc).read_text(encoding="utf-8") for doc in REQUIRED_DOCS}
    details = {doc: {"length": len(text)} for doc, text in sizes.items()}
    passed = (
        len(sizes["PROJECT.md"]) > 200
        and len(sizes["DISCUSSION.md"]) > 200
        and len(sizes["LOGS.md"]) > 200
        and "content_demo" in sizes["PROJECT.md"]  # project_id substitution
        and "content_demo" in sizes["DISCUSSION.md"]
        and "AGENT_REVISIONS_END" in sizes["LOGS.md"]
    )
    report.record(
        name="canonical docs are populated from the templates",
        purpose="After init, each required doc must be non-trivial and templated with the project id.",
        inputs={"project_dir": str(project_dir)},
        expected={
            "PROJECT.md length > 200": True,
            "DISCUSSION.md length > 200": True,
            "LOGS.md length > 200": True,
            "LOGS.md has AGENT_REVISIONS_END marker": True,
        },
        actual={
            **{f"{k} length": v["length"] for k, v in details.items()},
            "LOGS.md has AGENT_REVISIONS_END marker": "AGENT_REVISIONS_END" in sizes["LOGS.md"],
        },
        passed=passed,
        conclusion=(
            "Templates are non-empty and interpolated with the project id. "
            "LOGS.md carries the anchor that append_revision_log relies on."
        ),
    )
    assert passed


def test_append_revision_log_writes_before_marker(tmp_path: Path, report) -> None:
    project_dir = _scaffold(tmp_path, "revision_demo")

    ts = append_revision_log(
        project_dir,
        agent="adversarial-review",
        stage="significance",
        target="PROJECT.md § Scope",
        revision="Narrowed scope to rigid pegs only.",
        result="g1 passed after the narrowing.",
        feedback="Reviewer agreed scope is now defensible.",
    )

    logs_text = (project_dir / "LOGS.md").read_text(encoding="utf-8")
    entry_pos = logs_text.find(f"### {ts}")
    marker_pos = logs_text.find("<!-- AGENT_REVISIONS_END -->")
    passed = (
        entry_pos != -1
        and marker_pos != -1
        and entry_pos < marker_pos
        and "adversarial-review" in logs_text
        and "Narrowed scope to rigid pegs only." in logs_text
        and "Reviewer agreed" in logs_text
    )
    report.record(
        name="append_revision_log injects entry above AGENT_REVISIONS_END",
        purpose=(
            "append_revision_log should insert the structured revision "
            "entry directly before the AGENT_REVISIONS_END marker so "
            "subsequent entries remain chronological and nested under the "
            "'## Agent revisions' section."
        ),
        inputs={
            "agent": "adversarial-review",
            "stage": "significance",
            "target": "PROJECT.md § Scope",
            "revision": "Narrowed scope to rigid pegs only.",
        },
        expected={
            "entry_before_marker": True,
            "contains_agent_name": True,
            "contains_revision_text": True,
            "contains_feedback": True,
        },
        actual={
            "entry_before_marker": entry_pos != -1 and entry_pos < marker_pos,
            "contains_agent_name": "adversarial-review" in logs_text,
            "contains_revision_text": "Narrowed scope to rigid pegs only." in logs_text,
            "contains_feedback": "Reviewer agreed" in logs_text,
            "timestamp": ts,
        },
        passed=passed,
        conclusion=(
            "Agents can now append a human-readable audit entry to LOGS.md "
            "that sits next to — and never displaces — the weekly log section."
        ),
    )
    assert passed


def test_append_revision_log_also_writes_provenance(tmp_path: Path, report) -> None:
    project_dir = _scaffold(tmp_path, "provenance_demo")

    append_revision_log(
        project_dir,
        agent="paper-evaluate",
        stage="formalization",
        target="evaluation.jsonl",
        revision="Scored paper against Appendix B rubric.",
    )

    prov = read_records(project_dir, "provenance")
    # init_project writes the first provenance record, append_revision_log
    # writes the second.
    agent_entries = [r for r in prov if r.get("action_name") == "paper-evaluate"]
    passed = len(agent_entries) == 1 and agent_entries[0]["project_stage"] == "formalization"
    report.record(
        name="append_revision_log also appends a provenance record",
        purpose=(
            "Every revision entry in LOGS.md should have a matching "
            "provenance.jsonl record so the audit trail stays synchronized "
            "across the markdown log and the structured store."
        ),
        inputs={"agent": "paper-evaluate", "stage": "formalization"},
        expected={"provenance_records_for_agent": 1, "stage": "formalization"},
        actual={
            "provenance_records_for_agent": len(agent_entries),
            "stage": agent_entries[0]["project_stage"] if agent_entries else None,
        },
        passed=passed,
        conclusion=(
            "Dual-write keeps markdown and JSONL in lockstep so a reviewer "
            "can follow either representation without drift."
        ),
    )
    assert passed


def test_append_revision_log_missing_file_raises(tmp_path: Path, report) -> None:
    empty = tmp_path / "not_a_project"
    empty.mkdir()

    raised = False
    try:
        append_revision_log(
            empty,
            agent="x",
            stage="significance",
            target="y",
            revision="z",
        )
    except FileNotFoundError:
        raised = True

    report.record(
        name="append_revision_log refuses to create LOGS.md implicitly",
        purpose=(
            "The helper must raise FileNotFoundError when LOGS.md is "
            "missing — callers should run `project init` first instead of "
            "the helper silently auto-creating a stub."
        ),
        inputs={"project_dir": str(empty)},
        expected={"raises_FileNotFoundError": True},
        actual={"raises_FileNotFoundError": raised},
        passed=raised,
        conclusion=(
            "Fail-fast makes the three-doc invariant load-bearing — every "
            "agent that revises a project can trust LOGS.md exists or learn "
            "immediately that it does not."
        ),
    )
    assert raised
