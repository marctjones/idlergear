"""File annotation storage backend - one file per annotation.

This module provides a storage backend for file annotations that stores
each annotation in a separate JSON file, enabling:
- Git-friendly diffs (only changed annotations show up)
- No merge conflicts (different files = no conflicts)
- Infinite scalability (no monolithic file to load)
- Selective version control (can .gitignore specific directories)
- Consistency with tasks/notes/plans storage pattern
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from idlergear.file_registry import FileEntry, FileStatus, PatternRule


class FileAnnotationStorage:
    """Storage backend for file annotations using one-file-per-annotation.

    Directory structure:
        .idlergear/file_annotations/
            src/
                api/
                    auth.py.json      # Annotation for src/api/auth.py
                    routes.py.json
                models/
                    user.py.json
            tests/
                test_api.py.json
            patterns.json              # Pattern rules (single file)

    Each annotation file contains:
        {
            "path": "src/api/auth.py",
            "status": "current",
            "description": "REST API endpoints",
            "tags": ["api", "auth"],
            "components": ["AuthController"],
            "related_files": ["src/models/user.py"],
            "reason": null,
            "deprecated_at": null,
            "current_version": null,
            "replaces": [],
            "deprecated_versions": [],
            "metadata": {},
            "created": "2026-02-01T20:00:00Z",
            "updated": "2026-02-01T20:00:00Z"
        }
    """

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize storage backend.

        Args:
            base_path: Base directory for annotations.
                      Defaults to .idlergear/file_annotations/
        """
        if base_path is None:
            base_path = Path.cwd() / ".idlergear" / "file_annotations"

        self.base_path = base_path
        self.patterns_file = base_path / "patterns.json"

    def _get_annotation_path(self, file_path: str) -> Path:
        """Get the storage path for a file's annotation.

        Args:
            file_path: Original file path (e.g., "src/api/auth.py")

        Returns:
            Path to annotation file (e.g., ".idlergear/file_annotations/src/api/auth.py.json")
        """
        # Preserve directory structure, add .json extension
        return self.base_path / f"{file_path}.json"

    def save_annotation(self, entry: FileEntry) -> None:
        """Save annotation to individual file.

        Args:
            entry: FileEntry to save
        """
        annotation_path = self._get_annotation_path(entry.path)

        # Create parent directories
        annotation_path.parent.mkdir(parents=True, exist_ok=True)

        # Add timestamps
        data = entry.to_dict()
        data["path"] = entry.path  # Include path in saved data
        now = datetime.now().astimezone().isoformat()

        # Check if file exists to determine if this is create or update
        if annotation_path.exists():
            # Update: preserve created timestamp
            try:
                with open(annotation_path) as f:
                    existing = json.load(f)
                    data["created"] = existing.get("created", now)
            except (json.JSONDecodeError, KeyError):
                data["created"] = now
        else:
            # Create: set created timestamp
            data["created"] = now

        data["updated"] = now

        # Write atomically (write to temp file, then rename)
        temp_path = annotation_path.with_suffix(".json.tmp")
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)

        temp_path.rename(annotation_path)

    def load_annotation(self, file_path: str) -> Optional[FileEntry]:
        """Load annotation from individual file.

        Args:
            file_path: Path to original file

        Returns:
            FileEntry if annotation exists, None otherwise
        """
        annotation_path = self._get_annotation_path(file_path)

        if not annotation_path.exists():
            return None

        try:
            with open(annotation_path) as f:
                data = json.load(f)

            return FileEntry.from_dict(file_path, data)
        except (json.JSONDecodeError, KeyError, ValueError):
            # Corrupted file - log warning and return None
            return None

    def delete_annotation(self, file_path: str) -> bool:
        """Delete annotation file.

        Args:
            file_path: Path to original file

        Returns:
            True if annotation was deleted, False if not found
        """
        annotation_path = self._get_annotation_path(file_path)

        if annotation_path.exists():
            annotation_path.unlink()

            # Clean up empty parent directories
            try:
                parent = annotation_path.parent
                while parent != self.base_path:
                    if not any(parent.iterdir()):
                        parent.rmdir()
                        parent = parent.parent
                    else:
                        break
            except OSError:
                pass  # Directory not empty or other error

            return True

        return False

    def list_annotations(self) -> List[FileEntry]:
        """List all annotations by walking directory tree.

        Returns:
            List of all FileEntry objects
        """
        if not self.base_path.exists():
            return []

        annotations = []

        # Walk directory tree
        for json_file in self.base_path.rglob("*.json"):
            # Skip patterns.json
            if json_file == self.patterns_file:
                continue

            # Extract original file path from annotation path
            # e.g., ".idlergear/file_annotations/src/api/auth.py.json" -> "src/api/auth.py"
            relative = json_file.relative_to(self.base_path)
            file_path = str(relative)[:-5]  # Remove .json extension

            entry = self.load_annotation(file_path)
            if entry:
                annotations.append(entry)

        return annotations

    def save_patterns(self, patterns: Dict[str, PatternRule]) -> None:
        """Save pattern rules to patterns.json.

        Args:
            patterns: Dictionary of pattern rules
        """
        self.base_path.mkdir(parents=True, exist_ok=True)

        data = {
            pattern: rule.to_dict()
            for pattern, rule in patterns.items()
        }

        with open(self.patterns_file, "w") as f:
            json.dump(data, f, indent=2)

    def load_patterns(self) -> Dict[str, PatternRule]:
        """Load pattern rules from patterns.json.

        Returns:
            Dictionary of pattern rules
        """
        if not self.patterns_file.exists():
            return {}

        try:
            with open(self.patterns_file) as f:
                data = json.load(f)

            return {
                pattern: PatternRule.from_dict(pattern, rule_data)
                for pattern, rule_data in data.items()
            }
        except (json.JSONDecodeError, KeyError, ValueError):
            return {}


def migrate_from_legacy(
    legacy_path: Path,
    storage: FileAnnotationStorage,
    backup: bool = True,
) -> Dict[str, Any]:
    """Migrate from legacy single-file registry to new storage.

    Args:
        legacy_path: Path to legacy file_registry.json
        storage: FileAnnotationStorage instance
        backup: Whether to backup legacy file

    Returns:
        Migration report with counts
    """
    if not legacy_path.exists():
        return {
            "success": False,
            "error": "Legacy file not found",
            "files_migrated": 0,
            "patterns_migrated": 0,
        }

    try:
        # Load legacy data
        with open(legacy_path) as f:
            data = json.load(f)

        files_migrated = 0
        patterns_migrated = 0

        # Migrate file entries
        for path, entry_data in data.get("files", {}).items():
            entry = FileEntry.from_dict(path, entry_data)
            storage.save_annotation(entry)
            files_migrated += 1

        # Migrate patterns
        patterns = {}
        for pattern, rule_data in data.get("patterns", {}).items():
            patterns[pattern] = PatternRule.from_dict(pattern, rule_data)
            patterns_migrated += 1

        if patterns:
            storage.save_patterns(patterns)

        # Backup legacy file
        if backup:
            backup_path = legacy_path.with_suffix(".json.backup")
            legacy_path.rename(backup_path)

        return {
            "success": True,
            "files_migrated": files_migrated,
            "patterns_migrated": patterns_migrated,
            "backup_path": str(backup_path) if backup else None,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "files_migrated": 0,
            "patterns_migrated": 0,
        }
