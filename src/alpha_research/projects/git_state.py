"""Deterministic git inspection service.

Provides read-only git operations to capture source-tree state for the
project lifecycle.  All git commands are non-destructive: only
inspection, diff, and worktree add/remove are performed.

SAFETY: This module NEVER runs ``git reset``, ``git checkout`` over
files, ``git stash``, ``git push``, or any branch-rewriting command.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

from alpha_research.models.project import BindingType, SourceBinding
from alpha_research.models.snapshot import SourceSnapshot, VcsType


# ---------------------------------------------------------------------------
# Low-level git helpers
# ---------------------------------------------------------------------------

def _run_git(
    args: list[str],
    cwd: Path,
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the CompletedProcess result."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_git_repo(path: Path) -> bool:
    """Check if *path* is inside a git repository."""
    result = _run_git(
        ["rev-parse", "--is-inside-work-tree"],
        cwd=path,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def get_repo_info(path: Path) -> dict:
    """Return repository metadata for *path*.

    Returns a dict with keys:
        root       – absolute path to the repo root
        branch     – current branch name (or "" for detached HEAD)
        commit_sha – full SHA of HEAD
        remote     – origin URL (or "" if no remote)
        is_dirty   – True when the working tree has uncommitted changes
    """
    root = _run_git(
        ["rev-parse", "--show-toplevel"], cwd=path,
    ).stdout.strip()

    commit_sha = _run_git(
        ["rev-parse", "HEAD"], cwd=path,
    ).stdout.strip()

    branch_result = _run_git(
        ["branch", "--show-current"], cwd=path, check=False,
    )
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""

    remote_result = _run_git(
        ["remote", "get-url", "origin"], cwd=path, check=False,
    )
    remote = remote_result.stdout.strip() if remote_result.returncode == 0 else ""

    porcelain = _run_git(
        ["status", "--porcelain"], cwd=path,
    ).stdout.strip()
    is_dirty = len(porcelain) > 0

    return {
        "root": root,
        "branch": branch,
        "commit_sha": commit_sha,
        "remote": remote,
        "is_dirty": is_dirty,
    }


def get_tracked_diff(path: Path) -> str:
    """Return ``git diff HEAD --binary`` output (staged + unstaged)."""
    return _run_git(
        ["diff", "HEAD", "--binary"], cwd=path,
    ).stdout


def get_untracked_files(path: Path) -> list[str]:
    """Return list of untracked file paths relative to the repo root."""
    output = _run_git(
        ["ls-files", "--others", "--exclude-standard"], cwd=path,
    ).stdout.strip()
    if not output:
        return []
    return output.splitlines()


def compute_source_fingerprint(commit_sha: str, diff: str) -> str:
    """Return ``sha256(commit_sha + diff)`` as a hex string."""
    h = hashlib.sha256()
    h.update(commit_sha.encode())
    h.update(diff.encode())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Non-git fingerprint helper
# ---------------------------------------------------------------------------

def _compute_directory_fingerprint(root: Path) -> str:
    """Hash a directory listing (relative paths + sizes) for non-git sources."""
    entries: list[str] = []
    for dirpath, _dirnames, filenames in sorted(os.walk(root)):
        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            rel = fpath.relative_to(root)
            try:
                size = fpath.stat().st_size
            except OSError:
                size = 0
            entries.append(f"{rel}:{size}")
    h = hashlib.sha256()
    h.update("\n".join(entries).encode())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Snapshot capture
# ---------------------------------------------------------------------------

def capture_source_snapshot(
    binding: SourceBinding,
    snapshot_dir: Path,
) -> SourceSnapshot:
    """Capture the current source state for a binding.

    For ``git_repo`` bindings:
      1. Inspect repo via :func:`get_repo_info`.
      2. If dirty: save ``tracked.diff`` and ``untracked_manifest.json``
         under ``snapshot_dir/patches/``.
      3. Compute source fingerprint.
      4. Return a populated :class:`SourceSnapshot`.

    For non-git bindings:
      - Fingerprint = hash of file listing + sizes.
      - ``vcs_type`` = ``"none"``.
    """
    root = Path(binding.root_path)

    if binding.binding_type == BindingType.GIT_REPO and is_git_repo(root):
        return _capture_git_snapshot(binding, root, snapshot_dir)
    return _capture_non_git_snapshot(binding, root, snapshot_dir)


def _capture_git_snapshot(
    binding: SourceBinding,
    root: Path,
    snapshot_dir: Path,
) -> SourceSnapshot:
    info = get_repo_info(root)

    diff = get_tracked_diff(root)
    untracked = get_untracked_files(root)
    fingerprint = compute_source_fingerprint(info["commit_sha"], diff)

    patch_path: str | None = None
    untracked_manifest_path: str | None = None

    if info["is_dirty"]:
        patches_dir = snapshot_dir / "patches"
        patches_dir.mkdir(parents=True, exist_ok=True)

        # Save tracked diff
        diff_file = patches_dir / "tracked.diff"
        diff_file.write_text(diff)
        patch_path = str(diff_file)

        # Save untracked file manifest
        manifest_file = patches_dir / "untracked_manifest.json"
        manifest_file.write_text(json.dumps(untracked, indent=2))
        untracked_manifest_path = str(manifest_file)

    return SourceSnapshot(
        binding_id=binding.binding_id,
        captured_at=datetime.now(),
        vcs_type=VcsType.GIT,
        repo_root=info["root"],
        branch_name=info["branch"] or None,
        commit_sha=info["commit_sha"],
        is_dirty=info["is_dirty"],
        patch_path=patch_path,
        untracked_manifest_path=untracked_manifest_path,
        source_fingerprint=fingerprint,
        selected_paths=binding.include_paths,
    )


def _capture_non_git_snapshot(
    binding: SourceBinding,
    root: Path,
    snapshot_dir: Path,
) -> SourceSnapshot:
    fingerprint = _compute_directory_fingerprint(root)

    return SourceSnapshot(
        binding_id=binding.binding_id,
        captured_at=datetime.now(),
        vcs_type=VcsType.NONE,
        repo_root=str(root),
        source_fingerprint=fingerprint,
        selected_paths=binding.include_paths,
    )


# ---------------------------------------------------------------------------
# Worktree management
# ---------------------------------------------------------------------------

def create_worktree(
    repo_path: Path,
    commit_sha: str,
    target_path: Path,
) -> Path:
    """Create a git worktree at *commit_sha* in *target_path*.

    Uses ``git worktree add --detach`` so the user's current branch and
    working tree are not affected.

    Returns the worktree path.
    """
    _run_git(
        ["worktree", "add", "--detach", str(target_path), commit_sha],
        cwd=repo_path,
    )
    return target_path


def remove_worktree(worktree_path: Path) -> None:
    """Remove a git worktree.

    Uses ``git worktree remove`` so the user's working tree is
    unaffected.
    """
    # Resolve the main repo's .git directory from the worktree via
    # --git-common-dir, then find the main repo root.
    git_common = _run_git(
        ["rev-parse", "--git-common-dir"],
        cwd=worktree_path,
    ).stdout.strip()
    # git_common is the shared .git dir (e.g. /path/to/repo/.git).
    # The main repo root is its parent.
    main_root = Path(git_common).resolve().parent
    _run_git(
        ["worktree", "remove", "--force", str(worktree_path)],
        cwd=main_root,
    )
