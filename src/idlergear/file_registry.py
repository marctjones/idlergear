"""File Registry for tracking file status and deprecation.

The file registry tracks which files are current, deprecated, archived, or problematic.
It prevents AI assistants from accessing outdated files during development sessions.
"""

import json
import re
import time
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

    # Annotation fields (NEW in v0.6.0)
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)

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
            # Annotation fields
            "description": self.description,
            "tags": self.tags,
            "components": self.components,
            "related_files": self.related_files,
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
            # Annotation fields (backward compatible)
            description=data.get("description"),
            tags=data.get("tags", []),
            components=data.get("components", []),
            related_files=data.get("related_files", []),
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
    """Registry for tracking file status and deprecation.

    Storage: Uses one-file-per-annotation for git-friendly diffs and scalability.
    Backward compatible: Auto-migrates from legacy single-file format.

    Performance optimizations:
    - Lazy loading: Annotations loaded on demand
    - TTL-based caching: Status cache expires after 60 seconds
    - Pattern compilation: Regex patterns compiled once and cached
    - Batch operations: Check multiple files in single call
    """

    # Cache TTL in seconds (60s = 1 minute)
    CACHE_TTL = 60

    def __init__(
        self,
        registry_path: Optional[Path] = None,
        lazy_load: bool = True,
        storage_backend: Optional[Any] = None,
    ):
        """Initialize file registry.

        Args:
            registry_path: Legacy path or base directory. Defaults to .idlergear/
            lazy_load: If True, delay loading until first access (default: True)
            storage_backend: Storage backend to use (FileAnnotationStorage).
                           If None, creates default backend.
        """
        # Import here to avoid circular dependency
        from idlergear.file_annotation_storage import FileAnnotationStorage

        # Determine paths
        if registry_path is None:
            base_path = Path.cwd() / ".idlergear"
            legacy_path = base_path / "file_registry.json"
        elif registry_path.name == "file_registry.json":
            # Legacy path: .idlergear/file_registry.json
            legacy_path = registry_path
            base_path = registry_path.parent
        else:
            # Base directory path
            base_path = registry_path
            legacy_path = base_path / "file_registry.json"

        # Create storage backend
        if storage_backend is None:
            storage_backend = FileAnnotationStorage(base_path / "file_annotations")

        self.storage = storage_backend
        self.registry_path = legacy_path  # Keep for backward compatibility (tests expect this)
        self._legacy_path = legacy_path

        # In-memory cache for performance
        self.files: Dict[str, FileEntry] = {}
        self.patterns: Dict[str, PatternRule] = {}
        self._status_cache: Dict[str, tuple[Optional[FileStatus], float]] = {}
        self._event_callbacks: Dict[str, list] = {
            "file_registered": [],
            "file_deprecated": [],
        }
        self._loaded: bool = False
        self._patterns_loaded: bool = False
        self._last_load_time: Optional[float] = None

        # Auto-migrate from legacy format if detected
        if not lazy_load and self._legacy_path and self._legacy_path.exists():
            self._auto_migrate_if_needed()

    def _clear_cache(self) -> None:
        """Clear the status lookup cache."""
        self._status_cache.clear()

    def _auto_migrate_if_needed(self) -> None:
        """Auto-migrate from legacy format if detected."""
        if self._legacy_path and self._legacy_path.exists():
            # Check if migration is needed (legacy file exists, new storage doesn't)
            annotations = self.storage.list_annotations()
            if len(annotations) == 0:
                # Migrate
                from idlergear.file_annotation_storage import migrate_from_legacy
                report = migrate_from_legacy(self._legacy_path, self.storage, backup=True)
                if report["success"]:
                    # Mark as migrated
                    self._loaded = True
                    self._patterns_loaded = True

    def _ensure_loaded(self) -> None:
        """Ensure registry patterns are loaded (lazy loading).

        Note: Individual file annotations are loaded on-demand, not bulk loaded.
        Only patterns need to be loaded upfront.
        """
        if not self._patterns_loaded:
            # Auto-migrate if needed
            if self._legacy_path and self._legacy_path.exists():
                self._auto_migrate_if_needed()

            # Load patterns
            self.patterns = self.storage.load_patterns()
            self._patterns_loaded = True
            self._loaded = True

    def on(self, event: str, callback) -> None:
        """Register a callback for an event.

        Args:
            event: Event name ("file_registered" or "file_deprecated")
            callback: Callable that takes event data as parameter
        """
        if event in self._event_callbacks:
            self._event_callbacks[event].append(callback)

    def _emit(self, event: str, data: Dict[str, Any]) -> None:
        """Emit an event to all registered callbacks.

        Args:
            event: Event name
            data: Event data
        """
        for callback in self._event_callbacks.get(event, []):
            try:
                callback(data)
            except Exception:
                # Don't let callback failures break registry operations
                pass

    def load(self) -> None:
        """Load registry (backward compatibility method).

        Note: With new storage, annotations are loaded on-demand.
        This method now only loads patterns and is called automatically.
        """
        self._ensure_loaded()

    def save(self) -> None:
        """Save registry (backward compatibility method).

        Note: With new storage, annotations are auto-saved individually.
        This method is a no-op but kept for backward compatibility.
        """
        # Patterns are saved automatically by annotate_file, etc.
        # This is a no-op for backward compatibility
        pass

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
        self._ensure_loaded()
        entry = FileEntry(
            path=path,
            status=status,
            reason=reason,
            metadata=metadata or {},
        )

        # Save to storage
        self.storage.save_annotation(entry)

        # Update in-memory cache
        self.files[path] = entry
        self._clear_cache()

        # Emit event
        self._emit(
            "file_registered",
            {
                "path": path,
                "status": status.value,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            },
        )

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
        self._ensure_loaded()
        entry = FileEntry(
            path=path,
            status=FileStatus.DEPRECATED,
            reason=reason,
            deprecated_at=datetime.now().isoformat(),
            current_version=successor,
        )

        # Save to storage
        self.storage.save_annotation(entry)

        # Update in-memory cache
        self.files[path] = entry

        # Update successor's deprecated_versions list
        if successor:
            successor_entry = self.storage.load_annotation(successor)
            if successor_entry:
                if path not in successor_entry.deprecated_versions:
                    successor_entry.deprecated_versions.append(path)
                    self.storage.save_annotation(successor_entry)
                    self.files[successor] = successor_entry

        self._clear_cache()

        # Emit event
        self._emit(
            "file_deprecated",
            {
                "path": path,
                "successor": successor,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            },
        )

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
        self._ensure_loaded()
        rule = PatternRule(pattern=pattern, status=status, reason=reason)
        self.patterns[pattern] = rule

        # Save patterns to storage
        self.storage.save_patterns(self.patterns)

        self._clear_cache()

    def get_status(self, path: str) -> Optional[FileStatus]:
        """Get status of a file.

        Args:
            path: File path to check

        Returns:
            FileStatus if file is registered or matches pattern, None otherwise
        """
        # Ensure registry is loaded
        self._ensure_loaded()

        # Check cache first (with TTL)
        if path in self._status_cache:
            cached_status, timestamp = self._status_cache[path]
            if time.time() - timestamp < self.CACHE_TTL:
                return cached_status

        # Check in-memory cache
        if path in self.files:
            status = self.files[path].status
            self._status_cache[path] = (status, time.time())
            return status

        # Load from storage (lazy load individual file)
        entry = self.storage.load_annotation(path)
        if entry:
            self.files[path] = entry  # Update cache
            status = entry.status
            self._status_cache[path] = (status, time.time())
            return status

        # Check pattern rules
        for rule in self.patterns.values():
            if rule.matches(path):
                status = rule.status
                self._status_cache[path] = (status, time.time())
                return status

        # Cache negative result
        self._status_cache[path] = (None, time.time())
        return None

    def get_status_batch(self, paths: List[str]) -> Dict[str, Optional[FileStatus]]:
        """Get status for multiple files in a single call (batch operation).

        This is more efficient than calling get_status() multiple times as it:
        - Loads registry only once
        - Processes cache checks in batch
        - Minimizes pattern matching overhead

        Args:
            paths: List of file paths to check

        Returns:
            Dictionary mapping file paths to their status (or None if not registered)

        Example:
            >>> registry = FileRegistry()
            >>> statuses = registry.get_status_batch(["file1.csv", "file2.py", "file3.md"])
            >>> print(statuses["file1.csv"])  # FileStatus.DEPRECATED or None
        """
        self._ensure_loaded()

        results = {}
        current_time = time.time()

        for path in paths:
            # Check cache first (with TTL)
            if path in self._status_cache:
                cached_status, timestamp = self._status_cache[path]
                if current_time - timestamp < self.CACHE_TTL:
                    results[path] = cached_status
                    continue

            # Check exact match
            if path in self.files:
                status = self.files[path].status
                self._status_cache[path] = (status, current_time)
                results[path] = status
                continue

            # Check pattern rules
            matched = False
            for rule in self.patterns.values():
                if rule.matches(path):
                    status = rule.status
                    self._status_cache[path] = (status, current_time)
                    results[path] = status
                    matched = True
                    break

            if not matched:
                # Cache negative result
                self._status_cache[path] = (None, current_time)
                results[path] = None

        return results

    def get_entry(self, path: str) -> Optional[FileEntry]:
        """Get full entry for a file.

        Args:
            path: File path

        Returns:
            FileEntry if file is registered, None otherwise
        """
        self._ensure_loaded()

        # Check cache first
        if path in self.files:
            return self.files[path]

        # Load from storage
        entry = self.storage.load_annotation(path)
        if entry:
            # Update cache
            self.files[path] = entry

        return entry

    def get_current_version(self, path: str) -> Optional[str]:
        """Get current version of a deprecated file.

        Args:
            path: File path

        Returns:
            Path to current version, or None
        """
        self._ensure_loaded()
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
        self._ensure_loaded()
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
        self._ensure_loaded()

        # Load all annotations from storage
        entries = self.storage.list_annotations()

        # Update cache
        for entry in entries:
            self.files[entry.path] = entry

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
        self._ensure_loaded()

        # Delete from storage
        result = self.storage.delete_annotation(path)

        # Remove from cache
        if path in self.files:
            del self.files[path]

        self._clear_cache()
        return result

    def remove_pattern(self, pattern: str) -> bool:
        """Remove pattern rule.

        Args:
            pattern: Pattern to remove

        Returns:
            True if pattern was removed, False if not found
        """
        self._ensure_loaded()
        if pattern in self.patterns:
            del self.patterns[pattern]

            # Save patterns to storage
            self.storage.save_patterns(self.patterns)

            self._clear_cache()
            return True
        return False

    # Annotation methods (NEW in v0.6.0)

    def annotate_file(
        self,
        path: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        components: Optional[List[str]] = None,
        related_files: Optional[List[str]] = None,
    ) -> FileEntry:
        """Annotate file with purpose, tags, and components.

        Args:
            path: Path to file
            description: What this file does
            tags: Searchable tags
            components: Key classes/functions in file
            related_files: Related file paths

        Returns:
            Updated or created FileEntry
        """
        self._ensure_loaded()

        # Load existing annotation or create new
        entry = self.storage.load_annotation(path)
        if entry is None:
            entry = FileEntry(path=path, status=FileStatus.CURRENT)

        # Update annotations (only if provided)
        if description is not None:
            entry.description = description
        if tags is not None:
            entry.tags = tags
        if components is not None:
            entry.components = components
        if related_files is not None:
            entry.related_files = related_files

        # Save to storage
        self.storage.save_annotation(entry)

        # Update in-memory cache
        self.files[path] = entry
        self._clear_cache()

        return entry

    def search_files(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        components: Optional[List[str]] = None,
        status: Optional[FileStatus] = None,
    ) -> List[FileEntry]:
        """Search files by description, tags, or components.

        Args:
            query: Full-text search in descriptions (case-insensitive)
            tags: Filter by tags (OR logic - matches if any tag matches)
            components: Filter by component names (OR logic)
            status: Filter by file status

        Returns:
            List of matching FileEntry objects
        """
        self._ensure_loaded()

        # Load all annotations from storage
        all_entries = self.storage.list_annotations()

        # Update cache
        for entry in all_entries:
            self.files[entry.path] = entry

        results = []

        for entry in all_entries:
            # Filter by status
            if status and entry.status != status:
                continue

            # Full-text search in description
            if query:
                if not entry.description:
                    continue
                if query.lower() not in entry.description.lower():
                    continue

            # Filter by tags (OR logic)
            if tags:
                if not entry.tags:
                    continue
                if not any(tag in entry.tags for tag in tags):
                    continue

            # Filter by components (OR logic)
            if components:
                if not entry.components:
                    continue
                if not any(comp in entry.components for comp in components):
                    continue

            results.append(entry)

        return results

    def get_annotation(self, path: str) -> Optional[FileEntry]:
        """Get full annotation for a specific file.

        Args:
            path: Path to file

        Returns:
            FileEntry with annotations, or None if not registered
        """
        self._ensure_loaded()

        # Check cache first
        if path in self.files:
            return self.files[path]

        # Load from storage
        entry = self.storage.load_annotation(path)
        if entry:
            # Update cache
            self.files[path] = entry

        return entry

    def list_tags(self) -> Dict[str, Dict[str, Any]]:
        """List all tags used in annotations with usage counts.

        Returns:
            Dictionary mapping tag names to metadata:
            {
                "tag_name": {
                    "count": 5,
                    "files": ["path1", "path2", ...]
                }
            }
        """
        self._ensure_loaded()

        # Load all annotations from storage
        all_entries = self.storage.list_annotations()

        # Update cache
        for entry in all_entries:
            self.files[entry.path] = entry

        tag_map: Dict[str, Dict[str, Any]] = {}

        for entry in all_entries:
            for tag in entry.tags:
                if tag not in tag_map:
                    tag_map[tag] = {"count": 0, "files": []}
                tag_map[tag]["count"] += 1
                tag_map[tag]["files"].append(entry.path)

        return tag_map

    def audit_project(
        self,
        since_hours: int = 24,
        include_code_scan: bool = False,
    ) -> Dict[str, Any]:
        """Audit project for deprecated file usage.

        Scans:
        1. Access log for recent deprecated file access
        2. (Optional) Code for string references to deprecated files

        Args:
            since_hours: Audit access log for last N hours (default: 24)
            include_code_scan: Include static code analysis (default: False)

        Returns:
            Audit report with accessed files and code references
        """
        from datetime import datetime, timedelta, timezone

        report = {
            "accessed": [],
            "code_references": [],
            "summary": {
                "deprecated_files_accessed": 0,
                "code_references_found": 0,
                "audit_period_hours": since_hours,
                "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        # 1. Check access log
        access_log_path = self.registry_path.parent / "access_log.jsonl"
        if access_log_path.exists():
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=since_hours)
            accessed_files = self._parse_access_log(access_log_path, cutoff_time)

            # Filter for deprecated files only
            for file_path, access_data in accessed_files.items():
                entry = self.files.get(file_path)
                if entry and entry.status == FileStatus.DEPRECATED:
                    report["accessed"].append({
                        "file": file_path,
                        "current_version": entry.current_version,
                        "access_count": access_data["count"],
                        "last_accessed": access_data["last_accessed"],
                        "accessed_by": access_data["agents"],
                        "tools_used": list(access_data["tools"]),
                    })

            report["summary"]["deprecated_files_accessed"] = len(report["accessed"])

        # 2. (Optional) Static code analysis
        if include_code_scan:
            code_refs = self._scan_code_for_deprecated_files()
            report["code_references"] = code_refs
            report["summary"]["code_references_found"] = len(code_refs)

        return report

    def _parse_access_log(
        self,
        log_path: Path,
        cutoff_time: datetime,
    ) -> Dict[str, Dict[str, Any]]:
        """Parse access log and aggregate by file.

        Args:
            log_path: Path to access_log.jsonl
            cutoff_time: Only include entries after this time

        Returns:
            Dictionary mapping file paths to access statistics
        """
        from datetime import datetime

        accessed = {}

        try:
            with open(log_path) as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)

                        # Parse timestamp
                        timestamp_str = entry.get("timestamp")
                        if not timestamp_str:
                            continue

                        try:
                            # Handle ISO format with timezone
                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        except ValueError:
                            continue

                        # Skip if before cutoff
                        if timestamp < cutoff_time:
                            continue

                        file_path = entry.get("file_path")
                        if not file_path:
                            continue

                        # Initialize or update statistics
                        if file_path not in accessed:
                            accessed[file_path] = {
                                "count": 0,
                                "last_accessed": timestamp.isoformat(),
                                "agents": set(),
                                "tools": set(),
                            }

                        accessed[file_path]["count"] += 1

                        # Update last accessed time if more recent
                        if timestamp.isoformat() > accessed[file_path]["last_accessed"]:
                            accessed[file_path]["last_accessed"] = timestamp.isoformat()

                        # Track agents and tools
                        agent_id = entry.get("agent_id", "unknown")
                        accessed[file_path]["agents"].add(agent_id)

                        tool = entry.get("tool", "unknown")
                        accessed[file_path]["tools"].add(tool)

                    except json.JSONDecodeError:
                        continue  # Skip malformed lines

        except FileNotFoundError:
            pass  # Log doesn't exist yet

        # Convert sets to lists for JSON serialization
        for file_data in accessed.values():
            file_data["agents"] = list(file_data["agents"])
            file_data["tools"] = list(file_data["tools"])

        return accessed

    def _scan_code_for_deprecated_files(self) -> List[Dict[str, Any]]:
        """Scan Python files for references to deprecated files.

        Returns:
            List of code references found
        """
        references = []

        # Get list of deprecated files
        deprecated_files = [
            entry.path for entry in self.files.values()
            if entry.status == FileStatus.DEPRECATED
        ]

        if not deprecated_files:
            return references

        # Scan Python files
        project_root = self.registry_path.parent.parent
        for py_file in project_root.glob("**/*.py"):
            # Skip virtual environments, test files, .git
            if any(part in py_file.parts for part in ["venv", ".venv", "env", ".git", ".tox", "__pycache__"]):
                continue

            try:
                content = py_file.read_text()
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    # Check if line contains any deprecated file path
                    for dep_file in deprecated_files:
                        # Look for path in string literals (quoted)
                        if dep_file in line and (f'"{dep_file}"' in line or f"'{dep_file}'" in line):
                            entry = self.files[dep_file]
                            references.append({
                                "file": str(py_file.relative_to(project_root)),
                                "line": line_num,
                                "code": line.strip(),
                                "deprecated_file": dep_file,
                                "current_version": entry.current_version,
                            })

            except (UnicodeDecodeError, PermissionError):
                continue  # Skip files we can't read

        return references
