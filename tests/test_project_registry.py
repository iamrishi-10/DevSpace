from pathlib import Path

import pytest

from devspace.enums import ProjectType
from devspace.exceptions import DuplicateProjectError, ProjectNotFoundError, StorageError
from devspace.models.project import Project
from devspace.registry.project_registry import ProjectRegistry
from devspace.storage.base import ProjectStore
from devspace.storage.json_store import JsonProjectStore


class FakeStore(ProjectStore):
    """In-memory store that records every save() call."""

    def __init__(self, initial: dict[str, Project] | None = None) -> None:
        self.initial = initial or {}
        self.saves: list[dict[str, Project]] = []

    def load(self) -> dict[str, Project]:
        return dict(self.initial)

    def save(self, projects: dict[str, Project]) -> None:
        self.saves.append(dict(projects))


def make_project(name: str, path: str) -> Project:
    return Project(name=name, path=Path(path), project_type=ProjectType.PYTHON)


@pytest.fixture
def store() -> FakeStore:
    return FakeStore()


@pytest.fixture
def registry(store: FakeStore) -> ProjectRegistry:
    return ProjectRegistry(store)


def test_new_registry_is_empty(registry):
    assert registry.list_all() == []


def test_registry_starts_with_projects_from_store():
    raglens = make_project("raglens", "/project/a")
    registry = ProjectRegistry(FakeStore({"raglens": raglens}))

    assert registry.list_all() == [raglens]
    assert registry.get("raglens") is raglens


def test_construction_does_not_save(store):
    ProjectRegistry(store)

    assert store.saves == []


def test_add_and_get(registry):
    raglens = make_project("raglens", "/project/a")

    registry.add(raglens)

    assert registry.get("raglens") is raglens


def test_add_persists_updated_projects(registry, store):
    raglens = make_project("raglens", "/project/a")

    registry.add(raglens)

    assert store.saves == [{"raglens": raglens}]


def test_add_duplicate_name_raises(registry):
    registry.add(make_project("raglens", "/project/a"))

    with pytest.raises(DuplicateProjectError):
        registry.add(make_project("raglens", "/project/b"))


def test_add_duplicate_path_raises(registry):
    registry.add(make_project("raglens", "/project/a"))

    with pytest.raises(DuplicateProjectError):
        registry.add(make_project("another-name", "/project/a"))


def test_failed_add_leaves_registry_unchanged_and_does_not_save(registry, store):
    registry.add(make_project("raglens", "/project/a"))

    with pytest.raises(DuplicateProjectError):
        registry.add(make_project("another-name", "/project/a"))

    assert [p.name for p in registry.list_all()] == ["raglens"]
    assert len(store.saves) == 1


def test_get_unknown_raises(registry):
    with pytest.raises(ProjectNotFoundError):
        registry.get("unknown")


def test_get_does_not_save(registry, store):
    registry.add(make_project("raglens", "/project/a"))
    saves_before = len(store.saves)

    registry.get("raglens")

    assert len(store.saves) == saves_before


def test_list_all_returns_all_projects(registry):
    projects = [make_project(f"p{i}", f"/project/{i}") for i in range(3)]
    for project in projects:
        registry.add(project)

    assert registry.list_all() == projects


def test_list_all_does_not_expose_internal_state(registry):
    registry.add(make_project("raglens", "/project/a"))

    registry.list_all().clear()

    assert len(registry.list_all()) == 1


def test_list_all_does_not_save(registry, store):
    registry.add(make_project("raglens", "/project/a"))
    saves_before = len(store.saves)

    registry.list_all()

    assert len(store.saves) == saves_before


def test_remove_returns_project_and_unregisters_it(registry):
    raglens = make_project("raglens", "/project/a")
    registry.add(raglens)

    assert registry.remove("raglens") is raglens

    with pytest.raises(ProjectNotFoundError):
        registry.get("raglens")


def test_remove_persists_updated_projects(registry, store):
    registry.add(make_project("raglens", "/project/a"))

    registry.remove("raglens")

    assert store.saves[-1] == {}


def test_removed_project_name_and_path_can_be_reused(registry):
    registry.add(make_project("raglens", "/project/a"))
    registry.remove("raglens")

    registry.add(make_project("raglens", "/project/a"))

    assert registry.get("raglens").path == Path("/project/a")


def test_remove_unknown_raises_and_does_not_save(registry, store):
    with pytest.raises(ProjectNotFoundError):
        registry.remove("unknown")

    assert store.saves == []


def test_storage_error_from_save_propagates_on_add():
    class FailingStore(FakeStore):
        def save(self, projects):
            raise StorageError("disk full")

    registry = ProjectRegistry(FailingStore())

    with pytest.raises(StorageError):
        registry.add(make_project("raglens", "/project/a"))


def test_projects_survive_a_new_registry_with_json_store(tmp_path):
    file_path = tmp_path / "projects.json"
    first = ProjectRegistry(JsonProjectStore(file_path))
    raglens = make_project("raglens", "/project/a")
    first.add(raglens)

    second = ProjectRegistry(JsonProjectStore(file_path))

    assert second.list_all() == [raglens]


def test_removal_survives_a_new_registry_with_json_store(tmp_path):
    file_path = tmp_path / "projects.json"
    first = ProjectRegistry(JsonProjectStore(file_path))
    first.add(make_project("raglens", "/project/a"))
    first.remove("raglens")

    second = ProjectRegistry(JsonProjectStore(file_path))

    assert second.list_all() == []
