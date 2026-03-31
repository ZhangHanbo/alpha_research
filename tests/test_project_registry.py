"""Tests for ProjectRegistry."""

import json

import pytest

from alpha_research.models.project import ProjectManifest
from alpha_research.projects.registry import ProjectRegistry


@pytest.fixture
def registry(tmp_path):
    return ProjectRegistry(base_dir=tmp_path / "projects")


@pytest.fixture
def sample_manifest():
    return ProjectManifest(
        name="Test Project",
        slug="test-project",
        primary_question="Does it work?",
    )


# ------------------------------------------------------------------
# init
# ------------------------------------------------------------------

def test_creates_base_dir_and_index(tmp_path):
    base = tmp_path / "new" / "nested" / "projects"
    reg = ProjectRegistry(base_dir=base)
    assert base.exists()
    assert (base / "index.json").exists()
    assert json.loads((base / "index.json").read_text()) == []


# ------------------------------------------------------------------
# register + list
# ------------------------------------------------------------------

def test_register_and_list(registry, sample_manifest):
    registry.register_project(sample_manifest)
    # Save the manifest file where the registry expects it
    project_dir = registry.base_dir / sample_manifest.slug
    project_dir.mkdir(parents=True, exist_ok=True)
    sample_manifest.save(project_dir / "project.json")

    projects = registry.list_projects()
    assert len(projects) == 1
    assert projects[0].project_id == sample_manifest.project_id
    assert projects[0].name == "Test Project"


def test_register_overwrites_duplicate(registry, sample_manifest):
    registry.register_project(sample_manifest)
    registry.register_project(sample_manifest)

    entries = registry._read_index()
    assert len(entries) == 1


# ------------------------------------------------------------------
# get
# ------------------------------------------------------------------

def test_get_project_found(registry, sample_manifest):
    registry.register_project(sample_manifest)
    project_dir = registry.base_dir / sample_manifest.slug
    project_dir.mkdir(parents=True, exist_ok=True)
    sample_manifest.save(project_dir / "project.json")

    result = registry.get_project(sample_manifest.project_id)
    assert result is not None
    assert result.project_id == sample_manifest.project_id


def test_get_project_not_found(registry):
    assert registry.get_project("nonexistent") is None


# ------------------------------------------------------------------
# remove
# ------------------------------------------------------------------

def test_remove_project(registry, sample_manifest):
    registry.register_project(sample_manifest)
    registry.remove_project(sample_manifest.project_id)

    assert registry.get_project(sample_manifest.project_id) is None
    assert registry.list_projects() == []


def test_remove_nonexistent_is_noop(registry):
    # Should not raise
    registry.remove_project("does-not-exist")
    assert registry._read_index() == []


# ------------------------------------------------------------------
# multiple projects
# ------------------------------------------------------------------

def test_list_multiple_projects(registry):
    manifests = []
    for i in range(3):
        m = ProjectManifest(
            name=f"Project {i}",
            slug=f"project-{i}",
            primary_question=f"Q{i}?",
        )
        registry.register_project(m)
        pdir = registry.base_dir / m.slug
        pdir.mkdir(parents=True, exist_ok=True)
        m.save(pdir / "project.json")
        manifests.append(m)

    projects = registry.list_projects()
    assert len(projects) == 3
    ids = {p.project_id for p in projects}
    assert ids == {m.project_id for m in manifests}
