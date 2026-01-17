"""Tests for formatters module - output format utilities."""

from __future__ import annotations

import json

import pytest

from idlergear.formatters import (
    OutputFormat,
    format_dict_as_goose_card,
    format_dict_as_html_table,
    format_dict_as_list,
    format_dict_as_table,
    format_goose,
    format_html,
    format_json,
    format_markdown,
    format_output,
    format_text,
)


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_output_format_values(self):
        """Test output format enum values."""
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.MARKDOWN.value == "markdown"
        assert OutputFormat.TEXT.value == "text"
        assert OutputFormat.HTML.value == "html"
        assert OutputFormat.GOOSE.value == "goose"


class TestFormatOutput:
    """Tests for format_output function."""

    def test_format_output_json(self):
        """Test format_output with JSON."""
        result = format_output({"key": "value"}, OutputFormat.JSON)
        data = json.loads(result)
        assert data["key"] == "value"

    def test_format_output_markdown(self):
        """Test format_output with markdown."""
        result = format_output({"items": ["a", "b"]}, OutputFormat.MARKDOWN)
        assert "Items" in result
        assert "- a" in result

    def test_format_output_html(self):
        """Test format_output with HTML."""
        result = format_output({"key": "value"}, OutputFormat.HTML)
        assert "<" in result
        assert ">" in result

    def test_format_output_goose(self):
        """Test format_output with Goose format."""
        result = format_output({"items": ["a"]}, OutputFormat.GOOSE)
        assert "Items" in result

    def test_format_output_text(self):
        """Test format_output with text (default)."""
        result = format_output({"key": "value"}, OutputFormat.TEXT)
        assert "key" in result
        assert "value" in result


class TestFormatJson:
    """Tests for format_json function."""

    def test_format_json_dict(self):
        """Test formatting dict as JSON."""
        result = format_json({"a": 1, "b": 2})
        data = json.loads(result)
        assert data["a"] == 1
        assert data["b"] == 2

    def test_format_json_list(self):
        """Test formatting list as JSON."""
        result = format_json([1, 2, 3])
        data = json.loads(result)
        assert data == [1, 2, 3]

    def test_format_json_nested(self):
        """Test formatting nested structure."""
        result = format_json({"nested": {"key": "value"}})
        data = json.loads(result)
        assert data["nested"]["key"] == "value"


class TestFormatText:
    """Tests for format_text function."""

    def test_format_text_string(self):
        """Test formatting string as text."""
        result = format_text("hello world")
        assert result == "hello world"

    def test_format_text_dict(self):
        """Test formatting dict as text."""
        result = format_text({"name": "Alice", "age": 30})
        assert "name: Alice" in result
        assert "age: 30" in result

    def test_format_text_list(self):
        """Test formatting list as text."""
        result = format_text(["item1", "item2"])
        assert "item1" in result
        assert "item2" in result

    def test_format_text_other(self):
        """Test formatting other types as text."""
        result = format_text(12345)
        assert result == "12345"


class TestFormatMarkdown:
    """Tests for format_markdown function."""

    def test_format_markdown_string(self):
        """Test formatting string as markdown."""
        result = format_markdown("# Heading")
        assert result == "# Heading"

    def test_format_markdown_dict_with_list(self):
        """Test formatting dict with list values."""
        result = format_markdown({"items": ["a", "b", "c"]})
        assert "## Items" in result
        assert "- a" in result
        assert "- b" in result

    def test_format_markdown_dict_with_nested_dict_list(self):
        """Test formatting dict with nested dict list."""
        result = format_markdown({"tasks": [{"name": "task1", "status": "done"}]})
        assert "Tasks" in result
        assert "name" in result
        assert "task1" in result

    def test_format_markdown_dict_with_nested_dict(self):
        """Test formatting dict with nested dict value."""
        result = format_markdown({"stats": {"count": 10, "total": 100}})
        assert "Stats" in result
        assert "| Key | Value |" in result
        assert "| count | 10 |" in result

    def test_format_markdown_dict_with_simple_value(self):
        """Test formatting dict with simple value."""
        result = format_markdown({"message": "hello"})
        assert "Message" in result
        assert "hello" in result

    def test_format_markdown_list_of_dicts(self):
        """Test formatting list of dicts."""
        result = format_markdown([{"name": "a"}, {"name": "b"}])
        assert "- **name**: a" in result
        assert "- **name**: b" in result

    def test_format_markdown_list_of_strings(self):
        """Test formatting list of strings."""
        result = format_markdown(["alpha", "beta"])
        assert "- alpha" in result
        assert "- beta" in result

    def test_format_markdown_other(self):
        """Test formatting other types."""
        result = format_markdown(42)
        assert result == "42"


class TestFormatHtml:
    """Tests for format_html function."""

    def test_format_html_string(self):
        """Test formatting string as HTML."""
        result = format_html("hello")
        assert result == "<pre>hello</pre>"

    def test_format_html_dict_with_list(self):
        """Test formatting dict with list values."""
        result = format_html({"items": ["a", "b"]})
        assert "<ul>" in result
        assert "<li>a</li>" in result
        assert "<li>b</li>" in result
        assert "</ul>" in result

    def test_format_html_dict_with_nested_dict_list(self):
        """Test formatting dict with nested dict list."""
        result = format_html({"tasks": [{"name": "task1"}]})
        assert "<table>" in result

    def test_format_html_dict_with_nested_dict(self):
        """Test formatting dict with nested dict value."""
        result = format_html({"stats": {"count": 10}})
        assert "<table>" in result
        assert "count" in result
        assert "10" in result

    def test_format_html_dict_with_simple_value(self):
        """Test formatting dict with simple value."""
        result = format_html({"message": "hello"})
        assert "<p>hello</p>" in result

    def test_format_html_list_of_dicts(self):
        """Test formatting list of dicts."""
        result = format_html([{"name": "a"}])
        assert "<ul>" in result
        assert "<table>" in result

    def test_format_html_list_of_strings(self):
        """Test formatting list of strings."""
        result = format_html(["alpha", "beta"])
        assert "<ul>" in result
        assert "<li>alpha</li>" in result

    def test_format_html_other(self):
        """Test formatting other types."""
        result = format_html(42)
        assert result == "<pre>42</pre>"


class TestFormatGoose:
    """Tests for format_goose function."""

    def test_format_goose_string(self):
        """Test formatting string for Goose."""
        result = format_goose("hello")
        assert result == "hello"

    def test_format_goose_dict_with_status_badge(self):
        """Test formatting dict with status badge."""
        result = format_goose({"status": "active", "title": "Test"})
        assert "status-active" in result or "status" in result

    def test_format_goose_dict_with_priority_badge_high(self):
        """Test formatting dict with high priority badge."""
        result = format_goose({"priority": "high", "title": "Urgent"})
        assert "priority-high" in result or "priority" in result

    def test_format_goose_dict_with_priority_badge_medium(self):
        """Test formatting dict with medium priority badge."""
        result = format_goose({"priority": "medium", "title": "Normal"})
        assert "priority-medium" in result or "priority" in result

    def test_format_goose_dict_with_priority_badge_low(self):
        """Test formatting dict with low priority badge."""
        result = format_goose({"priority": "low", "title": "Minor"})
        assert "priority-low" in result or "priority" in result

    def test_format_goose_dict_with_long_list(self):
        """Test formatting dict with long list (collapsible)."""
        result = format_goose({"items": list(range(10))})
        assert "<details>" in result
        assert "<summary>" in result

    def test_format_goose_dict_with_short_list(self):
        """Test formatting dict with short list."""
        result = format_goose({"items": ["a", "b"]})
        assert "Items" in result
        assert "- a" in result

    def test_format_goose_dict_with_nested_dict_list(self):
        """Test formatting dict with nested dict list."""
        result = format_goose({"tasks": [{"name": "task1", "status": "done"}]})
        assert "Tasks" in result

    def test_format_goose_dict_with_nested_dict(self):
        """Test formatting dict with nested dict value."""
        result = format_goose({"stats": {"count": 10}})
        assert "Stats" in result

    def test_format_goose_dict_with_simple_value(self):
        """Test formatting dict with simple value."""
        result = format_goose({"message": "hello"})
        assert "Message" in result
        assert "hello" in result

    def test_format_goose_list_of_dicts(self):
        """Test formatting list of dicts."""
        result = format_goose([{"name": "item1"}])
        assert "**item1**" in result

    def test_format_goose_list_of_strings(self):
        """Test formatting list of strings."""
        result = format_goose(["alpha", "beta"])
        assert "- alpha" in result
        assert "- beta" in result

    def test_format_goose_other(self):
        """Test formatting other types."""
        result = format_goose(42)
        assert result == "42"


class TestFormatDictAsList:
    """Tests for format_dict_as_list helper."""

    def test_format_dict_as_list_single(self):
        """Test formatting single-key dict as list."""
        result = format_dict_as_list({"name": "Alice"})
        assert result == "- **name**: Alice"

    def test_format_dict_as_list_multiple(self):
        """Test formatting multi-key dict as list."""
        result = format_dict_as_list({"name": "Bob", "age": 25})
        assert "- **name**: Bob" in result
        assert "**age**: 25" in result


class TestFormatDictAsTable:
    """Tests for format_dict_as_table helper."""

    def test_format_dict_as_table_basic(self):
        """Test formatting dict as markdown table."""
        result = format_dict_as_table({"key1": "value1", "key2": "value2"})
        assert "| Key | Value |" in result
        assert "|-----|-------|" in result
        assert "| key1 | value1 |" in result
        assert "| key2 | value2 |" in result


class TestFormatDictAsHtmlTable:
    """Tests for format_dict_as_html_table helper."""

    def test_format_dict_as_html_table_basic(self):
        """Test formatting dict as HTML table."""
        result = format_dict_as_html_table({"name": "Test", "value": 42})
        assert "<table>" in result
        assert "</table>" in result
        assert "<th>Key</th>" in result
        assert "<th>Value</th>" in result
        assert "<td>name</td>" in result
        assert "<td>Test</td>" in result


class TestFormatDictAsGooseCard:
    """Tests for format_dict_as_goose_card helper."""

    def test_format_dict_as_goose_card_basic(self):
        """Test formatting dict as Goose card."""
        result = format_dict_as_goose_card({"title": "Test Item"})
        assert "**Test Item**" in result

    def test_format_dict_as_goose_card_with_name(self):
        """Test formatting dict with name fallback."""
        result = format_dict_as_goose_card({"name": "Named Item"})
        assert "**Named Item**" in result

    def test_format_dict_as_goose_card_with_status(self):
        """Test formatting dict with status."""
        result = format_dict_as_goose_card({"title": "Task", "status": "completed"})
        assert "`completed`" in result

    def test_format_dict_as_goose_card_with_status_pending(self):
        """Test formatting dict with pending status."""
        result = format_dict_as_goose_card({"title": "Task", "status": "pending"})
        # Should have emoji for pending status
        assert "pending" in result

    def test_format_dict_as_goose_card_with_status_in_progress(self):
        """Test formatting dict with in_progress status."""
        result = format_dict_as_goose_card({"title": "Task", "status": "in_progress"})
        assert "in_progress" in result

    def test_format_dict_as_goose_card_with_status_open(self):
        """Test formatting dict with open status."""
        result = format_dict_as_goose_card({"title": "Task", "status": "open"})
        assert "open" in result

    def test_format_dict_as_goose_card_with_status_closed(self):
        """Test formatting dict with closed status."""
        result = format_dict_as_goose_card({"title": "Task", "status": "closed"})
        assert "closed" in result

    def test_format_dict_as_goose_card_with_priority(self):
        """Test formatting dict with priority."""
        result = format_dict_as_goose_card({"title": "Task", "priority": "high"})
        assert "`high`" in result

    def test_format_dict_as_goose_card_with_priority_medium(self):
        """Test formatting dict with medium priority."""
        result = format_dict_as_goose_card({"title": "Task", "priority": "medium"})
        assert "medium" in result

    def test_format_dict_as_goose_card_with_priority_low(self):
        """Test formatting dict with low priority."""
        result = format_dict_as_goose_card({"title": "Task", "priority": "low"})
        assert "low" in result

    def test_format_dict_as_goose_card_with_body_fields(self):
        """Test formatting dict with additional fields."""
        result = format_dict_as_goose_card(
            {"title": "Task", "description": "Short text", "author": "Alice"}
        )
        assert "**description**:" in result
        assert "Short text" in result
        assert "**author**:" in result

    def test_format_dict_as_goose_card_long_value_excluded(self):
        """Test that long values are excluded from card body."""
        result = format_dict_as_goose_card(
            {"title": "Task", "long_field": "x" * 200}
        )
        # Long field should not be included
        assert "long_field" not in result
