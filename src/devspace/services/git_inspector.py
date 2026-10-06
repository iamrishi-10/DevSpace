import subprocess
from dataclasses import dataclass
from pathlib import Path

from devspace.exceptions import CommandExecutionError


@dataclass
class GitInfo:
    is_repository: bool
    branch: str | None = None
    is_dirty: bool | None = None
    last_commit: str | None = None


class GitInspector:
    """Reads the current Git state of a project directory."""

    def inspect(self, path: Path) -> GitInfo:
        if not path.is_dir():
            return GitInfo(is_repository=False)

        status = self._run_git(["status", "--porcelain"], path)
        if status.returncode != 0:
            return GitInfo(is_repository=False)

        branch = self._run_git(["branch", "--show-current"], path)
        log = self._run_git(["log", "-1", "--pretty=%s"], path)

        return GitInfo(
            is_repository=True,
            branch=(branch.stdout.strip() or None) if branch.returncode == 0 else None,
            is_dirty=bool(status.stdout.strip()),
            last_commit=(log.stdout.strip() or None) if log.returncode == 0 else None,
        )

    @staticmethod
    def _run_git(args: list[str], path: Path) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["git", *args],
                cwd=path,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            raise CommandExecutionError(f"Could not run git: {exc}") from exc
