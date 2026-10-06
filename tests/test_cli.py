import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from devspace.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def fake_home(tmp_path, monkeypatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def project_dir(tmp_path) -> Path:
    directory = tmp_path / "RAGLens"
    directory.mkdir()
    return directory


def storage_file(home: Path) -> Path:
    return home / ".devspace" / "projects.json"


def test_no_args_shows_help():
    result = runner.invoke(app, [])

    assert "add" in result.output
    assert "Usage" in result.output


def test_add_registers_and_persists_project(fake_home, project_dir):
    result = runner.invoke(
        app,
        ["add", "raglens", str(project_dir)],
        input="python\nuv run uvicorn main:app\nuv run pytest\n",
    )

    assert result.exit_code == 0
    assert "Project 'raglens' added successfully." in result.output
    assert json.loads(storage_file(fake_home).read_text()) == {
        "raglens": {
            "name": "raglens",
            "path": str(project_dir.resolve()),
            "project_type": "python",
            "run_command": "uv run uvicorn main:app",
            "test_command": "uv run pytest",
        }
    }


def test_empty_commands_become_none(fake_home, project_dir):
    result = runner.invoke(app, ["add", "raglens", str(project_dir)], input="generic\n\n\n")

    assert result.exit_code == 0
    stored = json.loads(storage_file(fake_home).read_text())["raglens"]
    assert stored["run_command"] is None
    assert stored["test_command"] is None


def test_path_is_expanded_and_resolved(fake_home, project_dir):
    relative = fake_home / "link" / ".." / ".." / project_dir.name
    (fake_home / "link").mkdir()

    result = runner.invoke(app, ["add", "raglens", str(relative)], input="python\n\n\n")

    assert result.exit_code == 0
    stored = json.loads(storage_file(fake_home).read_text())["raglens"]
    assert stored["path"] == str(project_dir.resolve())


def test_tilde_is_expanded(fake_home):
    (fake_home / "proj").mkdir()

    result = runner.invoke(app, ["add", "proj", "~/proj"], input="python\n\n\n")

    assert result.exit_code == 0
    stored = json.loads(storage_file(fake_home).read_text())["proj"]
    assert stored["path"] == str((fake_home / "proj").resolve())


def test_missing_path_is_rejected(fake_home, tmp_path):
    result = runner.invoke(app, ["add", "raglens", str(tmp_path / "nope")])

    assert result.exit_code == 1
    assert "Error: Path does not exist" in result.output
    assert "Traceback" not in result.output
    assert not storage_file(fake_home).exists()


def test_file_instead_of_directory_is_rejected(fake_home, tmp_path):
    a_file = tmp_path / "file.txt"
    a_file.write_text("")

    result = runner.invoke(app, ["add", "raglens", str(a_file)])

    assert result.exit_code == 1
    assert "Error: Path is not a directory" in result.output
    assert not storage_file(fake_home).exists()


def test_invalid_project_type_is_reprompted(fake_home, project_dir):
    result = runner.invoke(app, ["add", "raglens", str(project_dir)], input="cobol\npython\n\n\n")

    assert result.exit_code == 0
    assert "cobol" in result.output
    assert "Traceback" not in result.output
    assert json.loads(storage_file(fake_home).read_text())["raglens"]["project_type"] == "python"


def test_project_type_is_case_insensitive(fake_home, project_dir):
    result = runner.invoke(app, ["add", "raglens", str(project_dir)], input="PYTHON\n\n\n")

    assert result.exit_code == 0
    assert json.loads(storage_file(fake_home).read_text())["raglens"]["project_type"] == "python"


def test_duplicate_name_shows_friendly_error(fake_home, project_dir, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    runner.invoke(app, ["add", "raglens", str(project_dir)], input="python\n\n\n")

    result = runner.invoke(app, ["add", "raglens", str(other)], input="python\n\n\n")

    assert result.exit_code == 1
    assert "Error: Project name already registered: raglens" in result.output
    assert "Traceback" not in result.output


def test_duplicate_path_shows_friendly_error(project_dir):
    runner.invoke(app, ["add", "raglens", str(project_dir)], input="python\n\n\n")

    result = runner.invoke(app, ["add", "another", str(project_dir)], input="python\n\n\n")

    assert result.exit_code == 1
    assert "Error: Project path already registered as 'raglens'" in result.output


def test_corrupt_storage_shows_friendly_error(fake_home, project_dir):
    storage_file(fake_home).parent.mkdir()
    storage_file(fake_home).write_text("this is not json")

    result = runner.invoke(app, ["add", "raglens", str(project_dir)], input="python\n\n\n")

    assert result.exit_code == 1
    assert "Error: Could not read projects" in result.output
    assert "Traceback" not in result.output


def test_remove_unregisters_project_and_keeps_directory(fake_home, project_dir):
    runner.invoke(app, ["add", "raglens", str(project_dir)], input="python\n\n\n")

    result = runner.invoke(app, ["remove", "raglens"])

    assert result.exit_code == 0
    assert "Project 'raglens' removed." in result.output
    assert json.loads(storage_file(fake_home).read_text()) == {}
    assert project_dir.is_dir()


def test_remove_only_removes_named_project(fake_home, project_dir, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    runner.invoke(app, ["add", "raglens", str(project_dir)], input="python\n\n\n")
    runner.invoke(app, ["add", "other", str(other)], input="generic\n\n\n")

    runner.invoke(app, ["remove", "raglens"])

    assert list(json.loads(storage_file(fake_home).read_text())) == ["other"]


def test_removed_project_can_be_added_again(project_dir):
    runner.invoke(app, ["add", "raglens", str(project_dir)], input="python\n\n\n")
    runner.invoke(app, ["remove", "raglens"])

    result = runner.invoke(app, ["add", "raglens", str(project_dir)], input="python\n\n\n")

    assert result.exit_code == 0


def test_remove_unknown_project_shows_friendly_error(fake_home):
    result = runner.invoke(app, ["remove", "unknown"])

    assert result.exit_code == 1
    assert "Error: Project not found: unknown" in result.output
    assert "Traceback" not in result.output
    assert not storage_file(fake_home).exists()


def test_remove_with_corrupt_storage_shows_friendly_error(fake_home):
    storage_file(fake_home).parent.mkdir()
    storage_file(fake_home).write_text("this is not json")

    result = runner.invoke(app, ["remove", "raglens"])

    assert result.exit_code == 1
    assert "Error: Could not read projects" in result.output
    assert "Traceback" not in result.output


@pytest.fixture
def wide_terminal(monkeypatch):
    monkeypatch.setenv("COLUMNS", "300")


def test_list_empty_registry_shows_friendly_message(fake_home):
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No projects registered." in result.output
    assert not storage_file(fake_home).exists()


def list_row(output: str, name: str) -> list[str]:
    """Return the cells of the table row whose first cell is `name`."""
    for line in output.splitlines():
        cells = [cell.strip() for cell in line.strip("│ ").split("│")]
        if cells and cells[0] == name:
            return cells
    raise AssertionError(f"No row for {name!r} in:\n{output}")


def make_git_dir(parent: Path, name: str, *, dirty: bool = False, commit: bool = True) -> Path:
    path = parent / name
    path.mkdir()
    run_git(path, "init", "-b", "main")
    if commit:
        run_git(path, "commit", "--allow-empty", "-m", "Secret commit subject")
    if dirty:
        (path / "new.txt").write_text("new")
    return path


def test_list_table_has_dashboard_columns_only(wide_terminal, git_env, project_dir):
    runner.invoke(
        app,
        ["add", "raglens", str(project_dir)],
        input="python\nuv run uvicorn main:app\nuv run pytest\n",
    )

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    header = next(line for line in result.output.splitlines() if "Name" in line)
    assert [cell.strip() for cell in header.strip("┃ ").split("┃")] == [
        "Name",
        "Type",
        "Branch",
        "Status",
        "Path",
    ]
    assert "Run command" not in result.output
    assert "Test command" not in result.output
    assert "uv run" not in result.output


def test_list_shows_branch_status_and_path_per_project(wide_terminal, git_env, tmp_path):
    clean = make_git_dir(tmp_path, "frontend")
    dirty = make_git_dir(tmp_path, "raglens", dirty=True)
    notes = tmp_path / "notes"
    notes.mkdir()
    runner.invoke(app, ["add", "frontend", str(clean)], input="typescript\n\n\n")
    runner.invoke(app, ["add", "raglens", str(dirty)], input="python\n\n\n")
    runner.invoke(app, ["add", "notes", str(notes)], input="generic\n\n\n")

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert list_row(result.output, "frontend") == [
        "frontend", "typescript", "main", "clean", str(clean.resolve())
    ]
    assert list_row(result.output, "raglens") == [
        "raglens", "python", "main", "dirty", str(dirty.resolve())
    ]
    assert list_row(result.output, "notes") == [
        "notes", "generic", "-", "not-git", str(notes.resolve())
    ]


def test_list_does_not_show_latest_commit(wide_terminal, git_env, tmp_path):
    repo = make_git_dir(tmp_path, "raglens")
    runner.invoke(app, ["add", "raglens", str(repo)], input="python\n\n\n")

    result = runner.invoke(app, ["list"])

    assert "Secret commit subject" not in result.output


def test_list_repo_without_commits_is_clean(wide_terminal, git_env, tmp_path):
    repo = make_git_dir(tmp_path, "fresh", commit=False)
    runner.invoke(app, ["add", "fresh", str(repo)], input="python\n\n\n")

    result = runner.invoke(app, ["list"])

    assert list_row(result.output, "fresh")[2:4] == ["main", "clean"]


def test_list_detached_head_shows_dash_for_branch(wide_terminal, git_env, tmp_path):
    repo = make_git_dir(tmp_path, "detached")
    run_git(repo, "checkout", "--detach")
    runner.invoke(app, ["add", "detached", str(repo)], input="python\n\n\n")

    result = runner.invoke(app, ["list"])

    assert list_row(result.output, "detached")[2:4] == ["-", "clean"]


def test_list_deleted_project_directory_is_not_git(wide_terminal, git_env, tmp_path):
    gone = tmp_path / "gone"
    gone.mkdir()
    runner.invoke(app, ["add", "gone", str(gone)], input="python\n\n\n")
    gone.rmdir()

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert list_row(result.output, "gone")[2:4] == ["-", "not-git"]


def test_list_does_not_treat_brackets_as_markup(wide_terminal, git_env, tmp_path):
    repo = make_git_dir(tmp_path, "proj")
    runner.invoke(app, ["add", "my[bold]proj", str(repo)], input="python\n\n\n")

    result = runner.invoke(app, ["list"])

    assert "my[bold]proj" in result.output


def test_list_git_not_installed_shows_friendly_error(wide_terminal, git_env, project_dir, monkeypatch):
    runner.invoke(app, ["add", "raglens", str(project_dir)], input="python\n\n\n")
    monkeypatch.setenv("PATH", "")

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 1
    assert "Error: Could not run git" in result.output
    assert "Traceback" not in result.output


def test_list_after_remove_no_longer_shows_project(wide_terminal, project_dir):
    runner.invoke(app, ["add", "raglens", str(project_dir)], input="python\n\n\n")
    runner.invoke(app, ["remove", "raglens"])

    result = runner.invoke(app, ["list"])

    assert "raglens" not in result.output
    assert "No projects registered." in result.output


def test_list_with_corrupt_storage_shows_friendly_error(fake_home):
    storage_file(fake_home).parent.mkdir()
    storage_file(fake_home).write_text("this is not json")

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 1
    assert "Error: Could not read projects" in result.output
    assert "Traceback" not in result.output


def run_git(path: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True)


@pytest.fixture
def git_env(monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@example.com")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(Path(os.environ["HOME"]).parent))


@pytest.fixture
def git_project(git_env, project_dir) -> Path:
    run_git(project_dir, "init", "-b", "main")
    runner.invoke(app, ["add", "raglens", str(project_dir)], input="python\n\n\n")
    return project_dir


def test_status_clean_repo(git_project):
    (git_project / "a.txt").write_text("a")
    run_git(git_project, "add", "a.txt")
    run_git(git_project, "commit", "-m", "Add JSON storage")

    result = runner.invoke(app, ["status", "raglens"])

    assert result.exit_code == 0
    assert "Project:      raglens" in result.output
    assert "Branch:       main" in result.output
    assert "Working tree: clean" in result.output
    assert "Last commit:  Add JSON storage" in result.output


def test_status_dirty_repo(git_project):
    run_git(git_project, "commit", "--allow-empty", "-m", "first")
    (git_project / "new.txt").write_text("new")

    result = runner.invoke(app, ["status", "raglens"])

    assert result.exit_code == 0
    assert "Working tree: dirty" in result.output


def test_status_repo_without_commits(git_project):
    result = runner.invoke(app, ["status", "raglens"])

    assert result.exit_code == 0
    assert "Branch:       main" in result.output
    assert "Last commit:  No commits yet" in result.output


def test_status_detached_head_shows_dash_for_branch(git_project):
    run_git(git_project, "commit", "--allow-empty", "-m", "first")
    run_git(git_project, "checkout", "--detach")

    result = runner.invoke(app, ["status", "raglens"])

    assert result.exit_code == 0
    assert "Branch:       -" in result.output


def test_status_non_git_project_is_not_an_error(git_env, project_dir):
    runner.invoke(app, ["add", "raglens", str(project_dir)], input="python\n\n\n")

    result = runner.invoke(app, ["status", "raglens"])

    assert result.exit_code == 0
    assert "Project:      raglens" in result.output
    assert "Git:          Not initialized" in result.output
    assert "Branch" not in result.output


def test_status_commit_message_with_brackets_is_shown_literally(git_project):
    run_git(git_project, "commit", "--allow-empty", "-m", "Fix [bold] bug")

    result = runner.invoke(app, ["status", "raglens"])

    assert "Last commit:  Fix [bold] bug" in result.output


def test_status_unknown_project_shows_friendly_error():
    result = runner.invoke(app, ["status", "unknown"])

    assert result.exit_code == 1
    assert "Error: Project not found: unknown" in result.output
    assert "Traceback" not in result.output


def test_status_requires_a_name():
    result = runner.invoke(app, ["status"])

    assert result.exit_code != 0


def test_status_git_not_installed_shows_friendly_error(git_project, monkeypatch):
    monkeypatch.setenv("PATH", "")

    result = runner.invoke(app, ["status", "raglens"])

    assert result.exit_code == 1
    assert "Error: Could not run git" in result.output
    assert "Traceback" not in result.output


def test_status_with_corrupt_storage_shows_friendly_error(fake_home):
    storage_file(fake_home).parent.mkdir()
    storage_file(fake_home).write_text("this is not json")

    result = runner.invoke(app, ["status", "raglens"])

    assert result.exit_code == 1
    assert "Error: Could not read projects" in result.output


def add_project(project_dir: Path, run: str = "", test: str = "", project_type: str = "python") -> None:
    runner.invoke(
        app, ["add", "raglens", str(project_dir)], input=f"{project_type}\n{run}\n{test}\n"
    )


def test_info_shows_stored_fields_and_clean_git_state(git_env, project_dir):
    run_git(project_dir, "init", "-b", "main")
    (project_dir / "a.txt").write_text("a")
    run_git(project_dir, "add", "a.txt")
    run_git(project_dir, "commit", "-m", "Add registry persistence")
    add_project(project_dir, run="uv run uvicorn main:app", test="uv run pytest")

    result = runner.invoke(app, ["info", "raglens"])

    assert result.exit_code == 0
    assert "Project Information" in result.output
    assert "Name:          raglens" in result.output
    assert "Type:          python" in result.output
    assert f"Path:          {project_dir.resolve()}" in result.output
    assert "Run command:   uv run uvicorn main:app" in result.output
    assert "Test command:  uv run pytest" in result.output
    assert "Git repository: Yes" in result.output
    assert "Branch:         main" in result.output
    assert "Working tree:   clean" in result.output
    assert "Last commit:    Add registry persistence" in result.output


def test_info_dirty_working_tree(git_env, project_dir):
    run_git(project_dir, "init", "-b", "main")
    run_git(project_dir, "commit", "--allow-empty", "-m", "first")
    (project_dir / "new.txt").write_text("new")
    add_project(project_dir)

    result = runner.invoke(app, ["info", "raglens"])

    assert "Working tree:   dirty" in result.output


def test_info_missing_commands_show_dash(git_env, project_dir):
    add_project(project_dir)

    result = runner.invoke(app, ["info", "raglens"])

    assert result.exit_code == 0
    assert "Run command:   -" in result.output
    assert "Test command:  -" in result.output


def test_info_non_git_project_shows_only_repository_no(git_env, project_dir):
    add_project(project_dir)

    result = runner.invoke(app, ["info", "raglens"])

    assert result.exit_code == 0
    assert "Name:          raglens" in result.output
    assert "Git repository: No" in result.output
    assert "Branch" not in result.output
    assert "Working tree" not in result.output
    assert "Last commit" not in result.output


def test_info_repo_without_commits(git_env, project_dir):
    run_git(project_dir, "init", "-b", "main")
    add_project(project_dir)

    result = runner.invoke(app, ["info", "raglens"])

    assert result.exit_code == 0
    assert "Git repository: Yes" in result.output
    assert "Last commit:    No commits yet" in result.output


def test_info_detached_head_shows_dash_for_branch(git_env, project_dir):
    run_git(project_dir, "init", "-b", "main")
    run_git(project_dir, "commit", "--allow-empty", "-m", "first")
    run_git(project_dir, "checkout", "--detach")
    add_project(project_dir)

    result = runner.invoke(app, ["info", "raglens"])

    assert "Branch:         -" in result.output


def test_info_values_with_brackets_are_shown_literally(git_env, project_dir):
    add_project(project_dir, run="pytest [bold] -k x")

    result = runner.invoke(app, ["info", "raglens"])

    assert "Run command:   pytest [bold] -k x" in result.output


def test_info_unknown_project_shows_friendly_error():
    result = runner.invoke(app, ["info", "unknown"])

    assert result.exit_code == 1
    assert "Error: Project not found: unknown" in result.output
    assert "Traceback" not in result.output


def test_info_requires_a_name():
    assert runner.invoke(app, ["info"]).exit_code != 0


def test_info_git_not_installed_shows_friendly_error(git_env, project_dir, monkeypatch):
    add_project(project_dir)
    monkeypatch.setenv("PATH", "")

    result = runner.invoke(app, ["info", "raglens"])

    assert result.exit_code == 1
    assert "Error: Could not run git" in result.output
    assert "Traceback" not in result.output


def test_info_with_corrupt_storage_shows_friendly_error(fake_home):
    storage_file(fake_home).parent.mkdir()
    storage_file(fake_home).write_text("this is not json")

    result = runner.invoke(app, ["info", "raglens"])

    assert result.exit_code == 1
    assert "Error: Could not read projects" in result.output


def py_cmd(code: str) -> str:
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}"


def test_run_executes_stored_command_in_project_directory(project_dir):
    add_project(project_dir, run=py_cmd("open('ran.txt', 'w').write('x')"))

    result = runner.invoke(app, ["run", "raglens"])

    assert result.exit_code == 0
    assert (project_dir / "ran.txt").read_text() == "x"


def test_run_output_goes_to_the_terminal(project_dir, capfd):
    add_project(project_dir, run=py_cmd("print('server started')"))

    runner.invoke(app, ["run", "raglens"])

    assert "server started" in capfd.readouterr().out


def test_run_without_run_command_shows_friendly_error(project_dir):
    add_project(project_dir)

    result = runner.invoke(app, ["run", "raglens"])

    assert result.exit_code == 1
    assert "Error: Project 'raglens' has no run command configured" in result.output
    assert "Traceback" not in result.output


def test_run_failing_command_shows_friendly_error(project_dir):
    add_project(project_dir, run=py_cmd("import sys; sys.exit(2)"))

    result = runner.invoke(app, ["run", "raglens"])

    assert result.exit_code == 1
    assert "Error: Command failed with exit code 2" in result.output
    assert "Traceback" not in result.output


def test_run_missing_executable_shows_friendly_error(project_dir):
    add_project(project_dir, run="definitely-not-a-real-program --flag")

    result = runner.invoke(app, ["run", "raglens"])

    assert result.exit_code == 1
    assert "Error: Could not run command" in result.output
    assert "Traceback" not in result.output


def test_run_deleted_project_directory_shows_friendly_error(project_dir):
    add_project(project_dir, run=py_cmd("pass"))
    project_dir.rmdir()

    result = runner.invoke(app, ["run", "raglens"])

    assert result.exit_code == 1
    assert "Error: Could not run command" in result.output


def test_run_unknown_project_shows_friendly_error():
    result = runner.invoke(app, ["run", "unknown"])

    assert result.exit_code == 1
    assert "Error: Project not found: unknown" in result.output


def test_run_requires_a_name():
    assert runner.invoke(app, ["run"]).exit_code != 0


def test_run_with_corrupt_storage_shows_friendly_error(fake_home):
    storage_file(fake_home).parent.mkdir()
    storage_file(fake_home).write_text("this is not json")

    result = runner.invoke(app, ["run", "raglens"])

    assert result.exit_code == 1
    assert "Error: Could not read projects" in result.output


def test_test_executes_stored_command_in_project_directory(project_dir):
    add_project(project_dir, test=py_cmd("open('tested.txt', 'w').write('x')"))

    result = runner.invoke(app, ["test", "raglens"])

    assert result.exit_code == 0
    assert (project_dir / "tested.txt").read_text() == "x"


def test_test_without_test_command_shows_friendly_error(project_dir):
    add_project(project_dir, run=py_cmd("pass"))

    result = runner.invoke(app, ["test", "raglens"])

    assert result.exit_code == 1
    assert "Error: Project 'raglens' has no test command configured" in result.output
    assert "Traceback" not in result.output


def test_test_failing_command_shows_friendly_error(project_dir):
    add_project(project_dir, test=py_cmd("import sys; sys.exit(4)"))

    result = runner.invoke(app, ["test", "raglens"])

    assert result.exit_code == 1
    assert "Error: Command failed with exit code 4" in result.output
    assert "Traceback" not in result.output


def test_test_unknown_project_shows_friendly_error():
    result = runner.invoke(app, ["test", "unknown"])

    assert result.exit_code == 1
    assert "Error: Project not found: unknown" in result.output
