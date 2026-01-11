"""Tests for watch mode functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


from idlergear.watch import (
    Suggestion,
    WatchStatus,
    WatchConfig,
    WatchEvent,
    FileWatcher,
    ActionResult,
    analyze,
    get_watch_stats,
    act_on_suggestion,
    act_on_all_suggestions,
    analyze_and_act,
)


class TestSuggestion:
    """Tests for Suggestion dataclass."""

    def test_to_dict(self):
        suggestion = Suggestion(
            id="s1",
            category="commit",
            message="Test message",
            severity="action",
            context={"key": "value"},
        )
        result = suggestion.to_dict()

        assert result["id"] == "s1"
        assert result["category"] == "commit"
        assert result["message"] == "Test message"
        assert result["severity"] == "action"
        assert result["context"] == {"key": "value"}


class TestWatchStatus:
    """Tests for WatchStatus dataclass."""

    def test_to_dict(self):
        status = WatchStatus(
            files_changed=5,
            lines_added=100,
            lines_deleted=50,
            minutes_since_commit=30,
            suggestions=[
                Suggestion(
                    id="s1",
                    category="commit",
                    message="Test",
                    severity="action",
                )
            ],
        )
        result = status.to_dict()

        assert result["files_changed"] == 5
        assert result["lines_added"] == 100
        assert result["lines_deleted"] == 50
        assert result["minutes_since_commit"] == 30
        assert len(result["suggestions"]) == 1


class TestWatchConfig:
    """Tests for WatchConfig."""

    def test_default_values(self):
        config = WatchConfig()

        assert config.enabled is False
        assert config.debounce == 5
        assert config.files_changed_threshold == 5
        assert config.uncommitted_lines_threshold == 100
        assert config.test_failures_threshold == 1
        assert config.detect_todos is True
        assert config.poll_interval == 10

    def test_load_defaults(self):
        """Test that load returns defaults when no config exists."""
        with patch("idlergear.watch.get_config_value", return_value=None):
            config = WatchConfig.load()

        assert config.enabled is False
        assert config.debounce == 5


class TestWatchEvent:
    """Tests for WatchEvent dataclass."""

    def test_to_dict(self):
        event = WatchEvent(
            event_type="modified",
            path="/test/file.py",
            is_directory=False,
        )
        result = event.to_dict()

        assert result["event_type"] == "modified"
        assert result["path"] == "/test/file.py"
        assert result["is_directory"] is False
        assert "timestamp" in result


class TestFileWatcher:
    """Tests for FileWatcher class."""

    def test_init(self):
        config = WatchConfig()
        watcher = FileWatcher(config=config)

        assert watcher.config == config
        assert watcher._running is False
        assert watcher._callbacks == []

    def test_add_callback(self):
        watcher = FileWatcher()
        callback = MagicMock()
        watcher.add_callback(callback)

        assert callback in watcher._callbacks

    def test_should_ignore(self):
        watcher = FileWatcher()

        assert watcher._should_ignore("/project/.git/objects/abc") is True
        assert watcher._should_ignore("/project/__pycache__/module.pyc") is True
        assert watcher._should_ignore("/project/venv/lib/python/site.py") is True
        assert watcher._should_ignore("/project/src/main.py") is False

    def test_notify_callbacks(self):
        watcher = FileWatcher()
        callback = MagicMock()
        watcher.add_callback(callback)

        status = WatchStatus(
            files_changed=1,
            lines_added=10,
            lines_deleted=5,
            minutes_since_commit=10,
            suggestions=[],
        )
        watcher._notify_callbacks(status)

        callback.assert_called_once_with(status)

    def test_has_changes_first_status(self):
        watcher = FileWatcher()
        status = WatchStatus(
            files_changed=1,
            lines_added=10,
            lines_deleted=5,
            minutes_since_commit=10,
            suggestions=[],
        )

        assert watcher._has_changes(status) is True

    def test_has_changes_same_status(self):
        watcher = FileWatcher()
        status = WatchStatus(
            files_changed=1,
            lines_added=10,
            lines_deleted=5,
            minutes_since_commit=10,
            suggestions=[],
        )
        watcher._last_status = status

        assert watcher._has_changes(status) is False

    def test_has_changes_different_files(self):
        watcher = FileWatcher()
        old_status = WatchStatus(
            files_changed=1,
            lines_added=10,
            lines_deleted=5,
            minutes_since_commit=10,
            suggestions=[],
        )
        watcher._last_status = old_status

        new_status = WatchStatus(
            files_changed=2,  # Different
            lines_added=10,
            lines_deleted=5,
            minutes_since_commit=10,
            suggestions=[],
        )

        assert watcher._has_changes(new_status) is True


class TestAnalyze:
    """Tests for analyze function."""

    def test_analyze_no_project(self):
        with patch("idlergear.watch.find_idlergear_root", return_value=None):
            status = analyze()

        assert status.files_changed == 0
        assert len(status.suggestions) == 1
        assert status.suggestions[0].category == "error"

    @patch("idlergear.watch.get_config_value")
    @patch("idlergear.watch.get_git_status")
    @patch("idlergear.watch.get_minutes_since_last_commit")
    @patch("idlergear.watch.scan_diff_for_todos")
    @patch("idlergear.watch.check_reference_staleness")
    def test_analyze_with_changes(
        self,
        mock_staleness,
        mock_todos,
        mock_minutes,
        mock_git_status,
        mock_config,
    ):
        mock_config.return_value = None
        mock_git_status.return_value = {
            "files_changed": 6,
            "files_staged": 0,
            "files_untracked": 0,
            "lines_added": 150,
            "lines_deleted": 50,
            "modified_files": ["a.py", "b.py", "c.py", "d.py", "e.py", "f.py"],
            "staged_files": [],
            "untracked_files": [],
        }
        mock_minutes.return_value = 45
        mock_todos.return_value = []
        mock_staleness.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".idlergear").mkdir()

            status = analyze(project_root)

        assert status.files_changed == 6
        assert status.lines_added == 150
        # Should have suggestions for file count and line count
        assert len(status.suggestions) >= 2


class TestGetWatchStats:
    """Tests for get_watch_stats function."""

    @patch("idlergear.watch.analyze")
    def test_get_watch_stats(self, mock_analyze):
        mock_analyze.return_value = WatchStatus(
            files_changed=3,
            lines_added=50,
            lines_deleted=20,
            minutes_since_commit=15,
            suggestions=[
                Suggestion(
                    id="s1",
                    category="todo",
                    message="Found TODO",
                    severity="action",
                    context={"type": "TODO"},
                ),
                Suggestion(
                    id="s2",
                    category="todo",
                    message="Found FIXME",
                    severity="action",
                    context={"type": "FIXME"},
                ),
            ],
        )

        stats = get_watch_stats()

        assert stats["changed_files"] == 3
        assert stats["changed_lines"] == 70
        assert stats["todos"] == 1
        assert stats["fixmes"] == 1
        assert stats["suggestion_count"] == 2


class TestActionResult:
    """Tests for ActionResult dataclass."""

    def test_to_dict(self):
        result = ActionResult(
            success=True,
            action="create_task",
            message="Created task #1",
            created_id=1,
        )
        data = result.to_dict()

        assert data["success"] is True
        assert data["action"] == "create_task"
        assert data["message"] == "Created task #1"
        assert data["created_id"] == 1

    def test_to_dict_no_id(self):
        result = ActionResult(
            success=True,
            action="inform",
            message="Commit suggestion noted.",
        )
        data = result.to_dict()

        assert data["success"] is True
        assert data["created_id"] is None


class TestActOnSuggestion:
    """Tests for act_on_suggestion function."""

    def test_act_on_commit_suggestion(self):
        """Commit suggestions return informational result."""
        suggestion = Suggestion(
            id="s1",
            category="commit",
            message="Consider committing",
            severity="action",
        )

        result = act_on_suggestion(suggestion)

        assert result.success is True
        assert result.action == "inform"
        assert "Commit suggestion" in result.message

    def test_act_on_reference_suggestion(self):
        """Reference suggestions return informational result."""
        suggestion = Suggestion(
            id="s1",
            category="reference",
            message="Reference stale",
            severity="warning",
            context={"reference": "API.md"},
        )

        result = act_on_suggestion(suggestion)

        assert result.success is True
        assert result.action == "inform"
        assert "stale" in result.message.lower()

    def test_act_on_test_suggestion(self):
        """Test suggestions return informational result."""
        suggestion = Suggestion(
            id="s1",
            category="test",
            message="Run tests",
            severity="info",
        )

        result = act_on_suggestion(suggestion)

        assert result.success is True
        assert result.action == "inform"
        assert "test" in result.message.lower()

    def test_act_on_docs_suggestion(self):
        """Docs suggestions return informational result."""
        suggestion = Suggestion(
            id="s1",
            category="docs",
            message="Sync wiki",
            severity="info",
        )

        result = act_on_suggestion(suggestion)

        assert result.success is True
        assert result.action == "inform"
        assert "wiki" in result.message.lower()

    def test_act_on_unknown_category(self):
        """Unknown categories return failure."""
        suggestion = Suggestion(
            id="s1",
            category="unknown_category",
            message="Unknown",
            severity="info",
        )

        result = act_on_suggestion(suggestion)

        assert result.success is False
        assert result.action == "unknown"

    @patch("idlergear.tasks.create_task")
    def test_act_on_todo_suggestion(self, mock_create_task):
        """TODO suggestions create tasks."""
        mock_create_task.return_value = {"id": 42, "title": "Fix the bug"}

        suggestion = Suggestion(
            id="s1",
            category="todo",
            message="Found FIXME comment",
            severity="action",
            context={
                "type": "FIXME",
                "text": "Fix the bug",
                "file": "src/main.py",
            },
        )

        result = act_on_suggestion(suggestion)

        assert result.success is True
        assert result.action == "create_task"
        assert result.created_id == 42
        mock_create_task.assert_called_once()
        # Check that labels include 'bug' for FIXME
        call_kwargs = mock_create_task.call_args[1]
        assert "bug" in call_kwargs["labels"]

    @patch("idlergear.tasks.create_task")
    def test_act_on_todo_creates_tech_debt_label(self, mock_create_task):
        """TODO and HACK comments get technical-debt label."""
        mock_create_task.return_value = {"id": 1}

        suggestion = Suggestion(
            id="s1",
            category="todo",
            message="Found TODO",
            severity="action",
            context={
                "type": "TODO",
                "text": "Refactor later",
                "file": "src/utils.py",
            },
        )

        result = act_on_suggestion(suggestion)

        assert result.success is True
        call_kwargs = mock_create_task.call_args[1]
        assert "technical-debt" in call_kwargs["labels"]

    def test_act_on_todo_no_text(self):
        """TODO with no text returns failure."""
        suggestion = Suggestion(
            id="s1",
            category="todo",
            message="Found TODO",
            severity="action",
            context={
                "type": "TODO",
                "text": "",
                "file": "src/main.py",
            },
        )

        result = act_on_suggestion(suggestion)

        assert result.success is False
        assert "No TODO text" in result.message


class TestActOnAllSuggestions:
    """Tests for act_on_all_suggestions function."""

    def test_act_on_all_filters_by_category(self):
        """Only acts on specified categories."""
        status = WatchStatus(
            files_changed=1,
            lines_added=10,
            lines_deleted=5,
            minutes_since_commit=10,
            suggestions=[
                Suggestion(
                    id="s1", category="commit", message="Commit", severity="action"
                ),
                Suggestion(
                    id="s2",
                    category="todo",
                    message="TODO",
                    severity="action",
                    context={"type": "TODO", "text": "", "file": "x.py"},
                ),
                Suggestion(id="s3", category="test", message="Test", severity="info"),
            ],
        )

        # By default only acts on "todo" category
        results = act_on_all_suggestions(status)

        assert len(results) == 1
        assert results[0].action == "create_task"

    def test_act_on_all_custom_categories(self):
        """Can specify which categories to act on."""
        status = WatchStatus(
            files_changed=1,
            lines_added=10,
            lines_deleted=5,
            minutes_since_commit=10,
            suggestions=[
                Suggestion(
                    id="s1", category="commit", message="Commit", severity="action"
                ),
                Suggestion(id="s2", category="test", message="Test", severity="info"),
            ],
        )

        results = act_on_all_suggestions(status, categories=["commit", "test"])

        assert len(results) == 2


class TestAnalyzeAndAct:
    """Tests for analyze_and_act function."""

    @patch("idlergear.watch.analyze")
    def test_analyze_and_act_no_todos(self, mock_analyze):
        """Returns empty actions when no TODOs found."""
        mock_analyze.return_value = WatchStatus(
            files_changed=1,
            lines_added=10,
            lines_deleted=5,
            minutes_since_commit=10,
            suggestions=[
                Suggestion(
                    id="s1", category="commit", message="Commit", severity="action"
                ),
            ],
        )

        status, actions = analyze_and_act()

        assert status.files_changed == 1
        assert len(actions) == 0

    @patch("idlergear.watch.analyze")
    @patch("idlergear.tasks.create_task")
    def test_analyze_and_act_with_todos(self, mock_create_task, mock_analyze):
        """Creates tasks from TODOs when auto_create_tasks is True."""
        mock_create_task.return_value = {"id": 1}
        mock_analyze.return_value = WatchStatus(
            files_changed=1,
            lines_added=10,
            lines_deleted=5,
            minutes_since_commit=10,
            suggestions=[
                Suggestion(
                    id="s1",
                    category="todo",
                    message="Found TODO",
                    severity="action",
                    context={"type": "TODO", "text": "Do something", "file": "x.py"},
                ),
            ],
        )

        status, actions = analyze_and_act(auto_create_tasks=True)

        assert len(actions) == 1
        assert actions[0].success is True
        mock_create_task.assert_called_once()

    @patch("idlergear.watch.analyze")
    def test_analyze_and_act_disabled(self, mock_analyze):
        """Does not create tasks when auto_create_tasks is False."""
        mock_analyze.return_value = WatchStatus(
            files_changed=1,
            lines_added=10,
            lines_deleted=5,
            minutes_since_commit=10,
            suggestions=[
                Suggestion(
                    id="s1",
                    category="todo",
                    message="Found TODO",
                    severity="action",
                    context={"type": "TODO", "text": "Do something", "file": "x.py"},
                ),
            ],
        )

        status, actions = analyze_and_act(auto_create_tasks=False)

        assert len(actions) == 0


# =============================================================================
# Tests for Test-Aware Watch Suggestions (Issues #160, #161)
# =============================================================================


class TestAnalyzeTestSuggestions:
    """Tests for test-aware suggestions in analyze function."""

    @patch("idlergear.watch.get_config_value")
    @patch("idlergear.watch.get_git_status")
    @patch("idlergear.watch.get_minutes_since_last_commit")
    @patch("idlergear.watch.scan_diff_for_todos")
    @patch("idlergear.watch.check_reference_staleness")
    def test_source_files_changed_no_tests_recorded(
        self,
        mock_staleness,
        mock_todos,
        mock_minutes,
        mock_git_status,
        mock_config,
    ):
        """Warn when source files changed but no tests recorded."""
        mock_config.return_value = None
        mock_git_status.return_value = {
            "files_changed": 2,
            "files_staged": 0,
            "files_untracked": 0,
            "lines_added": 50,
            "lines_deleted": 10,
            "modified_files": ["src/api.py", "src/utils.py"],
            "staged_files": [],
            "untracked_files": [],
        }
        mock_minutes.return_value = 5
        mock_todos.return_value = []
        mock_staleness.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".idlergear").mkdir()

            # Mock testing module to return no last result
            with patch("idlergear.testing.get_last_result", return_value=None):
                with patch("idlergear.testing.get_tests_for_changes", return_value=[]):
                    status = analyze(project_root)

        # Should have a suggestion about source files modified with no tests
        test_suggestions = [s for s in status.suggestions if s.category == "test"]
        assert len(test_suggestions) >= 1
        assert any("no tests recorded" in s.message.lower() for s in test_suggestions)

    @patch("idlergear.watch.get_config_value")
    @patch("idlergear.watch.get_git_status")
    @patch("idlergear.watch.get_minutes_since_last_commit")
    @patch("idlergear.watch.scan_diff_for_todos")
    @patch("idlergear.watch.check_reference_staleness")
    def test_tests_failing_from_last_run(
        self,
        mock_staleness,
        mock_todos,
        mock_minutes,
        mock_git_status,
        mock_config,
    ):
        """Warn when last test run had failures."""
        from idlergear.testing import TestResult

        mock_config.return_value = None
        mock_git_status.return_value = {
            "files_changed": 1,
            "files_staged": 0,
            "files_untracked": 0,
            "lines_added": 10,
            "lines_deleted": 5,
            "modified_files": ["src/main.py"],
            "staged_files": [],
            "untracked_files": [],
        }
        mock_minutes.return_value = 5
        mock_todos.return_value = []
        mock_staleness.return_value = []

        # Create a failing test result
        failing_result = TestResult(
            framework="pytest",
            timestamp="2026-01-11T10:00:00Z",
            duration_seconds=5.0,
            total=10,
            passed=8,
            failed=2,
            skipped=0,
            errors=0,
            failed_tests=["test_foo", "test_bar"],
            command="pytest",
            exit_code=1,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".idlergear").mkdir()

            with patch(
                "idlergear.testing.get_last_result", return_value=failing_result
            ):
                with patch("idlergear.testing.get_tests_for_changes", return_value=[]):
                    status = analyze(project_root)

        # Should have a suggestion about failing tests
        test_suggestions = [s for s in status.suggestions if s.category == "test"]
        assert len(test_suggestions) >= 1
        assert any("failing" in s.message.lower() for s in test_suggestions)

    @patch("idlergear.watch.get_config_value")
    @patch("idlergear.watch.get_git_status")
    @patch("idlergear.watch.get_minutes_since_last_commit")
    @patch("idlergear.watch.scan_diff_for_todos")
    @patch("idlergear.watch.check_reference_staleness")
    def test_tests_for_changed_files_suggestion(
        self,
        mock_staleness,
        mock_todos,
        mock_minutes,
        mock_git_status,
        mock_config,
    ):
        """Suggest specific tests for changed source files."""
        from idlergear.testing import TestResult

        mock_config.return_value = None
        mock_git_status.return_value = {
            "files_changed": 1,
            "files_staged": 0,
            "files_untracked": 0,
            "lines_added": 20,
            "lines_deleted": 5,
            "modified_files": ["src/api.py"],
            "staged_files": [],
            "untracked_files": [],
        }
        mock_minutes.return_value = 5
        mock_todos.return_value = []
        mock_staleness.return_value = []

        # Create a passing test result
        passing_result = TestResult(
            framework="pytest",
            timestamp="2026-01-11T10:00:00Z",
            duration_seconds=5.0,
            total=10,
            passed=10,
            failed=0,
            skipped=0,
            errors=0,
            command="pytest",
            exit_code=0,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".idlergear").mkdir()

            with patch(
                "idlergear.testing.get_last_result", return_value=passing_result
            ):
                with patch(
                    "idlergear.testing.get_tests_for_changes",
                    return_value=["tests/test_api.py"],
                ):
                    status = analyze(project_root)

        # Should have a suggestion about tests for changed files
        test_suggestions = [s for s in status.suggestions if s.category == "test"]
        assert any(
            "tests for changed files" in s.message.lower() for s in test_suggestions
        )

    @patch("idlergear.watch.get_config_value")
    @patch("idlergear.watch.get_git_status")
    @patch("idlergear.watch.get_minutes_since_last_commit")
    @patch("idlergear.watch.scan_diff_for_todos")
    @patch("idlergear.watch.check_reference_staleness")
    def test_test_files_changed_suggestion(
        self,
        mock_staleness,
        mock_todos,
        mock_minutes,
        mock_git_status,
        mock_config,
    ):
        """Suggest running tests when test files are modified."""
        mock_config.return_value = None
        mock_git_status.return_value = {
            "files_changed": 1,
            "files_staged": 0,
            "files_untracked": 0,
            "lines_added": 20,
            "lines_deleted": 5,
            "modified_files": ["tests/test_api.py"],  # Test file modified
            "staged_files": [],
            "untracked_files": [],
        }
        mock_minutes.return_value = 5
        mock_todos.return_value = []
        mock_staleness.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".idlergear").mkdir()

            status = analyze(project_root)

        # Should have a suggestion about running tests
        test_suggestions = [s for s in status.suggestions if s.category == "test"]
        assert len(test_suggestions) >= 1
        assert any("test files changed" in s.message.lower() for s in test_suggestions)
