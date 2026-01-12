"""Tests for CLI commands."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from idlergear.cli import app

runner = CliRunner()


@pytest.fixture
def cli_project():
    """Create a temporary project for CLI tests."""
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            os.chdir(project_path)

            # Initialize project
            result = runner.invoke(app, ["init"])
            assert result.exit_code == 0

            yield project_path
    finally:
        os.chdir(old_cwd)


class TestInitCommand:
    """Tests for init command."""

    def test_init(self, save_cwd):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            assert "Initialized IdlerGear" in result.output
            assert (Path(tmpdir) / ".idlergear").exists()

    def test_init_already_initialized(self, save_cwd):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            runner.invoke(app, ["init"])
            result = runner.invoke(app, ["init"])

            assert "already initialized" in result.output


class TestTaskCommands:
    """Tests for task commands."""

    def test_task_create(self, cli_project):
        result = runner.invoke(app, ["task", "create", "Test task"])

        assert result.exit_code == 0
        assert "Created task #1" in result.output

    def test_task_create_with_body(self, cli_project):
        result = runner.invoke(app, ["task", "create", "Test", "--body", "Description"])

        assert result.exit_code == 0

    def test_task_list_empty(self, cli_project):
        result = runner.invoke(app, ["--output", "human", "task", "list"])

        assert result.exit_code == 0
        assert "No" in result.output and "task" in result.output

    def test_task_list(self, cli_project):
        runner.invoke(app, ["task", "create", "Task one"])
        runner.invoke(app, ["task", "create", "Task two"])

        result = runner.invoke(app, ["task", "list"])

        assert result.exit_code == 0
        assert "Task one" in result.output
        assert "Task two" in result.output

    def test_task_show(self, cli_project):
        runner.invoke(app, ["task", "create", "Test task", "--body", "Task body"])

        result = runner.invoke(app, ["task", "show", "1"])

        assert result.exit_code == 0
        assert "Test task" in result.output
        assert "Task body" in result.output

    def test_task_show_not_found(self, cli_project):
        result = runner.invoke(app, ["--output", "human", "task", "show", "999"])

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_task_close(self, cli_project):
        runner.invoke(app, ["task", "create", "Test task"])

        result = runner.invoke(app, ["task", "close", "1"])

        assert result.exit_code == 0
        assert "Closed task #1" in result.output

    def test_task_edit(self, cli_project):
        runner.invoke(app, ["task", "create", "Original"])

        result = runner.invoke(app, ["task", "edit", "1", "--title", "Updated"])

        assert result.exit_code == 0
        assert "Updated task #1" in result.output


class TestNoteCommands:
    """Tests for note commands."""

    def test_note_create(self, cli_project):
        result = runner.invoke(app, ["note", "create", "Quick note"])

        assert result.exit_code == 0
        assert "Created note #1" in result.output

    def test_note_list(self, cli_project):
        runner.invoke(app, ["note", "create", "First note"])
        runner.invoke(app, ["note", "create", "Second note"])

        result = runner.invoke(app, ["note", "list"])

        assert result.exit_code == 0
        assert "First note" in result.output

    def test_note_show(self, cli_project):
        runner.invoke(app, ["note", "create", "Test note content"])

        result = runner.invoke(app, ["note", "show", "1"])

        assert result.exit_code == 0
        assert "Test note content" in result.output

    def test_note_delete(self, cli_project):
        runner.invoke(app, ["note", "create", "To delete"])

        result = runner.invoke(app, ["note", "delete", "1"])

        assert result.exit_code == 0
        assert "Deleted note #1" in result.output

    def test_note_promote(self, cli_project):
        runner.invoke(app, ["note", "create", "Promote me"])

        result = runner.invoke(app, ["note", "promote", "1", "--to", "task"])

        assert result.exit_code == 0
        assert "Promoted" in result.output


class TestVisionCommands:
    """Tests for vision commands."""

    def test_vision_show(self, cli_project):
        result = runner.invoke(app, ["vision", "show"])

        assert result.exit_code == 0
        # Default vision content
        assert "Project Vision" in result.output

    def test_vision_edit_with_content(self, cli_project):
        result = runner.invoke(app, ["vision", "edit", "--content", "New vision"])

        assert result.exit_code == 0
        assert "Vision updated" in result.output


class TestPlanCommands:
    """Tests for plan commands."""

    def test_plan_create(self, cli_project):
        result = runner.invoke(app, ["plan", "create", "my-plan"])

        assert result.exit_code == 0
        assert "Created plan: my-plan" in result.output

    def test_plan_list(self, cli_project):
        runner.invoke(app, ["plan", "create", "plan-a"])
        runner.invoke(app, ["plan", "create", "plan-b"])

        result = runner.invoke(app, ["plan", "list"])

        assert result.exit_code == 0
        assert "plan-a" in result.output
        assert "plan-b" in result.output

    def test_plan_show(self, cli_project):
        runner.invoke(app, ["plan", "create", "test-plan", "--title", "Test Plan"])

        result = runner.invoke(app, ["plan", "show", "test-plan"])

        assert result.exit_code == 0
        assert "Test Plan" in result.output

    def test_plan_switch(self, cli_project):
        runner.invoke(app, ["plan", "create", "my-plan"])

        result = runner.invoke(app, ["plan", "switch", "my-plan"])

        assert result.exit_code == 0
        assert "Switched to plan: my-plan" in result.output


class TestReferenceCommands:
    """Tests for reference commands."""

    def test_reference_add(self, cli_project):
        result = runner.invoke(app, ["reference", "add", "API Guide"])

        assert result.exit_code == 0
        assert "Added reference: API Guide" in result.output

    def test_reference_list(self, cli_project):
        runner.invoke(app, ["reference", "add", "Doc One"])
        runner.invoke(app, ["reference", "add", "Doc Two"])

        result = runner.invoke(app, ["reference", "list"])

        assert result.exit_code == 0
        assert "Doc One" in result.output
        assert "Doc Two" in result.output

    def test_reference_show(self, cli_project):
        runner.invoke(app, ["reference", "add", "Test Doc", "--body", "Content here"])

        result = runner.invoke(app, ["reference", "show", "Test Doc"])

        assert result.exit_code == 0
        assert "Test Doc" in result.output

    def test_reference_search(self, cli_project):
        runner.invoke(app, ["reference", "add", "Python Guide"])
        runner.invoke(app, ["reference", "add", "JavaScript Guide"])

        result = runner.invoke(app, ["reference", "search", "python"])

        assert result.exit_code == 0
        assert "Python Guide" in result.output


class TestConfigCommands:
    """Tests for config commands."""

    def test_config_set_and_get(self, cli_project):
        runner.invoke(app, ["config", "set", "test.key", "test-value"])

        result = runner.invoke(app, ["config", "get", "test.key"])

        assert result.exit_code == 0
        assert "test-value" in result.output

    def test_config_get_not_set(self, cli_project):
        result = runner.invoke(
            app, ["--output", "human", "config", "get", "nonexistent"]
        )

        assert result.exit_code == 0
        assert "not set" in result.output


class TestInstallCommands:
    """Tests for install/uninstall commands."""

    def test_install(self, cli_project):
        result = runner.invoke(app, ["install"])

        assert result.exit_code == 0
        assert (cli_project / ".mcp.json").exists()

    def test_uninstall(self, cli_project):
        runner.invoke(app, ["install"])
        result = runner.invoke(app, ["uninstall", "--force"])

        assert result.exit_code == 0


class TestNewCommand:
    """Tests for new command."""

    def test_new_project(self, save_cwd):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            result = runner.invoke(app, ["new", "test-project", "--no-git"])

            assert result.exit_code == 0
            assert "Created project" in result.output
            assert (Path(tmpdir) / "test-project").exists()

    def test_new_python_project(self, save_cwd):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            result = runner.invoke(
                app, ["new", "test-app", "--python", "--no-git", "--no-venv"]
            )

            assert result.exit_code == 0
            assert (Path(tmpdir) / "test-app" / "pyproject.toml").exists()


class TestDaemonCommands:
    """Tests for daemon commands."""

    def test_daemon_status_not_running(self, cli_project):
        result = runner.invoke(app, ["--output", "human", "daemon", "status"])

        assert result.exit_code == 0
        assert "not running" in result.output


class TestServeCommand:
    """Tests for serve command (MCP server)."""

    # Note: We can't easily test the serve command as it runs indefinitely
    # Integration tests for MCP are in test_mcp_server.py
    pass


class TestRunCommands:
    """Tests for run commands."""

    def test_run_start(self, cli_project):
        result = runner.invoke(
            app, ["run", "start", "echo hello", "--name", "test-run"]
        )

        assert result.exit_code == 0
        assert "Started run" in result.output
        assert "test-run" in result.output

    def test_run_list_empty(self, cli_project):
        result = runner.invoke(app, ["--output", "human", "run", "list"])

        assert result.exit_code == 0
        assert "No runs found" in result.output

    def test_run_list(self, cli_project):
        import time

        runner.invoke(app, ["run", "start", "echo hello", "--name", "my-run"])
        time.sleep(0.3)

        result = runner.invoke(app, ["run", "list"])

        assert result.exit_code == 0
        assert "my-run" in result.output

    def test_run_status(self, cli_project):
        import time

        runner.invoke(app, ["run", "start", "echo hello", "--name", "status-run"])
        time.sleep(0.3)

        result = runner.invoke(app, ["run", "status", "status-run"])

        assert result.exit_code == 0
        assert "status-run" in result.output

    def test_run_status_not_found(self, cli_project):
        result = runner.invoke(
            app, ["--output", "human", "run", "status", "nonexistent"]
        )

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_run_logs(self, cli_project):
        import time

        runner.invoke(app, ["run", "start", "echo 'hello world'", "--name", "log-run"])
        time.sleep(0.5)

        result = runner.invoke(app, ["run", "logs", "log-run"])

        assert result.exit_code == 0
        assert "hello" in result.output

    def test_run_logs_not_found(self, cli_project):
        result = runner.invoke(app, ["--output", "human", "run", "logs", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_run_stop(self, cli_project):
        import time

        runner.invoke(app, ["run", "start", "sleep 60", "--name", "stop-run"])
        time.sleep(0.3)

        result = runner.invoke(app, ["run", "stop", "stop-run"])

        assert result.exit_code == 0
        assert "Stopped run" in result.output

    def test_run_stop_not_found(self, cli_project):
        result = runner.invoke(app, ["--output", "human", "run", "stop", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.output


class TestErrorHandling:
    """Tests for error handling when not in a project."""

    def test_task_list_not_initialized(self, save_cwd):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            result = runner.invoke(app, ["task", "list"])

            assert result.exit_code == 1
            assert "Not in an IdlerGear project" in result.output

    def test_note_list_not_initialized(self, save_cwd):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            result = runner.invoke(app, ["note", "list"])

            assert result.exit_code == 1
            assert "Not in an IdlerGear project" in result.output


class TestAdditionalTaskCommands:
    """Additional task command tests."""

    def test_task_list_with_state(self, cli_project):
        runner.invoke(app, ["task", "create", "Open task"])
        runner.invoke(app, ["task", "create", "Task to close"])
        runner.invoke(app, ["task", "close", "2"])

        # List only open tasks
        result = runner.invoke(app, ["task", "list", "--state", "open"])
        assert "Open task" in result.output
        assert "Task to close" not in result.output

        # List closed tasks
        result = runner.invoke(app, ["task", "list", "--state", "closed"])
        assert "Task to close" in result.output

        # List all tasks
        result = runner.invoke(app, ["task", "list", "--state", "all"])
        assert "Open task" in result.output
        assert "Task to close" in result.output

    def test_task_close_not_found(self, cli_project):
        result = runner.invoke(app, ["--output", "human", "task", "close", "999"])

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_task_edit_not_found(self, cli_project):
        result = runner.invoke(
            app, ["--output", "human", "task", "edit", "999", "--title", "New"]
        )

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_task_edit_add_label(self, cli_project):
        runner.invoke(app, ["task", "create", "Task with labels"])

        result = runner.invoke(app, ["task", "edit", "1", "--add-label", "bug"])

        assert result.exit_code == 0
        assert "Updated task" in result.output

    def test_task_sync(self, cli_project):
        result = runner.invoke(app, ["task", "sync"])

        assert result.exit_code == 0
        assert "Syncing tasks" in result.output


class TestAdditionalNoteCommands:
    """Additional note command tests."""

    def test_note_show_not_found(self, cli_project):
        result = runner.invoke(app, ["--output", "human", "note", "show", "999"])

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_note_delete_not_found(self, cli_project):
        result = runner.invoke(app, ["--output", "human", "note", "delete", "999"])

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_note_promote_not_found(self, cli_project):
        result = runner.invoke(
            app, ["--output", "human", "note", "promote", "999", "--to", "task"]
        )

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_note_list_empty(self, cli_project):
        result = runner.invoke(app, ["--output", "human", "note", "list"])

        assert result.exit_code == 0
        assert "No notes found" in result.output


class TestAdditionalPlanCommands:
    """Additional plan command tests."""

    def test_plan_show_not_found(self, cli_project):
        result = runner.invoke(
            app, ["--output", "human", "plan", "show", "nonexistent"]
        )

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_plan_show_current(self, cli_project):
        runner.invoke(app, ["plan", "create", "my-plan"])
        runner.invoke(app, ["plan", "switch", "my-plan"])

        result = runner.invoke(app, ["--output", "human", "plan", "show"])

        assert result.exit_code == 0
        assert "my-plan" in result.output

    def test_plan_show_no_current(self, cli_project):
        result = runner.invoke(app, ["--output", "human", "plan", "show"])

        assert result.exit_code == 0
        assert "No current plan" in result.output

    def test_plan_switch_not_found(self, cli_project):
        result = runner.invoke(
            app, ["--output", "human", "plan", "switch", "nonexistent"]
        )

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_plan_list_empty(self, cli_project):
        result = runner.invoke(app, ["--output", "human", "plan", "list"])

        assert result.exit_code == 0
        assert "No plans found" in result.output

    def test_plan_sync(self, cli_project):
        result = runner.invoke(app, ["plan", "sync"])

        assert result.exit_code == 0
        assert "Syncing plans" in result.output


class TestAdditionalReferenceCommands:
    """Additional reference command tests."""

    def test_reference_show_not_found(self, cli_project):
        result = runner.invoke(
            app, ["--output", "human", "reference", "show", "nonexistent"]
        )

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_reference_edit(self, cli_project):
        runner.invoke(app, ["reference", "add", "Original"])

        result = runner.invoke(
            app, ["reference", "edit", "Original", "--title", "Updated"]
        )

        assert result.exit_code == 0
        assert "Updated reference" in result.output

    def test_reference_edit_not_found(self, cli_project):
        result = runner.invoke(
            app,
            ["--output", "human", "reference", "edit", "nonexistent", "--body", "New"],
        )

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_reference_search_no_results(self, cli_project):
        result = runner.invoke(
            app, ["--output", "human", "reference", "search", "nonexistent"]
        )

        assert result.exit_code == 0
        assert "No references found" in result.output

    def test_reference_list_includes_pinned(self, cli_project):
        """Test that reference list includes pinned references like vision."""
        result = runner.invoke(app, ["--output", "human", "reference", "list"])

        assert result.exit_code == 0
        # Should include vision (pinned reference)
        assert "vision" in result.output.lower()

    def test_reference_sync(self, cli_project):
        # Test with --status since full sync requires GitHub access
        result = runner.invoke(
            app, ["--output", "human", "reference", "sync", "--status"]
        )

        assert result.exit_code == 0
        assert "Sync Status" in result.output
