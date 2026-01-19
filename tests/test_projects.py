"""Tests for projects module."""

import pytest

from idlergear.projects import (
    DEFAULT_COLUMNS,
    add_task_to_project,
    auto_add_task_if_configured,
    create_project,
    delete_project,
    get_project,
    list_projects,
    move_task,
    remove_task_from_project,
)


@pytest.fixture
def project_dir(tmp_path):
    """Create an initialized IdlerGear project."""
    idlergear_dir = tmp_path / ".idlergear"
    idlergear_dir.mkdir()
    (idlergear_dir / "config.toml").write_text("")
    return tmp_path


def test_create_project(project_dir, monkeypatch):
    """Test creating a project."""
    monkeypatch.chdir(project_dir)

    project = create_project("My Sprint")

    assert project["title"] == "My Sprint"
    assert project["id"] == "my-sprint"
    assert project["columns"] == DEFAULT_COLUMNS
    assert "Backlog" in project["tasks"]
    assert project["tasks"]["Backlog"] == []


def test_create_project_custom_columns(project_dir, monkeypatch):
    """Test creating a project with custom columns."""
    monkeypatch.chdir(project_dir)

    columns = ["Todo", "Doing", "Done"]
    project = create_project("Custom Board", columns=columns)

    assert project["columns"] == columns
    assert "Todo" in project["tasks"]
    assert "Doing" in project["tasks"]
    assert "Done" in project["tasks"]


def test_create_project_duplicate(project_dir, monkeypatch):
    """Test that duplicate projects fail."""
    monkeypatch.chdir(project_dir)

    create_project("My Sprint")

    with pytest.raises(ValueError, match="already exists"):
        create_project("My Sprint")


def test_list_projects(project_dir, monkeypatch):
    """Test listing projects."""
    monkeypatch.chdir(project_dir)

    create_project("Alpha")
    create_project("Beta")

    projects = list_projects()

    assert len(projects) == 2
    titles = [p["title"] for p in projects]
    assert "Alpha" in titles
    assert "Beta" in titles


def test_get_project(project_dir, monkeypatch):
    """Test getting a project by name."""
    monkeypatch.chdir(project_dir)

    create_project("My Sprint")

    # By slug
    project = get_project("my-sprint")
    assert project is not None
    assert project["title"] == "My Sprint"

    # By title (case insensitive)
    project = get_project("MY SPRINT")
    assert project is not None
    assert project["title"] == "My Sprint"


def test_get_project_not_found(project_dir, monkeypatch):
    """Test getting a non-existent project."""
    monkeypatch.chdir(project_dir)

    project = get_project("nonexistent")
    assert project is None


def test_delete_project(project_dir, monkeypatch):
    """Test deleting a project."""
    monkeypatch.chdir(project_dir)

    create_project("My Sprint")
    assert get_project("my-sprint") is not None

    result = delete_project("my-sprint")
    assert result is True

    assert get_project("my-sprint") is None


def test_add_task_to_project(project_dir, monkeypatch):
    """Test adding a task to a project."""
    monkeypatch.chdir(project_dir)

    create_project("My Sprint")

    project = add_task_to_project("my-sprint", "1")

    assert "1" in project["tasks"]["Backlog"]


def test_add_task_to_specific_column(project_dir, monkeypatch):
    """Test adding a task to a specific column."""
    monkeypatch.chdir(project_dir)

    create_project("My Sprint")

    project = add_task_to_project("my-sprint", "1", column="In Progress")

    assert "1" in project["tasks"]["In Progress"]
    assert "1" not in project["tasks"]["Backlog"]


def test_add_task_invalid_column(project_dir, monkeypatch):
    """Test that adding to invalid column fails."""
    monkeypatch.chdir(project_dir)

    create_project("My Sprint")

    with pytest.raises(ValueError, match="Column 'Invalid' not found"):
        add_task_to_project("my-sprint", "1", column="Invalid")


def test_move_task(project_dir, monkeypatch):
    """Test moving a task between columns."""
    monkeypatch.chdir(project_dir)

    create_project("My Sprint")
    add_task_to_project("my-sprint", "1", column="Backlog")

    project = move_task("my-sprint", "1", "In Progress")

    assert "1" in project["tasks"]["In Progress"]
    assert "1" not in project["tasks"]["Backlog"]


def test_remove_task_from_project(project_dir, monkeypatch):
    """Test removing a task from a project."""
    monkeypatch.chdir(project_dir)

    create_project("My Sprint")
    add_task_to_project("my-sprint", "1")

    project = remove_task_from_project("my-sprint", "1")

    assert "1" not in project["tasks"]["Backlog"]


def test_task_only_in_one_column(project_dir, monkeypatch):
    """Test that a task can only be in one column."""
    monkeypatch.chdir(project_dir)

    create_project("My Sprint")
    add_task_to_project("my-sprint", "1", column="Backlog")
    add_task_to_project("my-sprint", "1", column="In Progress")

    project = get_project("my-sprint")

    # Task should only be in In Progress, not Backlog
    assert "1" not in project["tasks"]["Backlog"]
    assert "1" in project["tasks"]["In Progress"]


def test_auto_add_disabled(project_dir, monkeypatch):
    """Test that auto-add does nothing when disabled."""
    monkeypatch.chdir(project_dir)

    create_project("My Sprint")
    # Don't set auto_add config

    result = auto_add_task_if_configured("123")

    assert result is False


def test_auto_add_no_default_project(project_dir, monkeypatch):
    """Test that auto-add does nothing when no default project is set."""
    monkeypatch.chdir(project_dir)
    import tomli_w

    config_path = project_dir / ".idlergear" / "config.toml"
    config_path.write_text("")

    # Enable auto-add but don't set default project
    with open(config_path, "wb") as f:
        tomli_w.dump({"projects": {"auto_add": True}}, f)

    result = auto_add_task_if_configured("123")

    assert result is False


def test_auto_add_enabled(project_dir, monkeypatch):
    """Test that auto-add works when properly configured."""
    monkeypatch.chdir(project_dir)
    import tomli_w

    create_project("My Sprint")

    config_path = project_dir / ".idlergear" / "config.toml"
    with open(config_path, "wb") as f:
        tomli_w.dump(
            {
                "projects": {
                    "auto_add": True,
                    "default_project": "my-sprint",
                    "default_column": "Backlog",
                }
            },
            f,
        )

    result = auto_add_task_if_configured("123")

    assert result is True

    # Verify task was added
    project = get_project("my-sprint")
    assert "123" in project["tasks"]["Backlog"]


def test_auto_add_custom_column(project_dir, monkeypatch):
    """Test that auto-add uses custom column."""
    monkeypatch.chdir(project_dir)
    import tomli_w

    create_project("My Sprint")

    config_path = project_dir / ".idlergear" / "config.toml"
    with open(config_path, "wb") as f:
        tomli_w.dump(
            {
                "projects": {
                    "auto_add": True,
                    "default_project": "my-sprint",
                    "default_column": "In Progress",
                }
            },
            f,
        )

    result = auto_add_task_if_configured("123")

    assert result is True

    # Verify task was added to custom column
    project = get_project("my-sprint")
    assert "123" in project["tasks"]["In Progress"]
    assert "123" not in project["tasks"]["Backlog"]


def test_auto_add_project_not_found(project_dir, monkeypatch):
    """Test that auto-add fails silently if project doesn't exist."""
    monkeypatch.chdir(project_dir)
    import tomli_w

    config_path = project_dir / ".idlergear" / "config.toml"
    with open(config_path, "wb") as f:
        tomli_w.dump(
            {
                "projects": {
                    "auto_add": True,
                    "default_project": "nonexistent",
                }
            },
            f,
        )

    # Should not raise, just return False
    result = auto_add_task_if_configured("123")

    assert result is False
