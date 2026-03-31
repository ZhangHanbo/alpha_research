"""Snapshot persistence service (deterministic, no LLM).

Creates, loads, and lists immutable project snapshots on disk.
Each snapshot is a self-contained directory under
``data/projects/<slug>/snapshots/<snapshot_id>/``.

Source: project_lifecycle_revision_plan.md §117-126, §537-557, §630-658
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from alpha_research.models.snapshot import (
    ProjectSnapshot,
    SnapshotKind,
    SourceSnapshot,
    UnderstandingSnapshot,
)
from alpha_research.projects.git_state import _run_git, is_git_repo


class SnapshotWriter:
    """Persist and retrieve immutable project snapshots.

    Parameters
    ----------
    project_dir : Path
        On-disk directory of the project (``data/projects/<slug>/``).
    """

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = Path(project_dir)
        self.snapshots_dir = self.project_dir / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_project_snapshot(
        self,
        project_id: str,
        kind: str | SnapshotKind,
        source_snapshot: SourceSnapshot,
        understanding_snapshot: UnderstandingSnapshot | None = None,
        blackboard_path: str | None = None,
        run_id: str | None = None,
        parent_snapshot_id: str | None = None,
        summary: str = "",
        note: str = "",
    ) -> ProjectSnapshot:
        """Create an immutable project snapshot on disk.

        Returns the populated :class:`ProjectSnapshot`.
        """
        if isinstance(kind, str):
            kind = SnapshotKind(kind)

        snapshot = ProjectSnapshot(
            project_id=project_id,
            snapshot_kind=kind,
            source_snapshot_id=source_snapshot.source_snapshot_id,
            understanding_snapshot_id=(
                understanding_snapshot.understanding_snapshot_id
                if understanding_snapshot else None
            ),
            blackboard_path=blackboard_path,
            run_id=run_id,
            parent_snapshot_id=parent_snapshot_id,
            summary=summary,
            note=note,
        )

        snap_dir = self.snapshots_dir / snapshot.snapshot_id
        snap_dir.mkdir(parents=True, exist_ok=True)

        # Write the snapshot metadata
        snapshot.save(snap_dir / "snapshot.json")

        # Write the source snapshot
        source_snapshot.save(snap_dir / "source.json")

        # Write understanding snapshot if provided
        if understanding_snapshot is not None:
            understanding_snapshot.save(snap_dir / "understanding.json")

        # Copy the current blackboard into the snapshot
        if blackboard_path:
            bb_src = Path(blackboard_path)
            if bb_src.exists():
                shutil.copy2(bb_src, snap_dir / "blackboard.json")
        else:
            # Try the project-level blackboard
            project_bb = self.project_dir / "blackboard.json"
            if project_bb.exists():
                shutil.copy2(project_bb, snap_dir / "blackboard.json")

        # Copy patch files if they exist in the source snapshot
        if source_snapshot.patch_path:
            patch_src = Path(source_snapshot.patch_path)
            if patch_src.exists():
                patches_dst = snap_dir / "patches"
                patches_dst.mkdir(exist_ok=True)
                shutil.copy2(patch_src, patches_dst / patch_src.name)
        if source_snapshot.untracked_manifest_path:
            manifest_src = Path(source_snapshot.untracked_manifest_path)
            if manifest_src.exists():
                patches_dst = snap_dir / "patches"
                patches_dst.mkdir(exist_ok=True)
                shutil.copy2(manifest_src, patches_dst / manifest_src.name)

        return snapshot

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load_snapshot(self, snapshot_id: str) -> ProjectSnapshot:
        """Load a snapshot by ID."""
        snap_dir = self.snapshots_dir / snapshot_id
        path = snap_dir / "snapshot.json"
        if not path.exists():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_id}")
        return ProjectSnapshot.load(path)

    def load_source_snapshot(self, snapshot_id: str) -> SourceSnapshot | None:
        """Load the source snapshot for a project snapshot."""
        path = self.snapshots_dir / snapshot_id / "source.json"
        if not path.exists():
            return None
        return SourceSnapshot.load(path)

    def load_understanding(self, snapshot_id: str) -> UnderstandingSnapshot | None:
        """Load the understanding snapshot for a project snapshot."""
        path = self.snapshots_dir / snapshot_id / "understanding.json"
        if not path.exists():
            return None
        return UnderstandingSnapshot.load(path)

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def list_snapshots(
        self, kind: SnapshotKind | None = None,
    ) -> list[ProjectSnapshot]:
        """Return all snapshots, sorted by ``created_at`` ascending.

        Optionally filter by ``kind``.
        """
        snapshots: list[ProjectSnapshot] = []
        if not self.snapshots_dir.exists():
            return snapshots
        for snap_dir in sorted(self.snapshots_dir.iterdir()):
            meta = snap_dir / "snapshot.json"
            if meta.exists():
                snap = ProjectSnapshot.load(meta)
                if kind is None or snap.snapshot_kind == kind:
                    snapshots.append(snap)
        snapshots.sort(key=lambda s: s.created_at)
        return snapshots

    def get_latest_snapshot(
        self, kind: SnapshotKind | None = None,
    ) -> ProjectSnapshot | None:
        """Return the most recent snapshot, optionally filtered by kind."""
        snaps = self.list_snapshots(kind=kind)
        return snaps[-1] if snaps else None

    # ------------------------------------------------------------------
    # Milestone tagging
    # ------------------------------------------------------------------

    def tag_milestone(
        self,
        snapshot_id: str,
        tag_name: str,
        project_slug: str,
    ) -> None:
        """Create a git tag at the source snapshot's commit SHA.

        Tag format: ``alpha-research/<project_slug>/milestone/<tag_name>``
        """
        source = self.load_source_snapshot(snapshot_id)
        if source is None or not source.commit_sha:
            return
        repo_root = Path(source.repo_root)
        if not repo_root.exists() or not is_git_repo(repo_root):
            return
        tag = f"alpha-research/{project_slug}/milestone/{tag_name}"
        _run_git(
            ["tag", tag, source.commit_sha],
            cwd=repo_root,
            check=False,  # don't fail if tag already exists
        )
