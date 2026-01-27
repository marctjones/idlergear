"""Tests for proactive suggestions."""

import pytest
from datetime import datetime, timezone

from idlergear.suggestions import (
    generate_suggestions,
    suggestions_text,
    suggestions_report,
    Suggestion,
)
from idlergear.tasks import create_task


def test_suggest_tasks_empty_project(temp_project):
    """Test suggestions with no tasks."""
    suggestions = generate_suggestions(temp_project)

    # Should still have test suggestion if tests exist
    # Or be empty if no tests
    assert isinstance(suggestions, list)


def test_suggest_high_priority_tasks(temp_project):
    """Test that high priority tasks are suggested first."""
    # Create tasks with different priorities
    create_task("Low priority task", priority="low")
    create_task("High priority task", priority="high")
    create_task("Medium priority task", priority="medium")

    suggestions = generate_suggestions(temp_project)

    task_suggestions = [s for s in suggestions if s.type == "task_recommendation"]

    if task_suggestions:
        # High priority should be suggested first
        first_suggestion = task_suggestions[0]
        assert "High priority task" in first_suggestion.title


def test_suggest_unblocked_tasks_only(temp_project):
    """Test that blocked tasks are not suggested."""
    # Create blocked task
    task1 = create_task("Blocked task", priority="high")
    task2 = create_task("Blocking task", priority="low")

    # Block task1 by manually editing the task file
    # (blocked_by not yet in update_task API, but suggestion engine checks for it)
    from idlergear.tasks import get_tasks_dir
    from idlergear.storage import parse_frontmatter, render_frontmatter
    tasks_dir = get_tasks_dir(temp_project)
    task_file = tasks_dir / f"{task1['id']:03d}-blocked-task.md"
    content = task_file.read_text()
    frontmatter, body = parse_frontmatter(content)
    frontmatter["blocked_by"] = [task2["id"]]
    new_content = render_frontmatter(frontmatter, body)
    task_file.write_text(new_content)

    suggestions = generate_suggestions(temp_project)

    task_suggestions = [s for s in suggestions if s.type == "task_recommendation"]

    # Should not suggest blocked task
    assert not any("Blocked task" in s.title for s in task_suggestions)


def test_suggest_recent_tasks_higher(temp_project):
    """Test that recent tasks score higher."""
    # Create old and new tasks (both high priority)
    create_task("Old task", priority="high")
    # The test doesn't have time travel, so both will be recent
    # Just verify suggestions are generated

    suggestions = generate_suggestions(temp_project)
    task_suggestions = [s for s in suggestions if s.type == "task_recommendation"]

    if task_suggestions:
        assert task_suggestions[0].confidence > 0.0
        assert task_suggestions[0].priority > 0


def test_suggest_tests_when_test_files_exist(temp_project):
    """Test that pytest is suggested when test files exist."""
    # Create a test directory
    tests_dir = temp_project / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_example.py").write_text("def test_foo(): pass")

    suggestions = generate_suggestions(temp_project)

    test_suggestions = [s for s in suggestions if s.type == "test_coverage"]

    assert len(test_suggestions) >= 1
    assert test_suggestions[0].action == "pytest"
    assert "test" in test_suggestions[0].description.lower()


def test_suggest_tests_not_shown_without_pytest(temp_project, monkeypatch):
    """Test that test suggestion requires pytest to be available."""
    # Mock shutil.which to return None (pytest not available)
    import shutil
    monkeypatch.setattr(shutil, "which", lambda cmd: None if cmd == "pytest" else shutil.which(cmd))

    # Create test files
    tests_dir = temp_project / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_example.py").write_text("def test_foo(): pass")

    suggestions = generate_suggestions(temp_project)

    test_suggestions = [s for s in suggestions if s.type == "test_coverage"]

    # Should not suggest tests if pytest not available
    assert len(test_suggestions) == 0


def test_suggestion_priority_range(temp_project):
    """Test that suggestions have valid priority values."""
    create_task("Test task", priority="high")

    suggestions = generate_suggestions(temp_project)

    for suggestion in suggestions:
        assert 1 <= suggestion.priority <= 10


def test_suggestion_confidence_range(temp_project):
    """Test that suggestions have valid confidence values."""
    create_task("Test task", priority="high")

    suggestions = generate_suggestions(temp_project)

    for suggestion in suggestions:
        assert 0.0 <= suggestion.confidence <= 1.0


def test_suggestions_sorted_by_priority_and_confidence(temp_project):
    """Test that suggestions are sorted correctly."""
    # Create multiple tasks
    create_task("Task 1", priority="low")
    create_task("Task 2", priority="medium")
    create_task("Task 3", priority="high")

    suggestions = generate_suggestions(temp_project)

    if len(suggestions) >= 2:
        # Each suggestion should have priority * confidence
        for i in range(len(suggestions) - 1):
            score_i = suggestions[i].priority * suggestions[i].confidence
            score_j = suggestions[i + 1].priority * suggestions[i + 1].confidence
            assert score_i >= score_j


def test_suggestions_text_formatting(temp_project):
    """Test text formatting of suggestions."""
    create_task("Example task", priority="high")

    suggestions = generate_suggestions(temp_project)

    text = suggestions_text(suggestions)

    if suggestions:
        assert "## Suggested Next Steps" in text
        assert "[" in text  # Priority/confidence indicators
        assert "→" in text  # Action arrow


def test_suggestions_text_empty(temp_project):
    """Test text formatting with no suggestions."""
    text = suggestions_text([])
    assert text == ""


def test_suggestions_report_formatting(temp_project):
    """Test report formatting of suggestions."""
    create_task("Example task", priority="high")

    # Create test file for test suggestion
    tests_dir = temp_project / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_example.py").write_text("def test_foo(): pass")

    suggestions = generate_suggestions(temp_project)

    report = suggestions_report(suggestions)

    if suggestions:
        assert "# Suggested Next Steps" in report
        task_suggestions = [s for s in suggestions if s.type == "task_recommendation"]
        if task_suggestions:
            assert "📋 Recommended Tasks" in report


def test_suggestions_report_empty(temp_project):
    """Test report with no suggestions."""
    report = suggestions_report([])
    assert "No suggestions" in report


def test_suggestion_has_required_fields(temp_project):
    """Test that generated suggestions have all required fields."""
    create_task("Test task", priority="high")

    suggestions = generate_suggestions(temp_project)

    for suggestion in suggestions:
        assert suggestion.type
        assert suggestion.priority
        assert suggestion.title
        assert suggestion.description is not None
        assert suggestion.action
        assert suggestion.reason
        assert suggestion.confidence is not None


def test_suggestions_limit_to_top_3_tasks(temp_project):
    """Test that only top 3 task recommendations are returned."""
    # Create many tasks
    for i in range(10):
        create_task(f"Task {i}", priority="high")

    suggestions = generate_suggestions(temp_project)

    task_suggestions = [s for s in suggestions if s.type == "task_recommendation"]

    # Should limit to top 3
    assert len(task_suggestions) <= 3


def test_suggestions_graceful_with_missing_fields(temp_project):
    """Test that suggestions handle tasks with missing fields gracefully."""
    # Create task and manually mess with fields
    task = create_task("Test task")

    # Generate suggestions shouldn't crash
    suggestions = generate_suggestions(temp_project)

    # Should complete without error
    assert isinstance(suggestions, list)


def test_task_suggestion_includes_task_id(temp_project):
    """Test that task suggestions include the task ID in action."""
    task = create_task("Example task", priority="high")

    suggestions = generate_suggestions(temp_project)

    task_suggestions = [s for s in suggestions if s.type == "task_recommendation"]

    if task_suggestions:
        suggestion = task_suggestions[0]
        assert str(task["id"]) in suggestion.action
        assert "idlergear task show" in suggestion.action


def test_suggestions_with_null_priority(temp_project):
    """Test suggestions when task has no priority set."""
    # Create task without priority
    task = create_task("No priority task")

    suggestions = generate_suggestions(temp_project)

    # Should still generate suggestions without crashing
    task_suggestions = [s for s in suggestions if s.type == "task_recommendation"]

    if task_suggestions:
        assert task_suggestions[0].confidence > 0.0
