# DevSpace

DevSpace is a lightweight local CLI workspace manager for developers.

It lets you register local projects once, inspect their Git state, and run project-specific commands from anywhere in your terminal.

Instead of repeatedly navigating into project directories and remembering how each project is started or tested, DevSpace keeps that information in one place.

---

## Features

- Register local development projects
- Persistent project registry
- Support for:
  - Python
  - Java
  - JavaScript
  - TypeScript
  - Generic projects
- View all registered projects in a workspace dashboard
- Inspect live Git information
  - Current branch
  - Clean / dirty working tree
  - Latest commit
- Store project-specific run commands
- Store project-specific test commands
- Execute commands directly inside the registered project directory
- Works independently of package managers or frameworks
- Friendly CLI errors
- Local JSON-based persistence
- Installable as a global CLI command

---

## Why DevSpace?

Development projects often use different commands and live in different directories.

For example:

```bash
cd /projects/api
uv run uvicorn main:app --reload
```

or:

```bash
cd /projects/frontend
npm run dev
```

or:

```bash
cd /projects/service
./gradlew bootRun
```

With DevSpace, you register those details once:

```bash
devspace add api /projects/api
```

and later run:

```bash
devspace run api
```

from anywhere.

DevSpace does not try to guess your framework, package manager, virtual environment, or project structure.

You define the commands. DevSpace remembers and executes them.

---

# Installation

## Requirements

- Python 3.12+
- Git
- uv

Clone the repository:

```bash
git clone <your-repository-url>
cd devspace
```

Install DevSpace as an editable global CLI tool:

```bash
uv tool install --editable .
```

If the `devspace` command is not available after installation:

```bash
uv tool update-shell
```

Reload your shell:

```bash
exec $SHELL
```

Verify the installation:

```bash
devspace --help
```

You should now be able to use DevSpace from any directory.

---

# Usage

## Add a project

```bash
devspace add NAME PATH
```

Example:

```bash
devspace add raglens /projects/raglens
```

If the project name or path contains spaces, wrap it in quotes:

```bash
devspace add "AI Agents" "/projects/AI Agents"
```

DevSpace will prompt for the project type:

```text
Project type (python/java/javascript/typescript/generic):
```

and optionally ask for:

```text
Run command
Test command
```

Example:

```text
Project type: python
Run command: uv run uvicorn main:app --reload
Test command: uv run pytest
```

The run and test commands are optional.

---

## List projects

```bash
devspace list
```

Example output:

```text
┌────────────┬────────────┬────────┬─────────┬──────────────────────┐
│ Name       │ Type       │ Branch │ Status  │ Path                 │
├────────────┼────────────┼────────┼─────────┼──────────────────────┤
│ raglens    │ python     │ main   │ clean   │ /projects/raglens    │
│ frontend   │ typescript │ dev    │ dirty   │ /projects/frontend   │
│ notes      │ generic    │ -      │ not-git │ /projects/notes      │
└────────────┴────────────┴────────┴─────────┴──────────────────────┘
```

The Git status is read live whenever the command runs.

---

## Show project information

```bash
devspace info NAME
```

Example:

```bash
devspace info raglens
```

Example output:

```text
Project Information

Name:          raglens
Type:          python
Path:          /projects/raglens
Run command:   uv run uvicorn main:app --reload
Test command:  uv run pytest

Git repository: Yes
Branch:         main
Working tree:   clean
Last commit:    Add JSON persistence
```

---

## Check Git status

```bash
devspace status NAME
```

Example:

```bash
devspace status raglens
```

Example output:

```text
Project:      raglens
Branch:       main
Working tree: clean
Last commit:  Add JSON persistence
```

If the project is not a Git repository:

```text
Project: raglens
Git:     Not initialized
```

---

## Run a project

```bash
devspace run NAME
```

Example:

```bash
devspace run raglens
```

If the stored run command is:

```bash
uv run uvicorn main:app --reload
```

DevSpace executes that command with the registered project directory as the working directory.

This means you do not need to manually:

```bash
cd /projects/raglens
```

first.

---

## Run project tests

```bash
devspace test NAME
```

Example:

```bash
devspace test raglens
```

If the stored test command is:

```bash
uv run pytest
```

DevSpace runs it inside the registered project directory.

---

## Remove a project

```bash
devspace remove NAME
```

Example:

```bash
devspace remove raglens
```

Removing a project only removes it from the DevSpace registry.

It does **not** delete the actual project directory or any files.

---

# Supported Project Types

DevSpace currently supports the following project classifications:

```text
python
java
javascript
typescript
generic
```

The project type is metadata only.

DevSpace does not use it to decide how a project should run.

For example, a Python project could use:

```bash
uv run python main.py
```

while another Python project could use:

```bash
poetry run python app.py
```

DevSpace simply executes the command provided during registration.

---

# How DevSpace Works

DevSpace follows a small layered architecture:

```text
CLI
 │
 ▼
ProjectRegistry
 │
 ▼
ProjectStore
 │
 ▼
JsonProjectStore
```

Additional services handle external operations:

```text
GitInspector
    │
    └── Git subprocess commands

CommandRunner
    │
    └── User-defined commands
```

The CLI handles user interaction.

The registry handles project-related business rules.

The storage layer handles persistence.

GitInspector handles Git information.

CommandRunner handles execution of stored commands.

---

# Project Architecture

```text
devspace/
├── pyproject.toml
├── README.md
├── src/
│   └── devspace/
│       ├── __init__.py
│       ├── cli.py
│       ├── enums.py
│       ├── exceptions.py
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   └── project.py
│       │
│       ├── registry/
│       │   ├── __init__.py
│       │   └── project_registry.py
│       │
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   └── json_store.py
│       │
│       └── services/
│           ├── __init__.py
│           ├── git_inspector.py
│           └── command_runner.py
│
└── tests/
    ├── test_project_registry.py
    ├── test_json_store.py
    ├── test_git_inspector.py
    ├── test_command_runner.py
    └── test_cli.py
```

---

# Persistence

Registered projects are stored locally at:

```text
~/.devspace/projects.json
```

Example:

```json
{
  "raglens": {
    "name": "raglens",
    "path": "/projects/raglens",
    "project_type": "python",
    "run_command": "uv run uvicorn main:app --reload",
    "test_command": "uv run pytest"
  }
}
```

Only project configuration is persisted.

Git information such as branch, working-tree state, and latest commit is queried live and is never stored.

---

# Design Decisions

## Explicit configuration instead of automatic detection

DevSpace intentionally does not try to infer whether a project uses:

```text
uv
pip
Poetry
npm
pnpm
Yarn
Maven
Gradle
```

or any specific framework.

Modern projects can be configured in many different ways, and automatic detection quickly becomes unreliable.

Instead, the developer explicitly provides the commands DevSpace should run.

---

## No shell execution

Stored commands are parsed using Python's `shlex` module and executed without:

```python
shell=True
```

For example:

```text
uv run pytest -q
```

becomes:

```text
["uv", "run", "pytest", "-q"]
```

This keeps command execution simple and predictable.

Shell-specific expressions such as:

```bash
command1 && command2
command > output.txt
echo $HOME
```

are intentionally outside the current V1 scope.

---

## Dependency inversion

`ProjectRegistry` does not depend directly on JSON storage.

Instead it depends on the `ProjectStore` abstraction:

```text
ProjectRegistry
      ↓
ProjectStore
      ↑
JsonProjectStore
```

This keeps the business layer independent from the persistence implementation.

---

# Development

Install dependencies:

```bash
uv sync
```

Run the complete test suite:

```bash
uv run pytest
```

Or:

```bash
uv run pytest -q
```

Run DevSpace from the development environment:

```bash
uv run devspace --help
```

For editable global development:

```bash
uv tool install --editable .
```

Source-code changes are then reflected without reinstalling the tool.

---

# Testing

DevSpace includes tests for:

- Project registry behavior
- Duplicate project handling
- Project persistence
- JSON serialization/deserialization
- Storage failures
- Git repository detection
- Git branches
- Clean and dirty working trees
- Detached HEAD
- Repositories without commits
- Command execution
- Working-directory handling
- Exit-code handling
- Missing executables
- CLI registration and removal
- CLI Git information
- CLI run/test execution
- Friendly CLI error handling

Tests use temporary directories so normal user projects and the real DevSpace registry are not modified.

---

# Example Workflow

Register projects:

```bash
devspace add raglens "/projects/RAGLens"
devspace add "AI Agents" "/projects/AI Agents"
devspace add frontend "/projects/frontend"
```

Check your workspace:

```bash
devspace list
```

Inspect one project:

```bash
devspace info raglens
```

Check its Git state:

```bash
devspace status raglens
```

Start it:

```bash
devspace run raglens
```

Run its tests:

```bash
devspace test raglens
```

All of these commands can be executed from any directory.

---

# V1 Scope

DevSpace V1 intentionally stays small.

It does not currently include:

- Automatic project detection
- Framework detection
- Environment discovery
- Git commit/push/pull operations
- Remote repository management
- GUI
- Database storage
- Cloud synchronization
- Complex shell pipelines

The goal of V1 is to provide a small, reliable local developer workspace manager without unnecessary abstraction or configuration.

---

## License

## License

DevSpace is free and open-source software licensed under the [MIT License](LICENSE).

You are free to use, modify, distribute, and build upon DevSpace, including for commercial purposes, subject to the terms of the MIT License.