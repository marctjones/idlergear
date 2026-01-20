"""Tests for file registry."""

import json
import tempfile
from pathlib import Path

import pytest

from idlergear.file_registry import FileEntry, FileRegistry, FileStatus, PatternRule


def test_file_status_enum():
    """Test FileStatus enum."""
    assert FileStatus.CURRENT.value == "current"
    assert FileStatus.DEPRECATED.value == "deprecated"
    assert FileStatus.ARCHIVED.value == "archived"
    assert FileStatus.PROBLEMATIC.value == "problematic"


def test_file_entry_to_dict():
    """Test FileEntry serialization."""
    entry = FileEntry(
        path="data.csv",
        status=FileStatus.DEPRECATED,
        reason="Old schema",
        current_version="data_v2.csv",
    )

    data = entry.to_dict()
    assert data["status"] == "deprecated"
    assert data["reason"] == "Old schema"
    assert data["current_version"] == "data_v2.csv"


def test_file_entry_from_dict():
    """Test FileEntry deserialization."""
    data = {
        "status": "deprecated",
        "reason": "Old schema",
        "current_version": "data_v2.csv",
        "replaces": ["data_v1.csv"],
    }

    entry = FileEntry.from_dict("data.csv", data)
    assert entry.path == "data.csv"
    assert entry.status == FileStatus.DEPRECATED
    assert entry.reason == "Old schema"
    assert entry.current_version == "data_v2.csv"
    assert entry.replaces == ["data_v1.csv"]


def test_pattern_rule_matches():
    """Test pattern matching."""
    rule = PatternRule(pattern="*.bak", status=FileStatus.DEPRECATED)

    assert rule.matches("file.bak")
    assert rule.matches("dir/file.bak")
    assert not rule.matches("file.txt")


def test_pattern_rule_glob_patterns():
    """Test various glob patterns."""
    # Wildcard without / matches basename anywhere
    rule = PatternRule(pattern="*.py", status=FileStatus.CURRENT)
    assert rule.matches("test.py")
    assert rule.matches("dir/test.py")  # Matches anywhere due to no /
    assert not rule.matches("test.txt")

    # Recursive wildcard
    rule = PatternRule(pattern="archive/**/*", status=FileStatus.ARCHIVED)
    assert rule.matches("archive/old.csv")
    assert rule.matches("archive/deep/path/file.txt")
    assert not rule.matches("other/file.txt")

    # Question mark (no /, so matches anywhere)
    rule = PatternRule(pattern="file?.txt", status=FileStatus.CURRENT)
    assert rule.matches("file1.txt")
    assert rule.matches("dir/fileX.txt")  # Matches anywhere due to no /
    assert not rule.matches("file12.txt")


def test_file_registry_init():
    """Test FileRegistry initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        assert registry.registry_path == registry_path
        assert registry.files == {}
        assert registry.patterns == {}


def test_file_registry_register_file():
    """Test registering a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        registry.register_file("data.csv", FileStatus.CURRENT)

        assert "data.csv" in registry.files
        assert registry.files["data.csv"].status == FileStatus.CURRENT


def test_file_registry_deprecate_file():
    """Test deprecating a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        registry.deprecate_file(
            "data.csv", successor="data_v2.csv", reason="Old schema"
        )

        assert "data.csv" in registry.files
        entry = registry.files["data.csv"]
        assert entry.status == FileStatus.DEPRECATED
        assert entry.current_version == "data_v2.csv"
        assert entry.reason == "Old schema"
        assert entry.deprecated_at is not None


def test_file_registry_add_pattern():
    """Test adding pattern rules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        registry.add_pattern("*.bak", FileStatus.DEPRECATED, reason="Backup files")

        assert "*.bak" in registry.patterns
        assert registry.patterns["*.bak"].status == FileStatus.DEPRECATED


def test_file_registry_get_status():
    """Test getting file status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        # Register specific file
        registry.register_file("specific.txt", FileStatus.CURRENT)

        # Add pattern
        registry.add_pattern("*.bak", FileStatus.DEPRECATED)

        # Test exact match
        assert registry.get_status("specific.txt") == FileStatus.CURRENT

        # Test pattern match
        assert registry.get_status("file.bak") == FileStatus.DEPRECATED

        # Test no match
        assert registry.get_status("unknown.txt") is None


def test_file_registry_get_current_version():
    """Test getting current version."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        registry.deprecate_file("data.csv", successor="data_v2.csv")

        assert registry.get_current_version("data.csv") == "data_v2.csv"
        assert registry.get_current_version("unknown.csv") is None


def test_file_registry_get_reason():
    """Test getting status reason."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        registry.deprecate_file("data.csv", reason="Old schema")
        registry.add_pattern("*.bak", FileStatus.DEPRECATED, reason="Backup files")

        # From specific file
        assert registry.get_reason("data.csv") == "Old schema"

        # From pattern
        assert registry.get_reason("file.bak") == "Backup files"

        # No reason
        assert registry.get_reason("unknown.txt") is None


def test_file_registry_list_files():
    """Test listing files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        registry.register_file("current.txt", FileStatus.CURRENT)
        registry.deprecate_file("deprecated.txt", reason="Old")
        registry.register_file("archived.txt", FileStatus.ARCHIVED)

        # List all
        all_files = registry.list_files()
        assert len(all_files) == 3

        # Filter by status
        deprecated = registry.list_files(FileStatus.DEPRECATED)
        assert len(deprecated) == 1
        assert deprecated[0].path == "deprecated.txt"


def test_file_registry_save_and_load():
    """Test saving and loading registry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"

        # Create and save
        registry1 = FileRegistry(registry_path)
        registry1.register_file("data.csv", FileStatus.CURRENT)
        registry1.deprecate_file("old.csv", successor="data.csv", reason="Old")
        registry1.add_pattern("*.bak", FileStatus.DEPRECATED)
        registry1.save()

        # Load in new instance
        registry2 = FileRegistry(registry_path)

        assert "data.csv" in registry2.files
        assert "old.csv" in registry2.files
        assert "*.bak" in registry2.patterns
        assert registry2.files["old.csv"].current_version == "data.csv"


def test_file_registry_unregister():
    """Test unregistering files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        registry.register_file("test.txt", FileStatus.CURRENT)
        assert "test.txt" in registry.files

        # Unregister existing file
        assert registry.unregister("test.txt") is True
        assert "test.txt" not in registry.files

        # Unregister non-existent file
        assert registry.unregister("unknown.txt") is False


def test_file_registry_remove_pattern():
    """Test removing pattern rules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        registry.add_pattern("*.bak", FileStatus.DEPRECATED)
        assert "*.bak" in registry.patterns

        # Remove existing pattern
        assert registry.remove_pattern("*.bak") is True
        assert "*.bak" not in registry.patterns

        # Remove non-existent pattern
        assert registry.remove_pattern("*.tmp") is False
