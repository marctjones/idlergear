"""Tests for vision management."""

from idlergear.vision import get_vision, get_vision_path, set_vision


class TestGetVisionPath:
    """Tests for get_vision_path."""

    def test_get_vision_path(self, temp_project):
        path = get_vision_path()
        assert path is not None
        assert path.name == "VISION.md"
        # Vision is in repo root, not .idlergear
        assert path.parent == temp_project

    def test_get_vision_path_with_project_path(self, temp_project):
        path = get_vision_path(temp_project)
        assert path is not None
        assert str(temp_project) in str(path)


class TestGetVision:
    """Tests for get_vision."""

    def test_get_vision(self, temp_project):
        vision = get_vision()
        assert vision is not None
        # Default vision content from conftest fixture
        assert "Project Vision" in vision

    def test_get_vision_nonexistent(self, temp_project):
        import os

        # Remove vision file
        vision_path = get_vision_path()
        os.unlink(vision_path)

        vision = get_vision()
        assert vision is None


class TestSetVision:
    """Tests for set_vision."""

    def test_set_vision(self, temp_project):
        new_vision = "# New Vision\n\nThis is the updated vision."

        set_vision(new_vision)

        vision = get_vision()
        assert vision == new_vision

    def test_set_vision_overwrites(self, temp_project):
        set_vision("First vision")
        set_vision("Second vision")

        vision = get_vision()
        assert vision == "Second vision"

    def test_set_vision_preserves_formatting(self, temp_project):
        content = """# Vision

## Goals
- Goal 1
- Goal 2

## Non-goals
- Non-goal 1
"""
        set_vision(content)

        vision = get_vision()
        assert vision == content
