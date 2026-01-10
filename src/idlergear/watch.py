"""Watch mode for IdlerGear - monitors changes and suggests knowledge capture.

Phase 1: One-shot analysis via `idlergear watch check`
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root, get_config_value


@dataclass
class Suggestion:
    """A suggestion for the user/AI to act on."""

    id: str
    category: str  # commit, todo, reference, test, docs
    message: str
    severity: str  # info, warning, action
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "message": self.message,
            "severity": self.severity,
            "context": self.context,
        }


@dataclass
class WatchStatus:
    """Current status from watch analysis."""

    files_changed: int
    lines_added: int
    lines_deleted: int
    minutes_since_commit: int | None
    suggestions: list[Suggestion]

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_changed": self.files_changed,
            "lines_added": self.lines_added,
            "lines_deleted": self.lines_deleted,
            "minutes_since_commit": self.minutes_since_commit,
            "suggestions": [s.to_dict() for s in self.suggestions],
        }


def _run_git(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1, "", "git not available"


def get_git_status(project_root: Path) -> dict[str, Any]:
    """Get current git status with file and line counts."""
    status = {
        "files_changed": 0,
        "files_staged": 0,
        "files_untracked": 0,
        "lines_added": 0,
        "lines_deleted": 0,
        "modified_files": [],
        "staged_files": [],
        "untracked_files": [],
    }

    # Get modified/staged files
    returncode, stdout, _ = _run_git(["status", "--porcelain"], cwd=project_root)
    if returncode != 0:
        return status

    for line in stdout.strip().split("\n"):
        if not line:
            continue
        status_code = line[:2]
        filepath = line[3:]

        if status_code[0] in "MADRC":  # Staged
            status["files_staged"] += 1
            status["staged_files"].append(filepath)
        if status_code[1] in "MADRC":  # Modified (not staged)
            status["files_changed"] += 1
            status["modified_files"].append(filepath)
        if status_code == "??":  # Untracked
            status["files_untracked"] += 1
            status["untracked_files"].append(filepath)

    # Get line counts from diff
    returncode, stdout, _ = _run_git(["diff", "--numstat"], cwd=project_root)
    if returncode == 0:
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                try:
                    added = int(parts[0]) if parts[0] != "-" else 0
                    deleted = int(parts[1]) if parts[1] != "-" else 0
                    status["lines_added"] += added
                    status["lines_deleted"] += deleted
                except ValueError:
                    pass

    # Also check staged diff
    returncode, stdout, _ = _run_git(
        ["diff", "--cached", "--numstat"], cwd=project_root
    )
    if returncode == 0:
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                try:
                    added = int(parts[0]) if parts[0] != "-" else 0
                    deleted = int(parts[1]) if parts[1] != "-" else 0
                    status["lines_added"] += added
                    status["lines_deleted"] += deleted
                except ValueError:
                    pass

    return status


def get_minutes_since_last_commit(project_root: Path) -> int | None:
    """Get minutes since the last commit."""
    returncode, stdout, _ = _run_git(["log", "-1", "--format=%ct"], cwd=project_root)
    if returncode != 0 or not stdout.strip():
        return None

    try:
        timestamp = int(stdout.strip())
        commit_time = datetime.fromtimestamp(timestamp)
        delta = datetime.now() - commit_time
        return int(delta.total_seconds() / 60)
    except (ValueError, OSError):
        return None


def scan_diff_for_todos(project_root: Path) -> list[dict[str, Any]]:
    """Scan the current diff for TODO/FIXME/HACK comments."""
    todos = []

    # Get the diff (both staged and unstaged)
    returncode, stdout, _ = _run_git(["diff", "HEAD"], cwd=project_root)
    if returncode != 0:
        # Try just unstaged diff
        returncode, stdout, _ = _run_git(["diff"], cwd=project_root)
        if returncode != 0:
            return todos

    # Patterns to look for
    patterns = [
        r"^\+.*(?://|#|/\*)\s*(TODO|FIXME|HACK|XXX):\s*(.+)",
        r"^\+.*<!--\s*(TODO|FIXME):\s*(.+?)-->",
    ]

    current_file = None
    for line in stdout.split("\n"):
        # Track current file
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue

        # Check for TODO patterns in added lines
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                todos.append(
                    {
                        "file": current_file,
                        "type": match.group(1).upper(),
                        "text": match.group(2).strip(),
                        "line": line[1:].strip(),  # Remove the + prefix
                    }
                )
                break

    return todos


def check_reference_staleness(project_root: Path) -> list[dict[str, Any]]:
    """Check if any references are stale compared to related code files."""
    stale = []

    # Get threshold from config (default: 7 days)
    try:
        threshold_days = int(get_config_value("watch.staleness_days") or 7)
    except (ValueError, TypeError):
        threshold_days = 7

    idlergear_dir = project_root / ".idlergear"
    wiki_dir = idlergear_dir / "wiki"
    reference_dir = idlergear_dir / "reference"  # Legacy

    # Check both directories
    for ref_dir in [wiki_dir, reference_dir]:
        if not ref_dir.exists():
            continue

        for ref_file in ref_dir.glob("*.md"):
            ref_mtime = datetime.fromtimestamp(ref_file.stat().st_mtime)
            age_days = (datetime.now() - ref_mtime).days

            if age_days > threshold_days:
                # Check if there are recent changes to potentially related code
                ref_name = ref_file.stem.lower().replace("-", " ").replace("_", " ")

                # Simple heuristic: look for files with similar names
                for code_ext in ["*.py", "*.js", "*.ts", "*.go", "*.rs"]:
                    for code_file in project_root.glob(f"**/{code_ext}"):
                        if ".idlergear" in str(code_file) or "venv" in str(code_file):
                            continue
                        code_name = (
                            code_file.stem.lower().replace("-", " ").replace("_", " ")
                        )

                        # Check if names are similar
                        if ref_name in code_name or code_name in ref_name:
                            code_mtime = datetime.fromtimestamp(
                                code_file.stat().st_mtime
                            )
                            if code_mtime > ref_mtime:
                                stale.append(
                                    {
                                        "reference": ref_file.name,
                                        "reference_age_days": age_days,
                                        "related_file": str(
                                            code_file.relative_to(project_root)
                                        ),
                                        "code_updated": code_mtime.isoformat(),
                                    }
                                )
                                break
                    else:
                        continue
                    break

    return stale


def analyze(project_root: Path | None = None) -> WatchStatus:
    """Analyze the project and return suggestions.

    This is the main entry point for `idlergear watch check`.
    """
    if project_root is None:
        project_root = find_idlergear_root()
    if project_root is None:
        return WatchStatus(
            files_changed=0,
            lines_added=0,
            lines_deleted=0,
            minutes_since_commit=None,
            suggestions=[
                Suggestion(
                    id="no-project",
                    category="error",
                    message="Not in an IdlerGear project",
                    severity="warning",
                )
            ],
        )

    suggestions = []
    suggestion_id = 0

    def next_id() -> str:
        nonlocal suggestion_id
        suggestion_id += 1
        return f"s{suggestion_id}"

    # Get git status
    git_status = get_git_status(project_root)
    minutes_since_commit = get_minutes_since_last_commit(project_root)

    # Get thresholds from config
    try:
        file_threshold = int(get_config_value("watch.commit_file_threshold") or 5)
    except (ValueError, TypeError):
        file_threshold = 5

    try:
        line_threshold = int(get_config_value("watch.commit_line_threshold") or 100)
    except (ValueError, TypeError):
        line_threshold = 100

    try:
        time_threshold = int(get_config_value("watch.commit_time_minutes") or 30)
    except (ValueError, TypeError):
        time_threshold = 30

    total_files = git_status["files_changed"] + git_status["files_staged"]
    total_lines = git_status["lines_added"] + git_status["lines_deleted"]

    # Check file threshold
    if total_files >= file_threshold:
        suggestions.append(
            Suggestion(
                id=next_id(),
                category="commit",
                message=f"Consider committing: {total_files} files modified",
                severity="action",
                context={
                    "files": git_status["modified_files"] + git_status["staged_files"]
                },
            )
        )

    # Check line threshold
    if total_lines >= line_threshold:
        suggestions.append(
            Suggestion(
                id=next_id(),
                category="commit",
                message=f"Significant changes (~{total_lines} lines). Consider committing.",
                severity="action",
                context={
                    "lines_added": git_status["lines_added"],
                    "lines_deleted": git_status["lines_deleted"],
                },
            )
        )

    # Check time since commit
    if (
        minutes_since_commit is not None
        and minutes_since_commit >= time_threshold
        and total_files > 0
    ):
        suggestions.append(
            Suggestion(
                id=next_id(),
                category="commit",
                message=f"{minutes_since_commit} min since last commit, {total_files} files changed",
                severity="info",
            )
        )

    # Check for test file changes
    test_files = [
        f
        for f in git_status["modified_files"] + git_status["staged_files"]
        if "test" in f.lower() or f.startswith("tests/")
    ]
    if test_files:
        suggestions.append(
            Suggestion(
                id=next_id(),
                category="test",
                message="Test files changed - run tests before committing?",
                severity="info",
                context={"test_files": test_files},
            )
        )

    # Check for doc changes
    doc_files = [
        f
        for f in git_status["modified_files"] + git_status["staged_files"]
        if f.lower().endswith(".md") or f.startswith("docs/")
    ]
    if doc_files:
        suggestions.append(
            Suggestion(
                id=next_id(),
                category="docs",
                message="Documentation changed - sync to wiki?",
                severity="info",
                context={"doc_files": doc_files},
            )
        )

    # Scan for TODOs in diff
    scan_todos_config = get_config_value("watch.scan_todos")
    scan_todos = str(scan_todos_config).lower() == "true" if scan_todos_config else True
    if scan_todos:
        todos = scan_diff_for_todos(project_root)
        for todo in todos:
            suggestions.append(
                Suggestion(
                    id=next_id(),
                    category="todo",
                    message=f"Found {todo['type']} comment - create task?",
                    severity="action",
                    context=todo,
                )
            )

    # Check reference staleness
    check_staleness_config = get_config_value("watch.check_reference_staleness")
    check_staleness = (
        str(check_staleness_config).lower() == "true"
        if check_staleness_config
        else True
    )
    if check_staleness:
        stale_refs = check_reference_staleness(project_root)
        for stale in stale_refs:
            suggestions.append(
                Suggestion(
                    id=next_id(),
                    category="reference",
                    message=f"Reference '{stale['reference']}' may be stale ({stale['reference_age_days']} days old)",
                    severity="warning",
                    context=stale,
                )
            )

    return WatchStatus(
        files_changed=total_files,
        lines_added=git_status["lines_added"],
        lines_deleted=git_status["lines_deleted"],
        minutes_since_commit=minutes_since_commit,
        suggestions=suggestions,
    )


# ============================================================================
# Stub implementations for CLI backward compatibility
# These will be implemented properly in Phase 2 (continuous watch mode)
# ============================================================================


@dataclass
class WatchConfig:
    """Configuration for watch mode."""

    enabled: bool = False
    debounce: int = 5
    files_changed_threshold: int = 5
    uncommitted_lines_threshold: int = 100
    test_failures_threshold: int = 1
    detect_todos: bool = True
    detect_fixmes: bool = True
    detect_hacks: bool = True

    @classmethod
    def load(cls) -> "WatchConfig":
        """Load config from .idlergear/config.toml."""
        try:
            enabled = get_config_value("watch.enabled")
            debounce = get_config_value("watch.debounce")
            files_threshold = get_config_value("watch.files_changed_threshold")
            lines_threshold = get_config_value("watch.uncommitted_lines_threshold")
            test_threshold = get_config_value("watch.test_failures_threshold")
            detect_todos = get_config_value("watch.detect_todos")
            detect_fixmes = get_config_value("watch.detect_fixmes")
            detect_hacks = get_config_value("watch.detect_hacks")

            return cls(
                enabled=str(enabled).lower() == "true" if enabled else False,
                debounce=int(debounce) if debounce else 5,
                files_changed_threshold=int(files_threshold) if files_threshold else 5,
                uncommitted_lines_threshold=int(lines_threshold)
                if lines_threshold
                else 100,
                test_failures_threshold=int(test_threshold) if test_threshold else 1,
                detect_todos=str(detect_todos).lower() != "false"
                if detect_todos
                else True,
                detect_fixmes=str(detect_fixmes).lower() != "false"
                if detect_fixmes
                else True,
                detect_hacks=str(detect_hacks).lower() != "false"
                if detect_hacks
                else True,
            )
        except Exception:
            return cls()

    def save(self) -> None:
        """Save config to .idlergear/config.json."""
        from idlergear.config import set_config_value

        set_config_value("watch.enabled", str(self.enabled).lower())
        set_config_value("watch.debounce", str(self.debounce))
        set_config_value(
            "watch.files_changed_threshold", str(self.files_changed_threshold)
        )
        set_config_value(
            "watch.uncommitted_lines_threshold", str(self.uncommitted_lines_threshold)
        )
        set_config_value(
            "watch.test_failures_threshold", str(self.test_failures_threshold)
        )
        set_config_value("watch.detect_todos", str(self.detect_todos).lower())
        set_config_value("watch.detect_fixmes", str(self.detect_fixmes).lower())
        set_config_value("watch.detect_hacks", str(self.detect_hacks).lower())


class FileWatcher:
    """File watcher for continuous monitoring (Phase 2)."""

    def __init__(self, config: WatchConfig | None = None):
        self.config = config or WatchConfig.load()

    def watch(self, interval: int = 10) -> None:
        """Start watching for changes. Placeholder for Phase 2."""
        import sys

        print("Watch mode (continuous) is not yet implemented.")
        print("Use 'idlergear watch check' for one-shot analysis.")
        sys.exit(1)


def get_watch_stats() -> dict[str, Any]:
    """Get current watch statistics.

    This is a convenience function that runs analyze() and returns
    a simplified stats dictionary for the CLI.
    """
    status = analyze()

    # Count different types of markers
    todos = 0
    fixmes = 0
    hacks = 0

    for suggestion in status.suggestions:
        if suggestion.category == "todo":
            marker_type = suggestion.context.get("type", "").upper()
            if marker_type == "TODO":
                todos += 1
            elif marker_type == "FIXME":
                fixmes += 1
            elif marker_type in ("HACK", "XXX"):
                hacks += 1

    return {
        "changed_files": status.files_changed,
        "changed_lines": status.lines_added + status.lines_deleted,
        "todos": todos,
        "fixmes": fixmes,
        "hacks": hacks,
        "minutes_since_commit": status.minutes_since_commit,
        "suggestion_count": len(status.suggestions),
    }
