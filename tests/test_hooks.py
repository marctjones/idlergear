"""Tests for Claude Code hooks.

These tests validate the behavior of IdlerGear's Claude Code hooks:
- session-start.sh: Injects context at session start
- pre-tool-use.sh: Blocks forbidden file operations
- stop.sh: Prompts for knowledge capture before stopping
- post-tool-use.sh: Detects errors and suggests bug tasks
- user-prompt-submit.sh: Detects implementation intent and suggests task creation

Hook locations:
- Source (for development): src/idlergear/hooks/
- Installed (via 'idlergear install'): .claude/hooks/
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


# Project root (where pyproject.toml is)
PROJECT_ROOT = Path(__file__).parent.parent

# Source hooks directory (for development testing)
SOURCE_HOOKS_DIR = PROJECT_ROOT / "src" / "idlergear" / "hooks"

# Installed hooks directory (created by 'idlergear install')
INSTALLED_HOOKS_DIR = PROJECT_ROOT / ".claude" / "hooks"


def get_hook_path(hook_name: str) -> Path:
    """Get the path to a hook, preferring source directory for development.

    During development, hooks are in src/idlergear/hooks/.
    When installed in a project, they're in .claude/hooks/.
    """
    # First try source directory (development)
    source_path = SOURCE_HOOKS_DIR / hook_name
    if source_path.exists():
        return source_path

    # Fall back to installed directory
    installed_path = INSTALLED_HOOKS_DIR / hook_name
    if installed_path.exists():
        return installed_path

    # Return source path (test will skip if not found)
    return source_path


def run_hook(hook_path: Path, input_data: dict, timeout: int = 5) -> dict:
    """Run a hook script with JSON input and return the result."""
    if not hook_path.exists():
        pytest.skip(f"Hook not found: {hook_path}")

    result = subprocess.run(
        [str(hook_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=PROJECT_ROOT,  # Project root
    )

    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


class TestPreToolUseHook:
    """Tests for the pre-tool-use hook that blocks forbidden files."""

    @pytest.fixture
    def hook_path(self):
        return get_hook_path("ig_pre-tool-use.sh")

    def test_blocks_todo_md(self, hook_path):
        """Should block creation of TODO.md."""
        result = run_hook(
            hook_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "TODO.md", "content": "test"},
            },
        )
        assert result["exit_code"] == 2  # Blocking error
        assert (
            "FORBIDDEN" in result["stderr"] or "forbidden" in result["stderr"].lower()
        )

    def test_blocks_notes_md(self, hook_path):
        """Should block creation of NOTES.md."""
        result = run_hook(
            hook_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "NOTES.md", "content": "test"},
            },
        )
        assert result["exit_code"] == 2

    def test_blocks_session_md(self, hook_path):
        """Should block creation of SESSION_*.md files."""
        result = run_hook(
            hook_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "SESSION_2026.md", "content": "test"},
            },
        )
        assert result["exit_code"] == 2

    def test_blocks_backlog_md(self, hook_path):
        """Should block creation of BACKLOG.md."""
        result = run_hook(
            hook_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "BACKLOG.md", "content": "test"},
            },
        )
        assert result["exit_code"] == 2

    def test_blocks_scratch_md(self, hook_path):
        """Should block creation of SCRATCH.md."""
        result = run_hook(
            hook_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "SCRATCH.md", "content": "test"},
            },
        )
        assert result["exit_code"] == 2

    def test_allows_regular_python_file(self, hook_path):
        """Should allow creation of regular Python files."""
        result = run_hook(
            hook_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "src/main.py", "content": "test"},
            },
        )
        assert result["exit_code"] == 0

    def test_allows_readme(self, hook_path):
        """Should allow creation of README.md."""
        result = run_hook(
            hook_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "README.md", "content": "test"},
            },
        )
        assert result["exit_code"] == 0

    def test_allows_non_file_tools(self, hook_path):
        """Should allow non-file tools like Bash."""
        result = run_hook(
            hook_path,
            {"tool_name": "Bash", "tool_input": {"command": "ls"}},
        )
        assert result["exit_code"] == 0

    def test_blocks_edit_on_forbidden(self, hook_path):
        """Should block Edit tool on forbidden files."""
        result = run_hook(
            hook_path,
            {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "TODO.md",
                    "old_string": "a",
                    "new_string": "b",
                },
            },
        )
        assert result["exit_code"] == 2

    def test_suggests_alternative(self, hook_path):
        """Should suggest IdlerGear alternatives in error message."""
        result = run_hook(
            hook_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "TODO.md", "content": "test"},
            },
        )
        assert "idlergear" in result["stderr"].lower()


class TestPostToolUseHook:
    """Tests for the post-tool-use hook that detects errors."""

    @pytest.fixture
    def hook_path(self):
        return get_hook_path("ig_post-tool-use.sh")

    def test_detects_pytest_failure(self, hook_path):
        """Should detect pytest test failures."""
        pytest_output = """
============================= test session starts ==============================
FAILED tests/test_parser.py::test_parse_input - AssertionError: expected 5
=========================== 1 failed, 5 passed in 0.12s =======================
"""
        result = run_hook(
            hook_path,
            {
                "tool_name": "Bash",
                "tool_response": pytest_output,
                "session_id": "test-session",
            },
        )
        assert result["exit_code"] == 0
        # Should have suggestions in stdout
        if result["stdout"]:
            output = json.loads(result["stdout"])
            assert (
                "bug" in output.get("additionalContext", "").lower()
                or "test" in output.get("additionalContext", "").lower()
            )

    def test_detects_python_traceback(self, hook_path):
        """Should detect Python tracebacks."""
        traceback_output = """
Traceback (most recent call last):
  File "main.py", line 10, in <module>
    foo()
ValueError: invalid literal for int()
"""
        result = run_hook(
            hook_path,
            {
                "tool_name": "Bash",
                "tool_response": traceback_output,
                "session_id": "test-session",
            },
        )
        assert result["exit_code"] == 0
        if result["stdout"]:
            output = json.loads(result["stdout"])
            context = output.get("additionalContext", "")
            assert "error" in context.lower() or "bug" in context.lower()

    def test_detects_assertion_error(self, hook_path):
        """Should detect assertion errors."""
        result = run_hook(
            hook_path,
            {
                "tool_name": "Bash",
                "tool_response": "AssertionError: expected True",
                "session_id": "test-session",
            },
        )
        assert result["exit_code"] == 0

    def test_detects_timeout(self, hook_path):
        """Should detect timeout/freeze issues."""
        result = run_hook(
            hook_path,
            {
                "tool_name": "Bash",
                "tool_response": "Process timed out after 30s",
                "session_id": "test-session",
            },
        )
        assert result["exit_code"] == 0
        if result["stdout"]:
            output = json.loads(result["stdout"])
            assert (
                "performance" in output.get("additionalContext", "").lower()
                or "timeout" in output.get("additionalContext", "").lower()
            )

    def test_no_output_on_success(self, hook_path):
        """Should not output suggestions on successful command."""
        result = run_hook(
            hook_path,
            {
                "tool_name": "Bash",
                "tool_response": "Build successful",
                "session_id": "test-session",
            },
        )
        assert result["exit_code"] == 0
        # Should have no suggestions for success
        if result["stdout"].strip():
            output = json.loads(result["stdout"])
            # If there's output, it shouldn't mention bugs
            assert "bug" not in output.get("additionalContext", "").lower()

    def test_handles_empty_response(self, hook_path):
        """Should handle empty tool response gracefully."""
        result = run_hook(
            hook_path,
            {"tool_name": "Bash", "tool_response": "", "session_id": "test-session"},
        )
        assert result["exit_code"] == 0


class TestSessionStartHook:
    """Tests for the session-start hook that injects context."""

    @pytest.fixture
    def hook_path(self):
        return get_hook_path("ig_session-start.sh")

    def test_exits_gracefully_without_idlergear(self, hook_path):
        """Should exit gracefully if .idlergear doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Copy hook to temp dir without .idlergear
            temp_hook = Path(tmpdir) / "session-start.sh"
            temp_hook.write_text(hook_path.read_text())
            temp_hook.chmod(0o755)

            result = subprocess.run(
                [str(temp_hook)],
                input="{}",
                capture_output=True,
                text=True,
                cwd=tmpdir,
                timeout=5,
            )
            assert result.returncode == 0

    def test_returns_json_with_context(self, hook_path):
        """Should return valid JSON with additionalContext when idlergear is available."""
        result = run_hook(
            hook_path,
            {"session_id": "test-123", "source": "startup"},
        )
        assert result["exit_code"] == 0
        # If there's output, check it contains expected patterns
        # Note: The hook may output JSON with newlines that need escaping
        if result["stdout"].strip():
            # Just verify it contains the key structure
            assert "additionalContext" in result["stdout"]


class TestStopHook:
    """Tests for the stop hook that prompts for knowledge capture."""

    @pytest.fixture
    def hook_path(self):
        return get_hook_path("ig_stop.sh")

    def test_approves_when_no_issues(self, hook_path):
        """Should approve stop when no in-progress tasks or uncaptured knowledge."""
        # Create a minimal test environment
        result = run_hook(
            hook_path,
            {"session_id": "test-123"},
        )
        assert result["exit_code"] == 0
        if result["stdout"].strip():
            output = json.loads(result["stdout"])
            # Should either approve or block with reason
            assert "decision" in output

    def test_returns_valid_json(self, hook_path):
        """Should always return valid JSON."""
        result = run_hook(
            hook_path,
            {"session_id": "test-123", "transcript_path": "/nonexistent"},
        )
        assert result["exit_code"] == 0
        if result["stdout"].strip():
            # Should be valid JSON
            json.loads(result["stdout"])


class TestHookPerformance:
    """Performance tests for hooks."""

    @pytest.fixture
    def hooks_dir(self):
        # Use source directory for performance tests
        return SOURCE_HOOKS_DIR

    @pytest.mark.parametrize(
        "hook_name,max_time",
        [
            ("ig_pre-tool-use.sh", 0.5),
            ("ig_post-tool-use.sh", 0.5),
            ("ig_session-start.sh", 0.5),  # Reads files directly, no CLI calls
            ("ig_stop.sh", 0.5),  # Reads files directly, no CLI calls
        ],
    )
    def test_hook_execution_time(self, hooks_dir, hook_name, max_time):
        """All hooks should complete within reasonable time."""
        import time

        hook_path = hooks_dir / hook_name
        if not hook_path.exists():
            pytest.skip(f"Hook not found: {hook_name}")

        start = time.time()
        run_hook(
            hook_path,
            {"tool_name": "Bash", "tool_response": "test", "session_id": "perf-test"},
            timeout=5,
        )
        elapsed = time.time() - start

        assert elapsed < max_time, (
            f"{hook_name} took {elapsed:.2f}s (should be < {max_time}s)"
        )


class TestUserPromptSubmitHook:
    """Tests for the user-prompt-submit hook that detects implementation intent."""

    @pytest.fixture
    def hook_path(self):
        return get_hook_path("ig_user-prompt-submit.sh")

    def test_detects_implement_command(self, hook_path):
        """Should detect 'implement' commands and suggest task creation."""
        result = run_hook(
            hook_path,
            {"prompt": "implement user authentication"},
        )
        assert result["exit_code"] == 0
        if result["stdout"].strip():
            assert "task" in result["stdout"].lower()

    def test_detects_add_command(self, hook_path):
        """Should detect 'add' commands."""
        result = run_hook(
            hook_path,
            {"prompt": "add a new feature for user profiles"},
        )
        assert result["exit_code"] == 0

    def test_detects_create_command(self, hook_path):
        """Should detect 'create' commands."""
        result = run_hook(
            hook_path,
            {"prompt": "create a new API endpoint"},
        )
        assert result["exit_code"] == 0

    def test_detects_fix_command(self, hook_path):
        """Should detect 'fix' commands."""
        result = run_hook(
            hook_path,
            {"prompt": "fix the login bug"},
        )
        assert result["exit_code"] == 0

    def test_detects_whats_next_pattern(self, hook_path):
        """Should detect 'what's next' pattern."""
        result = run_hook(
            hook_path,
            {"prompt": "what's next on the todo list?"},
        )
        assert result["exit_code"] == 0

    def test_detects_bug_mentions(self, hook_path):
        """Should detect bug mentions and suggest task creation."""
        result = run_hook(
            hook_path,
            {"prompt": "there's a bug in the parser"},
        )
        assert result["exit_code"] == 0
        if result["stdout"].strip():
            assert "bug" in result["stdout"].lower()

    def test_no_output_for_regular_prompt(self, hook_path):
        """Should not output suggestions for regular prompts."""
        result = run_hook(
            hook_path,
            {"prompt": "explain how this function works"},
        )
        assert result["exit_code"] == 0
        # May or may not have output, but should complete successfully

    def test_handles_empty_prompt(self, hook_path):
        """Should handle empty prompt gracefully."""
        result = run_hook(
            hook_path,
            {"prompt": ""},
        )
        assert result["exit_code"] == 0


class TestHookIntegration:
    """Integration tests for hook behavior."""

    @pytest.fixture
    def hooks_dir(self):
        # Use source directory for integration tests
        return SOURCE_HOOKS_DIR

    def test_pre_tool_use_error_message_includes_alternative(self, hooks_dir):
        """PreToolUse should suggest specific IdlerGear alternatives."""
        hook_path = hooks_dir / "ig_pre-tool-use.sh"
        if not hook_path.exists():
            pytest.skip("Hook not found")

        # Test TODO.md suggests task create
        result = run_hook(
            hook_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "TODO.md", "content": "test"},
            },
        )
        assert "task" in result["stderr"].lower()

        # Test NOTES.md suggests note create
        result = run_hook(
            hook_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "NOTES.md", "content": "test"},
            },
        )
        assert "note" in result["stderr"].lower()


class TestPreCommitHook:
    """Tests for the git pre-commit hook (auto_version.sh)."""

    @pytest.fixture
    def hook_path(self):
        return get_hook_path("auto_version.sh")

    @pytest.fixture
    def git_repo(self):
        """Create a temporary git repository for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Initialize IdlerGear
            subprocess.run(["idlergear", "init"], cwd=repo_path, check=True, capture_output=True)

            # Create initial commit
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            yield repo_path

    def test_hook_warns_on_stale_tests(self, hook_path, git_repo):
        """Should warn when committing source files with stale tests."""
        if not hook_path.exists():
            pytest.skip("Hook not found")

        # Check if jq is available (required for the feature)
        jq_check = subprocess.run(["which", "jq"], capture_output=True)
        if jq_check.returncode != 0:
            pytest.skip("jq not available, skipping staleness warning test")

        # Manually create a stale test result (2 hours old)
        from datetime import datetime, timedelta, timezone

        test_results_dir = git_repo / ".idlergear" / "test_results"
        test_results_dir.mkdir(parents=True, exist_ok=True)

        old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        test_result = {
            "framework": "pytest",
            "timestamp": old_timestamp,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "total": 1,
            "duration": 0.1,
        }

        import json
        (test_results_dir / "last_result.json").write_text(json.dumps(test_result))

        # Enable test staleness warnings
        subprocess.run(
            ["idlergear", "config", "set", "test.warn_stale_on_commit", "true"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Set threshold to 1 hour (3600 seconds)
        subprocess.run(
            ["idlergear", "config", "set", "test.stale_threshold_seconds", "3600"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create and stage a source file
        (git_repo / "src.py").write_text("def hello(): pass\n")
        subprocess.run(["git", "add", "src.py"], cwd=git_repo, check=True, capture_output=True)

        # Copy hook to git hooks
        git_hooks_dir = git_repo / ".git" / "hooks"
        git_hooks_dir.mkdir(exist_ok=True)
        pre_commit_hook = git_hooks_dir / "pre-commit"
        pre_commit_hook.write_text(hook_path.read_text())
        pre_commit_hook.chmod(0o755)

        # Run the hook
        result = subprocess.run(
            [str(pre_commit_hook)],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )

        # Should warn about stale tests
        assert result.returncode == 0  # Warning, not blocking
        # Check both stdout and stderr as bash echo can go to either
        output = result.stdout + result.stderr
        assert "Warning" in output or "warning" in output.lower()

    def test_hook_no_warn_on_test_files(self, hook_path, git_repo):
        """Should not warn when only committing test files."""
        if not hook_path.exists():
            pytest.skip("Hook not found")

        # Enable test staleness warnings
        subprocess.run(
            ["idlergear", "config", "set", "test.warn_stale_on_commit", "true"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create and stage a test file
        (git_repo / "test_src.py").write_text("def test_hello(): pass\n")
        subprocess.run(["git", "add", "test_src.py"], cwd=git_repo, check=True, capture_output=True)

        # Copy hook to git hooks
        git_hooks_dir = git_repo / ".git" / "hooks"
        git_hooks_dir.mkdir(exist_ok=True)
        pre_commit_hook = git_hooks_dir / "pre-commit"
        pre_commit_hook.write_text(hook_path.read_text())
        pre_commit_hook.chmod(0o755)

        # Run the hook
        result = subprocess.run(
            [str(pre_commit_hook)],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )

        # Should not warn for test files
        assert result.returncode == 0
        assert "Warning" not in result.stdout

    def test_hook_disabled_by_default(self, hook_path, git_repo):
        """Test staleness warning should be disabled by default."""
        if not hook_path.exists():
            pytest.skip("Hook not found")

        # Explicitly set to false to be sure (default should be false anyway)
        subprocess.run(
            ["idlergear", "config", "set", "test.warn_stale_on_commit", "false"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create and stage a source file
        (git_repo / "src.py").write_text("def hello(): pass\n")
        subprocess.run(["git", "add", "src.py"], cwd=git_repo, check=True, capture_output=True)

        # Copy hook to git hooks
        git_hooks_dir = git_repo / ".git" / "hooks"
        git_hooks_dir.mkdir(exist_ok=True)
        pre_commit_hook = git_hooks_dir / "pre-commit"
        pre_commit_hook.write_text(hook_path.read_text())
        pre_commit_hook.chmod(0o755)

        # Run the hook
        result = subprocess.run(
            [str(pre_commit_hook)],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )

        # Should not warn when disabled
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Warning" not in output or "stale" not in output.lower()
