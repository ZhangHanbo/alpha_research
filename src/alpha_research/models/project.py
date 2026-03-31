"""Project lifecycle models.

Defines the durable project container, source bindings, and mutable
operational state.  These are the top-level lifecycle abstractions that
wrap the existing blackboard-and-agent core.

Source: project_lifecycle_revision_plan.md §55-110, §432-494
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _new_id() -> str:
    return uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProjectType(str, Enum):
    LITERATURE = "literature"
    CODEBASE = "codebase"
    HYBRID = "hybrid"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class OperationalStatus(str, Enum):
    IDLE = "idle"
    UNDERSTANDING = "understanding"
    RESEARCHING = "researching"
    REVIEWING = "reviewing"
    PAUSED = "paused"
    ERROR = "error"


class BindingType(str, Enum):
    GIT_REPO = "git_repo"
    DIRECTORY = "directory"
    PAPER_SET = "paper_set"
    ARTIFACT_SET = "artifact_set"


# ---------------------------------------------------------------------------
# Source Binding
# ---------------------------------------------------------------------------

class SourceBinding(BaseModel):
    """Formal link from a project to an external source root."""

    binding_id: str = Field(default_factory=_new_id)
    binding_type: BindingType = BindingType.DIRECTORY
    root_path: str = ""
    include_paths: list[str] = Field(default_factory=list)
    exclude_paths: list[str] = Field(default_factory=list)
    is_primary: bool = True
    repo_remote: str | None = None
    tracked_branch: str | None = None
    default_worktree_path: str | None = None


# ---------------------------------------------------------------------------
# Project Manifest — stable identity
# ---------------------------------------------------------------------------

class ProjectManifest(BaseModel):
    """Stable identity and configuration for a research project.

    This is the mostly-immutable part of a project.  Changes are rare
    (rename, add source binding, change status).
    """

    project_id: str = Field(default_factory=_new_id)
    slug: str = ""
    name: str = ""
    description: str = ""
    project_type: ProjectType = ProjectType.LITERATURE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: ProjectStatus = ProjectStatus.DRAFT
    primary_question: str = ""
    domain: str = ""
    tags: list[str] = Field(default_factory=list)
    source_bindings: list[SourceBinding] = Field(default_factory=list)
    default_resume_mode: str = "current_workspace"
    alpha_research_version: str = "0.1.0"

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(
            self.model_dump(mode="json"), indent=2, default=str,
        ))

    @classmethod
    def load(cls, path: Path) -> ProjectManifest:
        return cls.model_validate(json.loads(path.read_text()))


# ---------------------------------------------------------------------------
# Project State — mutable operational head
# ---------------------------------------------------------------------------

class ProjectState(BaseModel):
    """Mutable operational head of a project.

    Changes frequently — updated after every run, snapshot, and resume.
    """

    project_id: str = ""
    current_snapshot_id: str | None = None
    current_blackboard_path: str | None = None
    current_status: OperationalStatus = OperationalStatus.IDLE
    last_understanding_snapshot_id: str | None = None
    last_completed_run_id: str | None = None
    active_run_id: str | None = None
    resume_required: bool = False
    source_changed_since_last_snapshot: bool = False
    last_seen_source_snapshot_id: str | None = None
    last_resumed_at: datetime | None = None
    notes: str = ""

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(
            self.model_dump(mode="json"), indent=2, default=str,
        ))

    @classmethod
    def load(cls, path: Path) -> ProjectState:
        return cls.model_validate(json.loads(path.read_text()))
