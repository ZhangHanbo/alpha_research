"""Quick smoke tests for the API layer."""

from fastapi.testclient import TestClient

from alpha_research.api.app import app


client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_papers_empty():
    r = client.get("/api/papers")
    assert r.status_code == 200
    assert r.json() == []


def test_paper_not_found():
    r = client.get("/api/papers/nonexistent")
    assert r.status_code == 404


def test_list_evaluations_empty():
    r = client.get("/api/evaluations")
    assert r.status_code == 200
    assert r.json() == []


def test_graph_nodes_empty():
    r = client.get("/api/graph/nodes")
    assert r.status_code == 200
    assert r.json() == []


def test_graph_edges_empty():
    r = client.get("/api/graph/edges")
    assert r.status_code == 200
    assert r.json() == []


def test_agent_status():
    r = client.get("/api/agent/status")
    assert r.status_code == 200
    data = r.json()
    assert data["state"] == "idle"


def test_feedback_post():
    r = client.post(
        "/api/evaluations/test123/feedback",
        json={"score_override": 4.5, "note": "Great paper", "flagged": False},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "saved"
    assert "id" in data


def test_papers_with_filters():
    r = client.get("/api/papers", params={"topic": "robotics", "year_min": 2020, "limit": 10})
    assert r.status_code == 200


if __name__ == "__main__":
    test_health()
    test_list_papers_empty()
    test_paper_not_found()
    test_list_evaluations_empty()
    test_graph_nodes_empty()
    test_graph_edges_empty()
    test_agent_status()
    test_feedback_post()
    test_papers_with_filters()
    print("ALL TESTS PASSED")
