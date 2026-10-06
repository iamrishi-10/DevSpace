import subprocess
from pathlib import Path

import pytest

from devspace.exceptions import CommandExecutionError
from devspace.services.git_inspector import GitInfo, GitInspector


def git(path: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True)


@pytest.fixture(autouse=True)
def isolated_git_env(tmp_path, monkeypatch):
    """Keep tests independent of the developer's git config and surrounding repos."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    for key, value in {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def repo(tmp_path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-b", "main")
    return path


def commit_file(repo: Path, name: str, message: str) -> None:
    (repo / name).write_text(name)
    git(repo, "add", name)
    git(repo, "commit", "-m", message)


def test_clean_repo_with_commit(repo):
    commit_file(repo, "a.txt", "Add JSON persistence")

    assert GitInspector().inspect(repo) == GitInfo(
        is_repository=True,
        branch="main",
        is_dirty=False,
        last_commit="Add JSON persistence",
    )


def test_modified_tracked_file_is_dirty(repo):
    commit_file(repo, "a.txt", "first")
    (repo / "a.txt").write_text("changed")

    assert GitInspector().inspect(repo).is_dirty is True


def test_untracked_file_is_dirty(repo):
    commit_file(repo, "a.txt", "first")
    (repo / "new.txt").write_text("new")

    assert GitInspector().inspect(repo).is_dirty is True


def test_last_commit_is_most_recent_subject(repo):
    commit_file(repo, "a.txt", "first")
    commit_file(repo, "b.txt", "second")

    assert GitInspector().inspect(repo).last_commit == "second"


def test_branch_name_is_reported(repo):
    commit_file(repo, "a.txt", "first")
    git(repo, "checkout", "-b", "feature/x")

    assert GitInspector().inspect(repo).branch == "feature/x"


def test_repo_with_no_commits_is_still_a_repository(repo):
    info = GitInspector().inspect(repo)

    assert info.is_repository is True
    assert info.branch == "main"
    assert info.is_dirty is False
    assert info.last_commit is None


def test_detached_head_has_no_branch(repo):
    commit_file(repo, "a.txt", "first")
    git(repo, "checkout", "--detach")

    info = GitInspector().inspect(repo)

    assert info.is_repository is True
    assert info.branch is None
    assert info.last_commit == "first"


def test_non_git_directory_is_not_a_repository(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()

    assert GitInspector().inspect(plain) == GitInfo(
        is_repository=False, branch=None, is_dirty=None, last_commit=None
    )


def test_missing_directory_is_not_a_repository(tmp_path):
    assert GitInspector().inspect(tmp_path / "gone").is_repository is False


def test_missing_git_executable_raises_command_execution_error(repo, monkeypatch):
    monkeypatch.setenv("PATH", "")

    with pytest.raises(CommandExecutionError) as exc_info:
        GitInspector().inspect(repo)

    assert isinstance(exc_info.value.__cause__, FileNotFoundError)


def test_git_is_run_in_project_directory_without_a_shell(repo, monkeypatch):
    calls = []
    real_run = subprocess.run

    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy)

    GitInspector().inspect(repo)

    assert [args[0] for args, _ in calls] == [
        ["git", "status", "--porcelain"],
        ["git", "branch", "--show-current"],
        ["git", "log", "-1", "--pretty=%s"],
    ]
    for _, kwargs in calls:
        assert kwargs["cwd"] == repo
        assert not kwargs.get("shell")
