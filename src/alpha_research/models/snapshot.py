"""Snapshot and run models for the project lifecycle.

Defines immutable checkpoint types (source, understanding, project) and
the execution record (research run).  Once created, snapshot objects
should not be mutated.

Source: project_lifecycle_revision_plan.md §117-177, §495-578
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field


def _new_id() -> str:
    return uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VcsType(str, Enum):
    GIT = "git"
    NONE = "none"


class SnapshotKind(str, Enum):
    CREATE = "create"
    RESUME = "resume"
    PRE_RUN = "pre_run"
    POST_RUN = "post_run"
    MILESTONE = "milestone"
    MANUAL = "manual"


class RunType(str, Enum):
    UNDERSTANDING = "understanding"
    DIGEST = "digest"
    DEEP = "deep"
    LOOP = "loop"
    RESUME_REFRESH = "resume_refresh"


class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Source Snapshot — immutable captured source-tree state
# ---------------------------------------------------------------------------

class SourceSnapshot(BaseModel):
    """Immutable record of source-tree state at a point in time.

    For git-backed projects the authoritative identifier is
    ``commit_sha``.  If the working tree was dirty, the delta is
    preserved via ``patch_path`` and ``untracked_manifest_path``.
    """

    source_snapshot_id: str = Field(default_factory=_new_id)
    binding_id: str = ""
    captured_at: datetime = Field(default_factory=datetime.now)
    vcs_type: VcsType = VcsType.NONE
    repo_root: str = ""
    branch_name: str | None = None
    commit_sha: str | None = None
    is_dirty: bool = False
    patch_path: str | None = None
    untracked_manifest_path: str | None = None
    source_fingerprint: str = ""
    selected_paths: list[str] = Field(default_factory=list)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(
            self.model_dump(mode="json"), indent=2, default=str,
        ))

    @classmethod
    def load(cls, path: Path) -> SourceSnapshot:
        return cls.model_validate(json.loads(path.read_text()))


# ---------------------------------------------------------------------------
# Understanding Snapshot — derived structured understanding
# ---------------------------------------------------------------------------

class UnderstandingSnapshot(BaseModel):
    """Agent-produced structured interpretation of a project at a
    specific source snapshot.  This is a derived artifact, not a
    source of truth.
    """

    understanding_snapshot_id: str = Field(default_factory=_new_id)
    project_id: str = ""
    source_snapshot_id: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    summary: str = ""
    architecture_map: dict[str, str] = Field(default_factory=dict)
    important_paths: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    confidence: str = "low"

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(
            self.model_dump(mode="json"), indent=2, default=str,
        ))

    @classmethod
    def load(cls, path: Path) -> UnderstandingSnapshot:
        return cls.model_validate(json.loads(path.read_text()))


# ---------------------------------------------------------------------------
# Project Snapshot — immutable checkpoint binding everything together
# ---------------------------------------------------------------------------

class ProjectSnapshot(BaseModel):
    """Immutable checkpoint that binds source state, understanding,
    blackboard, and artifacts together.

    Every important moment in the project should be represented as a
    project snapshot.  Once written, snapshot contents must not be
    modified.
    """

    snapshot_id: str = Field(default_factory=_new_id)
    project_id: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    snapshot_kind: SnapshotKind = SnapshotKind.MANUAL
    parent_snapshot_id: str | None = None
    source_snapshot_id: str = ""
    understanding_snapshot_id: str | None = None
    blackboard_path: str | None = None
    artifact_refs: list[str] = Field(default_factory=list)
    run_id: str | None = None
    summary: str = ""
    note: str = ""

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(
            self.model_dump(mode="json"), indent=2, default=str,
        ))

    @classmethod
    def load(cls, path: Path) -> ProjectSnapshot:
        return cls.model_validate(json.loads(path.read_text()))


# ---------------------------------------------------------------------------
# Research Run — immutable execution record
# ---------------------------------------------------------------------------

class ResearchRun(BaseModel):
    """Record of one bounded execution of the system against a project."""

    run_id: str = Field(default_factory=_new_id)
    project_id: str = ""
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime | None = None
    run_type: RunType = RunType.DIGEST
    question: str = ""
    status: RunStatus = RunStatus.RUNNING
    input_snapshot_id: str | None = None
    output_snapshot_id: str | None = None
    outputs: list[str] = Field(default_factory=list)
    summary: str = ""
    error: str = ""

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(
            self.model_dump(mode="json"), indent=2, default=str,
        ))

    @classmethod
    def load(cls, path: Path) -> ResearchRun:
        return cls.model_validate(json.loads(path.read_text()))
