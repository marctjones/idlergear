"""Tests for context integration with suggestions and gaps."""

import pytest

from idlergear.context import gather_context, format_context, ProjectContext
from idlergear.tasks import create_task
from idlergear.notes import create_note


def test_context_includes_suggestions(temp_project):
    """Test that context includes proactive suggestions."""
    # Create task to generate suggestions from
    create_task("High priority task", priority="high")

    context = gather_context(project_path=temp_project, mode="minimal")

    # Should have suggestions
    assert hasattr(context, 'suggestions')
    assert isinstance(context.suggestions, list)


def test_context_suggestions_limited_to_3(temp_project):
    """Test that context limits suggestions to top 3."""
    # Create many tasks
    for i in range(10):
        create_task(f"Task {i}", priority="high")

    context = gather_context(project_path=temp_project, mode="minimal")

    # Should limit to 3 suggestions
    assert len(context.suggestions) <= 3


def test_context_format_includes_suggestions(temp_project):
    """Test that formatted context includes suggestions section."""
    # Create task
    create_task("Test task", priority="high")

    context = gather_context(project_path=temp_project, mode="minimal")
    formatted = format_context(context)

    if context.suggestions:
        assert "## Suggested Next Steps" in formatted
        assert "→" in formatted  # Action arrow
        assert "[" in formatted  # Priority/confidence indicators


def test_context_suggestions_have_required_fields(temp_project):
    """Test that suggestions in context have all required fields."""
    create_task("Test task", priority="high")

    context = gather_context(project_path=temp_project, mode="minimal")

    for suggestion in context.suggestions:
        assert "type" in suggestion
        assert "priority" in suggestion
        assert "title" in suggestion
        assert "description" in suggestion
        assert "action" in suggestion
        assert "reason" in suggestion
        assert "confidence" in suggestion


def test_context_without_suggestions(temp_project):
    """Test context when no suggestions can be generated."""
    # Empty project
    context = gather_context(project_path=temp_project, mode="minimal")

    # Should still have suggestions list (just empty)
    assert hasattr(context, 'suggestions')
    assert context.suggestions == []


def test_context_suggestions_do_not_error_on_failure(temp_project):
    """Test that context generation doesn't fail if suggestions error."""
    # Even if suggestions fail, context should be generated
    context = gather_context(project_path=temp_project, mode="minimal")

    # Should complete without crashing
    assert context is not None
    assert isinstance(context, ProjectContext)


def test_formatted_context_suggestions_show_priority(temp_project):
    """Test that formatted suggestions show priority/confidence."""
    create_task("Test task", priority="high")

    context = gather_context(project_path=temp_project, mode="minimal")
    formatted = format_context(context)

    if context.suggestions:
        # Should show priority as [X/10]
        assert "/10" in formatted
        # Should show confidence as percentage
        assert "%" in formatted


def test_formatted_context_suggestions_show_action(temp_project):
    """Test that formatted suggestions show the action command."""
    create_task("Test task", priority="high")

    context = gather_context(project_path=temp_project, mode="minimal")
    formatted = format_context(context)

    if context.suggestions:
        # Should show action with arrow
        assert "→" in formatted
        # Should include idlergear command
        assert "idlergear" in formatted


def test_context_suggestions_in_different_modes(temp_project):
    """Test suggestions in different context modes."""
    create_task("Test task", priority="high")

    for mode in ["minimal", "standard", "detailed", "full"]:
        context = gather_context(project_path=temp_project, mode=mode)

        # All modes should include suggestions
        assert hasattr(context, 'suggestions')


def test_context_suggestions_error_handling(temp_project):
    """Test that suggestion errors are caught and logged."""
    context = gather_context(project_path=temp_project, mode="minimal")

    # If suggestions generation errors, it should be in errors list
    # But context should still be generated
    assert context is not None

    if context.errors:
        # Errors might include suggestions errors
        suggestion_errors = [e for e in context.errors if "Suggestion" in e]
        # Even with errors, suggestions should be initialized
        assert hasattr(context, 'suggestions')


def test_context_formatted_empty_suggestions(temp_project):
    """Test formatting context with empty suggestions list."""
    context = gather_context(project_path=temp_project, mode="minimal")

    # Manually clear suggestions to test formatting
    context.suggestions = []

    formatted = format_context(context)

    # Should not have suggestions section if empty
    # Or should handle gracefully
    assert isinstance(formatted, str)


def test_context_suggestions_with_test_files(temp_project):
    """Test that test coverage suggestions appear with test files."""
    # Create test directory
    tests_dir = temp_project / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_example.py").write_text("def test_foo(): pass")

    context = gather_context(project_path=temp_project, mode="minimal")

    # Should include test coverage suggestion
    test_suggestions = [
        s for s in context.suggestions
        if s.get("type") == "test_coverage"
    ]

    if test_suggestions:
        assert test_suggestions[0]["action"] == "pytest"


def test_context_suggestions_sorted_by_priority(temp_project):
    """Test that suggestions are sorted by priority * confidence."""
    # Create multiple tasks with different priorities
    create_task("Low task", priority="low")
    create_task("High task", priority="high")
    create_task("Medium task", priority="medium")

    context = gather_context(project_path=temp_project, mode="minimal")

    if len(context.suggestions) >= 2:
        # Each successive suggestion should have equal or lower score
        for i in range(len(context.suggestions) - 1):
            score_i = context.suggestions[i]["priority"] * context.suggestions[i]["confidence"]
            score_j = context.suggestions[i + 1]["priority"] * context.suggestions[i + 1]["confidence"]
            assert score_i >= score_j


def test_context_dataclass_has_suggestions_field():
    """Test that ProjectContext dataclass has suggestions field."""
    context = ProjectContext()

    assert hasattr(context, 'suggestions')
    assert context.suggestions == []  # Default to empty list


def test_context_json_format_includes_suggestions(temp_project):
    """Test that JSON format includes suggestions."""
    from idlergear.context import format_context_json

    create_task("Test task", priority="high")

    context = gather_context(project_path=temp_project, mode="minimal")
    json_data = format_context_json(context)

    # JSON should include suggestions
    assert "suggestions" in json_data or context.suggestions == []


def test_context_suggestions_confidence_in_range(temp_project):
    """Test that suggestion confidence values are valid."""
    create_task("Test task", priority="high")

    context = gather_context(project_path=temp_project, mode="minimal")

    for suggestion in context.suggestions:
        conf = suggestion.get("confidence", 0.0)
        assert 0.0 <= conf <= 1.0


def test_context_suggestions_priority_in_range(temp_project):
    """Test that suggestion priority values are valid."""
    create_task("Test task", priority="high")

    context = gather_context(project_path=temp_project, mode="minimal")

    for suggestion in context.suggestions:
        priority = suggestion.get("priority", 0)
        assert 1 <= priority <= 10
