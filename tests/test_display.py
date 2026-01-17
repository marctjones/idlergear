"""Tests for display module - CLI output formatting."""

from __future__ import annotations

import json
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
import typer

from idlergear.display import (
    display,
    format_note,
    format_note_list,
    format_plan,
    format_plan_list,
    format_reference,
    format_reference_list,
    format_search_results,
    format_task,
    format_task_list,
    format_vision,
    is_interactive,
    print_human,
    print_json,
)


class TestIsInteractive:
    """Tests for is_interactive function."""

    def test_is_interactive_tty(self):
        """Test detection of TTY."""
        with patch.object(sys.stdout, "isatty", return_value=True):
            assert is_interactive() is True

    def test_is_interactive_not_tty(self):
        """Test detection of non-TTY."""
        with patch.object(sys.stdout, "isatty", return_value=False):
            assert is_interactive() is False


class TestDisplay:
    """Tests for the display function."""

    def test_display_json(self, capsys):
        """Test display with json format."""
        data = {"key": "value"}
        display(data, "json", "test")
        captured = capsys.readouterr()
        assert '"key": "value"' in captured.out

    def test_display_human(self, capsys):
        """Test display with human format."""
        data = "test message"
        display(data, "human", "test")
        captured = capsys.readouterr()
        assert "test message" in captured.out


class TestPrintJson:
    """Tests for print_json function."""

    def test_print_json_none(self, capsys):
        """Test printing None as JSON."""
        print_json(None)
        captured = capsys.readouterr()
        assert "null" in captured.out

    def test_print_json_string(self, capsys):
        """Test printing string directly."""
        print_json("raw string")
        captured = capsys.readouterr()
        assert "raw string" in captured.out

    def test_print_json_bytes(self, capsys):
        """Test printing bytes directly."""
        print_json(b"raw bytes")
        captured = capsys.readouterr()
        assert "raw bytes" in captured.out

    def test_print_json_dict(self, capsys):
        """Test printing dict as JSON."""
        print_json({"foo": "bar"})
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["foo"] == "bar"

    def test_print_json_list(self, capsys):
        """Test printing list as JSON."""
        print_json([1, 2, 3])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data == [1, 2, 3]


class TestPrintHuman:
    """Tests for print_human function."""

    def test_print_human_empty_list(self, capsys):
        """Test printing empty list with unknown type."""
        print_human([], "unknown_type")
        captured = capsys.readouterr()
        assert "No unknown_type found." in captured.out

    def test_print_human_string(self, capsys):
        """Test printing string directly."""
        print_human("hello world", "unknown")
        captured = capsys.readouterr()
        assert "hello world" in captured.out

    def test_print_human_none(self, capsys):
        """Test printing None (no output)."""
        print_human(None, "test")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_print_human_fallback(self, capsys):
        """Test fallback for unknown data types."""
        print_human(12345, "number")
        captured = capsys.readouterr()
        assert "12345" in captured.out


class TestFormatTaskList:
    """Tests for format_task_list function."""

    def test_format_empty_task_list(self, capsys):
        """Test formatting empty task list."""
        format_task_list([])
        captured = capsys.readouterr()
        assert "No tasks found." in captured.out

    def test_format_task_list_open(self, capsys):
        """Test formatting open tasks."""
        tasks = [{"id": 1, "title": "Test task", "state": "open"}]
        format_task_list(tasks)
        captured = capsys.readouterr()
        assert "[o]" in captured.out
        assert "#1" in captured.out
        assert "Test task" in captured.out

    def test_format_task_list_closed(self, capsys):
        """Test formatting closed tasks."""
        tasks = [{"id": 2, "title": "Done task", "state": "closed"}]
        format_task_list(tasks)
        captured = capsys.readouterr()
        assert "[x]" in captured.out
        assert "#2" in captured.out

    def test_format_task_list_with_labels(self, capsys):
        """Test formatting tasks with labels."""
        tasks = [
            {"id": 1, "title": "Bug fix", "state": "open", "labels": ["bug", "urgent"]}
        ]
        format_task_list(tasks)
        captured = capsys.readouterr()
        assert "[bug, urgent]" in captured.out

    def test_format_task_list_with_priority(self, capsys):
        """Test formatting tasks with priority."""
        tasks = [{"id": 1, "title": "Urgent task", "state": "open", "priority": "high"}]
        format_task_list(tasks)
        captured = capsys.readouterr()
        assert "!high" in captured.out

    def test_format_task_list_with_due(self, capsys):
        """Test formatting tasks with due date."""
        tasks = [
            {"id": 1, "title": "Deadline task", "state": "open", "due": "2025-01-15"}
        ]
        format_task_list(tasks)
        captured = capsys.readouterr()
        assert "@2025-01-15" in captured.out


class TestFormatTask:
    """Tests for format_task function."""

    def test_format_task_not_found(self):
        """Test formatting None task raises Exit."""
        with pytest.raises(typer.Exit):
            format_task(None)

    def test_format_task_basic(self, capsys):
        """Test formatting basic task."""
        task = {"id": 1, "title": "Test task", "state": "open"}
        format_task(task)
        captured = capsys.readouterr()
        assert "Task #1" in captured.out
        assert "Test task" in captured.out
        assert "State: open" in captured.out

    def test_format_task_with_priority_high(self, capsys):
        """Test formatting task with high priority."""
        task = {"id": 1, "title": "High priority", "state": "open", "priority": "high"}
        format_task(task)
        captured = capsys.readouterr()
        assert "Priority: high" in captured.out

    def test_format_task_with_priority_medium(self, capsys):
        """Test formatting task with medium priority."""
        task = {"id": 1, "title": "Medium", "state": "open", "priority": "medium"}
        format_task(task)
        captured = capsys.readouterr()
        assert "Priority: medium" in captured.out

    def test_format_task_with_priority_low(self, capsys):
        """Test formatting task with low priority."""
        task = {"id": 1, "title": "Low", "state": "open", "priority": "low"}
        format_task(task)
        captured = capsys.readouterr()
        assert "Priority: low" in captured.out

    def test_format_task_with_due(self, capsys):
        """Test formatting task with due date."""
        task = {"id": 1, "title": "Deadline", "state": "open", "due": "2025-01-20"}
        format_task(task)
        captured = capsys.readouterr()
        assert "Due: 2025-01-20" in captured.out

    def test_format_task_with_labels(self, capsys):
        """Test formatting task with labels."""
        task = {
            "id": 1,
            "title": "Labeled",
            "state": "open",
            "labels": ["bug", "feature"],
        }
        format_task(task)
        captured = capsys.readouterr()
        assert "Labels: bug, feature" in captured.out

    def test_format_task_with_assignees(self, capsys):
        """Test formatting task with assignees."""
        task = {
            "id": 1,
            "title": "Assigned",
            "state": "open",
            "assignees": ["alice", "bob"],
        }
        format_task(task)
        captured = capsys.readouterr()
        assert "Assignees: alice, bob" in captured.out

    def test_format_task_with_created(self, capsys):
        """Test formatting task with created date."""
        task = {"id": 1, "title": "Created", "state": "open", "created": "2025-01-01"}
        format_task(task)
        captured = capsys.readouterr()
        assert "Created: 2025-01-01" in captured.out

    def test_format_task_with_created_at(self, capsys):
        """Test formatting task with created_at field."""
        task = {"id": 1, "title": "Created", "state": "open", "created_at": "2025-01-01"}
        format_task(task)
        captured = capsys.readouterr()
        assert "Created: 2025-01-01" in captured.out

    def test_format_task_with_github_issue(self, capsys):
        """Test formatting task with GitHub issue."""
        task = {
            "id": 1,
            "title": "Linked",
            "state": "open",
            "github_issue": 42,
        }
        format_task(task)
        captured = capsys.readouterr()
        assert "GitHub: #42" in captured.out

    def test_format_task_with_body(self, capsys):
        """Test formatting task with body."""
        task = {
            "id": 1,
            "title": "With body",
            "state": "open",
            "body": "This is the description.",
        }
        format_task(task)
        captured = capsys.readouterr()
        assert "This is the description." in captured.out


class TestFormatVision:
    """Tests for format_vision function."""

    def test_format_vision_none(self, capsys):
        """Test formatting None vision."""
        format_vision(None)
        captured = capsys.readouterr()
        assert "No vision set" in captured.out

    def test_format_vision_empty(self, capsys):
        """Test formatting empty vision."""
        format_vision("   ")
        captured = capsys.readouterr()
        assert "No vision set" in captured.out

    def test_format_vision_content(self, capsys):
        """Test formatting vision with content."""
        format_vision("Build an awesome project")
        captured = capsys.readouterr()
        assert "Build an awesome project" in captured.out


class TestFormatNoteList:
    """Tests for format_note_list function."""

    def test_format_empty_note_list(self, capsys):
        """Test formatting empty note list."""
        format_note_list([])
        captured = capsys.readouterr()
        assert "No notes found." in captured.out

    def test_format_note_list_basic(self, capsys):
        """Test formatting notes list."""
        notes = [{"id": 1, "content": "A short note"}]
        format_note_list(notes)
        captured = capsys.readouterr()
        assert "#1" in captured.out
        assert "A short note" in captured.out

    def test_format_note_list_long_content(self, capsys):
        """Test formatting notes with long content (truncated)."""
        notes = [{"id": 1, "content": "x" * 100}]
        format_note_list(notes)
        captured = capsys.readouterr()
        assert "..." in captured.out
        assert len([line for line in captured.out.split("\n") if "#1" in line]) == 1

    def test_format_note_list_with_tags(self, capsys):
        """Test formatting notes with tags."""
        notes = [{"id": 1, "content": "Tagged note", "tags": ["explore", "idea"]}]
        format_note_list(notes)
        captured = capsys.readouterr()
        assert "[explore, idea]" in captured.out

    def test_format_note_list_multiline(self, capsys):
        """Test formatting notes with multiline content."""
        notes = [{"id": 1, "content": "Line1\nLine2\nLine3"}]
        format_note_list(notes)
        captured = capsys.readouterr()
        # Should replace newlines with space in preview
        assert "Line1 Line2" in captured.out


class TestFormatNote:
    """Tests for format_note function."""

    def test_format_note_not_found(self):
        """Test formatting None note raises Exit."""
        with pytest.raises(typer.Exit):
            format_note(None)

    def test_format_note_basic(self, capsys):
        """Test formatting basic note."""
        note = {"id": 1, "content": "Test note content", "created": "2025-01-01"}
        format_note(note)
        captured = capsys.readouterr()
        assert "Note #1" in captured.out
        assert "Created: 2025-01-01" in captured.out
        assert "Test note content" in captured.out

    def test_format_note_with_tags(self, capsys):
        """Test formatting note with tags."""
        note = {
            "id": 1,
            "content": "Tagged",
            "created": "2025-01-01",
            "tags": ["explore"],
        }
        format_note(note)
        captured = capsys.readouterr()
        assert "Tags: explore" in captured.out


class TestFormatPlanList:
    """Tests for format_plan_list function."""

    def test_format_empty_plan_list(self, capsys):
        """Test formatting empty plan list."""
        format_plan_list([])
        captured = capsys.readouterr()
        assert "No plans found." in captured.out

    def test_format_plan_list_basic(self, capsys):
        """Test formatting plan list."""
        plans = [{"name": "v1", "title": "Version 1"}]
        format_plan_list(plans)
        captured = capsys.readouterr()
        assert "v1" in captured.out
        assert "Version 1" in captured.out

    def test_format_plan_list_current(self, capsys):
        """Test formatting plan list with current marker."""
        plans = [{"name": "active", "title": "Active Plan", "is_current": True}]
        format_plan_list(plans)
        captured = capsys.readouterr()
        assert "*" in captured.out
        assert "active" in captured.out


class TestFormatPlan:
    """Tests for format_plan function."""

    def test_format_plan_none(self, capsys):
        """Test formatting None plan (no output)."""
        format_plan(None)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_format_plan_basic(self, capsys):
        """Test formatting basic plan."""
        plan = {
            "name": "v1",
            "title": "Version 1",
            "state": "active",
            "created": "2025-01-01",
        }
        format_plan(plan)
        captured = capsys.readouterr()
        assert "Plan: v1" in captured.out
        assert "Title: Version 1" in captured.out
        assert "State: active" in captured.out
        assert "Created: 2025-01-01" in captured.out

    def test_format_plan_with_github_project(self, capsys):
        """Test formatting plan with GitHub project."""
        plan = {
            "name": "v1",
            "title": "Version 1",
            "state": "active",
            "created": "2025-01-01",
            "github_project": 123,
        }
        format_plan(plan)
        captured = capsys.readouterr()
        assert "GitHub: Project #123" in captured.out

    def test_format_plan_with_body(self, capsys):
        """Test formatting plan with body."""
        plan = {
            "name": "v1",
            "title": "Version 1",
            "state": "active",
            "created": "2025-01-01",
            "body": "Plan description here.",
        }
        format_plan(plan)
        captured = capsys.readouterr()
        assert "Plan description here." in captured.out


class TestFormatReferenceList:
    """Tests for format_reference_list function."""

    def test_format_empty_reference_list(self, capsys):
        """Test formatting empty reference list."""
        format_reference_list([])
        captured = capsys.readouterr()
        assert "No reference documents found." in captured.out

    def test_format_reference_list_basic(self, capsys):
        """Test formatting reference list."""
        refs = [{"title": "API Guide"}]
        format_reference_list(refs)
        captured = capsys.readouterr()
        assert "API Guide" in captured.out


class TestFormatReference:
    """Tests for format_reference function."""

    def test_format_reference_not_found(self):
        """Test formatting None reference raises Exit."""
        with pytest.raises(typer.Exit):
            format_reference(None)

    def test_format_reference_basic(self, capsys):
        """Test formatting basic reference."""
        ref = {"title": "API Guide", "created": "2025-01-01", "updated": "2025-01-05"}
        format_reference(ref)
        captured = capsys.readouterr()
        assert "Reference: API Guide" in captured.out
        assert "Created: 2025-01-01" in captured.out
        assert "Updated: 2025-01-05" in captured.out

    def test_format_reference_with_body(self, capsys):
        """Test formatting reference with body."""
        ref = {
            "title": "API Guide",
            "created": "2025-01-01",
            "updated": "2025-01-05",
            "body": "API documentation content.",
        }
        format_reference(ref)
        captured = capsys.readouterr()
        assert "API documentation content." in captured.out


class TestFormatSearchResults:
    """Tests for format_search_results function."""

    def test_format_empty_search_results(self, capsys):
        """Test formatting empty search results."""
        format_search_results([])
        captured = capsys.readouterr()
        assert "No results found." in captured.out

    def test_format_search_results_with_tasks(self, capsys):
        """Test formatting search results with tasks."""
        results = [
            {"type": "task", "id": 1, "title": "Test task", "_query": "test"}
        ]
        format_search_results(results)
        captured = capsys.readouterr()
        assert "Found 1 result(s)" in captured.out
        assert "TASKS" in captured.out
        assert "#1" in captured.out
        assert "Test task" in captured.out

    def test_format_search_results_with_notes(self, capsys):
        """Test formatting search results with notes."""
        results = [
            {"type": "note", "id": 2, "title": "Test note", "_query": "test"}
        ]
        format_search_results(results)
        captured = capsys.readouterr()
        assert "NOTES" in captured.out

    def test_format_search_results_with_references(self, capsys):
        """Test formatting search results with references."""
        results = [
            {"type": "reference", "name": "doc", "title": "API Doc", "_query": "api"}
        ]
        format_search_results(results)
        captured = capsys.readouterr()
        assert "REFERENCES" in captured.out
        assert "#doc" in captured.out

    def test_format_search_results_with_preview(self, capsys):
        """Test formatting search results with preview."""
        results = [
            {
                "type": "task",
                "id": 1,
                "title": "Title",
                "preview": "This is a preview text",
                "_query": "test",
            }
        ]
        format_search_results(results)
        captured = capsys.readouterr()
        assert "This is a preview text" in captured.out

    def test_format_search_results_multiple_types(self, capsys):
        """Test formatting search results with multiple types."""
        results = [
            {"type": "task", "id": 1, "title": "Task 1", "_query": "test"},
            {"type": "note", "id": 2, "title": "Note 1", "_query": "test"},
            {"type": "plan", "name": "v1", "title": "Plan 1", "_query": "test"},
        ]
        format_search_results(results)
        captured = capsys.readouterr()
        assert "Found 3 result(s)" in captured.out
        assert "TASKS" in captured.out
        assert "NOTES" in captured.out
        assert "PLANS" in captured.out
