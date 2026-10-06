from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from devspace.enums import ProjectType
from devspace.exceptions import CommandExecutionError, DevSpaceError, InvalidProjectPathError
from devspace.models.project import Project
from devspace.registry.project_registry import ProjectRegistry
from devspace.storage.json_store import JsonProjectStore
from devspace.services.command_runner import CommandRunner
from devspace.services.git_inspector import GitInspector




app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """DevSpace: register and manage your local projects."""


def _storage_path() -> Path:
    return Path.home() / ".devspace" / "projects.json"


def _build_registry() -> ProjectRegistry:
    """Composition root: choose the concrete store and hand it to the registry."""
    store = JsonProjectStore(_storage_path())
    return ProjectRegistry(store)


def _validate_project_path(path: Path) -> Path:
    path = path.expanduser().resolve()

    if not path.exists():
        raise InvalidProjectPathError(f"Path does not exist: {path}")
    if not path.is_dir():
        raise InvalidProjectPathError(f"Path is not a directory: {path}")

    return path


def _parse_project_type(value: str) -> ProjectType:
    try:
        return ProjectType(value.strip().lower())
    except ValueError:
        choices = ", ".join(project_type.value for project_type in ProjectType)
        raise typer.BadParameter(f"'{value}' is not one of: {choices}") from None


def _prompt_project_type() -> ProjectType:
    choices = "/".join(project_type.value for project_type in ProjectType)
    return typer.prompt(f"Project type ({choices})", value_proc=_parse_project_type)


def _prompt_optional(label: str) -> str | None:
    value = typer.prompt(f"{label} (optional)", default="", show_default=False)
    return value.strip() or None


@app.command()
def add(
    name: Annotated[str, typer.Argument(help="Unique project name.")],
    path: Annotated[Path, typer.Argument(help="Path to the project directory.")],
) -> None:
    """Register a project."""
    try:
        project_path = _validate_project_path(path)
        project_type = _prompt_project_type()
        run_command = _prompt_optional("Run command")
        test_command = _prompt_optional("Test command")

        project = Project(
            name=name,
            path=project_path,
            project_type=project_type,
            run_command=run_command,
            test_command=test_command,
        )
        _build_registry().add(project)
    except DevSpaceError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Project '{name}' added successfully.")


@app.command("list")
def list_projects() -> None:
    """List registered projects."""
    try:
        projects = _build_registry().list_all()
        inspector = GitInspector()
        git_infos = [inspector.inspect(project.path) for project in projects]
    except DevSpaceError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    console = Console()

    if not projects:
        console.print("No projects registered.")
        return

    table = Table()
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Branch")
    table.add_column("Status")
    table.add_column("Path")

    for project, git_info in zip(projects, git_infos):
        if not git_info.is_repository:
            status = "not-git"
        else:
            status = "dirty" if git_info.is_dirty else "clean"

        table.add_row(
            escape(project.name),
            project.project_type.value,
            escape(git_info.branch or "-"),
            status,
            escape(str(project.path)),
        )

    console.print(table)


@app.command()
def remove(
    name: Annotated[str, typer.Argument(help="Name of the project to unregister.")],
) -> None:
    """Unregister a project (does not delete its directory)."""
    try:
        _build_registry().remove(name)
    except DevSpaceError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Project '{name}' removed.")


@app.command()
def status(
    name: Annotated[str, typer.Argument(help="Name of the registered project.")],
) -> None:
    """Show the live Git status of a registered project."""
    try:
        project = _build_registry().get(name)
        git_info = GitInspector().inspect(project.path)
    except DevSpaceError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    console = Console()
    console.print(f"Project:      {escape(project.name)}")

    if not git_info.is_repository:
        console.print("Git:          Not initialized")
        return

    console.print(f"Branch:       {escape(git_info.branch or '-')}")
    console.print(f"Working tree: {'dirty' if git_info.is_dirty else 'clean'}")
    console.print(f"Last commit:  {escape(git_info.last_commit or 'No commits yet')}")


@app.command()
def run(
    name: Annotated[str, typer.Argument(help="Name of the registered project.")],
) -> None:
    """Run the project's stored run command in its directory."""
    try:
        project = _build_registry().get(name)
        if project.run_command is None:
            raise CommandExecutionError(f"Project '{name}' has no run command configured")
        CommandRunner().run(project.run_command, project.path)
    except DevSpaceError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command("test")
def test_project(
    name: Annotated[str, typer.Argument(help="Name of the registered project.")],
) -> None:
    """Run the project's stored test command in its directory."""
    try:
        project = _build_registry().get(name)
        if project.test_command is None:
            raise CommandExecutionError(f"Project '{name}' has no test command configured")
        CommandRunner().run(project.test_command, project.path)
    except DevSpaceError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def info(
    name: Annotated[str, typer.Argument(help="Name of the registered project.")],
) -> None:
    """Show stored project details together with live Git information."""
    try:
        project = _build_registry().get(name)
        git_info = GitInspector().inspect(project.path)
    except DevSpaceError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    console = Console(soft_wrap=True)
    console.print("Project Information\n")
    console.print(f"Name:          {escape(project.name)}")
    console.print(f"Type:          {project.project_type.value}")
    console.print(f"Path:          {escape(str(project.path))}")
    console.print(f"Run command:   {escape(project.run_command or '-')}")
    console.print(f"Test command:  {escape(project.test_command or '-')}")
    console.print()

    if not git_info.is_repository:
        console.print("Git repository: No")
        return

    console.print("Git repository: Yes")
    console.print(f"Branch:         {escape(git_info.branch or '-')}")
    console.print(f"Working tree:   {'dirty' if git_info.is_dirty else 'clean'}")
    console.print(f"Last commit:    {escape(git_info.last_commit or 'No commits yet')}")


if __name__ == "__main__":
    app()
