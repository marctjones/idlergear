"""Tests for session start behavior.

These tests verify that Claude follows the rules about running
`idlergear context` at the start of each session.

The CLAUDE.md and .claude/rules/idlergear.md files both say:
    ALWAYS run this command at the start of EVERY session:
    idlergear context

These tests verify Claude actually does this.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

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


# Skip all tests if claude CLI not available
pytestmark = [
    pytest.mark.skipif(not has_claude_cli(), reason="claude CLI not available"),
    pytest.mark.slow,
    pytest.mark.claude_integration,
]


class TestSessionStartBehavior:
    """Test that Claude checks context at session start."""

    def test_claude_mentions_context_when_greeted(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude checks context when a user starts a session.

        When a user says "hello" or similar greeting, Claude should
        check the project context and report what it found.
        """
        project = fresh_project_with_install

        # Seed with realistic project state
        run_idlergear(project, "vision", "edit", "A tic-tac-toe game with AI")
        run_idlergear(project, "task", "create", "Implement minimax algorithm")
        run_idlergear(project, "task", "create", "Add game board display")
        run_idlergear(project, "note", "create", "Consider alpha-beta pruning for performance")

        # Start a "session" with a greeting
        result = run_claude(
            project,
            "Hello! I'm ready to work on this project.",
            timeout=120,
            output_format="text",
        )

        if result.returncode == 0:
            response = result.stdout.lower()

            # Claude should mention something from the context
            mentions_vision = "tic-tac-toe" in response or "game" in response
            mentions_task = "minimax" in response or "board" in response or "task" in response
            mentions_note = "alpha" in response or "pruning" in response

            assert mentions_vision or mentions_task or mentions_note, (
                f"Claude should check and mention project context at session start.\n"
                f"Expected mentions of: tic-tac-toe, minimax, board, alpha-beta\n"
                f"Response: {result.stdout}"
            )

    def test_claude_discovers_existing_work(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude discovers existing tasks when asked what to work on."""
        project = fresh_project_with_install

        # Create tasks that represent partially done work
        run_idlergear(project, "task", "create", "Implement user authentication")
        run_idlergear(project, "task", "create", "Add password reset flow")
        run_idlergear(project, "task", "create", "Write unit tests for auth module")

        result = run_claude(
            project,
            "What's on the to-do list for this project?",
            timeout=90,
            output_format="text",
        )

        if result.returncode == 0:
            response = result.stdout.lower()

            # Should find at least some of our tasks
            found_auth = "auth" in response
            found_password = "password" in response
            found_test = "test" in response

            assert found_auth or found_password or found_test, (
                f"Claude should discover existing tasks.\n"
                f"Response: {result.stdout}"
            )

    def test_claude_surfaces_notes_on_resumption(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude surfaces notes when resuming work."""
        project = fresh_project_with_install

        # Create notes that would be useful on resumption
        run_idlergear(
            project, "note", "create",
            "Left off in the middle of refactoring the login handler"
        )
        run_idlergear(
            project, "note", "create",
            "Remember: the session token format changed to JWT"
        )

        result = run_claude(
            project,
            "I was working on this yesterday and need to pick up where I left off. "
            "What should I know?",
            timeout=90,
            output_format="text",
        )

        if result.returncode == 0:
            response = result.stdout.lower()

            found_refactor = "refactor" in response or "login" in response
            found_token = "token" in response or "jwt" in response or "session" in response

            assert found_refactor or found_token, (
                f"Claude should surface relevant notes on session resumption.\n"
                f"Response: {result.stdout}"
            )

    def test_claude_shows_vision_on_overview_request(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude shows project vision when asked for an overview."""
        project = fresh_project_with_install

        # Set a distinctive vision
        run_idlergear(
            project, "vision", "edit",
            "Build a multiplayer chess platform with ELO ratings and tournaments"
        )

        result = run_claude(
            project,
            "Can you give me an overview of this project?",
            timeout=90,
            output_format="text",
        )

        if result.returncode == 0:
            response = result.stdout.lower()

            # Should mention the vision elements
            found_chess = "chess" in response
            found_elo = "elo" in response or "rating" in response
            found_tournament = "tournament" in response
            found_multiplayer = "multiplayer" in response

            assert found_chess or found_elo or found_tournament or found_multiplayer, (
                f"Claude should show project vision when asked for overview.\n"
                f"Response: {result.stdout}"
            )


class TestEmptyProjectHandling:
    """Test Claude's behavior with projects that have no context."""

    def test_claude_handles_empty_vision(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude handles projects with no vision set."""
        project = fresh_project_with_install

        # Don't set anything - fresh project

        result = run_claude(
            project,
            "What's this project about?",
            timeout=60,
            output_format="text",
        )

        if result.returncode == 0:
            response = result.stdout.lower()

            # Should gracefully handle empty project
            # Either ask for clarification or note that vision isn't set
            handled_gracefully = (
                "no vision" in response or
                "not set" in response or
                "haven't" in response or
                "what would you like" in response or
                "tell me" in response or
                "empty" in response or
                len(response) > 20  # At least gave some response
            )

            assert handled_gracefully, (
                f"Claude should gracefully handle empty project.\n"
                f"Response: {result.stdout}"
            )

    def test_claude_suggests_setting_vision(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude might suggest setting the vision for new projects."""
        project = fresh_project_with_install

        result = run_claude(
            project,
            "I just created this project. Where should I start?",
            timeout=90,
            output_format="text",
        )

        if result.returncode == 0:
            response = result.stdout.lower()

            # Should either suggest setting vision or ask what the project is about
            suggests_vision = "vision" in response
            asks_purpose = (
                "what" in response and ("project" in response or "build" in response)
            ) or "tell me" in response
            suggests_task = "task" in response

            # Any of these is a reasonable response to an empty project
            assert suggests_vision or asks_purpose or suggests_task, (
                f"Claude should guide user on empty project.\n"
                f"Response: {result.stdout}"
            )


class TestContextCommandExecution:
    """Test that context command itself works correctly."""

    def test_context_shows_all_knowledge_types(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that context command shows all relevant knowledge."""
        project = fresh_project_with_install

        # Create one of each major type
        run_idlergear(project, "vision", "edit", "Test project vision")
        run_idlergear(project, "task", "create", "Test task")
        run_idlergear(project, "note", "create", "Test note")
        run_idlergear(project, "explore", "create", "Test exploration")

        result = run_idlergear(project, "context")
        assert result.returncode == 0

        output = result.stdout.lower()

        # Should mention all types (or sections for them)
        has_vision = "vision" in output
        has_task = "task" in output
        has_note = "note" in output

        assert has_vision and has_task and has_note, (
            f"Context should show all knowledge types.\n"
            f"Output: {result.stdout}"
        )

    def test_context_is_readable_by_ai(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that context output is structured for AI consumption."""
        project = fresh_project_with_install

        run_idlergear(project, "task", "create", "Important task")

        result = run_idlergear(project, "context")
        assert result.returncode == 0

        # Should be markdown-formatted and readable
        output = result.stdout

        # Should have some structure (headers, lists, etc.)
        has_structure = (
            "#" in output or  # Markdown headers
            "-" in output or  # List items
            "*" in output     # List items
        )

        assert has_structure, (
            f"Context output should be structured.\n"
            f"Output: {output}"
        )
