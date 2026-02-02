"""Tests for file annotation storage backend."""

import json
import tempfile
from pathlib import Path

import pytest

from idlergear.file_annotation_storage import FileAnnotationStorage, migrate_from_legacy
from idlergear.file_registry import FileEntry, FileStatus, PatternRule


def test_save_and_load_annotation():
    """Test saving and loading individual annotations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileAnnotationStorage(Path(tmpdir))

        # Create annotation
        entry = FileEntry(
            path="src/api/auth.py",
            status=FileStatus.CURRENT,
            description="Authentication API",
            tags=["api", "auth"],
            components=["AuthController"],
            related_files=["src/models/user.py"],
        )

        # Save
        storage.save_annotation(entry)

        # Verify file exists at correct path
        expected_path = Path(tmpdir) / "src" / "api" / "auth.py.json"
        assert expected_path.exists()

        # Verify content
        with open(expected_path) as f:
            data = json.load(f)
        assert data["path"] == "src/api/auth.py"
        assert data["description"] == "Authentication API"
        assert data["tags"] == ["api", "auth"]
        assert "created" in data
        assert "updated" in data

        # Load
        loaded = storage.load_annotation("src/api/auth.py")
        assert loaded is not None
        assert loaded.path == "src/api/auth.py"
        assert loaded.description == "Authentication API"
        assert loaded.tags == ["api", "auth"]


def test_git_friendly_diffs():
    """Test that changes only affect single files (git-friendly)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileAnnotationStorage(Path(tmpdir))

        # Save two annotations
        entry1 = FileEntry(
            path="file1.py",
            status=FileStatus.CURRENT,
            description="File 1",
        )
        entry2 = FileEntry(
            path="file2.py",
            status=FileStatus.CURRENT,
            description="File 2",
        )

        storage.save_annotation(entry1)
        storage.save_annotation(entry2)

        # Get initial file contents
        file1_path = Path(tmpdir) / "file1.py.json"
        file2_path = Path(tmpdir) / "file2.py.json"

        with open(file1_path) as f:
            file1_before = f.read()
        with open(file2_path) as f:
            file2_before = f.read()

        # Update only file1
        entry1.description = "File 1 UPDATED"
        storage.save_annotation(entry1)

        # Check that file1 changed
        with open(file1_path) as f:
            file1_after = f.read()
        assert file1_after != file1_before
        assert "File 1 UPDATED" in file1_after

        # Check that file2 is UNCHANGED (git-friendly!)
        with open(file2_path) as f:
            file2_after = f.read()
        assert file2_after == file2_before  # No changes!


def test_no_merge_conflicts():
    """Test that different files don't cause merge conflicts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileAnnotationStorage(Path(tmpdir))

        # Simulate two developers annotating different files
        # Developer 1: Annotates auth.py
        dev1_entry = FileEntry(
            path="src/api/auth.py",
            status=FileStatus.CURRENT,
            description="Dev 1's annotation",
        )
        storage.save_annotation(dev1_entry)

        # Developer 2: Annotates routes.py (different file)
        dev2_entry = FileEntry(
            path="src/api/routes.py",
            status=FileStatus.CURRENT,
            description="Dev 2's annotation",
        )
        storage.save_annotation(dev2_entry)

        # Both files exist independently - NO CONFLICTS!
        assert (Path(tmpdir) / "src" / "api" / "auth.py.json").exists()
        assert (Path(tmpdir) / "src" / "api" / "routes.py.json").exists()

        # In git, this would be:
        # - Dev 1 modifies: src/api/auth.py.json
        # - Dev 2 modifies: src/api/routes.py.json
        # = Zero merge conflicts!


def test_list_annotations():
    """Test listing all annotations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileAnnotationStorage(Path(tmpdir))

        # Create multiple annotations
        entries = [
            FileEntry(path="src/api/auth.py", status=FileStatus.CURRENT),
            FileEntry(path="src/models/user.py", status=FileStatus.CURRENT),
            FileEntry(path="tests/test_api.py", status=FileStatus.CURRENT),
        ]

        for entry in entries:
            storage.save_annotation(entry)

        # List all
        loaded = storage.list_annotations()
        assert len(loaded) == 3

        paths = {e.path for e in loaded}
        assert paths == {"src/api/auth.py", "src/models/user.py", "tests/test_api.py"}


def test_delete_annotation():
    """Test deleting annotations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileAnnotationStorage(Path(tmpdir))

        # Create annotation
        entry = FileEntry(path="src/api/auth.py", status=FileStatus.CURRENT)
        storage.save_annotation(entry)

        # Verify exists
        assert storage.load_annotation("src/api/auth.py") is not None

        # Delete
        result = storage.delete_annotation("src/api/auth.py")
        assert result is True

        # Verify deleted
        assert storage.load_annotation("src/api/auth.py") is None

        # Delete non-existent
        result = storage.delete_annotation("nonexistent.py")
        assert result is False


def test_migrate_from_legacy():
    """Test migration from legacy single-file format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create legacy file
        legacy_path = tmpdir / "file_registry.json"
        legacy_data = {
            "files": {
                "file1.py": {
                    "status": "current",
                    "description": "File 1",
                    "tags": ["test"],
                    "components": [],
                    "related_files": [],
                    "reason": None,
                    "deprecated_at": None,
                    "current_version": None,
                    "replaces": [],
                    "deprecated_versions": [],
                    "metadata": {},
                },
                "file2.py": {
                    "status": "deprecated",
                    "description": "File 2",
                    "tags": [],
                    "components": [],
                    "related_files": [],
                    "reason": "Old",
                    "deprecated_at": "2026-01-01T00:00:00Z",
                    "current_version": None,
                    "replaces": [],
                    "deprecated_versions": [],
                    "metadata": {},
                },
            },
            "patterns": {
                "*.bak": {
                    "status": "deprecated",
                    "reason": "Backup file",
                    "metadata": {},
                }
            },
        }

        with open(legacy_path, "w") as f:
            json.dump(legacy_data, f)

        # Migrate
        storage = FileAnnotationStorage(tmpdir / "file_annotations")
        report = migrate_from_legacy(legacy_path, storage, backup=True)

        # Verify migration
        assert report["success"] is True
        assert report["files_migrated"] == 2
        assert report["patterns_migrated"] == 1

        # Verify files were created
        file1 = storage.load_annotation("file1.py")
        assert file1 is not None
        assert file1.description == "File 1"
        assert file1.tags == ["test"]

        file2 = storage.load_annotation("file2.py")
        assert file2 is not None
        assert file2.status == FileStatus.DEPRECATED
        assert file2.reason == "Old"

        # Verify patterns
        patterns = storage.load_patterns()
        assert "*.bak" in patterns
        assert patterns["*.bak"].status == FileStatus.DEPRECATED

        # Verify backup was created
        backup_path = tmpdir / "file_registry.json.backup"
        assert backup_path.exists()


def test_scalability():
    """Test that storage scales to thousands of files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileAnnotationStorage(Path(tmpdir))

        # Create 1000 annotations
        num_files = 1000
        for i in range(num_files):
            entry = FileEntry(
                path=f"src/file_{i}.py",
                status=FileStatus.CURRENT,
                description=f"File {i}",
            )
            storage.save_annotation(entry)

        # List all (should be fast - no monolithic file to load)
        annotations = storage.list_annotations()
        assert len(annotations) == num_files

        # Update one file (should only touch one file, not all 1000)
        entry = storage.load_annotation("src/file_500.py")
        entry.description = "UPDATED"
        storage.save_annotation(entry)

        # Verify only that file changed
        updated = storage.load_annotation("src/file_500.py")
        assert updated.description == "UPDATED"
