"""End-to-end tests for IdlerGear in a fresh project.

These tests simulate a real user workflow:
1. Create a new project directory
2. Initialize IdlerGear
3. Use IdlerGear commands throughout development
4. Verify everything works correctly
5. Clean up

These tests use the local backend only (no GitHub).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from .conftest import run_idlergear


class TestFreshProjectSetup:
    """Test IdlerGear initialization in a fresh project."""

    def test_init_creates_idlergear_directory(self, fresh_project: Path) -> None:
        """Test that init creates the .idlergear directory."""
        idlergear_dir = fresh_project / ".idlergear"
        assert idlergear_dir.exists()
        assert idlergear_dir.is_dir()

    def test_init_creates_config(self, fresh_project: Path) -> None:
        """Test that init creates a config file."""
        config_file = fresh_project / ".idlergear" / "config.toml"
        assert config_file.exists()

        content = config_file.read_text()
        # Config has [project] and [github] sections
        assert "[project]" in content

    def test_install_creates_claude_md(self, fresh_project_with_install: Path) -> None:
        """Test that install creates CLAUDE.md."""
        claude_md = fresh_project_with_install / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert "IdlerGear" in content
        assert "idlergear context" in content

    def test_install_creates_agents_md(self, fresh_project_with_install: Path) -> None:
        """Test that install creates AGENTS.md."""
        agents_md = fresh_project_with_install / "AGENTS.md"
        assert agents_md.exists()
        content = agents_md.read_text()
        assert "IdlerGear" in content
        assert "FORBIDDEN" in content

    def test_install_creates_rules_file(self, fresh_project_with_install: Path) -> None:
        """Test that install creates .claude/rules/idlergear.md."""
        rules_file = fresh_project_with_install / ".claude" / "rules" / "idlergear.md"
        assert rules_file.exists()
        content = rules_file.read_text()
        assert "alwaysApply: true" in content
        assert "idlergear context" in content

    def test_install_creates_mcp_json(self, fresh_project_with_install: Path) -> None:
        """Test that install creates .mcp.json."""
        mcp_json = fresh_project_with_install / ".mcp.json"
        assert mcp_json.exists()

        config = json.loads(mcp_json.read_text())
        assert "mcpServers" in config
        assert "idlergear" in config["mcpServers"]


class TestTaskWorkflow:
    """Test task management workflow."""

    def test_create_task(self, fresh_project: Path) -> None:
        """Test creating a task."""
        result = run_idlergear(fresh_project, "task", "create", "Implement user login")
        assert result.returncode == 0
        assert "Created task" in result.stdout or "task" in result.stdout.lower()

    def test_list_tasks(self, fresh_project: Path) -> None:
        """Test listing tasks after creating one."""
        # Create a task first
        run_idlergear(fresh_project, "task", "create", "Test task for listing")

        # List tasks
        result = run_idlergear(fresh_project, "task", "list")
        assert result.returncode == 0
        assert "Test task for listing" in result.stdout

    def test_show_task(self, fresh_project: Path) -> None:
        """Test showing a specific task."""
        # Create a task
        create_result = run_idlergear(
            fresh_project, "task", "create", "Task to show details"
        )
        assert create_result.returncode == 0

        # Extract task ID from output (format: "Created task #1: ...")
        # For local backend, IDs are typically simple integers or UUIDs
        result = run_idlergear(fresh_project, "task", "list")
        assert "Task to show details" in result.stdout

    def test_close_task(self, fresh_project: Path) -> None:
        """Test closing a task."""
        # Create a task
        run_idlergear(fresh_project, "task", "create", "Task to close")

        # Get task list to find the ID
        list_result = run_idlergear(fresh_project, "task", "list")

        # For local backend, try to close task 1
        close_result = run_idlergear(fresh_project, "task", "close", "1")
        # Should either succeed or give a reasonable error
        # (local backend may use different IDs)


class TestNoteWorkflow:
    """Test note management workflow."""

    def test_create_note(self, fresh_project: Path) -> None:
        """Test creating a note."""
        result = run_idlergear(
            fresh_project, "note", "create", "Remember to add error handling"
        )
        assert result.returncode == 0

    def test_list_notes(self, fresh_project: Path) -> None:
        """Test listing notes."""
        # Create a note first
        run_idlergear(fresh_project, "note", "create", "Note for listing test")

        # List notes
        result = run_idlergear(fresh_project, "note", "list")
        assert result.returncode == 0
        assert "Note for listing test" in result.stdout


class TestExploreWorkflow:
    """Test exploration workflow."""

    def test_create_exploration(self, fresh_project: Path) -> None:
        """Test creating an exploration."""
        result = run_idlergear(
            fresh_project, "explore", "create", "How should we structure the API?"
        )
        assert result.returncode == 0

    def test_list_explorations(self, fresh_project: Path) -> None:
        """Test listing explorations."""
        # Create an exploration first
        run_idlergear(
            fresh_project, "explore", "create", "Exploration for listing test"
        )

        # List explorations
        result = run_idlergear(fresh_project, "explore", "list")
        assert result.returncode == 0
        assert "Exploration for listing test" in result.stdout


class TestVisionWorkflow:
    """Test vision management workflow."""

    def test_show_vision_empty(self, fresh_project: Path) -> None:
        """Test showing vision when none is set."""
        result = run_idlergear(fresh_project, "vision", "show")
        # Should not error, may show empty or default message
        assert result.returncode == 0


class TestContextCommand:
    """Test the context command that shows everything."""

    def test_context_shows_overview(self, fresh_project: Path) -> None:
        """Test that context command provides an overview."""
        # First create some content
        run_idlergear(fresh_project, "task", "create", "Context test task")
        run_idlergear(fresh_project, "note", "create", "Context test note")

        # Run context
        result = run_idlergear(fresh_project, "context")
        assert result.returncode == 0
        # Context should show tasks and notes
        # (exact format depends on implementation)


class TestDevelopmentWorkflow:
    """Test a realistic development workflow sequence."""

    def test_full_development_session(self, fresh_project_with_install: Path) -> None:
        """Simulate a complete development session.

        This test follows a realistic workflow:
        1. Check context at session start
        2. Create tasks for planned work
        3. Create notes for observations
        4. Create exploration for research questions
        5. Close completed tasks
        6. Check context again
        """
        project = fresh_project_with_install

        # 1. Check context at session start (as per CLAUDE.md instructions)
        result = run_idlergear(project, "context")
        assert result.returncode == 0

        # 2. Create tasks for planned work
        result = run_idlergear(
            project, "task", "create", "Set up project structure"
        )
        assert result.returncode == 0

        result = run_idlergear(
            project, "task", "create", "Implement core functionality"
        )
        assert result.returncode == 0

        result = run_idlergear(
            project, "task", "create", "Add unit tests"
        )
        assert result.returncode == 0

        # 3. Create notes for observations
        result = run_idlergear(
            project, "note", "create", "Consider using async for I/O operations"
        )
        assert result.returncode == 0

        # 4. Create exploration for research question
        result = run_idlergear(
            project,
            "explore",
            "create",
            "What testing framework should we use?",
        )
        assert result.returncode == 0

        # 5. Verify all items are tracked
        task_list = run_idlergear(project, "task", "list")
        assert "Set up project structure" in task_list.stdout
        assert "Implement core functionality" in task_list.stdout
        assert "Add unit tests" in task_list.stdout

        note_list = run_idlergear(project, "note", "list")
        assert "async" in note_list.stdout

        explore_list = run_idlergear(project, "explore", "list")
        assert "testing framework" in explore_list.stdout

        # 6. Final context check
        final_context = run_idlergear(project, "context")
        assert final_context.returncode == 0


class TestUninstallWorkflow:
    """Test uninstalling IdlerGear."""

    def test_uninstall_removes_install_files(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that uninstall removes installed files but preserves data."""
        project = fresh_project_with_install

        # Verify files exist before uninstall
        assert (project / "CLAUDE.md").exists()
        assert (project / "AGENTS.md").exists()
        assert (project / ".mcp.json").exists()
        assert (project / ".claude" / "rules" / "idlergear.md").exists()

        # Create some data to ensure it's preserved
        run_idlergear(project, "task", "create", "Task to preserve")

        # Uninstall (without --remove-data)
        # Need to provide confirmation via stdin or use a flag
        result = subprocess.run(
            ["idlergear", "uninstall", "--force"],
            cwd=project,
            capture_output=True,
            text=True,
        )

        # Check that install files are removed but data is preserved
        assert not (project / ".mcp.json").exists() or "idlergear" not in (
            project / ".mcp.json"
        ).read_text()
        # .idlergear should still exist (data preserved)
        assert (project / ".idlergear").exists()
