"""Project registry backed by a JSON index file.

Maintains a lightweight index of all known projects at
``<base_dir>/index.json``.  Each entry stores just enough metadata to
list and locate projects; the full ``ProjectManifest`` lives inside the
project's own directory.
"""

from __future__ import annotations

import json
from pathlib import Path

from alpha_research.models.project import ProjectManifest


class ProjectRegistry:
    """Registry of known projects, backed by ``index.json``."""

    def __init__(self, base_dir: str | Path = "data/projects") -> None:
        self.base_dir = Path(base_dir)
        self._index_path = self.base_dir / "index.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if not self._index_path.exists():
            self._index_path.write_text("[]")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_index(self) -> list[dict]:
        return json.loads(self._index_path.read_text())

    def _write_index(self, entries: list[dict]) -> None:
        self._index_path.write_text(json.dumps(entries, indent=2))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_projects(self) -> list[ProjectManifest]:
        """Return full manifests for every registered project."""
        manifests: list[ProjectManifest] = []
        for entry in self._read_index():
            project_dir = Path(entry["project_dir"])
            manifest_path = project_dir / "project.json"
            if manifest_path.exists():
                manifests.append(ProjectManifest.load(manifest_path))
        return manifests

    def get_project(self, project_id: str) -> ProjectManifest | None:
        """Look up a single project by id.  Returns ``None`` if unknown."""
        for entry in self._read_index():
            if entry["project_id"] == project_id:
                manifest_path = Path(entry["project_dir"]) / "project.json"
                if manifest_path.exists():
                    return ProjectManifest.load(manifest_path)
                return None
        return None

    def register_project(self, manifest: ProjectManifest) -> None:
        """Add (or update) a project entry in the index."""
        entries = self._read_index()
        # Remove any existing entry with the same project_id
        entries = [e for e in entries if e["project_id"] != manifest.project_id]
        project_dir = str(self.base_dir / manifest.slug)
        entries.append({
            "project_id": manifest.project_id,
            "slug": manifest.slug,
            "name": manifest.name,
            "project_dir": project_dir,
        })
        self._write_index(entries)

    def remove_project(self, project_id: str) -> None:
        """Remove a project from the index (does *not* delete files)."""
        entries = self._read_index()
        entries = [e for e in entries if e["project_id"] != project_id]
        self._write_index(entries)
