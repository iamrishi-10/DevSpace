from dataclasses import dataclass
from pathlib import Path

from devspace.enums import ProjectType


@dataclass
class Project:
    name: str
    path: Path
    project_type: ProjectType
    run_command: str | None = None
    test_command: str | None = None

