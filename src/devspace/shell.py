import shlex
from pathlib import Path

import typer

try:
    import readline
except ImportError:  # not available on every platform (e.g. Windows)
    readline = None

PROMPT = "devspace> "
EXIT_WORDS = {"exit", "quit"}
HISTORY_LENGTH = 1000


def run_shell(app: typer.Typer, history_file: Path) -> None:
    """Interactive session: read a line, run it as a DevSpace command, repeat.

    Output stays in the terminal's scrollback, and readline provides line editing
    and Up/Down history, which is saved to `history_file` between sessions.
    """
    _load_history(history_file)
    typer.echo("DevSpace shell. Type 'help' for commands, 'exit' to quit.")

    try:
        while True:
            try:
                line = input(PROMPT).strip()
            except EOFError:
                typer.echo()
                break
            except KeyboardInterrupt:
                typer.echo()
                continue

            if not line:
                continue
            if line in EXIT_WORDS:
                _forget_last_history_entry()
                break

            _dispatch(app, line)
    finally:
        _save_history(history_file)


def _dispatch(app: typer.Typer, line: str) -> None:
    try:
        args = shlex.split(line)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        return

    if args[0] == "help":
        args = [*args[1:], "--help"]

    try:
        app(args=args, prog_name="devspace")
    except SystemExit:
        # Typer exits after every command; in the shell that only ends this command.
        pass
    except KeyboardInterrupt:
        typer.echo()


def _forget_last_history_entry() -> None:
    """Keep 'exit' out of history so Up-arrow recalls the last real command."""
    if readline is None:
        return
    length = readline.get_current_history_length()
    if length > 0 and readline.get_history_item(length) in EXIT_WORDS:
        readline.remove_history_item(length - 1)


def _load_history(history_file: Path) -> None:
    if readline is None:
        return
    readline.set_history_length(HISTORY_LENGTH)
    try:
        readline.read_history_file(history_file)
    except OSError:
        pass


def _save_history(history_file: Path) -> None:
    if readline is None:
        return
    try:
        history_file.parent.mkdir(parents=True, exist_ok=True)
        readline.write_history_file(history_file)
    except OSError:
        pass
