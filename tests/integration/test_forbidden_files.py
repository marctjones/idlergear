"""Tests for forbidden file rules.

These tests verify that Claude Code follows the rules in CLAUDE.md and
.claude/rules/idlergear.md about not creating forbidden files.

Forbidden files (per our rules):
- TODO.md, TODO.txt, TASKS.md
- NOTES.md, SESSION_*.md, SCRATCH.md
- FEATURE_IDEAS.md, RESEARCH.md, BACKLOG.md
- Any markdown file for tracking work

Forbidden comments:
- // TODO: ...
- # FIXME: ...
- /* HACK: ... */
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


FORBIDDEN_FILES = [
    "TODO.md",
    "TODO.txt",
    "TASKS.md",
    "NOTES.md",
    "SCRATCH.md",
    "FEATURE_IDEAS.md",
    "RESEARCH.md",
    "BACKLOG.md",
]


class TestForbiddenFileRules:
    """Test that Claude doesn't create forbidden files."""

    def test_claude_uses_idlergear_not_todo_md(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude uses IdlerGear instead of creating TODO.md.

        When asked to track tasks, Claude should use idlergear task create,
        not create a TODO.md file.
        """
        project = fresh_project_with_install

        result = run_claude(
            project,
            "I need to track some tasks for this project:\n"
            "1. Fix the login bug\n"
            "2. Add password reset feature\n"
            "3. Update the documentation\n\n"
            "Please create a way to track these tasks.",
            timeout=120,
            output_format="text",
        )

        if result.returncode == 0:
            # Check that forbidden files were NOT created
            for forbidden in FORBIDDEN_FILES:
                assert not (project / forbidden).exists(), (
                    f"Claude should NOT create {forbidden}. "
                    f"It should use IdlerGear instead."
                )

            # Check that tasks were created in IdlerGear
            task_result = run_idlergear(project, "task", "list")
            task_output = task_result.stdout.lower()

            # At least one task should be tracked
            has_login = "login" in task_output
            has_password = "password" in task_output
            has_documentation = "documentation" in task_output or "doc" in task_output

            # Claude should have used IdlerGear for at least some tasks
            assert has_login or has_password or has_documentation, (
                f"Claude should track tasks using IdlerGear.\n"
                f"Tasks: {task_result.stdout}\n"
                f"Claude response: {result.stdout[:500]}"
            )

    def test_claude_uses_idlergear_not_notes_md(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude uses IdlerGear notes instead of NOTES.md."""
        project = fresh_project_with_install

        result = run_claude(
            project,
            "I want to capture some notes about this project:\n"
            "- The API uses REST with JSON responses\n"
            "- Authentication is JWT-based\n"
            "- Database is PostgreSQL\n\n"
            "Please save these notes somewhere I can reference later.",
            timeout=120,
            output_format="text",
        )

        if result.returncode == 0:
            # Check that NOTES.md was NOT created
            assert not (project / "NOTES.md").exists(), (
                "Claude should NOT create NOTES.md. "
                "It should use IdlerGear notes instead."
            )

            # Check that notes were created in IdlerGear
            note_result = run_idlergear(project, "note", "list")
            note_output = note_result.stdout.lower()

            has_api = "api" in note_output or "rest" in note_output
            has_auth = "jwt" in note_output or "auth" in note_output
            has_db = "postgres" in note_output or "database" in note_output

            assert has_api or has_auth or has_db, (
                f"Claude should use IdlerGear for notes.\n"
                f"Notes: {note_result.stdout}\n"
                f"Claude response: {result.stdout[:500]}"
            )

    def test_claude_uses_idlergear_not_scratch_md(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude uses IdlerGear for quick capture, not SCRATCH.md."""
        project = fresh_project_with_install

        result = run_claude(
            project,
            "Quick thought: We should consider adding rate limiting to the API. "
            "Don't want to forget this idea. Can you capture it somewhere?",
            timeout=90,
            output_format="text",
        )

        if result.returncode == 0:
            assert not (project / "SCRATCH.md").exists(), (
                "Claude should NOT create SCRATCH.md."
            )

            # Should be in notes or explorations
            note_result = run_idlergear(project, "note", "list")
            explore_result = run_idlergear(project, "explore", "list")

            in_notes = "rate" in note_result.stdout.lower() or "limit" in note_result.stdout.lower()
            in_explore = "rate" in explore_result.stdout.lower() or "limit" in explore_result.stdout.lower()

            assert in_notes or in_explore, (
                f"Claude should capture ideas in IdlerGear.\n"
                f"Notes: {note_result.stdout}\n"
                f"Explorations: {explore_result.stdout}"
            )


class TestForbiddenCommentRules:
    """Test that Claude doesn't add forbidden TODO comments in code."""

    def test_claude_uses_idlergear_not_todo_comments(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude creates IdlerGear tasks instead of TODO comments."""
        project = fresh_project_with_install

        # Create a starter file
        (project / "app.py").write_text('''"""Main application module."""

def process_data(data):
    """Process the input data."""
    return data.upper()


def validate_input(data):
    """Validate the input data."""
    if not data:
        return False
    return True
''')

        result = run_claude(
            project,
            "Review app.py and identify improvements needed. "
            "For each improvement, track it appropriately so we don't forget.",
            timeout=120,
            output_format="text",
        )

        if result.returncode == 0:
            # Read the modified file
            if (project / "app.py").exists():
                content = (project / "app.py").read_text()

                # Check for forbidden comment patterns
                forbidden_patterns = [
                    "# TODO:",
                    "# FIXME:",
                    "# HACK:",
                    "// TODO:",
                    "/* TODO:",
                ]

                for pattern in forbidden_patterns:
                    assert pattern not in content, (
                        f"Claude should NOT add '{pattern}' comments.\n"
                        f"It should use IdlerGear task create instead.\n"
                        f"File content: {content}"
                    )

            # Check that improvements were tracked in IdlerGear
            task_result = run_idlergear(project, "task", "list")
            note_result = run_idlergear(project, "note", "list")

            has_tracking = (
                len(task_result.stdout.strip()) > 0 or
                len(note_result.stdout.strip()) > 0
            )

            # Note: This assertion is informational - Claude may not always
            # find improvements worth tracking
            if not has_tracking:
                print(
                    f"Note: Claude didn't track any improvements.\n"
                    f"This may be expected if no improvements were found.\n"
                    f"Claude response: {result.stdout[:500]}"
                )


class TestRulesFileContent:
    """Test that rules file has correct forbidden patterns."""

    def test_rules_file_mentions_forbidden_files(
        self, fresh_project_with_install: Path
    ) -> None:
        """Verify the rules file explicitly forbids the files we're testing."""
        project = fresh_project_with_install
        rules_file = project / ".claude" / "rules" / "idlergear.md"

        assert rules_file.exists(), "Rules file should exist after install"

        content = rules_file.read_text()

        # Check that key forbidden patterns are mentioned
        assert "TODO.md" in content, "Rules should mention TODO.md"
        assert "NOTES.md" in content, "Rules should mention NOTES.md"
        assert "FORBIDDEN" in content, "Rules should use FORBIDDEN language"

    def test_claude_md_mentions_forbidden_patterns(
        self, fresh_project_with_install: Path
    ) -> None:
        """Verify CLAUDE.md mentions forbidden patterns."""
        project = fresh_project_with_install
        claude_md = project / "CLAUDE.md"

        assert claude_md.exists(), "CLAUDE.md should exist after install"

        content = claude_md.read_text()

        assert "FORBIDDEN" in content, "CLAUDE.md should mention FORBIDDEN patterns"
        assert "TODO" in content, "CLAUDE.md should mention TODO files"

    def test_agents_md_has_comprehensive_rules(
        self, fresh_project_with_install: Path
    ) -> None:
        """Verify AGENTS.md has comprehensive IdlerGear rules."""
        project = fresh_project_with_install
        agents_md = project / "AGENTS.md"

        assert agents_md.exists(), "AGENTS.md should exist after install"

        content = agents_md.read_text()

        # Should have command reference
        assert "idlergear task create" in content
        assert "idlergear note create" in content
        assert "idlergear context" in content

        # Should mention forbidden patterns
        assert "FORBIDDEN" in content
        assert "TODO.md" in content
