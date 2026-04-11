"""Unit tests for ``alpha_research.models.snapshot``."""

from __future__ import annotations

from pathlib import Path

from alpha_research.models.snapshot import (
    ProjectSnapshot,
    ResearchRun,
    RunStatus,
    RunType,
    SnapshotKind,
    SourceSnapshot,
    UnderstandingSnapshot,
    VcsType,
)


def test_source_snapshot_defaults(report) -> None:
    s = SourceSnapshot()
    passed = (
        len(s.source_snapshot_id) == 12
        and s.vcs_type == VcsType.NONE
        and s.is_dirty is False
        and s.selected_paths == []
    )
    report.record(
        name="SourceSnapshot defaults are clean",
        purpose="A freshly constructed SourceSnapshot should have a 12-char id, vcs=none, is_dirty=False.",
        inputs={},
        expected={"id_length": 12, "vcs": "none", "is_dirty": False},
        actual={"id_length": len(s.source_snapshot_id), "vcs": s.vcs_type.value, "is_dirty": s.is_dirty},
        passed=passed,
        conclusion="IDs are deterministic-length hex — safe for filenames and record keys.",
    )
    assert passed


def test_source_snapshot_roundtrip(tmp_path: Path, report) -> None:
    s = SourceSnapshot(
        vcs_type=VcsType.GIT,
        repo_root="/tmp/proj",
        branch_name="master",
        commit_sha="abc123",
        is_dirty=True,
        source_fingerprint="fp_abc",
        selected_paths=["src/main.py"],
    )
    path = tmp_path / "source.json"
    s.save(path)
    loaded = SourceSnapshot.load(path)
    passed = (
        loaded.vcs_type == VcsType.GIT
        and loaded.commit_sha == "abc123"
        and loaded.is_dirty is True
        and loaded.selected_paths == ["src/main.py"]
    )
    report.record(
        name="SourceSnapshot JSON round-trip",
        purpose="save/load must preserve vcs_type, commit_sha, dirty flag and selected paths.",
        inputs=s.model_dump(mode="json"),
        expected={
            "vcs_type": "git",
            "commit_sha": "abc123",
            "is_dirty": True,
            "selected_paths": ["src/main.py"],
        },
        actual={
            "vcs_type": loaded.vcs_type.value,
            "commit_sha": loaded.commit_sha,
            "is_dirty": loaded.is_dirty,
            "selected_paths": loaded.selected_paths,
        },
        passed=passed,
        conclusion="Snapshots are an append-only audit trail — persistence fidelity is non-negotiable.",
    )
    assert passed


def test_understanding_snapshot_defaults(report) -> None:
    u = UnderstandingSnapshot()
    passed = u.confidence == "low" and u.architecture_map == {} and u.artifact_refs == []
    report.record(
        name="UnderstandingSnapshot starts with low confidence and empty maps",
        purpose="Derived interpretations default to low confidence so consumers know they are weak signals.",
        inputs={},
        expected={"confidence": "low", "architecture_map": {}, "artifact_refs": []},
        actual={"confidence": u.confidence, "architecture_map": u.architecture_map, "artifact_refs": u.artifact_refs},
        passed=passed,
        conclusion="Low confidence forces downstream code to treat the snapshot as a hypothesis, not fact.",
    )
    assert passed


def test_project_snapshot_save_load(tmp_path: Path, report) -> None:
    p = ProjectSnapshot(
        project_id="proj1",
        snapshot_kind=SnapshotKind.MILESTONE,
        source_snapshot_id="src1",
        understanding_snapshot_id="und1",
        summary="Hit milestone M1",
        note="Ready for review",
    )
    path = tmp_path / "snap.json"
    p.save(path)
    loaded = ProjectSnapshot.load(path)
    passed = (
        loaded.snapshot_kind == SnapshotKind.MILESTONE
        and loaded.source_snapshot_id == "src1"
        and loaded.summary == "Hit milestone M1"
    )
    report.record(
        name="ProjectSnapshot JSON round-trip",
        purpose="save/load must preserve kind, source id, and summary across disk.",
        inputs=p.model_dump(mode="json"),
        expected={"kind": "milestone", "source_id": "src1", "summary": "Hit milestone M1"},
        actual={"kind": loaded.snapshot_kind.value, "source_id": loaded.source_snapshot_id, "summary": loaded.summary},
        passed=passed,
        conclusion="ProjectSnapshot binds source+understanding together — the only reliable resume point.",
    )
    assert passed


def test_research_run_lifecycle(tmp_path: Path, report) -> None:
    r = ResearchRun(
        project_id="proj1",
        run_type=RunType.DIGEST,
        question="tactile insertion",
        status=RunStatus.RUNNING,
    )
    path = tmp_path / "run.json"
    r.save(path)
    loaded = ResearchRun.load(path)
    passed = (
        loaded.run_type == RunType.DIGEST
        and loaded.status == RunStatus.RUNNING
        and loaded.question == "tactile insertion"
    )
    report.record(
        name="ResearchRun round-trips status and type",
        purpose="A ResearchRun record should persist its run_type and initial RUNNING status.",
        inputs=r.model_dump(mode="json"),
        expected={"run_type": "digest", "status": "running"},
        actual={"run_type": loaded.run_type.value, "status": loaded.status.value},
        passed=passed,
        conclusion="Runs can be cancelled / marked-complete out-of-process; persistence must be lossless.",
    )
    assert passed
