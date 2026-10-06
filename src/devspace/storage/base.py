from abc import ABC, abstractmethod

from devspace.models.project import Project


class ProjectStore(ABC):
    """Contract for persisting the registry's project state."""

    @abstractmethod
    def load(self) -> dict[str, Project]:
        """Return all persisted projects, keyed by name."""

    @abstractmethod
    def save(self, projects: dict[str, Project]) -> None:
        """Persist the given projects, keyed by name."""
