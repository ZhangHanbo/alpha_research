"""Resume lifecycle service (deterministic, no LLM).

Implements the three resume modes from the lifecycle revision plan.
Prepares resume context that the understanding agent and orchestrator
consume — does not call LLM agents itself.

Source: project_lifecycle_revision_plan.md §152-166, §666-709
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from alpha_research.models.project import ProjectManifest, ProjectState
from alpha_research.models.snapshot import (
    SourceSnapshot,
    UnderstandingSnapshot,
)
from alpha_research.projects.git_state import (
    capture_source_snapshot,
    create_worktree,
)
from alpha_research.projects.snapshots import SnapshotWriter


class ResumeMode(str, Enum):
    CURRENT_WORKSPACE = "current_workspace"
    EXACT_SNAPSHOT = "exact_snapshot"
    MILESTONE = "milestone"


@dataclass
class ResumeContext:
    """All context needed to resume a project.

    The orchestrator uses this to drive understanding refresh and
    continued research.
    """

    source_snapshot: SourceSnapshot
    previous_understanding: UnderstandingSnapshot | None = None
    source_delta_summary: str = ""
    worktree_path: str | None = None
    resume_mode: ResumeMode = ResumeMode.CURRENT_WORKSPACE
    source_changed: bool = False


class ResumeService:
    """Deterministic resume lifecycle operations.

    Parameters
    ----------
    project_dir : Path
        On-disk directory of the project.
    """

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = Path(project_dir)
        self.snapshot_writer = SnapshotWriter(project_dir)

    def prepare_resume(
        self,
        manifest: ProjectManifest,
        state: ProjectState,
        mode: ResumeMode = ResumeMode.CURRENT_WORKSPACE,
        snapshot_id: str | None = None,
    ) -> ResumeContext:
        """Prepare context for resuming a project.

        Does NOT call any LLM — only captures source state, loads
        prior snapshots, and computes deltas.
        """
        if mode == ResumeMode.CURRENT_WORKSPACE:
            return self._resume_current_workspace(manifest, state)
        elif mode == ResumeMode.EXACT_SNAPSHOT:
            if snapshot_id is None:
                raise ValueError("exact_snapshot mode requires snapshot_id")
            return self._resume_exact_snapshot(manifest, state, snapshot_id)
        elif mode == ResumeMode.MILESTONE:
            if snapshot_id is None:
                raise ValueError("milestone mode requires snapshot_id")
            return self._resume_exact_snapshot(manifest, state, snapshot_id)
        else:
            raise ValueError(f"Unknown resume mode: {mode}")

    # ------------------------------------------------------------------
    # Mode A: current_workspace
    # ------------------------------------------------------------------

    def _resume_current_workspace(
        self,
        manifest: ProjectManifest,
        state: ProjectState,
    ) -> ResumeContext:
        """Resume from the current workspace state.

        1. Capture fresh SourceSnapshot of bound sources
        2. Compare against the last captured source snapshot
        3. Load previous understanding
        4. Compute source delta summary
        """
        # Capture current source state
        primary_binding = self._get_primary_binding(manifest)
        snap_dir = self.project_dir / "cache" / "resume_capture"
        snap_dir.mkdir(parents=True, exist_ok=True)

        new_source = capture_source_snapshot(primary_binding, snap_dir)

        # Load previous source snapshot and understanding
        prev_source: SourceSnapshot | None = None
        prev_understanding: UnderstandingSnapshot | None = None

        if state.current_snapshot_id:
            prev_source = self.snapshot_writer.load_source_snapshot(
                state.current_snapshot_id
            )
        if state.last_understanding_snapshot_id:
            prev_understanding = self.snapshot_writer.load_understanding(
                state.last_understanding_snapshot_id
            )

        # Compute delta
        source_changed = False
        delta_summary = "No previous snapshot to compare against."

        if prev_source is not None:
            delta_summary = compute_source_delta(prev_source, new_source)
            source_changed = (
                prev_source.source_fingerprint != new_source.source_fingerprint
            )

        return ResumeContext(
            source_snapshot=new_source,
            previous_understanding=prev_understanding,
            source_delta_summary=delta_summary,
            resume_mode=ResumeMode.CURRENT_WORKSPACE,
            source_changed=source_changed,
        )

    # ------------------------------------------------------------------
    # Mode B: exact_snapshot
    # ------------------------------------------------------------------

    def _resume_exact_snapshot(
        self,
        manifest: ProjectManifest,
        state: ProjectState,
        snapshot_id: str,
    ) -> ResumeContext:
        """Resume from an exact historical snapshot.

        1. Load the target ProjectSnapshot
        2. Resolve its SourceSnapshot
        3. If git-backed, create a worktree at the stored commit
        4. Load the understanding from that snapshot
        """
        target_snap = self.snapshot_writer.load_snapshot(snapshot_id)
        source = self.snapshot_writer.load_source_snapshot(snapshot_id)
        understanding = self.snapshot_writer.load_understanding(snapshot_id)

        if source is None:
            raise ValueError(
                f"Snapshot {snapshot_id} has no source snapshot"
            )

        worktree_path: str | None = None

        # Create worktree for git-backed source
        if source.commit_sha and source.repo_root:
            repo = Path(source.repo_root)
            if repo.exists():
                wt_dir = self.project_dir / "cache" / f"worktree-{snapshot_id}"
                try:
                    create_worktree(repo, source.commit_sha, wt_dir)
                    worktree_path = str(wt_dir)

                    # Apply dirty patch if it exists
                    if source.is_dirty and source.patch_path:
                        patch_file = Path(source.patch_path)
                        # Also check inside the snapshot dir
                        if not patch_file.exists():
                            patch_file = (
                                self.snapshot_writer.snapshots_dir
                                / snapshot_id / "patches" / "tracked.diff"
                            )
                        if patch_file.exists():
                            import subprocess
                            subprocess.run(
                                ["git", "apply", str(patch_file)],
                                cwd=wt_dir,
                                check=False,
                                capture_output=True,
                            )
                except Exception:
                    # Worktree creation may fail (e.g., commit no longer exists)
                    worktree_path = None

        return ResumeContext(
            source_snapshot=source,
            previous_understanding=understanding,
            source_delta_summary="Exact snapshot resume — no delta computed.",
            worktree_path=worktree_path,
            resume_mode=ResumeMode.EXACT_SNAPSHOT,
            source_changed=False,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_primary_binding(manifest: ProjectManifest):
        """Return the primary source binding, or the first one."""
        for binding in manifest.source_bindings:
            if binding.is_primary:
                return binding
        if manifest.source_bindings:
            return manifest.source_bindings[0]
        raise ValueError(
            f"Project '{manifest.name}' has no source bindings"
        )


# ---------------------------------------------------------------------------
# Source delta computation
# ---------------------------------------------------------------------------

def compute_source_delta(
    old: SourceSnapshot,
    new: SourceSnapshot,
) -> str:
    """Produce a human-readable summary of what changed between snapshots."""
    lines: list[str] = []

    if old.source_fingerprint == new.source_fingerprint:
        return "No changes detected since the last snapshot."

    # Commit range
    if old.commit_sha and new.commit_sha:
        if old.commit_sha == new.commit_sha:
            lines.append("Same commit, but working tree differs.")
        else:
            lines.append(
                f"Commit range: {old.commit_sha[:8]}..{new.commit_sha[:8]}"
            )

    # Dirty state changes
    if not old.is_dirty and new.is_dirty:
        lines.append("Working tree is now dirty (uncommitted changes).")
    elif old.is_dirty and not new.is_dirty:
        lines.append("Working tree is now clean.")

    # Branch change
    if old.branch_name != new.branch_name:
        lines.append(
            f"Branch changed: {old.branch_name or '(detached)'} "
            f"-> {new.branch_name or '(detached)'}"
        )

    if not lines:
        lines.append("Source fingerprint changed.")

    return "\n".join(lines)
