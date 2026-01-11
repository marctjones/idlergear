"""Tests for storage utilities."""

from idlergear.storage import (
    get_next_id,
    parse_frontmatter,
    render_frontmatter,
    slugify,
)


def test_parse_frontmatter():
    """Test parsing YAML frontmatter from markdown."""
    content = """---
title: My Title
state: open
---
This is the body content.
"""
    frontmatter, body = parse_frontmatter(content)

    assert frontmatter["title"] == "My Title"
    assert frontmatter["state"] == "open"
    assert body.strip() == "This is the body content."


def test_parse_frontmatter_no_frontmatter():
    """Test parsing content without frontmatter."""
    content = "Just plain content without frontmatter."
    frontmatter, body = parse_frontmatter(content)

    assert frontmatter == {}
    assert body == content


def test_render_frontmatter():
    """Test rendering frontmatter to markdown."""
    frontmatter = {"title": "Test", "count": 42}
    body = "Body text here."

    result = render_frontmatter(frontmatter, body)

    assert result.startswith("---\n")
    assert "title: Test" in result
    assert "count: 42" in result
    assert result.endswith("Body text here.")


def test_render_frontmatter_empty():
    """Test rendering with empty frontmatter."""
    result = render_frontmatter({}, "Just body")
    assert result == "Just body"


def test_slugify():
    """Test slugifying text."""
    assert slugify("Hello World") == "hello-world"
    assert slugify("Fix Parser Bug!") == "fix-parser-bug"
    assert slugify("  Spaces  ") == "spaces"
    assert slugify("Multiple---Dashes") == "multiple-dashes"


def test_slugify_max_length():
    """Test slugify with max length."""
    long_text = "This is a very long title that should be truncated"
    result = slugify(long_text, max_length=20)

    assert len(result) <= 20
    assert result == "this-is-a-very-long"


def test_get_next_id(temp_project):
    """Test getting next available ID."""

    notes_dir = temp_project / ".idlergear" / "notes"

    # First ID should be 1
    assert get_next_id(notes_dir) == 1

    # Create some files
    (notes_dir / "001.md").write_text("note 1")
    (notes_dir / "002.md").write_text("note 2")

    # Next ID should be 3
    assert get_next_id(notes_dir) == 3
