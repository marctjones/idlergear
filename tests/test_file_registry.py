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

# Annotation tests (NEW in v0.6.0)


def test_file_registry_annotate_file():
    """Test annotating a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        # Annotate new file
        entry = registry.annotate_file(
            "src/api/auth.py",
            description="REST API endpoints for authentication",
            tags=["api", "auth", "jwt"],
            components=["AuthController", "login"],
            related_files=["src/models/user.py"],
        )

        assert entry.path == "src/api/auth.py"
        assert entry.description == "REST API endpoints for authentication"
        assert entry.tags == ["api", "auth", "jwt"]
        assert entry.components == ["AuthController", "login"]
        assert entry.related_files == ["src/models/user.py"]
        assert entry.status == FileStatus.CURRENT  # Default status


def test_file_registry_annotate_existing_file():
    """Test annotating an existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        # Register file first
        registry.register_file("test.py", FileStatus.CURRENT)

        # Annotate it
        entry = registry.annotate_file(
            "test.py",
            description="Test file",
            tags=["test"],
        )

        assert entry.path == "test.py"
        assert entry.description == "Test file"
        assert entry.tags == ["test"]
        assert entry.status == FileStatus.CURRENT  # Preserves existing status


def test_file_registry_annotate_partial():
    """Test annotating with partial fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        # Annotate with only description
        entry = registry.annotate_file("test.py", description="Test file")

        assert entry.description == "Test file"
        assert entry.tags == []
        assert entry.components == []
        assert entry.related_files == []


def test_file_registry_search_files_by_query():
    """Test searching files by description query."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        # Annotate files
        registry.annotate_file(
            "auth.py",
            description="Authentication endpoints for REST API",
            tags=["api", "auth"],
        )
        registry.annotate_file(
            "user.py", description="User model and database operations", tags=["model"]
        )
        registry.annotate_file(
            "payment.py", description="Payment processing API", tags=["api", "payment"]
        )

        # Search by query (case-insensitive)
        results = registry.search_files(query="authentication")
        assert len(results) == 1
        assert results[0].path == "auth.py"

        # Search by different query
        results = registry.search_files(query="API")
        assert len(results) == 2  # auth.py and payment.py


def test_file_registry_search_files_by_tags():
    """Test searching files by tags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        # Annotate files
        registry.annotate_file("auth.py", tags=["api", "auth"])
        registry.annotate_file("user.py", tags=["model", "database"])
        registry.annotate_file("payment.py", tags=["api", "payment"])

        # Search by single tag
        results = registry.search_files(tags=["api"])
        assert len(results) == 2  # auth.py and payment.py

        # Search by multiple tags (OR logic)
        results = registry.search_files(tags=["auth", "payment"])
        assert len(results) == 2


def test_file_registry_search_files_by_components():
    """Test searching files by components."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        # Annotate files
        registry.annotate_file("auth.py", components=["AuthController", "login"])
        registry.annotate_file("user.py", components=["UserModel", "save"])
        registry.annotate_file("payment.py", components=["PaymentService"])

        # Search by component
        results = registry.search_files(components=["AuthController"])
        assert len(results) == 1
        assert results[0].path == "auth.py"

        # Search by multiple components (OR logic)
        results = registry.search_files(components=["UserModel", "PaymentService"])
        assert len(results) == 2


def test_file_registry_search_files_by_status():
    """Test searching files by status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        # Annotate files with different statuses
        registry.annotate_file("current.py", description="Current")
        registry.register_file("current.py", FileStatus.CURRENT)

        registry.annotate_file("deprecated.py", description="Deprecated")
        registry.deprecate_file("deprecated.py", reason="Old")

        # Search by status
        results = registry.search_files(status=FileStatus.CURRENT)
        assert len(results) == 1
        assert results[0].path == "current.py"

        results = registry.search_files(status=FileStatus.DEPRECATED)
        assert len(results) == 1
        assert results[0].path == "deprecated.py"


def test_file_registry_search_files_combined():
    """Test searching files with combined filters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        # Register files first, then annotate
        registry.register_file("auth.py", FileStatus.CURRENT)
        registry.annotate_file(
            "auth.py",
            description="Authentication API",
            tags=["api", "auth"],
        )

        registry.register_file("payment.py", FileStatus.CURRENT)
        registry.annotate_file(
            "payment.py",
            description="Payment API endpoints",
            tags=["api", "payment"],
        )

        registry.deprecate_file("old_auth.py", reason="Deprecated")
        registry.annotate_file(
            "old_auth.py",
            description="Old authentication code",
            tags=["api", "auth"],
        )

        # Search: tags=["api"] AND status=CURRENT
        results = registry.search_files(tags=["api"], status=FileStatus.CURRENT)
        assert len(results) == 2
        assert all(r.status == FileStatus.CURRENT for r in results)

        # Search: query="auth" AND tags=["api"] AND status=CURRENT
        results = registry.search_files(
            query="auth", tags=["api"], status=FileStatus.CURRENT
        )
        assert len(results) == 1
        assert results[0].path == "auth.py"


def test_file_registry_search_files_no_results():
    """Test searching with no matches."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        registry.annotate_file("test.py", description="Test file", tags=["test"])

        # No match
        results = registry.search_files(query="nonexistent")
        assert len(results) == 0

        results = registry.search_files(tags=["nonexistent"])
        assert len(results) == 0


def test_file_registry_get_annotation():
    """Test getting annotation for a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        # Annotate file
        registry.annotate_file(
            "test.py",
            description="Test file",
            tags=["test"],
            components=["TestClass"],
        )

        # Get annotation
        entry = registry.get_annotation("test.py")
        assert entry is not None
        assert entry.path == "test.py"
        assert entry.description == "Test file"
        assert entry.tags == ["test"]
        assert entry.components == ["TestClass"]

        # Get non-existent
        entry = registry.get_annotation("nonexistent.py")
        assert entry is None


def test_file_registry_list_tags():
    """Test listing all tags with usage counts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        # Annotate files with various tags
        registry.annotate_file("auth.py", tags=["api", "auth"])
        registry.annotate_file("user.py", tags=["model", "database"])
        registry.annotate_file("payment.py", tags=["api", "payment"])
        registry.annotate_file("order.py", tags=["api", "model"])

        # List tags
        tag_map = registry.list_tags()

        assert "api" in tag_map
        assert tag_map["api"]["count"] == 3
        assert len(tag_map["api"]["files"]) == 3

        assert "model" in tag_map
        assert tag_map["model"]["count"] == 2

        assert "auth" in tag_map
        assert tag_map["auth"]["count"] == 1

        assert "database" in tag_map
        assert "payment" in tag_map


def test_file_registry_list_tags_empty():
    """Test listing tags when no files annotated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        tag_map = registry.list_tags()
        assert tag_map == {}


def test_file_registry_annotations_persistence():
    """Test that annotations are saved and loaded correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"

        # Create and annotate
        registry1 = FileRegistry(registry_path)
        registry1.annotate_file(
            "test.py",
            description="Test file",
            tags=["test", "unit"],
            components=["TestClass"],
            related_files=["helper.py"],
        )
        registry1.save()

        # Load in new instance
        registry2 = FileRegistry(registry_path)
        entry = registry2.get_annotation("test.py")

        assert entry is not None
        assert entry.description == "Test file"
        assert entry.tags == ["test", "unit"]
        assert entry.components == ["TestClass"]
        assert entry.related_files == ["helper.py"]
