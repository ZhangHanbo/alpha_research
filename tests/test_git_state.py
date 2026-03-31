"""Tests for L3: git_state — deterministic git inspection service.

Uses a temporary git repository fixture to verify all read-only git
operations, snapshot capture, and worktree management.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from alpha_research.models.project import BindingType, SourceBinding
from alpha_research.models.snapshot import VcsType
from alpha_research.projects.git_state import (
    capture_source_snapshot,
    compute_source_fingerprint,
    create_worktree,
    get_repo_info,
    get_tracked_diff,
    get_untracked_files,
    is_git_repo,
    remove_worktree,
)


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

@pytest.fixture
def tmp_git_repo(tmp_path):
    """Create a temporary git repo with an initial commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo, check=True, capture_output=True,
    )
    (repo / "main.py").write_text("print('hello')")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo, check=True, capture_output=True,
    )
    return repo


@pytest.fixture
def tmp_non_git_dir(tmp_path):
    """Create a plain directory (not a git repo) with some files."""
    d = tmp_path / "plain"
    d.mkdir()
    (d / "file_a.txt").write_text("aaa")
    (d / "file_b.txt").write_text("bbb")
    sub = d / "sub"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested")
    return d


# -------------------------------------------------------------------
# is_git_repo
# -------------------------------------------------------------------

class TestIsGitRepo:
    def test_returns_true_for_git_repo(self, tmp_git_repo):
        assert is_git_repo(tmp_git_repo) is True

    def test_returns_false_for_non_git_dir(self, tmp_non_git_dir):
        assert is_git_repo(tmp_non_git_dir) is False

    def test_returns_true_for_subdirectory_of_repo(self, tmp_git_repo):
        sub = tmp_git_repo / "subdir"
        sub.mkdir()
        assert is_git_repo(sub) is True


# -------------------------------------------------------------------
# get_repo_info
# -------------------------------------------------------------------

class TestGetRepoInfo:
    def test_returns_correct_fields(self, tmp_git_repo):
        info = get_repo_info(tmp_git_repo)
        assert "root" in info
        assert "branch" in info
        assert "commit_sha" in info
        assert "remote" in info
        assert "is_dirty" in info

    def test_commit_sha_is_valid_hex(self, tmp_git_repo):
        info = get_repo_info(tmp_git_repo)
        assert len(info["commit_sha"]) == 40
        int(info["commit_sha"], 16)  # must be valid hex

    def test_clean_repo(self, tmp_git_repo):
        info = get_repo_info(tmp_git_repo)
        assert info["is_dirty"] is False

    def test_dirty_after_modify(self, tmp_git_repo):
        (tmp_git_repo / "main.py").write_text("print('changed')")
        info = get_repo_info(tmp_git_repo)
        assert info["is_dirty"] is True

    def test_no_remote_returns_empty(self, tmp_git_repo):
        info = get_repo_info(tmp_git_repo)
        assert info["remote"] == ""


# -------------------------------------------------------------------
# get_tracked_diff
# -------------------------------------------------------------------

class TestGetTrackedDiff:
    def test_empty_diff_on_clean_repo(self, tmp_git_repo):
        diff = get_tracked_diff(tmp_git_repo)
        assert diff == ""

    def test_non_empty_diff_after_modify(self, tmp_git_repo):
        (tmp_git_repo / "main.py").write_text("print('changed')")
        diff = get_tracked_diff(tmp_git_repo)
        assert len(diff) > 0
        assert "changed" in diff


# -------------------------------------------------------------------
# get_untracked_files
# -------------------------------------------------------------------

class TestGetUntrackedFiles:
    def test_no_untracked_on_clean(self, tmp_git_repo):
        assert get_untracked_files(tmp_git_repo) == []

    def test_lists_untracked_files(self, tmp_git_repo):
        (tmp_git_repo / "new_file.txt").write_text("new")
        (tmp_git_repo / "another.py").write_text("more")
        untracked = get_untracked_files(tmp_git_repo)
        assert "new_file.txt" in untracked
        assert "another.py" in untracked

    def test_ignores_gitignored_files(self, tmp_git_repo):
        (tmp_git_repo / ".gitignore").write_text("*.log\n")
        subprocess.run(
            ["git", "add", ".gitignore"],
            cwd=tmp_git_repo, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "add gitignore"],
            cwd=tmp_git_repo, check=True, capture_output=True,
        )
        (tmp_git_repo / "debug.log").write_text("log")
        untracked = get_untracked_files(tmp_git_repo)
        assert "debug.log" not in untracked


# -------------------------------------------------------------------
# compute_source_fingerprint
# -------------------------------------------------------------------

class TestComputeSourceFingerprint:
    def test_deterministic(self):
        fp1 = compute_source_fingerprint("abc123", "diff content")
        fp2 = compute_source_fingerprint("abc123", "diff content")
        assert fp1 == fp2

    def test_different_inputs_different_fingerprints(self):
        fp1 = compute_source_fingerprint("abc123", "diff1")
        fp2 = compute_source_fingerprint("abc123", "diff2")
        assert fp1 != fp2

    def test_returns_hex_string(self):
        fp = compute_source_fingerprint("sha", "diff")
        assert len(fp) == 64  # sha256 hex
        int(fp, 16)  # valid hex


# -------------------------------------------------------------------
# capture_source_snapshot — git repo
# -------------------------------------------------------------------

class TestCaptureSourceSnapshotGit:
    def _make_binding(self, repo_path: Path) -> SourceBinding:
        return SourceBinding(
            binding_id="test-binding-1",
            binding_type=BindingType.GIT_REPO,
            root_path=str(repo_path),
        )

    def test_clean_repo(self, tmp_git_repo, tmp_path):
        binding = self._make_binding(tmp_git_repo)
        snap_dir = tmp_path / "snapshots" / "s1"
        snap = capture_source_snapshot(binding, snap_dir)

        assert snap.vcs_type == VcsType.GIT
        assert snap.is_dirty is False
        assert snap.commit_sha is not None
        assert len(snap.source_fingerprint) == 64
        assert snap.binding_id == "test-binding-1"
        assert snap.patch_path is None
        assert snap.untracked_manifest_path is None

    def test_dirty_repo_saves_patch(self, tmp_git_repo, tmp_path):
        (tmp_git_repo / "main.py").write_text("print('dirty')")
        (tmp_git_repo / "untracked.txt").write_text("new file")

        binding = self._make_binding(tmp_git_repo)
        snap_dir = tmp_path / "snapshots" / "s2"
        snap = capture_source_snapshot(binding, snap_dir)

        assert snap.is_dirty is True
        assert snap.patch_path is not None
        assert Path(snap.patch_path).exists()
        assert "dirty" in Path(snap.patch_path).read_text()

        assert snap.untracked_manifest_path is not None
        manifest = json.loads(Path(snap.untracked_manifest_path).read_text())
        assert "untracked.txt" in manifest

    def test_fingerprint_changes_with_edits(self, tmp_git_repo, tmp_path):
        binding = self._make_binding(tmp_git_repo)

        snap1 = capture_source_snapshot(binding, tmp_path / "snap1")

        (tmp_git_repo / "main.py").write_text("print('v2')")
        snap2 = capture_source_snapshot(binding, tmp_path / "snap2")

        assert snap1.source_fingerprint != snap2.source_fingerprint


# -------------------------------------------------------------------
# capture_source_snapshot — non-git directory
# -------------------------------------------------------------------

class TestCaptureSourceSnapshotNonGit:
    def test_non_git_directory(self, tmp_non_git_dir, tmp_path):
        binding = SourceBinding(
            binding_id="dir-binding-1",
            binding_type=BindingType.DIRECTORY,
            root_path=str(tmp_non_git_dir),
        )
        snap_dir = tmp_path / "snapshots" / "s_dir"
        snap = capture_source_snapshot(binding, snap_dir)

        assert snap.vcs_type == VcsType.NONE
        assert snap.commit_sha is None
        assert snap.is_dirty is False
        assert len(snap.source_fingerprint) == 64
        assert snap.binding_id == "dir-binding-1"

    def test_fingerprint_changes_when_files_change(self, tmp_non_git_dir, tmp_path):
        binding = SourceBinding(
            binding_id="dir-binding-2",
            binding_type=BindingType.DIRECTORY,
            root_path=str(tmp_non_git_dir),
        )
        snap1 = capture_source_snapshot(binding, tmp_path / "snap1")

        (tmp_non_git_dir / "file_a.txt").write_text("aaaa_changed")
        snap2 = capture_source_snapshot(binding, tmp_path / "snap2")

        assert snap1.source_fingerprint != snap2.source_fingerprint


# -------------------------------------------------------------------
# create_worktree / remove_worktree
# -------------------------------------------------------------------

class TestWorktree:
    def test_create_and_remove_worktree(self, tmp_git_repo, tmp_path):
        info = get_repo_info(tmp_git_repo)
        wt_path = tmp_path / "worktree_target"

        result = create_worktree(tmp_git_repo, info["commit_sha"], wt_path)
        assert result == wt_path
        assert wt_path.exists()
        assert (wt_path / "main.py").exists()
        assert (wt_path / "main.py").read_text() == "print('hello')"

        remove_worktree(wt_path)
        assert not wt_path.exists()

    def test_worktree_is_isolated(self, tmp_git_repo, tmp_path):
        """Modifying the worktree must not change the original repo."""
        info = get_repo_info(tmp_git_repo)
        wt_path = tmp_path / "wt_isolated"

        create_worktree(tmp_git_repo, info["commit_sha"], wt_path)

        # Modify file in worktree
        (wt_path / "main.py").write_text("print('worktree_change')")

        # Original should be unchanged
        assert (tmp_git_repo / "main.py").read_text() == "print('hello')"

        remove_worktree(wt_path)

    def test_worktree_at_specific_commit(self, tmp_git_repo, tmp_path):
        """Worktree should reflect the state at the specified commit."""
        # Get the initial commit SHA
        initial_sha = get_repo_info(tmp_git_repo)["commit_sha"]

        # Make a second commit
        (tmp_git_repo / "main.py").write_text("print('v2')")
        subprocess.run(
            ["git", "add", "."], cwd=tmp_git_repo,
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "v2"], cwd=tmp_git_repo,
            check=True, capture_output=True,
        )

        # Create worktree at the initial commit
        wt_path = tmp_path / "wt_old"
        create_worktree(tmp_git_repo, initial_sha, wt_path)

        assert (wt_path / "main.py").read_text() == "print('hello')"

        remove_worktree(wt_path)
