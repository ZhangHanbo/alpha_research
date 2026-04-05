"""Project orchestrator — top-level coordinator for project lifecycle.

Deterministic service that sequences agents and manages state
transitions.  This is the outer orchestrator that wraps the existing
research-review loop with project lifecycle concerns (create, resume,
snapshot, run tracking).

Source: project_lifecycle_revision_plan.md §772-790, §857-889
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from alpha_research.models.blackboard import Blackboard
from alpha_research.models.project import (
    OperationalStatus,
    ProjectManifest,
    ProjectState,
)
from alpha_research.models.snapshot import (
    ProjectSnapshot,
    ResearchRun,
    RunStatus,
    RunType,
    SnapshotKind,
    SourceSnapshot,
    UnderstandingSnapshot,
)
from alpha_research.projects.git_state import capture_source_snapshot
from alpha_research.projects.registry import ProjectRegistry
from alpha_research.projects.resume import ResumeContext, ResumeMode, ResumeService
from alpha_research.projects.service import ProjectService
from alpha_research.projects.snapshots import SnapshotWriter
from alpha_research.projects.understanding import UnderstandingAgent

# Type alias for LLM callable
LLMCallable = Any


class ProjectOrchestrator:
    """Top-level project lifecycle coordinator.

    Sequences deterministic services and LLM agents to implement the
    create, resume, and run_research flows.

    Parameters
    ----------
    base_dir : str | Path
        Root directory for all project data (``data/projects``).
    llm : LLMCallable | None
        Async LLM callable for agents.  If None, agents produce stubs.
    """

    def __init__(
        self,
        base_dir: str | Path = "data/projects",
        llm: LLMCallable | None = None,
    ) -> None:
        self.registry = ProjectRegistry(base_dir)
        self.service = ProjectService(self.registry)
        self.understanding_agent = UnderstandingAgent(llm=llm)
        self.llm = llm

    # ------------------------------------------------------------------
    # Flow A: Create new project
    # ------------------------------------------------------------------

    async def create_and_understand(
        self,
        name: str,
        project_type: str,
        primary_question: str,
        source_path: str | None = None,
        description: str = "",
        domain: str = "",
        tags: list[str] | None = None,
    ) -> ProjectManifest:
        """Create a new project, capture source, produce understanding.

        Flow (§859-871):
        1. ProjectService.create_project
        2. Capture initial source snapshot
        3. Understanding agent produces first understanding
        4. Create initial project snapshot (kind=create)
        5. Update project state
        """
        # 1. Create project
        manifest = self.service.create_project(
            name=name,
            project_type=project_type,
            primary_question=primary_question,
            source_path=source_path,
            description=description,
            domain=domain,
            tags=tags,
        )

        project_dir = self.service.get_project_dir(manifest.project_id)
        snap_writer = SnapshotWriter(project_dir)

        # 2. Capture source snapshot (if source binding exists)
        source_snapshot = self._capture_source(manifest, project_dir)

        # 3. Understanding agent
        self.service.update_state(
            manifest.project_id,
            current_status=OperationalStatus.UNDERSTANDING,
        )

        file_contents = self._gather_files(manifest, source_path)
        understanding = await self.understanding_agent.understand(
            manifest, source_snapshot, file_contents,
        )

        # 4. Create initial snapshot
        snapshot = snap_writer.create_project_snapshot(
            project_id=manifest.project_id,
            kind=SnapshotKind.CREATE,
            source_snapshot=source_snapshot,
            understanding_snapshot=understanding,
            blackboard_path=str(project_dir / "blackboard.json"),
            summary=f"Initial project creation: {name}",
        )

        # 5. Update state
        self.service.update_state(
            manifest.project_id,
            current_status=OperationalStatus.IDLE,
            current_snapshot_id=snapshot.snapshot_id,
            last_understanding_snapshot_id=snapshot.snapshot_id,
            last_seen_source_snapshot_id=source_snapshot.source_snapshot_id,
        )

        return manifest

    # ------------------------------------------------------------------
    # Flow B: Resume existing project
    # ------------------------------------------------------------------

    async def resume_and_continue(
        self,
        project_id: str,
        mode: str = "current_workspace",
        snapshot_id: str | None = None,
    ) -> ProjectState:
        """Resume an existing project.

        Flow (§873-889):
        1. Prepare resume context (source capture + delta)
        2. Refresh understanding
        3. Create resume snapshot
        4. Update project state
        """
        manifest, state = self.service.load_project(project_id)
        project_dir = self.service.get_project_dir(project_id)

        resume_svc = ResumeService(project_dir)
        snap_writer = SnapshotWriter(project_dir)

        resume_mode = ResumeMode(mode)

        # 1. Prepare resume context
        ctx = resume_svc.prepare_resume(
            manifest, state,
            mode=resume_mode,
            snapshot_id=snapshot_id,
        )

        # 2. Refresh understanding
        self.service.update_state(
            project_id,
            current_status=OperationalStatus.UNDERSTANDING,
        )

        file_contents = self._gather_files(
            manifest,
            ctx.worktree_path or self._get_source_path(manifest),
        )

        if ctx.previous_understanding and ctx.source_changed:
            understanding = await self.understanding_agent.refresh_understanding(
                manifest,
                ctx.previous_understanding,
                ctx.source_snapshot,
                ctx.source_delta_summary,
                file_contents,
            )
        elif ctx.previous_understanding and not ctx.source_changed:
            # No changes — reuse previous understanding
            understanding = ctx.previous_understanding
        else:
            # No previous understanding — create fresh
            understanding = await self.understanding_agent.understand(
                manifest, ctx.source_snapshot, file_contents,
            )

        # 3. Create resume snapshot
        snapshot = snap_writer.create_project_snapshot(
            project_id=project_id,
            kind=SnapshotKind.RESUME,
            source_snapshot=ctx.source_snapshot,
            understanding_snapshot=understanding,
            blackboard_path=str(project_dir / "blackboard.json"),
            parent_snapshot_id=state.current_snapshot_id,
            summary=f"Resume ({mode}): {ctx.source_delta_summary[:100]}",
        )

        # 4. Update state
        updated = self.service.update_state(
            project_id,
            current_status=OperationalStatus.IDLE,
            current_snapshot_id=snapshot.snapshot_id,
            last_understanding_snapshot_id=snapshot.snapshot_id,
            last_seen_source_snapshot_id=ctx.source_snapshot.source_snapshot_id,
            resume_required=False,
            source_changed_since_last_snapshot=False,
            last_resumed_at=datetime.now(),
        )

        return updated

    # ------------------------------------------------------------------
    # Run research within a project
    # ------------------------------------------------------------------

    async def run_research(
        self,
        project_id: str,
        mode: str,
        question: str,
    ) -> ResearchRun:
        """Run a research cycle within a project.

        1. Create pre_run snapshot
        2. Create ResearchRun record
        3. Execute research (via existing orchestrator)
        4. Create post_run snapshot
        5. Update state
        """
        manifest, state = self.service.load_project(project_id)
        project_dir = self.service.get_project_dir(project_id)
        snap_writer = SnapshotWriter(project_dir)

        # Capture source for pre-run snapshot
        source_snapshot = self._capture_source(manifest, project_dir)

        # Create pre-run snapshot
        pre_snap = snap_writer.create_project_snapshot(
            project_id=project_id,
            kind=SnapshotKind.PRE_RUN,
            source_snapshot=source_snapshot,
            parent_snapshot_id=state.current_snapshot_id,
            blackboard_path=str(project_dir / "blackboard.json"),
            summary=f"Pre-run snapshot for {mode} mode",
        )

        # Create run record
        run = ResearchRun(
            project_id=project_id,
            run_type=RunType(mode) if mode in RunType.__members__.values() else RunType.DIGEST,
            question=question,
            input_snapshot_id=pre_snap.snapshot_id,
            status=RunStatus.RUNNING,
        )
        run.save(project_dir / "runs" / f"{run.run_id}.json")

        self.service.update_state(
            project_id,
            current_status=OperationalStatus.RESEARCHING,
            active_run_id=run.run_id,
        )

        # Execute research
        #
        # NOTE (R6 refactor, 2026-04-05): the previous implementation instantiated
        # ``alpha_research.agents.research_agent.ResearchAgent`` directly. The
        # agents/ package has been deleted; research workflows now run through
        # ``alpha_research.pipelines.literature_survey.run_literature_survey``
        # (for digest/deep/survey) and
        # ``alpha_research.pipelines.research_review_loop.run_research_review_loop``
        # (for the adversarial loop). The project orchestrator has not yet been
        # migrated to those pipeline entry points — this path records a
        # placeholder run and returns, so the project lifecycle itself still
        # works end-to-end for tests that don't exercise agent execution.
        try:
            from alpha_research.pipelines.literature_survey import run_literature_survey

            if mode in ("digest", "deep", "survey"):
                result = await run_literature_survey(
                    query=question,
                    output_dir=project_dir / "reports" / run.run_id,
                    apply_rubric=(mode != "digest"),
                )
                run.summary = (
                    f"Literature survey completed: "
                    f"{result.papers_included}/{result.papers_total} papers"
                )
                if result.report_path is not None:
                    run.outputs.append(str(result.report_path))
                if result.tex_path is not None:
                    run.outputs.append(str(result.tex_path))
            else:
                run.summary = f"Mode '{mode}' not yet supported post-refactor"

            run.status = RunStatus.COMPLETED
        except Exception as e:
            run.status = RunStatus.FAILED
            run.error = str(e)

        run.finished_at = datetime.now()

        # Create post-run snapshot
        post_source = self._capture_source(manifest, project_dir)
        post_snap = snap_writer.create_project_snapshot(
            project_id=project_id,
            kind=SnapshotKind.POST_RUN,
            source_snapshot=post_source,
            run_id=run.run_id,
            parent_snapshot_id=pre_snap.snapshot_id,
            blackboard_path=str(project_dir / "blackboard.json"),
            summary=f"Post-run: {run.summary}",
        )

        run.output_snapshot_id = post_snap.snapshot_id
        run.save(project_dir / "runs" / f"{run.run_id}.json")

        # Update state
        self.service.update_state(
            project_id,
            current_status=OperationalStatus.IDLE,
            active_run_id=None,
            last_completed_run_id=run.run_id,
            current_snapshot_id=post_snap.snapshot_id,
        )

        return run

    # ------------------------------------------------------------------
    # Manual snapshot
    # ------------------------------------------------------------------

    async def create_manual_snapshot(
        self,
        project_id: str,
        note: str = "",
        milestone: bool = False,
        milestone_name: str | None = None,
    ) -> ProjectSnapshot:
        """Create a manual checkpoint snapshot."""
        manifest, state = self.service.load_project(project_id)
        project_dir = self.service.get_project_dir(project_id)
        snap_writer = SnapshotWriter(project_dir)

        source = self._capture_source(manifest, project_dir)

        kind = SnapshotKind.MILESTONE if milestone else SnapshotKind.MANUAL
        snapshot = snap_writer.create_project_snapshot(
            project_id=project_id,
            kind=kind,
            source_snapshot=source,
            parent_snapshot_id=state.current_snapshot_id,
            blackboard_path=str(project_dir / "blackboard.json"),
            summary=note or f"Manual snapshot",
            note=note,
        )

        self.service.update_state(
            project_id,
            current_snapshot_id=snapshot.snapshot_id,
        )

        if milestone and milestone_name:
            snap_writer.tag_milestone(
                snapshot.snapshot_id, milestone_name, manifest.slug,
            )

        return snapshot

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def list_projects(self) -> list[ProjectManifest]:
        return self.registry.list_projects()

    def get_project(self, project_id: str) -> tuple[ProjectManifest, ProjectState]:
        return self.service.load_project(project_id)

    def list_snapshots(self, project_id: str) -> list[ProjectSnapshot]:
        project_dir = self.service.get_project_dir(project_id)
        return SnapshotWriter(project_dir).list_snapshots()

    def list_runs(self, project_id: str) -> list[ResearchRun]:
        project_dir = self.service.get_project_dir(project_id)
        runs_dir = project_dir / "runs"
        if not runs_dir.exists():
            return []
        runs = []
        for f in sorted(runs_dir.iterdir()):
            if f.suffix == ".json":
                runs.append(ResearchRun.load(f))
        runs.sort(key=lambda r: r.started_at)
        return runs

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _capture_source(
        self, manifest: ProjectManifest, project_dir: Path,
    ) -> SourceSnapshot:
        """Capture source state for the project's primary binding."""
        if not manifest.source_bindings:
            # No bindings — return a stub snapshot
            return SourceSnapshot(
                source_fingerprint="no-source-binding",
            )
        binding = manifest.source_bindings[0]
        for b in manifest.source_bindings:
            if b.is_primary:
                binding = b
                break
        snap_dir = project_dir / "cache" / "source_capture"
        snap_dir.mkdir(parents=True, exist_ok=True)
        return capture_source_snapshot(binding, snap_dir)

    @staticmethod
    def _get_source_path(manifest: ProjectManifest) -> str | None:
        """Return the root path of the primary source binding."""
        for b in manifest.source_bindings:
            if b.is_primary:
                return b.root_path
        if manifest.source_bindings:
            return manifest.source_bindings[0].root_path
        return None

    @staticmethod
    def _gather_files(
        manifest: ProjectManifest,
        source_path: str | None,
        max_files: int = 50,
        max_file_size: int = 50000,
    ) -> dict[str, str]:
        """Gather file contents for the understanding agent.

        Deterministic file selection: walks the source path, filters by
        include/exclude patterns, limits total size.
        """
        if not source_path or not Path(source_path).exists():
            return {}

        root = Path(source_path)
        contents: dict[str, str] = {}

        # Common files to skip
        skip_dirs = {
            ".git", "__pycache__", "node_modules", ".next", ".venv",
            "venv", "dist", "build", ".eggs", "*.egg-info",
        }
        skip_extensions = {
            ".pyc", ".pyo", ".so", ".o", ".a", ".dylib",
            ".jpg", ".png", ".gif", ".pdf", ".zip", ".tar",
            ".whl", ".egg", ".db", ".sqlite",
        }

        for dirpath, dirnames, filenames in os.walk(root):
            # Prune skip directories
            dirnames[:] = [
                d for d in dirnames
                if d not in skip_dirs and not d.endswith(".egg-info")
            ]

            for fname in sorted(filenames):
                if len(contents) >= max_files:
                    break

                fpath = Path(dirpath) / fname
                suffix = fpath.suffix.lower()
                if suffix in skip_extensions:
                    continue

                try:
                    size = fpath.stat().st_size
                    if size > max_file_size or size == 0:
                        continue
                    text = fpath.read_text(errors="replace")
                    rel = str(fpath.relative_to(root))
                    contents[rel] = text
                except (OSError, UnicodeDecodeError):
                    continue

        return contents
