"""Tests for the /api/projects endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alpha_research.api.app import app, set_orchestrator
from alpha_research.projects.orchestrator import ProjectOrchestrator


@pytest.fixture()
def client(tmp_path):
    """Create a TestClient with a temp-dir-backed orchestrator."""
    orch = ProjectOrchestrator(base_dir=tmp_path / "projects", llm=None)
    set_orchestrator(orch)
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
    finally:
        # Reset orchestrator so other tests are not affected
        set_orchestrator(None)


def _create_project(client: TestClient, **overrides) -> dict:
    """Helper to POST a project with defaults."""
    body = {
        "name": "Test Research",
        "project_type": "literature",
        "primary_question": "What is X?",
    }
    body.update(overrides)
    resp = client.post("/api/projects", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ------------------------------------------------------------------
# POST /api/projects — create
# ------------------------------------------------------------------


class TestCreateProject:
    def test_create_returns_manifest(self, client):
        data = _create_project(client)
        assert "project_id" in data
        assert data["name"] == "Test Research"
        assert data["project_type"] == "literature"
        assert data["primary_question"] == "What is X?"

    def test_create_with_optional_fields(self, client):
        data = _create_project(
            client,
            description="A description",
            domain="robotics",
            tags=["a", "b"],
        )
        assert data["description"] == "A description"
        assert data["domain"] == "robotics"
        assert data["tags"] == ["a", "b"]


# ------------------------------------------------------------------
# GET /api/projects — list
# ------------------------------------------------------------------


class TestListProjects:
    def test_empty_initially(self, client):
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_lists_created_projects(self, client):
        _create_project(client, name="Alpha")
        _create_project(client, name="Beta")
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()]
        assert "Alpha" in names
        assert "Beta" in names


# ------------------------------------------------------------------
# GET /api/projects/{id} — get manifest + state
# ------------------------------------------------------------------


class TestGetProject:
    def test_returns_manifest_and_state(self, client):
        data = _create_project(client)
        pid = data["project_id"]
        resp = client.get(f"/api/projects/{pid}")
        assert resp.status_code == 200
        body = resp.json()
        assert "manifest" in body
        assert "state" in body
        assert body["manifest"]["project_id"] == pid
        assert body["state"]["project_id"] == pid

    def test_404_for_unknown(self, client):
        resp = client.get("/api/projects/nonexistent")
        assert resp.status_code == 404


# ------------------------------------------------------------------
# GET /api/projects/{id}/state
# ------------------------------------------------------------------


class TestGetProjectState:
    def test_returns_state(self, client):
        data = _create_project(client)
        pid = data["project_id"]
        resp = client.get(f"/api/projects/{pid}/state")
        assert resp.status_code == 200
        state = resp.json()
        assert state["project_id"] == pid
        assert state["current_status"] == "idle"

    def test_404_for_unknown(self, client):
        resp = client.get("/api/projects/nonexistent/state")
        assert resp.status_code == 404


# ------------------------------------------------------------------
# GET /api/projects/{id}/snapshots — list snapshots
# ------------------------------------------------------------------


class TestListSnapshots:
    def test_returns_initial_snapshot(self, client):
        data = _create_project(client)
        pid = data["project_id"]
        resp = client.get(f"/api/projects/{pid}/snapshots")
        assert resp.status_code == 200
        snapshots = resp.json()
        # create_and_understand creates an initial "create" snapshot
        assert len(snapshots) >= 1
        assert snapshots[0]["project_id"] == pid
        assert snapshots[0]["snapshot_kind"] == "create"


# ------------------------------------------------------------------
# POST /api/projects/{id}/snapshots — create manual snapshot
# ------------------------------------------------------------------


class TestCreateSnapshot:
    def test_create_manual_snapshot(self, client):
        data = _create_project(client)
        pid = data["project_id"]
        resp = client.post(
            f"/api/projects/{pid}/snapshots",
            json={"note": "Checkpoint A"},
        )
        assert resp.status_code == 200
        snap = resp.json()
        assert snap["project_id"] == pid
        assert snap["snapshot_kind"] == "manual"
        assert snap["note"] == "Checkpoint A"

    def test_create_milestone_snapshot(self, client):
        data = _create_project(client)
        pid = data["project_id"]
        resp = client.post(
            f"/api/projects/{pid}/snapshots",
            json={"note": "v1 release", "milestone": True, "milestone_name": "v1"},
        )
        assert resp.status_code == 200
        snap = resp.json()
        assert snap["snapshot_kind"] == "milestone"

    def test_404_for_unknown_project(self, client):
        resp = client.post(
            "/api/projects/nonexistent/snapshots",
            json={"note": "test"},
        )
        assert resp.status_code == 404


# ------------------------------------------------------------------
# GET /api/projects/{id}/runs — list runs
# ------------------------------------------------------------------


class TestListRuns:
    def test_empty_initially(self, client):
        data = _create_project(client)
        pid = data["project_id"]
        resp = client.get(f"/api/projects/{pid}/runs")
        assert resp.status_code == 200
        assert resp.json() == []
