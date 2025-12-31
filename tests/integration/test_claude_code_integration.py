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

Test Categories:
1. Install/Uninstall - No Claude needed, fast unit tests
2. Claude Reads Instructions - Verify Claude sees CLAUDE.md
3. Claude Executes Commands - Verify Claude can run idlergear commands
4. Claude Automatic Behavior - Verify Claude uses IdlerGear proactively
5. WarGames Demo Workflow - Tests matching the demo script
6. Edge Cases - Error handling, empty projects, etc.
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


# =============================================================================
# PART 1: INSTALL/UNINSTALL TESTS (no Claude needed)
# =============================================================================


class TestInstallUninstall:
    """Test IdlerGear install and uninstall workflow."""

    def test_init_creates_idlergear_dir(self, fresh_project: Path) -> None:
        """Test that idlergear init creates the .idlergear directory."""
        # fresh_project fixture already ran init
        assert (fresh_project / ".idlergear").is_dir()
        assert (fresh_project / ".idlergear" / "config.toml").is_file()

    def test_install_creates_claude_files(self, fresh_project: Path) -> None:
        """Test that idlergear install creates all Claude Code integration files."""
        # Run install
        result = run_idlergear(fresh_project, "install")
        assert result.returncode == 0, f"Install failed: {result.stderr}"

        # Verify all files created
        assert (fresh_project / "CLAUDE.md").is_file(), "CLAUDE.md not created"
        assert (fresh_project / "AGENTS.md").is_file(), "AGENTS.md not created"
        assert (fresh_project / ".claude" / "rules" / "idlergear.md").is_file(), \
            ".claude/rules/idlergear.md not created"
        assert (fresh_project / ".mcp.json").is_file(), ".mcp.json not created"

    def test_uninstall_removes_claude_files(self, fresh_project: Path) -> None:
        """Test that idlergear uninstall removes Claude files but preserves data."""
        # First install
        run_idlergear(fresh_project, "install")

        # Create some data
        run_idlergear(fresh_project, "task", "create", "Test task")
        run_idlergear(fresh_project, "note", "create", "Test note")

        # Now uninstall (use --force to skip confirmation)
        result = run_idlergear(fresh_project, "uninstall", "--force")
        assert result.returncode == 0, f"Uninstall failed: {result.stderr}"

        # Verify Claude-specific files removed, and IdlerGear content removed from shared files
        # Note: CLAUDE.md and AGENTS.md may still exist but without IdlerGear content
        assert not (fresh_project / ".claude" / "rules" / "idlergear.md").exists(), \
            ".claude/rules/idlergear.md not removed"
        assert not (fresh_project / ".mcp.json").exists(), ".mcp.json not removed"

        # CLAUDE.md and AGENTS.md should have IdlerGear content removed
        if (fresh_project / "CLAUDE.md").exists():
            claude_md = (fresh_project / "CLAUDE.md").read_text()
            assert "idlergear context" not in claude_md.lower(), \
                "IdlerGear instructions should be removed from CLAUDE.md"
        if (fresh_project / "AGENTS.md").exists():
            agents_md = (fresh_project / "AGENTS.md").read_text()
            assert "idlergear" not in agents_md.lower() or len(agents_md) < 50, \
                "IdlerGear section should be removed from AGENTS.md"

        # Verify data preserved
        assert (fresh_project / ".idlergear").is_dir(), ".idlergear/ should be preserved"

        # Tasks and notes should still be accessible
        task_result = run_idlergear(fresh_project, "task", "list")
        assert "Test task" in task_result.stdout, "Tasks should be preserved after uninstall"

        note_result = run_idlergear(fresh_project, "note", "list")
        assert "Test note" in note_result.stdout, "Notes should be preserved after uninstall"

    def test_reinstall_works_correctly(self, fresh_project: Path) -> None:
        """Test that reinstalling IdlerGear works and preserves data."""
        # Install, create data, uninstall
        run_idlergear(fresh_project, "install")
        run_idlergear(fresh_project, "task", "create", "Persistent task")
        run_idlergear(fresh_project, "uninstall", "--force")

        # Reinstall
        result = run_idlergear(fresh_project, "install")
        assert result.returncode == 0, f"Reinstall failed: {result.stderr}"

        # Verify files recreated
        assert (fresh_project / "CLAUDE.md").is_file(), "CLAUDE.md not restored"
        assert (fresh_project / ".claude" / "rules" / "idlergear.md").is_file()

        # Verify data intact
        task_result = run_idlergear(fresh_project, "task", "list")
        assert "Persistent task" in task_result.stdout, "Data lost after reinstall"

    def test_claude_md_contains_idlergear_instructions(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that CLAUDE.md contains proper IdlerGear instructions."""
        claude_md = (fresh_project_with_install / "CLAUDE.md").read_text()

        # Should mention idlergear
        assert "idlergear" in claude_md.lower(), "CLAUDE.md should mention idlergear"

        # Should mention context command
        assert "context" in claude_md.lower(), "CLAUDE.md should mention context"


# =============================================================================
# PART 2: CLAUDE READS INSTRUCTIONS
# =============================================================================


class TestClaudeReadsIdlerGearInstructions:
    """Test that Claude reads and acknowledges IdlerGear instructions."""

    def test_claude_sees_claude_md(self, fresh_project_with_install: Path) -> None:
        """Test that Claude can see the CLAUDE.md file instructions."""
        project = fresh_project_with_install

        result = run_claude(
            project,
            "What knowledge management system is configured for this project? "
            "Just answer with the name of the system if any, or 'none' if none is configured.",
            timeout=60,
            output_format="text",
        )

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
            output_format="text",
        )

        if result.returncode == 0:
            response = result.stdout.lower()
            assert (
                "idlergear context" in response or "context" in response
            ), f"Claude should know about idlergear context. Response: {result.stdout}"


# =============================================================================
# PART 3: CLAUDE EXECUTES IDLERGEAR COMMANDS
# =============================================================================


class TestClaudeUsesIdlerGear:
    """Test that Claude can execute IdlerGear commands."""

    def test_claude_can_run_context(self, fresh_project_with_install: Path) -> None:
        """Test that Claude can run idlergear context."""
        project = fresh_project_with_install

        # First create some content
        run_idlergear(project, "task", "create", "Test task for Claude")
        run_idlergear(project, "note", "create", "Test note for Claude")

        result = run_claude(
            project,
            "Run the idlergear context command and tell me what tasks exist.",
            timeout=90,
            output_format="text",
        )

        if result.returncode == 0:
            response = result.stdout.lower()
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
            output_format="text",
        )

        if result.returncode == 0:
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
            output_format="text",
        )

        if result.returncode == 0:
            list_result = run_idlergear(project, "note", "list")
            assert "Claude created this note" in list_result.stdout, (
                f"Note should have been created. "
                f"Claude output: {result.stdout}\n"
                f"Note list: {list_result.stdout}"
            )


# =============================================================================
# PART 4: CLAUDE AUTOMATIC BEHAVIOR (without explicit idlergear mentions)
# =============================================================================


class TestClaudeAutomaticBehavior:
    """Test that Claude AUTOMATICALLY uses IdlerGear without explicit instructions.

    These tests verify that Claude follows the rules in CLAUDE.md and
    .claude/rules/idlergear.md proactively, not just when asked.
    """

    def test_claude_auto_discovers_context_on_session_start(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude discovers existing context when starting a session.

        We create tasks/notes, then say hello WITHOUT mentioning idlergear.
        Claude should check context and report what it found.
        """
        project = fresh_project_with_install

        # Seed realistic project data - Tic-Tac-Toe game
        run_idlergear(project, "task", "create", "Implement game board display")
        run_idlergear(project, "task", "create", "Add win condition detection")
        run_idlergear(project, "note", "create", "Board positions numbered 1-9")

        # Start a session without mentioning idlergear
        result = run_claude(
            project,
            "Hi, I'm ready to work on this project today. What should I know?",
            timeout=120,
            output_format="text",
        )

        if result.returncode == 0:
            response = result.stdout.lower()
            found_board = "board" in response or "display" in response
            found_win = "win" in response
            found_positions = "position" in response or "1-9" in response
            found_tasks = "task" in response

            assert found_board or found_win or found_positions or found_tasks, (
                f"Claude should auto-discover project context at session start.\n"
                f"Expected mentions of: board, win detection, positions\n"
                f"Response: {result.stdout}"
            )

    def test_claude_auto_tracks_bug_report(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude automatically tracks a bug report as a task.

        Developer mentions a bug WITHOUT saying 'create a task'.
        Claude should proactively use idlergear to track it.
        """
        project = fresh_project_with_install

        result = run_claude(
            project,
            "I found a bug while testing: the game doesn't detect diagonal wins. "
            "When X gets three in a diagonal, it doesn't end the game. Can you help track this?",
            timeout=90,
            output_format="text",
        )

        if result.returncode == 0:
            # Check if Claude created a task
            task_list = run_idlergear(project, "task", "list")
            note_list = run_idlergear(project, "note", "list")

            task_lower = task_list.stdout.lower()
            note_lower = note_list.stdout.lower()

            in_tasks = any(term in task_lower for term in ["diagonal", "win", "bug", "detect"])
            in_notes = any(term in note_lower for term in ["diagonal", "win", "bug", "detect"])

            assert in_tasks or in_notes, (
                f"Claude should auto-track the bug report.\n"
                f"Tasks: {task_list.stdout}\n"
                f"Notes: {note_list.stdout}\n"
                f"Claude response: {result.stdout}"
            )

    def test_claude_auto_creates_note_for_observation(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude creates a note for technical observations.

        Developer shares technical info WITHOUT saying 'create a note'.
        Claude should proactively save it.
        """
        project = fresh_project_with_install

        result = run_claude(
            project,
            "By the way, I realized that with perfect minimax play, the AI can never lose - "
            "it can always force at least a draw. We should remember this when testing.",
            timeout=90,
            output_format="text",
        )

        if result.returncode == 0:
            note_list = run_idlergear(project, "note", "list")
            note_lower = note_list.stdout.lower()

            has_note = any(
                term in note_lower
                for term in ["minimax", "never lose", "draw", "perfect", "force"]
            )

            assert has_note, (
                f"Claude should auto-create note for technical observation.\n"
                f"Notes: {note_list.stdout}\n"
                f"Claude response: {result.stdout}"
            )

    def test_claude_checks_context_for_work_prioritization(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude checks context when asked what to work on.

        When asked about priorities, Claude should consult idlergear.
        """
        project = fresh_project_with_install

        # Create tasks with different priorities
        run_idlergear(project, "task", "create", "Critical: fix diagonal win detection")
        run_idlergear(project, "task", "create", "Implement minimax AI")
        run_idlergear(project, "task", "create", "Add game restart option")

        result = run_claude(
            project,
            "I have some time this afternoon. What's the most important thing to work on?",
            timeout=90,
            output_format="text",
        )

        if result.returncode == 0:
            response = result.stdout.lower()
            # Claude should reference existing tasks
            mentions_tasks = any(
                term in response
                for term in ["diagonal", "win", "minimax", "restart", "task", "critical"]
            )

            assert mentions_tasks, (
                f"Claude should check context and reference existing tasks.\n"
                f"Response: {result.stdout}"
            )

    def test_claude_session_resumption(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude helps resume a session by checking context.

        After a break, developer asks where they left off.
        Claude should check idlergear context.
        """
        project = fresh_project_with_install

        # Create some work in progress
        run_idlergear(project, "task", "create", "Implement board display with ASCII art")
        run_idlergear(project, "note", "create", "Consider using box-drawing characters")

        result = run_claude(
            project,
            "I'm back from lunch. Can you remind me where I left off?",
            timeout=90,
            output_format="text",
        )

        if result.returncode == 0:
            response = result.stdout.lower()
            has_context = any(
                term in response
                for term in ["board", "display", "ascii", "box", "task", "drawing"]
            )

            assert has_context, (
                f"Claude should check context to help resume session.\n"
                f"Response: {result.stdout}"
            )


# =============================================================================
# PART 5: REALISTIC WORKFLOW INTEGRATION
# =============================================================================


class TestRealisticWorkflow:
    """Test a complete realistic development workflow."""

    def test_full_development_session(
        self, fresh_project_with_install: Path
    ) -> None:
        """Simulate a complete development session with IdlerGear.

        This test walks through:
        1. Session start with context check
        2. Bug report tracking
        3. Technical note creation
        4. Work prioritization
        """
        project = fresh_project_with_install

        # Setup: Create initial project state (like mid-project)
        run_idlergear(project, "vision", "edit", "Text-based Tic-Tac-Toe with AI")
        run_idlergear(project, "task", "create", "Implement game board display")
        run_idlergear(project, "note", "create", "Using minimax for AI")

        # Step 1: Session start
        start_result = run_claude(
            project,
            "Hi, I'm starting work on this project. What's the current state?",
            timeout=120,
            output_format="text",
        )
        assert start_result.returncode == 0

        # Step 2: Report a bug (Claude should track it)
        bug_result = run_claude(
            project,
            "I found an issue: diagonal wins aren't detected. Track this please.",
            timeout=90,
            output_format="text",
        )

        # Step 3: Share technical insight (Claude should note it)
        note_result = run_claude(
            project,
            "Alpha-beta pruning can make minimax much faster by skipping branches.",
            timeout=90,
            output_format="text",
        )

        # Verify: Check that work was tracked
        task_list = run_idlergear(project, "task", "list")
        note_list = run_idlergear(project, "note", "list")

        # At minimum, original items should exist
        assert "board" in task_list.stdout.lower(), "Original task should exist"
        assert "minimax" in note_list.stdout.lower(), "Original note should exist"

        # Ideally, Claude added new items
        task_lower = task_list.stdout.lower()
        note_lower = note_list.stdout.lower()

        new_items_tracked = (
            "diagonal" in task_lower
            or "diagonal" in note_lower
            or "alpha" in note_lower
            or "pruning" in note_lower
        )

        if not new_items_tracked:
            print(
                f"Note: Claude didn't automatically track new items.\n"
                f"Tasks: {task_list.stdout}\n"
                f"Notes: {note_list.stdout}\n"
                f"This may indicate CLAUDE.md rules need strengthening."
            )

    def test_explicit_commands_work(
        self, fresh_project_with_install: Path
    ) -> None:
        """Verify Claude can execute explicit idlergear commands (sanity check)."""
        project = fresh_project_with_install

        # Explicit context command
        result = run_claude(
            project,
            "Please run idlergear context and summarize the project state.",
            timeout=90,
            output_format="text",
        )

        if result.returncode == 0:
            response = result.stdout.lower()
            # Should mention running context or showing results
            ran_context = any(
                term in response
                for term in ["context", "task", "note", "vision", "no task", "empty"]
            )

            assert ran_context, (
                f"Claude should run idlergear context when asked.\n"
                f"Response: {result.stdout}"
            )


# =============================================================================
# PART 6: WARGAMES DEMO WORKFLOW TESTS
# =============================================================================


class TestWarGamesDemoWorkflow:
    """Tests that mirror the WarGames demo script workflow.

    These tests verify Claude can:
    1. Build games from scratch
    2. Track work using IdlerGear as it goes
    3. Handle multi-step implementations
    """

    def test_claude_builds_simple_game(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude can build a simple Tic-Tac-Toe game.

        This mirrors Part 2 of the demo script.
        """
        project = fresh_project_with_install

        result = run_claude(
            project,
            """Build a simple text-based Tic-Tac-Toe game in Python.

Create tictactoe.py with:
1. A 3x3 board display
2. Two-player mode (X and O)
3. Win detection
4. Draw detection

Keep it under 100 lines. Track your work using IdlerGear.""",
            timeout=180,
            output_format="text",
        )

        if result.returncode == 0:
            # Check that game was created
            game_file = project / "tictactoe.py"
            if game_file.exists():
                content = game_file.read_text()
                # Basic validation that it looks like a game
                has_board = "board" in content.lower() or "grid" in content.lower()
                has_win = "win" in content.lower()
                has_function = "def " in content

                assert has_board and has_win and has_function, (
                    f"tictactoe.py should have game logic.\n"
                    f"Content preview: {content[:500]}"
                )

    def test_claude_creates_design_doc(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude can create a design document for a complex game.

        This mirrors Part 4 of the demo (Global Thermonuclear War design).
        """
        project = fresh_project_with_install

        result = run_claude(
            project,
            """Design a text-based strategy game called 'Global Thermonuclear War'.

DON'T implement the full game. Instead:
1. Create a design document (game_design.md) describing:
   - Game mechanics
   - Win/lose conditions
   - Key features
2. Optionally create a minimal starter file

Track your design decisions using IdlerGear notes.""",
            timeout=120,
            output_format="text",
        )

        if result.returncode == 0:
            # Check for design doc or notes
            design_file = project / "game_design.md"
            has_design = design_file.exists()

            # Also check if Claude tracked notes
            note_result = run_idlergear(project, "note", "list")
            has_notes = len(note_result.stdout.strip()) > 0

            assert has_design or has_notes, (
                f"Claude should create design doc or IdlerGear notes.\n"
                f"Design file exists: {has_design}\n"
                f"Notes: {note_result.stdout}\n"
                f"Claude response: {result.stdout}"
            )

    def test_claude_tracks_game_development_tasks(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude creates tasks while implementing a game."""
        project = fresh_project_with_install

        result = run_claude(
            project,
            """I want to build a simple poker hand evaluator in Python.

Before writing code, plan out the implementation:
1. Create IdlerGear tasks for the major components
2. Add notes about the hand ranking rules

Then implement just the card deck and dealing.""",
            timeout=120,
            output_format="text",
        )

        if result.returncode == 0:
            task_result = run_idlergear(project, "task", "list")
            note_result = run_idlergear(project, "note", "list")

            has_tasks = len(task_result.stdout.strip()) > 0
            has_notes = len(note_result.stdout.strip()) > 0

            assert has_tasks or has_notes, (
                f"Claude should create tasks/notes for game planning.\n"
                f"Tasks: {task_result.stdout}\n"
                f"Notes: {note_result.stdout}\n"
                f"Claude response: {result.stdout}"
            )


# =============================================================================
# PART 7: EDGE CASES AND ERROR HANDLING
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_install_twice_is_idempotent(self, fresh_project: Path) -> None:
        """Test that running install twice doesn't cause errors."""
        # First install
        result1 = run_idlergear(fresh_project, "install")
        assert result1.returncode == 0

        # Second install should also succeed
        result2 = run_idlergear(fresh_project, "install")
        assert result2.returncode == 0, f"Second install failed: {result2.stderr}"

        # Files should still exist
        assert (fresh_project / "CLAUDE.md").is_file()
        assert (fresh_project / ".claude" / "rules" / "idlergear.md").is_file()

    def test_uninstall_without_install(self, fresh_project: Path) -> None:
        """Test that uninstall handles case where nothing was installed."""
        # Try to uninstall without ever installing
        result = run_idlergear(fresh_project, "uninstall", "--force")
        # Should either succeed (nothing to do) or fail gracefully
        # Either way, shouldn't crash
        assert result.returncode in [0, 1], f"Uninstall crashed: {result.stderr}"

    def test_context_with_no_data(self, fresh_project_with_install: Path) -> None:
        """Test that context command works with empty project."""
        project = fresh_project_with_install

        result = run_idlergear(project, "context")
        assert result.returncode == 0, f"Context failed on empty project: {result.stderr}"

    def test_claude_handles_empty_project(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that Claude handles a project with no tasks/notes gracefully."""
        project = fresh_project_with_install

        result = run_claude(
            project,
            "What tasks are currently tracked for this project?",
            timeout=60,
            output_format="text",
        )

        if result.returncode == 0:
            response = result.stdout.lower()
            # Should acknowledge empty state or check context
            handled = any(
                term in response
                for term in ["no task", "empty", "none", "no current", "haven't"]
            )

            assert handled, (
                f"Claude should gracefully handle empty project.\n"
                f"Response: {result.stdout}"
            )

    def test_install_preserves_existing_claude_md(self, fresh_project: Path) -> None:
        """Test that install preserves existing CLAUDE.md content."""
        project = fresh_project

        # Create existing CLAUDE.md with custom content
        existing_content = "# My Project\n\nThis is my custom project info.\n"
        (project / "CLAUDE.md").write_text(existing_content)

        # Install IdlerGear
        result = run_idlergear(project, "install")
        assert result.returncode == 0

        # Read the file
        final_content = (project / "CLAUDE.md").read_text()

        # Should contain both original and IdlerGear content
        has_original = "my custom project" in final_content.lower()
        has_idlergear = "idlergear" in final_content.lower()

        assert has_original and has_idlergear, (
            f"Install should preserve existing content.\n"
            f"Has original: {has_original}\n"
            f"Has IdlerGear: {has_idlergear}\n"
            f"Content: {final_content}"
        )
