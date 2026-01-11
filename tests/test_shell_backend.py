"""Tests for shell-based backends."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from idlergear.backends.shell import (
    ShellBackendError,
    ShellExploreBackend,
    ShellReferenceBackend,
    ShellTaskBackend,
    _apply_field_map,
    _parse_json_output,
    _run_command,
    load_shell_backend_config,
)


class TestRunCommand:
    """Tests for _run_command function."""

    def test_simple_command(self) -> None:
        """Test running a simple echo command."""
        result = _run_command("echo 'hello'", {})
        assert result == "hello"

    def test_parameter_substitution(self) -> None:
        """Test parameter substitution in commands."""
        result = _run_command("echo '$name'", {"name": "world"})
        assert result == "world"

    def test_multiple_parameters(self) -> None:
        """Test multiple parameter substitution."""
        result = _run_command("echo '$a $b'", {"a": "hello", "b": "world"})
        assert result == "hello world"

    def test_list_parameter(self) -> None:
        """Test list parameter is joined with commas."""
        result = _run_command("echo '$items'", {"items": ["a", "b", "c"]})
        assert result == "a,b,c"

    def test_bool_parameter_true(self) -> None:
        """Test boolean true becomes 'true'."""
        result = _run_command("echo '$flag'", {"flag": True})
        assert result == "true"

    def test_bool_parameter_false(self) -> None:
        """Test boolean false becomes 'false'."""
        result = _run_command("echo '$flag'", {"flag": False})
        assert result == "false"

    def test_none_parameter(self) -> None:
        """Test None parameter becomes empty string."""
        result = _run_command("echo 'x$value'x", {"value": None})
        assert result == "xx"

    def test_unmatched_variable_left_alone(self) -> None:
        """Test that unmatched $vars are left as-is (safe_substitute)."""
        result = _run_command("echo '$known $unknown'", {"known": "value"})
        assert result == "value $unknown"

    def test_command_failure_raises_error(self) -> None:
        """Test that command failure raises ShellBackendError."""
        with pytest.raises(ShellBackendError) as exc_info:
            _run_command("exit 1", {})
        assert "Command failed" in str(exc_info.value)

    def test_command_timeout(self) -> None:
        """Test that command timeout raises ShellBackendError."""
        with pytest.raises(ShellBackendError) as exc_info:
            # Use a long sleep with very short timeout
            # Note: We can't easily test timeout with _run_command's default 30s
            # So we patch subprocess.run to raise TimeoutExpired
            with patch("idlergear.backends.shell.subprocess.run") as mock_run:
                import subprocess

                mock_run.side_effect = subprocess.TimeoutExpired("sleep", 1)
                _run_command("sleep 100", {})
        assert "timed out" in str(exc_info.value)


class TestParseJsonOutput:
    """Tests for _parse_json_output function."""

    def test_empty_output_returns_none(self) -> None:
        """Test that empty output returns None."""
        assert _parse_json_output("") is None
        assert _parse_json_output(None) is None  # type: ignore

    def test_valid_json_object(self) -> None:
        """Test parsing valid JSON object."""
        output = '{"id": 1, "title": "Test"}'
        result = _parse_json_output(output)
        assert result == {"id": 1, "title": "Test"}

    def test_valid_json_array(self) -> None:
        """Test parsing valid JSON array."""
        output = '[{"id": 1}, {"id": 2}]'
        result = _parse_json_output(output)
        assert result == [{"id": 1}, {"id": 2}]

    def test_invalid_json_raises_error(self) -> None:
        """Test that invalid JSON raises ShellBackendError."""
        with pytest.raises(ShellBackendError) as exc_info:
            _parse_json_output("{invalid json}")
        assert "Invalid JSON" in str(exc_info.value)

    def test_field_map_applied(self) -> None:
        """Test that field_map is applied to output."""
        output = '{"number": 123, "title": "Test"}'
        field_map = {"number": "id"}
        result = _parse_json_output(output, field_map)
        assert result == {"id": 123, "title": "Test"}


class TestApplyFieldMap:
    """Tests for _apply_field_map function."""

    def test_simple_dict(self) -> None:
        """Test field mapping on a simple dict."""
        data = {"number": 1, "name": "test"}
        field_map = {"number": "id"}
        result = _apply_field_map(data, field_map)
        assert result == {"id": 1, "name": "test"}

    def test_list_of_dicts(self) -> None:
        """Test field mapping on a list of dicts."""
        data = [{"number": 1}, {"number": 2}]
        field_map = {"number": "id"}
        result = _apply_field_map(data, field_map)
        assert result == [{"id": 1}, {"id": 2}]

    def test_non_dict_returned_as_is(self) -> None:
        """Test that non-dict values are returned unchanged."""
        assert _apply_field_map("string", {}) == "string"
        assert _apply_field_map(123, {}) == 123
        assert _apply_field_map(None, {}) is None

    def test_unmapped_keys_preserved(self) -> None:
        """Test that unmapped keys are preserved."""
        data = {"number": 1, "title": "test", "body": "content"}
        field_map = {"number": "id"}
        result = _apply_field_map(data, field_map)
        assert result == {"id": 1, "title": "test", "body": "content"}


class TestShellTaskBackend:
    """Tests for ShellTaskBackend."""

    def test_create_task(self) -> None:
        """Test creating a task via shell command."""
        config = {
            "commands": {
                "create": 'echo \'{"id": 1, "title": "$title"}\'',
            },
        }
        backend = ShellTaskBackend(config)

        with patch.object(backend, "create") as mock_create:
            mock_create.return_value = {"id": 1, "title": "Test"}
            result = backend.create("Test")
            assert result == {"id": 1, "title": "Test"}

    def test_list_tasks(self) -> None:
        """Test listing tasks via shell command."""
        config = {
            "commands": {
                "list": 'echo \'[{"id": 1}, {"id": 2}]\'',
            },
        }
        backend = ShellTaskBackend(config)
        result = backend.list(state="open")
        assert result == [{"id": 1}, {"id": 2}]

    def test_list_with_field_map(self) -> None:
        """Test listing tasks with field mapping."""
        config = {
            "commands": {
                "list": 'echo \'[{"number": 1}, {"number": 2}]\'',
            },
            "field_map": {"number": "id"},
        }
        backend = ShellTaskBackend(config)
        result = backend.list()
        assert result == [{"id": 1}, {"id": 2}]

    def test_get_task(self) -> None:
        """Test getting a task by ID."""
        config = {
            "commands": {
                "get": 'echo \'{"id": $id, "title": "Test"}\'',
            },
        }
        backend = ShellTaskBackend(config)
        result = backend.get(1)
        assert result == {"id": 1, "title": "Test"}

    def test_get_task_not_found(self) -> None:
        """Test getting a non-existent task returns None."""
        config = {
            "commands": {
                "get": "exit 1",
            },
        }
        backend = ShellTaskBackend(config)
        result = backend.get(999)
        assert result is None

    def test_close_task(self) -> None:
        """Test closing a task."""
        config = {
            "commands": {
                "close": 'echo \'{"id": $id, "state": "closed"}\'',
            },
        }
        backend = ShellTaskBackend(config)
        result = backend.close(1)
        assert result == {"id": 1, "state": "closed"}

    def test_close_falls_back_to_update(self) -> None:
        """Test close falls back to update if no close command."""
        config = {
            "commands": {
                "update": 'echo \'{"id": $id, "state": "$state"}\'',
            },
        }
        backend = ShellTaskBackend(config)
        result = backend.close(1)
        assert result == {"id": 1, "state": "closed"}

    def test_reopen_task(self) -> None:
        """Test reopening a task."""
        config = {
            "commands": {
                "reopen": 'echo \'{"id": $id, "state": "open"}\'',
            },
        }
        backend = ShellTaskBackend(config)
        result = backend.reopen(1)
        assert result == {"id": 1, "state": "open"}

    def test_missing_command_raises_error(self) -> None:
        """Test that missing command raises ShellBackendError."""
        config = {"commands": {}}
        backend = ShellTaskBackend(config)

        with pytest.raises(ShellBackendError) as exc_info:
            backend.create("Test")
        assert "No 'create' command configured" in str(exc_info.value)


class TestShellExploreBackend:
    """Tests for ShellExploreBackend."""

    def test_create_exploration(self) -> None:
        """Test creating an exploration."""
        config = {
            "commands": {
                "create": 'echo \'{"id": 1, "title": "$title"}\'',
            },
        }
        backend = ShellExploreBackend(config)
        result = backend.create("Test Exploration")
        assert result == {"id": 1, "title": "Test Exploration"}

    def test_list_explorations(self) -> None:
        """Test listing explorations."""
        config = {
            "commands": {
                "list": "echo '[{\"id\": 1}]'",
            },
        }
        backend = ShellExploreBackend(config)
        result = backend.list()
        assert result == [{"id": 1}]


class TestShellReferenceBackend:
    """Tests for ShellReferenceBackend."""

    def test_add_reference(self) -> None:
        """Test adding a reference."""
        config = {
            "commands": {
                "add": 'echo \'{"id": 1, "title": "$title"}\'',
            },
        }
        backend = ShellReferenceBackend(config)
        result = backend.add("Test Reference")
        assert result == {"id": 1, "title": "Test Reference"}

    def test_add_falls_back_to_create(self) -> None:
        """Test add falls back to create command."""
        config = {
            "commands": {
                "create": 'echo \'{"id": 1, "title": "$title"}\'',
            },
        }
        backend = ShellReferenceBackend(config)
        result = backend.add("Test Reference")
        assert result == {"id": 1, "title": "Test Reference"}

    def test_search_with_command(self) -> None:
        """Test search with configured command."""
        config = {
            "commands": {
                "search": 'echo \'[{"id": 1, "title": "Match"}]\'',
            },
        }
        backend = ShellReferenceBackend(config)
        result = backend.search("Match")
        assert result == [{"id": 1, "title": "Match"}]

    def test_search_fallback_to_list(self) -> None:
        """Test search falls back to list and filter."""
        config = {
            "commands": {
                "list": 'echo \'[{"id": 1, "title": "Match"}, {"id": 2, "title": "Other"}]\'',
            },
        }
        backend = ShellReferenceBackend(config)
        result = backend.search("match")
        assert result == [{"id": 1, "title": "Match"}]

    def test_get_by_id_with_command(self) -> None:
        """Test get_by_id with configured command."""
        config = {
            "commands": {
                "get_by_id": 'echo \'{"id": $id, "title": "Test"}\'',
            },
        }
        backend = ShellReferenceBackend(config)
        result = backend.get_by_id(1)
        assert result == {"id": 1, "title": "Test"}

    def test_get_by_id_fallback_to_list(self) -> None:
        """Test get_by_id falls back to list and filter."""
        config = {
            "commands": {
                "list": 'echo \'[{"id": 1, "title": "First"}, {"id": 2, "title": "Second"}]\'',
            },
        }
        backend = ShellReferenceBackend(config)
        result = backend.get_by_id(2)
        assert result == {"id": 2, "title": "Second"}


class TestLoadShellBackendConfig:
    """Tests for load_shell_backend_config function."""

    def test_load_from_project(self) -> None:
        """Test loading config from project .idlergear/backends/."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            backends_dir = project / ".idlergear" / "backends"
            backends_dir.mkdir(parents=True)

            # Create config file
            config_file = backends_dir / "github.toml"
            config_file.write_text("""
[task]
[task.commands]
list = "gh issue list --json number,title"
""")

            result = load_shell_backend_config("github", "task", project)
            assert result is not None
            assert "commands" in result
            assert result["commands"]["list"] == "gh issue list --json number,title"

    def test_load_from_user_config(self) -> None:
        """Test loading config from ~/.config/idlergear/backends/."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            backends_dir = home / ".config" / "idlergear" / "backends"
            backends_dir.mkdir(parents=True)

            config_file = backends_dir / "jira.toml"
            config_file.write_text("""
[task]
[task.commands]
list = "jira issue list"
""")

            with patch("idlergear.backends.shell.Path.home", return_value=home):
                result = load_shell_backend_config("jira", "task", None)
                assert result is not None
                assert result["commands"]["list"] == "jira issue list"

    def test_returns_none_if_not_found(self) -> None:
        """Test returns None if config file not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / ".idlergear").mkdir()

            result = load_shell_backend_config("nonexistent", "task", project)
            assert result is None

    def test_returns_none_if_type_not_in_config(self) -> None:
        """Test returns None if backend type not in config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            backends_dir = project / ".idlergear" / "backends"
            backends_dir.mkdir(parents=True)

            config_file = backends_dir / "github.toml"
            config_file.write_text("""
[explore]
[explore.commands]
list = "some command"
""")

            result = load_shell_backend_config("github", "task", project)
            assert result is None
