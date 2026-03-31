"""Core project lifecycle service (deterministic, no LLM).

Creates, loads, and mutates project state on disk.  All operations are
file-system based and require no network or model access.
"""

from __future__ import annotations

import re
from pathlib import Path

from alpha_research.knowledge.store import KnowledgeStore
from alpha_research.models.blackboard import Blackboard
from alpha_research.models.project import (
    BindingType,
    OperationalStatus,
    ProjectManifest,
    ProjectState,
    ProjectType,
    SourceBinding,
)
from alpha_research.projects.registry import ProjectRegistry


def _slugify(name: str) -> str:
    """Convert a project name to a filesystem-safe slug."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)   # drop special chars
    slug = re.sub(r"[\s]+", "-", slug)           # spaces -> hyphens
    slug = re.sub(r"-{2,}", "-", slug)           # collapse runs
    slug = slug.strip("-")
    return slug


# Subdirectories created inside every project folder
_PROJECT_SUBDIRS = [
    "runs",
    "snapshots",
    "reports",
    "notes",
    "cache",
]


class ProjectService:
    """Deterministic project lifecycle operations."""

    def __init__(self, registry: ProjectRegistry) -> None:
        self.registry = registry

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    def create_project(
        self,
        name: str,
        project_type: str,
        primary_question: str,
        source_path: str | None = None,
        description: str = "",
        domain: str = "",
        tags: list[str] | None = None,
    ) -> ProjectManifest:
        """Create a new project with full on-disk directory structure.

        Returns the saved ``ProjectManifest``.
        """
        manifest = ProjectManifest(
            name=name,
            slug=_slugify(name),
            project_type=ProjectType(project_type),
            primary_question=primary_question,
            description=description,
            domain=domain,
            tags=tags or [],
        )

        # Optional source binding
        if source_path:
            binding = SourceBinding(
                binding_type=BindingType.DIRECTORY,
                root_path=source_path,
                is_primary=True,
            )
            manifest.source_bindings.append(binding)

        project_dir = self.registry.base_dir / manifest.slug

        # Create directory skeleton
        project_dir.mkdir(parents=True, exist_ok=True)
        for subdir in _PROJECT_SUBDIRS:
            (project_dir / subdir).mkdir(exist_ok=True)

        # Persist manifest
        manifest.save(project_dir / "project.json")

        # Persist initial state
        state = ProjectState(project_id=manifest.project_id)
        state.save(project_dir / "state.json")

        # Persist empty blackboard
        bb = Blackboard()
        bb.save(project_dir / "blackboard.json")

        # Auto-create knowledge store (creates knowledge.db)
        KnowledgeStore(project_dir / "knowledge.db")

        # Register in index
        self.registry.register_project(manifest)

        return manifest

    # ------------------------------------------------------------------
    # load
    # ------------------------------------------------------------------

    def load_project(
        self, project_id: str
    ) -> tuple[ProjectManifest, ProjectState]:
        """Load manifest and state from disk for an existing project."""
        project_dir = self.get_project_dir(project_id)
        manifest = ProjectManifest.load(project_dir / "project.json")
        state = ProjectState.load(project_dir / "state.json")
        return manifest, state

    # ------------------------------------------------------------------
    # update state
    # ------------------------------------------------------------------

    def update_state(self, project_id: str, **updates) -> ProjectState:
        """Load current state, apply *updates*, save, and return."""
        project_dir = self.get_project_dir(project_id)
        state = ProjectState.load(project_dir / "state.json")
        for key, value in updates.items():
            setattr(state, key, value)
        state.save(project_dir / "state.json")
        return state

    # ------------------------------------------------------------------
    # directory helpers
    # ------------------------------------------------------------------

    def get_project_dir(self, project_id: str) -> Path:
        """Return the on-disk directory for *project_id*.

        Raises ``ValueError`` if the project is not registered.
        """
        manifest = self.registry.get_project(project_id)
        if manifest is None:
            raise ValueError(f"Unknown project: {project_id}")
        return self.registry.base_dir / manifest.slug

    def get_knowledge_store(self, project_id: str) -> KnowledgeStore:
        """Return a ``KnowledgeStore`` scoped to the project's db."""
        project_dir = self.get_project_dir(project_id)
        return KnowledgeStore(project_dir / "knowledge.db")
