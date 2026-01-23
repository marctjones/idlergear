"""Auto-detection scanner for file registry population.

Scans project for versioned files and suggests registry entries.
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .file_registry import FileStatus


@dataclass
class RegistrySuggestion:
    """Suggested registry entry from auto-detection."""

    file_path: str
    suggested_status: FileStatus
    confidence: str  # "high", "medium", "low"
    reason: str
    current_version: Optional[str] = None
    evidence: List[str] = None

    def __post_init__(self):
        if self.evidence is None:
            self.evidence = []


class FileRegistryScanner:
    """Auto-detect versioned files and suggest registry entries.

    Detection methods:
    1. Git rename history (high confidence)
    2. Filename pattern matching (medium/low confidence)
    3. Directory structure (medium confidence)

    Example:
        >>> scanner = FileRegistryScanner()
        >>> suggestions = scanner.scan()
        >>> for s in suggestions:
        ...     print(f"{s.file_path} -> {s.suggested_status.value} ({s.confidence})")
    """

    # Patterns for version detection
    VERSION_PATTERNS = [
        r".*_v(\d+).*",  # file_v1.txt, file_v2.py
        r".*_(\d+)\.(\d+)\.(\d+).*",  # file_1.2.3.txt
        r".*_old\b.*",  # file_old.txt
        r".*_new\b.*",  # file_new.txt
        r".*_backup\b.*",  # file_backup.txt
        r".*\.bak$",  # file.txt.bak
        r".*_(\d{8}).*",  # file_20260123.csv (timestamped)
        r".*_(\d{4}-\d{2}-\d{2}).*",  # file_2026-01-23.csv
    ]

    # Directories that suggest archived/deprecated status
    ARCHIVE_DIRS = ["archive", "old", "backup", "deprecated", ".bak", "tmp", "temp"]

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize scanner.

        Args:
            project_path: Path to project (defaults to current directory)
        """
        self.project_path = project_path or Path.cwd()
        self._git_renames_cache: Optional[Dict[str, str]] = None

    def scan(
        self,
        min_confidence: str = "low",
        include_git_renames: bool = True,
        include_patterns: bool = True,
        include_directories: bool = True,
    ) -> List[RegistrySuggestion]:
        """Scan project for versioned files.

        Args:
            min_confidence: Minimum confidence level ("high", "medium", "low")
            include_git_renames: Use git rename history
            include_patterns: Use filename pattern matching
            include_directories: Use directory structure

        Returns:
            List of registry suggestions sorted by confidence
        """
        suggestions = []

        # 1. Git rename detection (high confidence)
        if include_git_renames:
            git_suggestions = self._detect_git_renames()
            suggestions.extend(git_suggestions)

        # 2. Filename pattern matching (medium/low confidence)
        if include_patterns:
            pattern_suggestions = self._detect_version_patterns()
            suggestions.extend(pattern_suggestions)

        # 3. Directory structure (medium confidence)
        if include_directories:
            dir_suggestions = self._detect_archived_directories()
            suggestions.extend(dir_suggestions)

        # Filter by minimum confidence
        confidence_order = {"high": 2, "medium": 1, "low": 0}
        min_level = confidence_order.get(min_confidence, 0)
        suggestions = [
            s for s in suggestions
            if confidence_order.get(s.confidence, 0) >= min_level
        ]

        # Deduplicate by file path (keep highest confidence)
        seen = {}
        for suggestion in suggestions:
            if suggestion.file_path not in seen:
                seen[suggestion.file_path] = suggestion
            else:
                # Keep higher confidence suggestion
                existing = seen[suggestion.file_path]
                if confidence_order[suggestion.confidence] > confidence_order[existing.confidence]:
                    seen[suggestion.file_path] = suggestion

        # Sort by confidence (high -> low)
        result = list(seen.values())
        result.sort(key=lambda s: confidence_order[s.confidence], reverse=True)

        return result

    def _detect_git_renames(self) -> List[RegistrySuggestion]:
        """Detect deprecated files from git rename history.

        High confidence: File was explicitly renamed in git.
        """
        suggestions = []

        try:
            # Get rename history
            renames = self._get_git_renames()

            for old_path, new_path in renames.items():
                # Check if old file still exists
                old_file = self.project_path / old_path
                new_file = self.project_path / new_path

                if old_file.exists():
                    # Old file exists after rename -> deprecated
                    suggestions.append(
                        RegistrySuggestion(
                            file_path=old_path,
                            suggested_status=FileStatus.DEPRECATED,
                            confidence="high",
                            reason="Renamed in git history",
                            current_version=new_path,
                            evidence=[
                                f"Git rename: {old_path} -> {new_path}",
                                f"Old file still exists",
                            ],
                        )
                    )

        except Exception as e:
            # Git not available or not a git repo
            pass

        return suggestions

    def _get_git_renames(self) -> Dict[str, str]:
        """Get git rename history.

        Returns:
            Dictionary mapping old paths to new paths
        """
        if self._git_renames_cache is not None:
            return self._git_renames_cache

        renames = {}

        try:
            # Use git log to find renames
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.project_path),
                    "log",
                    "--diff-filter=R",
                    "--summary",
                    "--all",
                    "--format=",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse output for renames
            # Format: " rename path/old.txt => path/new.txt (100%)"
            for line in result.stdout.split("\n"):
                if "rename" in line and "=>" in line:
                    match = re.search(r"rename (.+?) => (.+?) \(\d+%\)", line.strip())
                    if match:
                        old_path = match.group(1).strip()
                        new_path = match.group(2).strip()
                        renames[old_path] = new_path

        except (subprocess.CalledProcessError, FileNotFoundError):
            # Git not available or not a repo
            pass

        self._git_renames_cache = renames
        return renames

    def _detect_version_patterns(self) -> List[RegistrySuggestion]:
        """Detect versioned files from filename patterns.

        Medium/low confidence based on pattern specificity.
        """
        suggestions = []

        # Scan all files in project
        for file_path in self.project_path.rglob("*"):
            # Skip directories
            if file_path.is_dir():
                continue

            # Skip hidden files and common exclusions
            if any(part.startswith(".") for part in file_path.parts):
                continue
            if any(part in file_path.parts for part in ["venv", ".venv", "node_modules", "__pycache__"]):
                continue

            relative_path = str(file_path.relative_to(self.project_path))

            # Check against version patterns
            for pattern in self.VERSION_PATTERNS:
                if re.match(pattern, file_path.name, re.IGNORECASE):
                    suggestion = self._analyze_version_pattern(relative_path, pattern)
                    if suggestion:
                        suggestions.append(suggestion)
                    break  # Only match first pattern

        return suggestions

    def _analyze_version_pattern(
        self,
        file_path: str,
        pattern: str,
    ) -> Optional[RegistrySuggestion]:
        """Analyze a file matching a version pattern.

        Args:
            file_path: Relative file path
            pattern: Regex pattern that matched

        Returns:
            Registry suggestion or None
        """
        file_name = Path(file_path).name

        # High-confidence patterns
        if re.search(r"_old\b", file_name, re.IGNORECASE):
            return RegistrySuggestion(
                file_path=file_path,
                suggested_status=FileStatus.DEPRECATED,
                confidence="medium",
                reason="Filename contains '_old'",
                current_version=self._guess_current_version(file_path, "_old"),
                evidence=[f"Pattern: {pattern}"],
            )

        if re.search(r"_backup\b", file_name, re.IGNORECASE):
            return RegistrySuggestion(
                file_path=file_path,
                suggested_status=FileStatus.ARCHIVED,
                confidence="medium",
                reason="Filename contains '_backup'",
                evidence=[f"Pattern: {pattern}"],
            )

        if file_name.endswith(".bak"):
            return RegistrySuggestion(
                file_path=file_path,
                suggested_status=FileStatus.ARCHIVED,
                confidence="medium",
                reason="Backup file extension (.bak)",
                current_version=file_path.replace(".bak", ""),
                evidence=[f"Pattern: {pattern}"],
            )

        # Version number patterns (lower confidence)
        if re.search(r"_v(\d+)", file_name):
            # Try to find higher version
            current = self._find_highest_version(file_path)
            if current and current != file_path:
                return RegistrySuggestion(
                    file_path=file_path,
                    suggested_status=FileStatus.DEPRECATED,
                    confidence="low",
                    reason="Versioned filename (lower version may exist)",
                    current_version=current,
                    evidence=[f"Pattern: {pattern}", f"Higher version: {current}"],
                )

        # Timestamp patterns
        if re.search(r"_(\d{8})", file_name) or re.search(r"_(\d{4}-\d{2}-\d{2})", file_name):
            return RegistrySuggestion(
                file_path=file_path,
                suggested_status=FileStatus.ARCHIVED,
                confidence="low",
                reason="Timestamped filename",
                evidence=[f"Pattern: {pattern}"],
            )

        return None

    def _guess_current_version(self, old_path: str, suffix: str) -> Optional[str]:
        """Guess the current version by removing version suffix.

        Args:
            old_path: Old file path
            suffix: Suffix to remove (e.g., "_old")

        Returns:
            Guessed current version path or None
        """
        # Remove suffix from filename
        path = Path(old_path)
        name_without_suffix = path.stem.replace(suffix, "")
        current_name = f"{name_without_suffix}{path.suffix}"
        current_path = str(path.parent / current_name)

        # Check if it exists
        full_path = self.project_path / current_path
        if full_path.exists():
            return current_path

        return None

    def _find_highest_version(self, file_path: str) -> Optional[str]:
        """Find highest version of a versioned file.

        Args:
            file_path: Path with version number

        Returns:
            Path to highest version or None
        """
        path = Path(file_path)

        # Extract version number
        match = re.search(r"_v(\d+)", path.stem)
        if not match:
            return None

        current_version = int(match.group(1))

        # Look for higher versions
        base_name = path.stem.replace(f"_v{current_version}", "_v")
        parent = path.parent

        highest = current_version
        highest_path = file_path

        # Check for versions up to current + 10
        for v in range(current_version + 1, current_version + 11):
            candidate_name = f"{base_name}{v}{path.suffix}"
            candidate_path = parent / candidate_name

            if (self.project_path / candidate_path).exists():
                highest = v
                highest_path = str(candidate_path)

        return highest_path if highest > current_version else None

    def _detect_archived_directories(self) -> List[RegistrySuggestion]:
        """Detect files in archive directories.

        Medium confidence: Directory name suggests archived status.
        """
        suggestions = []

        for archive_dir in self.ARCHIVE_DIRS:
            archive_paths = list(self.project_path.glob(f"**/{archive_dir}/**/*"))

            for file_path in archive_paths:
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(self.project_path))

                    suggestions.append(
                        RegistrySuggestion(
                            file_path=relative_path,
                            suggested_status=FileStatus.ARCHIVED,
                            confidence="medium",
                            reason=f"Located in '{archive_dir}/' directory",
                            evidence=[f"Directory: {archive_dir}/"],
                        )
                    )

        return suggestions

    def group_suggestions_by_confidence(
        self,
        suggestions: List[RegistrySuggestion],
    ) -> Dict[str, List[RegistrySuggestion]]:
        """Group suggestions by confidence level.

        Args:
            suggestions: List of suggestions

        Returns:
            Dictionary mapping confidence to suggestions
        """
        groups = {"high": [], "medium": [], "low": []}

        for suggestion in suggestions:
            groups[suggestion.confidence].append(suggestion)

        return groups
