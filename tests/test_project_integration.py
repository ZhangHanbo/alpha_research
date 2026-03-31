"""End-to-end integration tests for the project lifecycle.

Exercises the full create -> resume -> research -> snapshot flow using
temporary git repos and temporary project directories.  All tests run
without API keys (understanding agent returns stubs when llm=None).
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest

from alpha_research.models.project import OperationalStatus, ProjectType
from alpha_research.models.snapshot import (
    ProjectSnapshot,
    ResearchRun,
    RunStatus,
    SnapshotKind,
    SourceSnapshot,
)
from alpha_research.projects.orchestrator import ProjectOrchestrator
from alpha_research.projects.snapshots import SnapshotWriter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_git_repo(tmp_path):
    """Create a temporary git repo with Python files."""
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
    (repo / "main.py").write_text("def hello():\n    return 'world'\n")
    (repo / "config.yaml").write_text("name: test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=repo, check=True, capture_output=True,
    )
    return repo


@pytest.fixture
def project_base(tmp_path):
    """Temporary base dir for projects."""
    return tmp_path / "projects"


@pytest.fixture
def orchestrator(project_base):
    """ProjectOrchestrator with no LLM (stub understanding)."""
    return ProjectOrchestrator(base_dir=project_base, llm=None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _commit_change(repo: Path, filename: str, content: str, msg: str) -> str:
    """Add a file to the repo, commit, and return the new commit SHA."""
    (repo / filename).write_text(content)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=repo, check=True, capture_output=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo, check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# 1. test_create_project_literature
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_project_literature(orchestrator, project_base):
    """Create a literature project (no source path).

    Verify: manifest exists, state.json exists, knowledge.db exists,
    1 snapshot created (kind=create).
    """
    manifest = await orchestrator.create_and_understand(
        name="Lit Review",
        project_type="literature",
        primary_question="What are recent advances in RL?",
    )

    assert manifest.name == "Lit Review"
    assert manifest.project_type == ProjectType.LITERATURE
    assert len(manifest.source_bindings) == 0

    # Check on-disk artifacts
    project_dir = project_base / manifest.slug
    assert (project_dir / "project.json").is_file()
    assert (project_dir / "state.json").is_file()
    assert (project_dir / "knowledge.db").is_file()

    # Check snapshot
    snapshots = orchestrator.list_snapshots(manifest.project_id)
    assert len(snapshots) == 1
    assert snapshots[0].snapshot_kind == SnapshotKind.CREATE


# ---------------------------------------------------------------------------
# 2. test_create_project_codebase
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_project_codebase(orchestrator, tmp_git_repo):
    """Create a codebase project with a git repo as source.

    Verify: source binding created, source snapshot captures commit SHA,
    understanding snapshot exists.
    """
    manifest = await orchestrator.create_and_understand(
        name="Code Analysis",
        project_type="codebase",
        primary_question="How does the system work?",
        source_path=str(tmp_git_repo),
    )

    assert manifest.project_type == ProjectType.CODEBASE
    assert len(manifest.source_bindings) == 1
    assert manifest.source_bindings[0].root_path == str(tmp_git_repo)

    # Check snapshot exists with source and understanding
    snapshots = orchestrator.list_snapshots(manifest.project_id)
    assert len(snapshots) == 1
    snap = snapshots[0]
    assert snap.snapshot_kind == SnapshotKind.CREATE
    assert snap.source_snapshot_id  # non-empty
    assert snap.understanding_snapshot_id  # non-empty

    # Load the source snapshot from snapshot dir and verify it has content
    project_dir = orchestrator.service.get_project_dir(manifest.project_id)
    snap_writer = SnapshotWriter(project_dir)
    source = snap_writer.load_source_snapshot(snap.snapshot_id)
    assert source is not None
    assert source.source_fingerprint != ""

    # Understanding is on disk
    understanding = snap_writer.load_understanding(snap.snapshot_id)
    assert understanding is not None
    assert understanding.project_id == manifest.project_id


# ---------------------------------------------------------------------------
# 3. test_resume_after_source_change
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resume_after_source_change(orchestrator, tmp_git_repo):
    """Create a codebase project, add a commit, then resume.

    Verify: new source snapshot has different fingerprint, resume snapshot
    created (kind=resume), source_changed flag detected.
    """
    manifest = await orchestrator.create_and_understand(
        name="Resume Test",
        project_type="codebase",
        primary_question="How does it work?",
        source_path=str(tmp_git_repo),
    )

    # Capture fingerprint before change
    project_dir = orchestrator.service.get_project_dir(manifest.project_id)
    snap_writer = SnapshotWriter(project_dir)
    create_snaps = snap_writer.list_snapshots(kind=SnapshotKind.CREATE)
    assert len(create_snaps) == 1
    old_source = snap_writer.load_source_snapshot(create_snaps[0].snapshot_id)
    old_fingerprint = old_source.source_fingerprint

    # Add a commit to the repo
    _commit_change(tmp_git_repo, "new_module.py", "x = 1\n", "add new module")

    # Resume
    state = await orchestrator.resume_and_continue(manifest.project_id)
    assert state.current_status == OperationalStatus.IDLE

    # There should now be 2 snapshots: create + resume
    all_snaps = snap_writer.list_snapshots()
    assert len(all_snaps) == 2

    resume_snaps = snap_writer.list_snapshots(kind=SnapshotKind.RESUME)
    assert len(resume_snaps) == 1
    resume_snap = resume_snaps[0]

    # New source fingerprint should differ
    new_source = snap_writer.load_source_snapshot(resume_snap.snapshot_id)
    assert new_source is not None
    assert new_source.source_fingerprint != old_fingerprint


# ---------------------------------------------------------------------------
# 4. test_resume_no_change
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resume_no_change(orchestrator, tmp_git_repo):
    """Create a codebase project, then resume without changing source.

    Verify: source fingerprint unchanged, understanding reused
    (not regenerated).
    """
    manifest = await orchestrator.create_and_understand(
        name="No Change Resume",
        project_type="codebase",
        primary_question="How does it work?",
        source_path=str(tmp_git_repo),
    )

    project_dir = orchestrator.service.get_project_dir(manifest.project_id)
    snap_writer = SnapshotWriter(project_dir)

    create_snaps = snap_writer.list_snapshots(kind=SnapshotKind.CREATE)
    old_source = snap_writer.load_source_snapshot(create_snaps[0].snapshot_id)
    old_understanding = snap_writer.load_understanding(create_snaps[0].snapshot_id)

    # Resume WITHOUT changing the repo
    state = await orchestrator.resume_and_continue(manifest.project_id)

    resume_snaps = snap_writer.list_snapshots(kind=SnapshotKind.RESUME)
    assert len(resume_snaps) == 1
    resume_snap = resume_snaps[0]

    new_source = snap_writer.load_source_snapshot(resume_snap.snapshot_id)
    assert new_source.source_fingerprint == old_source.source_fingerprint

    # Understanding should be reused (same snapshot ID in the resume snapshot)
    new_understanding = snap_writer.load_understanding(resume_snap.snapshot_id)
    assert new_understanding is not None
    # When source is unchanged, the orchestrator reuses the previous
    # understanding object. The understanding_snapshot_id on the resume
    # snapshot still points to an understanding, and the summary should
    # match the original stub since no refresh was needed.
    assert old_understanding.summary == new_understanding.summary


# ---------------------------------------------------------------------------
# 5. test_manual_snapshot
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manual_snapshot(orchestrator):
    """Create a project, then create_manual_snapshot with a note.

    Verify: snapshot created with kind=manual, note preserved.
    """
    manifest = await orchestrator.create_and_understand(
        name="Manual Snap",
        project_type="literature",
        primary_question="What is X?",
    )

    note_text = "Saving progress before changing approach"
    snapshot = await orchestrator.create_manual_snapshot(
        manifest.project_id,
        note=note_text,
    )

    assert snapshot.snapshot_kind == SnapshotKind.MANUAL
    assert snapshot.note == note_text
    assert snapshot.summary == note_text

    # Should have 2 snapshots total: create + manual
    all_snaps = orchestrator.list_snapshots(manifest.project_id)
    assert len(all_snaps) == 2

    manual_snaps = [
        s for s in all_snaps if s.snapshot_kind == SnapshotKind.MANUAL
    ]
    assert len(manual_snaps) == 1
    assert manual_snaps[0].snapshot_id == snapshot.snapshot_id


# ---------------------------------------------------------------------------
# 6. test_run_research_digest
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_research_digest(orchestrator):
    """Create a project, then run_research(mode="digest", question="test").

    Without network access the ArXiv search returns zero papers, so the
    digest run completes (or fails) gracefully.  Verify: ResearchRun
    record created, pre_run and post_run snapshots created, run reaches
    a terminal status (completed or failed), state updated.
    """
    manifest = await orchestrator.create_and_understand(
        name="Research Run",
        project_type="literature",
        primary_question="What is X?",
    )

    run = await orchestrator.run_research(
        manifest.project_id,
        mode="digest",
        question="test query",
    )

    assert isinstance(run, ResearchRun)
    assert run.project_id == manifest.project_id
    assert run.question == "test query"
    # Run should reach a terminal status (completed with 0 papers, or failed)
    assert run.status in (RunStatus.COMPLETED, RunStatus.FAILED)
    assert run.finished_at is not None

    # Pre-run and post-run snapshots should exist
    project_dir = orchestrator.service.get_project_dir(manifest.project_id)
    snap_writer = SnapshotWriter(project_dir)
    all_snaps = snap_writer.list_snapshots()

    # create + pre_run + post_run = 3
    assert len(all_snaps) == 3

    pre_run_snaps = snap_writer.list_snapshots(kind=SnapshotKind.PRE_RUN)
    assert len(pre_run_snaps) == 1

    post_run_snaps = snap_writer.list_snapshots(kind=SnapshotKind.POST_RUN)
    assert len(post_run_snaps) == 1

    # State should be back to idle
    _, state = orchestrator.get_project(manifest.project_id)
    assert state.current_status == OperationalStatus.IDLE
    assert state.last_completed_run_id == run.run_id
    assert state.active_run_id is None

    # Run persisted on disk
    runs = orchestrator.list_runs(manifest.project_id)
    assert len(runs) == 1
    assert runs[0].run_id == run.run_id


# ---------------------------------------------------------------------------
# 7. test_snapshot_immutability
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_snapshot_immutability(orchestrator):
    """Create project + snapshot. Verify: snapshot directory contains
    snapshot.json, source.json. Load snapshot from disk and verify it matches.
    """
    manifest = await orchestrator.create_and_understand(
        name="Immutable Test",
        project_type="literature",
        primary_question="What is X?",
    )

    snapshots = orchestrator.list_snapshots(manifest.project_id)
    assert len(snapshots) == 1
    snap = snapshots[0]

    project_dir = orchestrator.service.get_project_dir(manifest.project_id)
    snap_dir = project_dir / "snapshots" / snap.snapshot_id

    # Directory contains the expected files
    assert (snap_dir / "snapshot.json").is_file()
    assert (snap_dir / "source.json").is_file()

    # Load from disk and verify fields match
    loaded = ProjectSnapshot.load(snap_dir / "snapshot.json")
    assert loaded.snapshot_id == snap.snapshot_id
    assert loaded.project_id == snap.project_id
    assert loaded.snapshot_kind == snap.snapshot_kind
    assert loaded.source_snapshot_id == snap.source_snapshot_id
    assert loaded.summary == snap.summary

    # Source snapshot also loads correctly
    loaded_source = SourceSnapshot.load(snap_dir / "source.json")
    assert loaded_source.source_snapshot_id == snap.source_snapshot_id


# ---------------------------------------------------------------------------
# 8. test_list_operations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_operations(project_base):
    """Create 2 projects. Verify: list_projects returns both.
    list_snapshots for each returns correct counts.
    list_runs returns empty initially.
    """
    orch = ProjectOrchestrator(base_dir=project_base, llm=None)

    m1 = await orch.create_and_understand(
        name="Project Alpha",
        project_type="literature",
        primary_question="What is A?",
    )
    m2 = await orch.create_and_understand(
        name="Project Beta",
        project_type="literature",
        primary_question="What is B?",
    )

    projects = orch.list_projects()
    assert len(projects) == 2
    project_ids = {p.project_id for p in projects}
    assert m1.project_id in project_ids
    assert m2.project_id in project_ids

    # Each project has exactly 1 snapshot (create)
    snaps1 = orch.list_snapshots(m1.project_id)
    snaps2 = orch.list_snapshots(m2.project_id)
    assert len(snaps1) == 1
    assert len(snaps2) == 1

    # No runs initially
    runs1 = orch.list_runs(m1.project_id)
    runs2 = orch.list_runs(m2.project_id)
    assert runs1 == []
    assert runs2 == []


# ---------------------------------------------------------------------------
# 9. test_invariant_every_run_has_snapshot (Invariant 8)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invariant_every_run_has_snapshot(orchestrator):
    """Run research (will fail), verify output_snapshot_id is set
    on the ResearchRun (Invariant 8: every run has an output snapshot).
    """
    manifest = await orchestrator.create_and_understand(
        name="Invariant Test",
        project_type="literature",
        primary_question="What is X?",
    )

    run = await orchestrator.run_research(
        manifest.project_id,
        mode="digest",
        question="invariant test",
    )

    # Even though the run failed, it must have an output snapshot
    assert run.output_snapshot_id is not None
    assert run.output_snapshot_id != ""

    # The snapshot should be loadable
    project_dir = orchestrator.service.get_project_dir(manifest.project_id)
    snap_writer = SnapshotWriter(project_dir)
    output_snap = snap_writer.load_snapshot(run.output_snapshot_id)
    assert output_snap is not None
    assert output_snap.snapshot_kind == SnapshotKind.POST_RUN
    assert output_snap.run_id == run.run_id

    # Input snapshot should also exist
    assert run.input_snapshot_id is not None
    input_snap = snap_writer.load_snapshot(run.input_snapshot_id)
    assert input_snap.snapshot_kind == SnapshotKind.PRE_RUN
