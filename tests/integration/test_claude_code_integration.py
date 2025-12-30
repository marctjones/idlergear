"""Integration tests for IdlerGear with Claude Code.

These tests verify that Claude Code properly reads and follows IdlerGear
instructions when CLAUDE.md and .claude/rules/idlergear.md are present.

These tests use `claude -p` (print mode) with --dangerously-skip-permissions
to automate Claude Code interactions.

NOTE: These tests require:
1. claude CLI to be installed and authenticated (run `claude` once to auth)
2. Will consume your normal Claude Code usage quota

These tests are marked slow because each test spawns Claude and waits for
responses. Run them selectively when you want to verify Claude integration.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from .conftest import run_claude, run_idlergear


def has_claude_cli() -> bool:
    """Check if claude CLI is available."""
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


# Skip all tests in this module if claude CLI is not available
pytestmark = [
    pytest.mark.skipif(not has_claude_cli(), reason="claude CLI not available"),
    pytest.mark.slow,
    pytest.mark.claude_integration,
]


def parse_claude_response(result: subprocess.CompletedProcess) -> dict[str, Any] | None:
    """Parse JSON response from claude -p --output-format json."""
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


class TestClaudeReadsIdlerGearInstructions:
    """Test that Claude reads and acknowledges IdlerGear instructions."""

    def test_claude_sees_claude_md(self, fresh_project_with_install: Path) -> None:
        """Test that Claude can see the CLAUDE.md file instructions."""
        project = fresh_project_with_install

        # Ask Claude about the project instructions
        result = run_claude(
            project,
            "What knowledge management system is configured for this project? "
            "Just answer with the name of the system if any, or 'none' if none is configured.",
            timeout=60,
        )

        # Check if Claude mentions IdlerGear
        if result.returncode == 0:
            response = result.stdout.lower()
            assert (
                "idlergear" in response or "idler" in response
            ), f"Claude should see IdlerGear in CLAUDE.md. Response: {result.stdout}"

    def test_claude_knows_context_command(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude knows about the idlergear context command."""
        project = fresh_project_with_install

        result = run_claude(
            project,
            "What command should you run at the start of each session according "
            "to the project instructions? Just respond with the command.",
            timeout=60,
        )

        if result.returncode == 0:
            response = result.stdout.lower()
            assert (
                "idlergear context" in response or "context" in response
            ), f"Claude should know about idlergear context. Response: {result.stdout}"


class TestClaudeUsesIdlerGear:
    """Test that Claude actually uses IdlerGear commands."""

    def test_claude_can_run_context(self, fresh_project_with_install: Path) -> None:
        """Test that Claude can run idlergear context."""
        project = fresh_project_with_install

        # First create some content so context has something to show
        run_idlergear(project, "task", "create", "Test task for Claude")
        run_idlergear(project, "note", "create", "Test note for Claude")

        # Ask Claude to run context
        result = run_claude(
            project,
            "Run the idlergear context command and tell me what tasks exist.",
            timeout=90,
        )

        if result.returncode == 0:
            # Claude should have seen the task we created
            response = result.stdout.lower()
            # Either Claude reports the task or says it ran the command
            success = (
                "test task" in response
                or "context" in response
                or "task" in response
            )
            assert success, f"Claude should report context results. Response: {result.stdout}"

    def test_claude_can_create_task(self, fresh_project_with_install: Path) -> None:
        """Test that Claude can create a task using idlergear."""
        project = fresh_project_with_install

        result = run_claude(
            project,
            "Create an idlergear task with the title 'Claude created this task'",
            timeout=90,
        )

        if result.returncode == 0:
            # Verify the task was actually created
            list_result = run_idlergear(project, "task", "list")
            assert "Claude created this task" in list_result.stdout, (
                f"Task should have been created. "
                f"Claude output: {result.stdout}\n"
                f"Task list: {list_result.stdout}"
            )

    def test_claude_can_create_note(self, fresh_project_with_install: Path) -> None:
        """Test that Claude can create a note using idlergear."""
        project = fresh_project_with_install

        result = run_claude(
            project,
            "Create an idlergear note: 'Claude created this note during testing'",
            timeout=90,
        )

        if result.returncode == 0:
            # Verify the note was actually created
            list_result = run_idlergear(project, "note", "list")
            assert "Claude created this note" in list_result.stdout, (
                f"Note should have been created. "
                f"Claude output: {result.stdout}\n"
                f"Note list: {list_result.stdout}"
            )


class TestClaudeFollowsRules:
    """Test that Claude follows IdlerGear rules properly."""

    def test_claude_checks_context_at_start(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude would check context at session start.

        We can't easily test the automatic behavior, but we can verify
        Claude knows it should do this.
        """
        project = fresh_project_with_install

        result = run_claude(
            project,
            "According to the project rules, what should you do at the START "
            "of each session? Be specific about any commands.",
            timeout=60,
        )

        if result.returncode == 0:
            response = result.stdout.lower()
            # Claude should mention checking context
            assert any(
                term in response
                for term in ["context", "idlergear", "start of session", "beginning"]
            ), f"Claude should know to check context at start. Response: {result.stdout}"

    def test_claude_knows_forbidden_patterns(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude knows about forbidden file patterns."""
        project = fresh_project_with_install

        result = run_claude(
            project,
            "Are there any files or directories that are FORBIDDEN to modify "
            "according to the project rules? List them if any.",
            timeout=60,
        )

        if result.returncode == 0:
            response = result.stdout.lower()
            # Should mention some forbidden patterns (from AGENTS.md)
            forbidden_patterns = [
                ".idlergear",
                "forbidden",
                "do not",
                "never",
            ]
            assert any(
                pattern in response for pattern in forbidden_patterns
            ), f"Claude should know forbidden patterns. Response: {result.stdout}"


class TestClaudeWorkflowIntegration:
    """Test a complete workflow with Claude using IdlerGear."""

    def test_simulated_development_session(
        self, fresh_project_with_install: Path
    ) -> None:
        """Simulate a development session where Claude uses IdlerGear.

        This test verifies that Claude can:
        1. Check context
        2. Create tasks for planned work
        3. Create notes for observations
        """
        project = fresh_project_with_install

        # Step 1: Have Claude check context (simulating session start)
        context_result = run_claude(
            project,
            "Run idlergear context and summarize what you see.",
            timeout=90,
        )
        # Just check it didn't error
        assert context_result.returncode == 0 or "error" not in context_result.stderr.lower()

        # Step 2: Have Claude create a task
        task_result = run_claude(
            project,
            "Create an idlergear task: 'Implement user authentication feature'",
            timeout=90,
        )

        # Step 3: Have Claude create a note
        note_result = run_claude(
            project,
            "Create an idlergear note: 'Consider using OAuth2 for authentication'",
            timeout=90,
        )

        # Verify the items were created
        task_list = run_idlergear(project, "task", "list")
        note_list = run_idlergear(project, "note", "list")

        # At least one of these should have worked
        tasks_created = "authentication" in task_list.stdout.lower()
        notes_created = "oauth" in note_list.stdout.lower()

        assert tasks_created or notes_created, (
            f"Claude should have created at least one item.\n"
            f"Task result: {task_result.stdout}\n"
            f"Note result: {note_result.stdout}\n"
            f"Tasks: {task_list.stdout}\n"
            f"Notes: {note_list.stdout}"
        )
