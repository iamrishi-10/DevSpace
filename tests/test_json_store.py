import json
from pathlib import Path

import pytest

from devspace.enums import ProjectType
from devspace.exceptions import StorageError
from devspace.models.project import Project
from devspace.storage.base import ProjectStore
from devspace.storage.json_store import JsonProjectStore


@pytest.fixture
def raglens() -> Project:
    return Project(
        name="raglens",
        path=Path("/projects/raglens"),
        project_type=ProjectType.PYTHON,
        run_command="uv run uvicorn main:app",
        test_command="uv run pytest",
    )


def test_is_a_project_store(tmp_path):
    assert isinstance(JsonProjectStore(tmp_path / "projects.json"), ProjectStore)


def test_load_missing_file_returns_empty_dict(tmp_path):
    assert JsonProjectStore(tmp_path / "projects.json").load() == {}


def test_load_missing_file_does_not_create_anything(tmp_path):
    file_path = tmp_path / "missing_dir" / "projects.json"

    JsonProjectStore(file_path).load()

    assert not file_path.parent.exists()


def test_save_writes_json_with_plain_values(tmp_path, raglens):
    file_path = tmp_path / "projects.json"

    JsonProjectStore(file_path).save({"raglens": raglens})

    assert json.loads(file_path.read_text()) == {
        "raglens": {
            "name": "raglens",
            "path": "/projects/raglens",
            "project_type": "python",
            "run_command": "uv run uvicorn main:app",
            "test_command": "uv run pytest",
        }
    }


def test_save_creates_missing_parent_directory(tmp_path, raglens):
    file_path = tmp_path / "nested" / ".devspace" / "projects.json"

    JsonProjectStore(file_path).save({"raglens": raglens})

    assert file_path.is_file()


def test_round_trip_restores_typed_project(tmp_path, raglens):
    store = JsonProjectStore(tmp_path / "projects.json")
    store.save({"raglens": raglens})

    loaded = store.load()["raglens"]

    assert loaded == raglens
    assert isinstance(loaded.path, Path)
    assert isinstance(loaded.project_type, ProjectType)


def test_round_trip_preserves_none_commands(tmp_path):
    project = Project(name="bare", path=Path("/projects/bare"), project_type=ProjectType.GENERIC)
    store = JsonProjectStore(tmp_path / "projects.json")
    store.save({"bare": project})

    assert store.load() == {"bare": project}


def test_save_empty_dict_then_load(tmp_path):
    store = JsonProjectStore(tmp_path / "projects.json")
    store.save({})

    assert store.load() == {}


def test_load_invalid_json_raises_storage_error(tmp_path):
    file_path = tmp_path / "projects.json"
    file_path.write_text("this is not json")

    with pytest.raises(StorageError) as exc_info:
        JsonProjectStore(file_path).load()

    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)


@pytest.mark.parametrize(
    "content",
    [
        "[]",
        '{"raglens": "not a dict"}',
        '{"raglens": {"name": "raglens"}}',
        '{"raglens": {"name": "raglens", "path": "/p", "project_type": "cobol"}}',
    ],
)
def test_load_malformed_data_raises_storage_error(tmp_path, content):
    file_path = tmp_path / "projects.json"
    file_path.write_text(content)

    with pytest.raises(StorageError):
        JsonProjectStore(file_path).load()


def test_load_unreadable_path_raises_storage_error(tmp_path):
    # A directory exists at the path but cannot be read as a file
    file_path = tmp_path / "projects.json"
    file_path.mkdir()

    with pytest.raises(StorageError):
        JsonProjectStore(file_path).load()


def test_save_unwritable_path_raises_storage_error(tmp_path, raglens):
    # The parent "directory" is actually a file, so it can't be created
    blocker = tmp_path / "blocker"
    blocker.write_text("")

    with pytest.raises(StorageError) as exc_info:
        JsonProjectStore(blocker / "projects.json").save({"raglens": raglens})

    assert isinstance(exc_info.value.__cause__, OSError)
