"""Project lifecycle endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from alpha_research.api.models import (
    CreateProjectRequest,
    CreateSnapshotRequest,
    ResumeProjectRequest,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _get_orchestrator():
    """Lazy import to avoid circular / startup issues."""
    from alpha_research.api.app import get_orchestrator

    return get_orchestrator()


# ------------------------------------------------------------------
# Project CRUD
# ------------------------------------------------------------------


@router.post("")
async def create_project(body: CreateProjectRequest):
    """Create a new project and run initial understanding."""
    orch = _get_orchestrator()
    try:
        manifest = await orch.create_and_understand(
            name=body.name,
            project_type=body.project_type,
            primary_question=body.primary_question,
            source_path=body.source_path,
            description=body.description,
            domain=body.domain,
            tags=body.tags,
        )
        return manifest.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("")
def list_projects():
    """List all registered projects."""
    orch = _get_orchestrator()
    return [m.model_dump(mode="json") for m in orch.list_projects()]


@router.get("/{project_id}")
def get_project(project_id: str):
    """Get project manifest and current state."""
    orch = _get_orchestrator()
    try:
        manifest, state = orch.get_project(project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "manifest": manifest.model_dump(mode="json"),
        "state": state.model_dump(mode="json"),
    }


@router.get("/{project_id}/state")
def get_project_state(project_id: str):
    """Get current project state only."""
    orch = _get_orchestrator()
    try:
        _, state = orch.get_project(project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")
    return state.model_dump(mode="json")


# ------------------------------------------------------------------
# Snapshots
# ------------------------------------------------------------------


@router.get("/{project_id}/snapshots")
def list_snapshots(project_id: str):
    """List all snapshots for a project."""
    orch = _get_orchestrator()
    try:
        snapshots = orch.list_snapshots(project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")
    return [s.model_dump(mode="json") for s in snapshots]


@router.post("/{project_id}/snapshots")
async def create_snapshot(project_id: str, body: CreateSnapshotRequest):
    """Create a manual snapshot."""
    orch = _get_orchestrator()
    try:
        snapshot = await orch.create_manual_snapshot(
            project_id=project_id,
            note=body.note,
            milestone=body.milestone,
            milestone_name=body.milestone_name,
        )
        return snapshot.model_dump(mode="json")
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ------------------------------------------------------------------
# Resume
# ------------------------------------------------------------------


@router.post("/{project_id}/resume")
async def resume_project(project_id: str, body: ResumeProjectRequest):
    """Resume an existing project."""
    orch = _get_orchestrator()
    try:
        state = await orch.resume_and_continue(
            project_id=project_id,
            mode=body.mode,
            snapshot_id=body.snapshot_id,
        )
        return state.model_dump(mode="json")
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ------------------------------------------------------------------
# Runs
# ------------------------------------------------------------------


@router.get("/{project_id}/runs")
def list_runs(project_id: str):
    """List all research runs for a project."""
    orch = _get_orchestrator()
    try:
        runs = orch.list_runs(project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")
    return [r.model_dump(mode="json") for r in runs]
