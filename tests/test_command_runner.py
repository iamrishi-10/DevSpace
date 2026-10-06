import shlex
import subprocess
import sys

import pytest

from devspace.exceptions import CommandExecutionError
from devspace.services.command_runner import CommandRunner

PYTHON = shlex.quote(sys.executable)


def python_command(code: str) -> str:
    return f"{PYTHON} -c {shlex.quote(code)}"


def test_successful_command_completes_normally(tmp_path):
    assert CommandRunner().run(python_command("pass"), tmp_path) is None


def test_command_runs_in_given_directory(tmp_path):
    marker = tmp_path / "marker.txt"

    CommandRunner().run(python_command("open('marker.txt', 'w').write('x')"), tmp_path)

    assert marker.read_text() == "x"


def test_command_arguments_are_split_like_a_shell_would(tmp_path):
    code = "import sys; open('args.txt', 'w').write('|'.join(sys.argv[1:]))"
    command = f"{PYTHON} -c {shlex.quote(code)} one 'two words' \"three words\""

    CommandRunner().run(command, tmp_path)

    assert (tmp_path / "args.txt").read_text() == "one|two words|three words"


def test_shell_syntax_is_not_interpreted(tmp_path):
    code = "import sys; open('args.txt', 'w').write('|'.join(sys.argv[1:]))"
    command = f"{PYTHON} -c {shlex.quote(code)} a && b > out.txt $HOME"

    CommandRunner().run(command, tmp_path)

    assert (tmp_path / "args.txt").read_text() == "a|&&|b|>|out.txt|$HOME"
    assert not (tmp_path / "out.txt").exists()


def test_output_goes_to_the_terminal_not_captured(tmp_path, capfd):
    CommandRunner().run(python_command("print('hello from child')"), tmp_path)

    assert "hello from child" in capfd.readouterr().out


def test_stderr_goes_to_the_terminal_not_captured(tmp_path, capfd):
    CommandRunner().run(
        python_command("import sys; print('oops', file=sys.stderr)"), tmp_path
    )

    assert "oops" in capfd.readouterr().err


def test_non_zero_exit_code_raises_command_execution_error(tmp_path):
    command = python_command("import sys; sys.exit(3)")

    with pytest.raises(CommandExecutionError) as exc_info:
        CommandRunner().run(command, tmp_path)

    assert "exit code 3" in str(exc_info.value)
    assert command in str(exc_info.value)


def test_missing_executable_raises_and_chains_original_error(tmp_path):
    with pytest.raises(CommandExecutionError) as exc_info:
        CommandRunner().run("definitely-not-a-real-program --flag", tmp_path)

    assert isinstance(exc_info.value.__cause__, FileNotFoundError)


def test_missing_working_directory_raises_and_chains_original_error(tmp_path):
    with pytest.raises(CommandExecutionError) as exc_info:
        CommandRunner().run(python_command("pass"), tmp_path / "gone")

    assert isinstance(exc_info.value.__cause__, OSError)


def test_permission_error_is_wrapped(tmp_path):
    script = tmp_path / "script.sh"
    script.write_text("#!/bin/sh\n")
    script.chmod(0o644)

    with pytest.raises(CommandExecutionError) as exc_info:
        CommandRunner().run(str(script), tmp_path)

    assert isinstance(exc_info.value.__cause__, PermissionError)


@pytest.mark.parametrize("command", ["", "   "])
def test_empty_command_raises(tmp_path, command):
    with pytest.raises(CommandExecutionError):
        CommandRunner().run(command, tmp_path)


def test_unbalanced_quotes_raise_and_chain_original_error(tmp_path):
    with pytest.raises(CommandExecutionError) as exc_info:
        CommandRunner().run("echo 'unterminated", tmp_path)

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_subprocess_is_called_with_split_args_cwd_no_shell_and_no_capture(tmp_path, monkeypatch):
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args[0], 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    CommandRunner().run("uv run pytest -q", tmp_path)

    (args, kwargs), = calls
    assert args == (["uv", "run", "pytest", "-q"],)
    assert kwargs == {"cwd": tmp_path}
