from devspace.exceptions import DuplicateProjectError, ProjectNotFoundError
from devspace.models.project import Project
from devspace.storage.base import ProjectStore


class ProjectRegistry:
    """Registry of projects, keyed by unique name and unique path.

    State is loaded from, and persisted through, the injected ProjectStore.
    """

    def __init__(self, store: ProjectStore) -> None:
        self._store: ProjectStore = store
        self._projects: dict[str, Project] = store.load()

    def add(self, project: Project) -> None:
        if project.name in self._projects:
            raise DuplicateProjectError(f"Project name already registered: {project.name}")

        for existing in self._projects.values():
            if existing.path == project.path:
                raise DuplicateProjectError(
                    f"Project path already registered as '{existing.name}': {project.path}"
                )

        self._projects[project.name] = project
        self._store.save(self._projects)

    def get(self, name: str) -> Project:
        try:
            return self._projects[name]
        except KeyError:
            raise ProjectNotFoundError(f"Project not found: {name}") from None

    def list_all(self) -> list[Project]:
        return list(self._projects.values())

    def remove(self, name: str) -> Project:
        try:
            removed = self._projects.pop(name)
        except KeyError:
            raise ProjectNotFoundError(f"Project not found: {name}") from None

        self._store.save(self._projects)
        return removed
