import io
import sys
from pathlib import Path

import pytest

from devspace.cli import app
from devspace.shell import run_shell


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


@pytest.fixture
def shell(monkeypatch, capsys, fake_home):
    """Run a shell session fed with the given lines; return everything it printed."""

    def run(*lines: str) -> str:
        monkeypatch.setattr(sys, "stdin", io.StringIO("\n".join(lines) + ("\n" if lines else "")))
        run_shell(app, fake_home / ".devspace" / "history")
        captured = capsys.readouterr()
        return captured.out + captured.err

    return run


def test_shell_shows_banner_and_exits_on_exit(shell):
    assert "DevSpace shell" in shell("exit")


def test_shell_exits_on_quit_and_on_end_of_input(shell):
    assert "DevSpace shell" in shell("quit")
    assert "DevSpace shell" in shell()


def test_shell_stops_reading_after_exit(shell):
    assert "No projects registered." not in shell("exit", "list")


def test_shell_runs_several_commands_in_one_session(shell, project_dir):
    out = shell(f"add raglens {project_dir}", "python", "", "", "list", "status raglens", "exit")

    assert "Project 'raglens' added successfully." in out
    assert "Name" in out and "not-git" in out
    assert "Git:          Not initialized" in out


def test_shell_session_continues_after_a_failing_command(shell):
    out = shell("remove unknown", "list", "exit")

    assert "Error: Project not found: unknown" in out
    assert "No projects registered." in out


def test_shell_session_continues_after_unknown_command_or_bad_usage(shell):
    out = shell("bogus", "status", "list", "exit")

    assert "No such command" in out
    assert "No projects registered." in out


def test_shell_ignores_blank_lines(shell):
    assert "No projects registered." in shell("", "   ", "list", "exit")


def test_shell_help_lists_commands(shell):
    out = shell("help", "exit")

    for command in ("add", "list", "remove", "status", "run", "test", "info"):
        assert command in out


def test_shell_help_for_one_command(shell):
    assert "Name of the registered project" in shell("help status", "exit")


def test_shell_unbalanced_quotes_do_not_end_session(shell):
    out = shell("add 'oops", "list", "exit")

    assert "No projects registered." in out


def test_shell_has_no_shell_command_of_its_own(shell):
    out = shell("shell", "list", "exit")

    assert "No such command 'shell'" in out
    assert "No projects registered." in out
