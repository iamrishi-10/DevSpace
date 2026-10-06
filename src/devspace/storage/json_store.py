import json
from pathlib import Path

from devspace.enums import ProjectType
from devspace.exceptions import StorageError
from devspace.models.project import Project
from devspace.storage.base import ProjectStore


class JsonProjectStore(ProjectStore):
    """Persists projects to a JSON file."""

    def __init__(self, file_path: Path) -> None:
        self._file_path: Path = file_path

    def load(self) -> dict[str, Project]:
        if not self._file_path.exists():
            return {}

        try:
            raw = json.loads(self._file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"Could not read projects from {self._file_path}") from exc

        try:
            return {name: self._from_dict(data) for name, data in raw.items()}
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise StorageError(f"Malformed project data in {self._file_path}") from exc

    def save(self, projects: dict[str, Project]) -> None:
        raw = {name: self._to_dict(project) for name, project in projects.items()}

        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        except OSError as exc:
            raise StorageError(f"Could not write projects to {self._file_path}") from exc

    @staticmethod
    def _to_dict(project: Project) -> dict[str, str | None]:
        return {
            "name": project.name,
            "path": str(project.path),
            "project_type": project.project_type.value,
            "run_command": project.run_command,
            "test_command": project.test_command,
        }

    @staticmethod
    def _from_dict(data: dict[str, str | None]) -> Project:
        return Project(
            name=data["name"],
            path=Path(data["path"]),
            project_type=ProjectType(data["project_type"]),
            run_command=data.get("run_command"),
            test_command=data.get("test_command"),
        )
