"""Tests for ProjectService."""

import pytest

from alpha_research.knowledge.store import KnowledgeStore
from alpha_research.models.blackboard import Blackboard
from alpha_research.models.project import (
    OperationalStatus,
    ProjectManifest,
    ProjectState,
)
from alpha_research.projects.registry import ProjectRegistry
from alpha_research.projects.service import ProjectService, _slugify


@pytest.fixture
def service(tmp_path):
    registry = ProjectRegistry(base_dir=tmp_path / "projects")
    return ProjectService(registry)


def _create_default(service: ProjectService, **overrides) -> ProjectManifest:
    defaults = dict(
        name="My Research",
        project_type="literature",
        primary_question="What is X?",
    )
    defaults.update(overrides)
    return service.create_project(**defaults)


# ------------------------------------------------------------------
# slugify
# ------------------------------------------------------------------

class TestSlugify:
    def test_simple(self):
        assert _slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert _slugify("My Project! v2.0") == "my-project-v20"

    def test_multiple_spaces(self):
        assert _slugify("a   b") == "a-b"

    def test_leading_trailing(self):
        assert _slugify("  hello  ") == "hello"

    def test_hyphens_preserved(self):
        assert _slugify("alpha-research") == "alpha-research"

    def test_mixed_case(self):
        assert _slugify("CamelCase Name") == "camelcase-name"


# ------------------------------------------------------------------
# create_project
# ------------------------------------------------------------------

class TestCreateProject:
    def test_returns_manifest(self, service):
        m = _create_default(service)
        assert isinstance(m, ProjectManifest)
        assert m.name == "My Research"
        assert m.slug == "my-research"
        assert m.primary_question == "What is X?"

    def test_directory_structure(self, service):
        m = _create_default(service)
        pdir = service.registry.base_dir / m.slug
        assert pdir.is_dir()
        assert (pdir / "project.json").is_file()
        assert (pdir / "state.json").is_file()
        assert (pdir / "blackboard.json").is_file()
        assert (pdir / "knowledge.db").is_file()
        for subdir in ("runs", "snapshots", "reports", "notes", "cache"):
            assert (pdir / subdir).is_dir()

    def test_source_binding_created(self, service):
        m = _create_default(service, source_path="/some/path")
        assert len(m.source_bindings) == 1
        assert m.source_bindings[0].root_path == "/some/path"

    def test_registered_in_index(self, service):
        m = _create_default(service)
        found = service.registry.get_project(m.project_id)
        assert found is not None
        assert found.project_id == m.project_id

    def test_blackboard_loadable(self, service):
        m = _create_default(service)
        pdir = service.registry.base_dir / m.slug
        bb = Blackboard.load(pdir / "blackboard.json")
        assert isinstance(bb, Blackboard)

    def test_state_loadable(self, service):
        m = _create_default(service)
        pdir = service.registry.base_dir / m.slug
        state = ProjectState.load(pdir / "state.json")
        assert state.project_id == m.project_id
        assert state.current_status == OperationalStatus.IDLE

    def test_optional_fields(self, service):
        m = _create_default(
            service,
            description="desc",
            domain="robotics",
            tags=["a", "b"],
        )
        assert m.description == "desc"
        assert m.domain == "robotics"
        assert m.tags == ["a", "b"]


# ------------------------------------------------------------------
# load_project
# ------------------------------------------------------------------

class TestLoadProject:
    def test_roundtrip(self, service):
        m = _create_default(service)
        manifest, state = service.load_project(m.project_id)
        assert manifest.project_id == m.project_id
        assert state.project_id == m.project_id

    def test_unknown_project_raises(self, service):
        with pytest.raises(ValueError, match="Unknown project"):
            service.load_project("nonexistent")


# ------------------------------------------------------------------
# update_state
# ------------------------------------------------------------------

class TestUpdateState:
    def test_modifies_and_persists(self, service):
        m = _create_default(service)
        updated = service.update_state(
            m.project_id,
            current_status=OperationalStatus.RESEARCHING,
            notes="hello",
        )
        assert updated.current_status == OperationalStatus.RESEARCHING
        assert updated.notes == "hello"

        # Reload from disk
        _, reloaded = service.load_project(m.project_id)
        assert reloaded.current_status == OperationalStatus.RESEARCHING
        assert reloaded.notes == "hello"


# ------------------------------------------------------------------
# get_project_dir
# ------------------------------------------------------------------

class TestGetProjectDir:
    def test_returns_path(self, service):
        m = _create_default(service)
        d = service.get_project_dir(m.project_id)
        assert d.is_dir()
        assert d.name == m.slug

    def test_unknown_raises(self, service):
        with pytest.raises(ValueError):
            service.get_project_dir("nope")


# ------------------------------------------------------------------
# get_knowledge_store
# ------------------------------------------------------------------

class TestGetKnowledgeStore:
    def test_returns_working_store(self, service):
        m = _create_default(service)
        store = service.get_knowledge_store(m.project_id)
        assert isinstance(store, KnowledgeStore)
        # Verify the DB file is in the right place
        pdir = service.get_project_dir(m.project_id)
        assert store.db_path == pdir / "knowledge.db"

    def test_unknown_raises(self, service):
        with pytest.raises(ValueError):
            service.get_knowledge_store("nope")


# ------------------------------------------------------------------
# list / remove via registry integration
# ------------------------------------------------------------------

class TestRegistryIntegration:
    def test_list_after_create(self, service):
        _create_default(service, name="A")
        _create_default(service, name="B")
        projects = service.registry.list_projects()
        assert len(projects) == 2

    def test_remove_from_index(self, service):
        m = _create_default(service)
        service.registry.remove_project(m.project_id)
        assert service.registry.get_project(m.project_id) is None
