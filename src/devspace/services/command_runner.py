import shlex
import subprocess
from pathlib import Path

from devspace.exceptions import CommandExecutionError


class CommandRunner:
    """Runs a stored command string in a working directory, attached to the terminal."""

    def run(self, command: str, cwd: Path) -> None:
        try:
            args = shlex.split(command)
        except ValueError as exc:
            raise CommandExecutionError(f"Invalid command: {command}") from exc

        if not args:
            raise CommandExecutionError("Command is empty")

        try:
            result = subprocess.run(args, cwd=cwd)
        except OSError as exc:
            raise CommandExecutionError(f"Could not run command '{command}': {exc}") from exc

        if result.returncode != 0:
            raise CommandExecutionError(
                f"Command failed with exit code {result.returncode}: {command}"
            )
