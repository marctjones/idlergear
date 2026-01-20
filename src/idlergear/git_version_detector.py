"""
Git-based file version detection.

Detects versioned files (api.py, api_old.py, api_v2.py) using git history
and naming patterns. Used by watch.py to detect version conflicts.
"""

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class VersionedFile:
    """Information about a versioned file."""

    path: str
    base_name: str
    version_suffix: str
    is_current: bool
    last_modified: Optional[datetime] = None
    rename_source: Optional[str] = None


# Regex patterns for version detection
VERSION_PATTERNS = [
    (r"_v(\d+)$", "version_number"),  # file_v2.py
    (r"_old$", "old"),  # file_old.py
    (r"_new$", "new"),  # file_new.py
    (r"_backup$", "backup"),  # file_backup.py
    (r"\.bak$", "bak"),  # file.py.bak
    (r"_(\d{8})$", "timestamp"),  # file_20250119.py
    (r"_copy$", "copy"),  # file_copy.py
    (r"_draft$", "draft"),  # file_draft.py
    (r"_tmp$", "tmp"),  # file_tmp.py
    (r"_temp$", "temp"),  # file_temp.py
]


def _run_git(args: List[str], cwd: Path) -> subprocess.CompletedProcess:
    """
    Run git command.

    Args:
        args: Git command arguments
        cwd: Working directory

    Returns:
        CompletedProcess result
    """
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def detect_renames(repo_path: Path, since: Optional[str] = None) -> List[Tuple[str, str]]:
    """
    Detect file renames using git history.

    Args:
        repo_path: Repository path
        since: Only check commits since this ref/date (e.g., "1 month ago", "HEAD~10")

    Returns:
        List of (old_path, new_path) tuples
    """
    args = [
        "log",
        "--diff-filter=R",
        "--find-renames=80",
        "--name-status",
        "--format=",
    ]

    if since:
        args.append(f"--since={since}")

    result = _run_git(args, repo_path)

    if result.returncode != 0:
        return []

    renames = []
    lines = result.stdout.strip().split("\n")

    for line in lines:
        if not line or not line.startswith("R"):
            continue

        # Format: R100  old_path  new_path
        parts = line.split("\t")
        if len(parts) >= 3:
            old_path = parts[1]
            new_path = parts[2]
            renames.append((old_path, new_path))

    return renames


def match_version_pattern(filepath: str) -> Optional[Tuple[str, str, str]]:
    """
    Check if filepath matches a version pattern.

    Args:
        filepath: File path to check

    Returns:
        (base_name, version_suffix, pattern_type) or None
    """
    path = Path(filepath)
    name_without_ext = path.stem
    extension = path.suffix
    full_name = path.name

    # Special case for .bak extension
    if full_name.endswith(".bak"):
        base_name = full_name[:-4]  # Remove .bak
        return (base_name, ".bak", "bak")

    for pattern, pattern_type in VERSION_PATTERNS:
        match = re.search(pattern, name_without_ext)
        if match:
            # Extract base name (everything before version suffix)
            base_name = name_without_ext[: match.start()]
            version_suffix = name_without_ext[match.start() :]

            return (base_name + extension, version_suffix, pattern_type)

    return None


def group_versioned_files(files: List[str]) -> Dict[str, List[str]]:
    """
    Group files by their base name.

    Args:
        files: List of file paths

    Returns:
        Dict mapping base_name -> [versioned files]

    Example:
        ['api.py', 'api_v2.py', 'api_old.py'] ->
        {'api.py': ['api_v2.py', 'api_old.py']}
    """
    groups: Dict[str, List[str]] = {}

    # First pass: collect all version suffixes
    versioned = {}
    base_names = set()

    for filepath in files:
        result = match_version_pattern(filepath)
        if result:
            base_name, suffix, pattern_type = result
            versioned[filepath] = (base_name, suffix, pattern_type)
            base_names.add(base_name)
        else:
            # File without version suffix might be a base
            base_names.add(filepath)

    # Second pass: group files
    for base_name in base_names:
        related = []
        for filepath in files:
            if filepath == base_name:
                continue

            if filepath in versioned:
                file_base, _, _ = versioned[filepath]
                if file_base == base_name:
                    related.append(filepath)

        if related:
            groups[base_name] = related

    return groups


def identify_current_version(versions: List[str]) -> str:
    """
    Identify which file is the "current" version.

    Heuristics:
    1. File without version suffix = current
    2. Higher version number (_v3 > _v2)
    3. "_new" > base > "_old"
    4. Most recently modified

    Args:
        versions: List of file paths (should include base name)

    Returns:
        Path of current version
    """
    if not versions:
        raise ValueError("No versions provided")

    if len(versions) == 1:
        return versions[0]

    # Separate base from versioned
    base_file = None
    versioned_files = []

    for filepath in versions:
        result = match_version_pattern(filepath)
        if result:
            versioned_files.append((filepath, result))
        else:
            base_file = filepath

    # Heuristic 1: If base file exists and no "_new" suffix, it's current
    has_new_suffix = any(
        pattern_type == "new" for _, (_, _, pattern_type) in versioned_files
    )

    if base_file and not has_new_suffix:
        return base_file

    # Heuristic 2: Check for version numbers
    version_numbered = [
        (path, int(re.search(r"_v(\d+)", path).group(1)))
        for path, (_, suffix, ptype) in versioned_files
        if ptype == "version_number"
    ]

    if version_numbered:
        # Return highest version number
        return max(version_numbered, key=lambda x: x[1])[0]

    # Heuristic 3: "_new" suffix is current
    if has_new_suffix:
        for path, (_, _, ptype) in versioned_files:
            if ptype == "new":
                return path

    # Heuristic 4: Fall back to base file if exists
    if base_file:
        return base_file

    # Heuristic 5: Return first versioned file (arbitrary)
    return versioned_files[0][0] if versioned_files else versions[0]


def detect_versioned_files(
    repo_path: Path, include_renames: bool = True
) -> Dict[str, List[VersionedFile]]:
    """
    Detect all versioned files in repository.

    Args:
        repo_path: Repository path
        include_renames: Include git rename history

    Returns:
        Dict mapping base_name -> [VersionedFile objects]
    """
    # Get all files in repository
    result = _run_git(["ls-files"], repo_path)
    if result.returncode != 0:
        return {}

    all_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]

    # Group by version patterns
    groups = group_versioned_files(all_files)

    # Build VersionedFile objects
    versioned_groups: Dict[str, List[VersionedFile]] = {}

    for base_name, related_files in groups.items():
        all_versions = [base_name] + related_files
        current = identify_current_version(all_versions)

        version_objects = []

        for filepath in all_versions:
            result = match_version_pattern(filepath)
            if result:
                _, suffix, _ = result
            else:
                suffix = ""

            version_objects.append(
                VersionedFile(
                    path=filepath,
                    base_name=base_name,
                    version_suffix=suffix,
                    is_current=(filepath == current),
                )
            )

        versioned_groups[base_name] = version_objects

    # Optionally add rename information
    if include_renames:
        renames = detect_renames(repo_path)
        for old_path, new_path in renames:
            # Find if this is a version relationship
            for base_name, versions in versioned_groups.items():
                for version in versions:
                    if version.path == new_path:
                        version.rename_source = old_path

    return versioned_groups


def get_stale_versions(
    versioned_groups: Dict[str, List[VersionedFile]]
) -> List[VersionedFile]:
    """
    Get list of stale (non-current) versioned files.

    Args:
        versioned_groups: Output from detect_versioned_files()

    Returns:
        List of stale VersionedFile objects
    """
    stale = []

    for base_name, versions in versioned_groups.items():
        for version in versions:
            if not version.is_current:
                stale.append(version)

    return stale
