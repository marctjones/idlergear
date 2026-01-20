"""File Registry for tracking file status and deprecation.

The file registry tracks which files are current, deprecated, archived, or problematic.
It prevents AI assistants from accessing outdated files during development sessions.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern


class FileStatus(Enum):
    """Status of a file in the registry."""

    CURRENT = "current"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    PROBLEMATIC = "problematic"


@dataclass
class FileEntry:
    """Entry in the file registry."""

    path: str
    status: FileStatus
    reason: Optional[str] = None
    deprecated_at: Optional[str] = None
    current_version: Optional[str] = None
    replaces: List[str] = field(default_factory=list)
    deprecated_versions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "reason": self.reason,
            "deprecated_at": self.deprecated_at,
            "current_version": self.current_version,
            "replaces": self.replaces,
            "deprecated_versions": self.deprecated_versions,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, path: str, data: Dict[str, Any]) -> "FileEntry":
        """Create from dictionary."""
        return cls(
            path=path,
            status=FileStatus(data.get("status", "current")),
            reason=data.get("reason"),
            deprecated_at=data.get("deprecated_at"),
            current_version=data.get("current_version"),
            replaces=data.get("replaces", []),
            deprecated_versions=data.get("deprecated_versions", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PatternRule:
    """Pattern-based rule for file status."""

    pattern: str
    status: FileStatus
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _compiled_pattern: Optional[Pattern] = field(default=None, init=False, repr=False)

    def matches(self, path: str) -> bool:
        """Check if path matches this pattern."""
        # Lazy compile and cache regex pattern
        if self._compiled_pattern is None:
            regex_pattern = self._glob_to_regex(self.pattern)
            self._compiled_pattern = re.compile(regex_pattern)
        return bool(self._compiled_pattern.match(path))

    def _glob_to_regex(self, pattern: str) -> str:
        """Convert glob pattern to regex.

        Pattern rules:
        - ** matches zero or more path components
        - * matches anything except /
        - ? matches single character
        - Patterns without / match anywhere in the path (basename)
        - Patterns with / match from the start
        """
        # Escape special regex characters except * and ?
        escaped = re.escape(pattern)

        # Handle ** before * to avoid conflicts
        # **/ or /** should match zero or more directories
        regex = escaped.replace(r"\*\*/", "(?:.*/)?")  # **/ matches zero or more dirs
        regex = regex.replace(r"/\*\*", "(?:/.*)?")    # /** matches zero or more dirs
        regex = regex.replace(r"\*\*", ".*")           # ** alone matches everything

        # * matches within path segment (no /)
        regex = regex.replace(r"\*", "[^/]*")

        # ? matches single character
        regex = regex.replace(r"\?", ".")

        # If pattern has no /, match basename anywhere in tree
        if "/" not in pattern:
            return f"^(?:.*/)?{regex}$"

        return f"^{regex}$"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "reason": self.reason,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, pattern: str, data: Dict[str, Any]) -> "PatternRule":
        """Create from dictionary."""
        return cls(
            pattern=pattern,
            status=FileStatus(data.get("status", "deprecated")),
            reason=data.get("reason"),
            metadata=data.get("metadata", {}),
        )


class FileRegistry:
    """Registry for tracking file status and deprecation."""

    def __init__(self, registry_path: Optional[Path] = None):
        """Initialize file registry.

        Args:
            registry_path: Path to registry JSON file. Defaults to .idlergear/file_registry.json
        """
        self.registry_path = registry_path or Path.cwd() / ".idlergear" / "file_registry.json"
        self.files: Dict[str, FileEntry] = {}
        self.patterns: Dict[str, PatternRule] = {}
        self._status_cache: Dict[str, Optional[FileStatus]] = {}

        # Load existing registry if it exists
        if self.registry_path.exists():
            self.load()

    def _clear_cache(self) -> None:
        """Clear the status lookup cache."""
        self._status_cache.clear()

    def load(self) -> None:
        """Load registry from JSON file."""
        if not self.registry_path.exists():
            return

        try:
            with open(self.registry_path) as f:
                data = json.load(f)

            # Load file entries
            self.files = {
                path: FileEntry.from_dict(path, entry)
                for path, entry in data.get("files", {}).items()
            }

            # Load pattern rules
            self.patterns = {
                pattern: PatternRule.from_dict(pattern, rule)
                for pattern, rule in data.get("patterns", {}).items()
            }

            # Clear cache after loading new data
            self._clear_cache()
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise ValueError(f"Failed to load file registry: {e}")

    def save(self) -> None:
        """Save registry to JSON file."""
        # Ensure directory exists
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "files": {path: entry.to_dict() for path, entry in self.files.items()},
            "patterns": {
                pattern: rule.to_dict() for pattern, rule in self.patterns.items()
            },
        }

        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2)

    def register_file(
        self,
        path: str,
        status: FileStatus,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a file with explicit status.

        Args:
            path: File path (relative to project root)
            status: File status
            reason: Optional reason for status
            metadata: Optional metadata
        """
        entry = FileEntry(
            path=path,
            status=status,
            reason=reason,
            metadata=metadata or {},
        )
        self.files[path] = entry
        self._clear_cache()
        self.save()

    def deprecate_file(
        self,
        path: str,
        successor: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Mark a file as deprecated.

        Args:
            path: File to deprecate
            successor: Optional current version to use instead
            reason: Reason for deprecation
        """
        entry = FileEntry(
            path=path,
            status=FileStatus.DEPRECATED,
            reason=reason,
            deprecated_at=datetime.now().isoformat(),
            current_version=successor,
        )
        self.files[path] = entry

        # Update successor's deprecated_versions list
        if successor and successor in self.files:
            if path not in self.files[successor].deprecated_versions:
                self.files[successor].deprecated_versions.append(path)

        self._clear_cache()
        self.save()

    def add_pattern(
        self,
        pattern: str,
        status: FileStatus,
        reason: Optional[str] = None,
    ) -> None:
        """Add a pattern-based rule.

        Args:
            pattern: Glob pattern (e.g., "*.bak", "archive/**/*")
            status: Status to assign to matching files
            reason: Reason for status
        """
        rule = PatternRule(pattern=pattern, status=status, reason=reason)
        self.patterns[pattern] = rule
        self._clear_cache()
        self.save()

    def get_status(self, path: str) -> Optional[FileStatus]:
        """Get status of a file.

        Args:
            path: File path to check

        Returns:
            FileStatus if file is registered or matches pattern, None otherwise
        """
        # Check cache first
        if path in self._status_cache:
            return self._status_cache[path]

        # Check exact match first
        if path in self.files:
            status = self.files[path].status
            self._status_cache[path] = status
            return status

        # Check pattern rules
        for rule in self.patterns.values():
            if rule.matches(path):
                status = rule.status
                self._status_cache[path] = status
                return status

        # Cache negative result
        self._status_cache[path] = None
        return None

    def get_entry(self, path: str) -> Optional[FileEntry]:
        """Get full entry for a file.

        Args:
            path: File path

        Returns:
            FileEntry if file is registered, None otherwise
        """
        return self.files.get(path)

    def get_current_version(self, path: str) -> Optional[str]:
        """Get current version of a deprecated file.

        Args:
            path: File path

        Returns:
            Path to current version, or None
        """
        entry = self.files.get(path)
        if entry:
            return entry.current_version
        return None

    def get_reason(self, path: str) -> Optional[str]:
        """Get reason for file status.

        Args:
            path: File path

        Returns:
            Reason string, or None
        """
        # Check exact match
        entry = self.files.get(path)
        if entry:
            return entry.reason

        # Check pattern rules
        for rule in self.patterns.values():
            if rule.matches(path):
                return rule.reason

        return None

    def list_files(
        self, status_filter: Optional[FileStatus] = None
    ) -> List[FileEntry]:
        """List all registered files.

        Args:
            status_filter: Optional status to filter by

        Returns:
            List of file entries
        """
        entries = list(self.files.values())

        if status_filter:
            entries = [e for e in entries if e.status == status_filter]

        return sorted(entries, key=lambda e: e.path)

    def unregister(self, path: str) -> bool:
        """Remove file from registry.

        Args:
            path: File path to remove

        Returns:
            True if file was removed, False if not found
        """
        if path in self.files:
            del self.files[path]
            self._clear_cache()
            self.save()
            return True
        return False

    def remove_pattern(self, pattern: str) -> bool:
        """Remove pattern rule.

        Args:
            pattern: Pattern to remove

        Returns:
            True if pattern was removed, False if not found
        """
        if pattern in self.patterns:
            del self.patterns[pattern]
            self._clear_cache()
            self.save()
            return True
        return False
