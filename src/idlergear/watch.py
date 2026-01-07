"""
Watch mode for proactive knowledge capture.

Monitors file system changes and provides smart prompts for:
- Committing changes
- Creating tasks from TODO comments
- Creating bugs from test failures
- Detecting documentation drift
"""

import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from .config import get_config_value, set_config_value


@dataclass
class WatchConfig:
    """Watch mode configuration."""

    enabled: bool = False
    debounce: int = 30  # seconds
    files_changed_threshold: int = 5
    uncommitted_lines_threshold: int = 100
    test_failures_threshold: int = 1
    detect_todos: bool = True
    detect_fixmes: bool = True
    detect_hacks: bool = True

    @classmethod
    def load(cls) -> "WatchConfig":
        """Load watch configuration from config."""
        return cls(
            enabled=(get_config_value("watch.enabled") or "false") == "true",
            debounce=int(get_config_value("watch.debounce") or "30"),
            files_changed_threshold=int(
                get_config_value("watch.thresholds.files_changed") or "5"
            ),
            uncommitted_lines_threshold=int(
                get_config_value("watch.thresholds.uncommitted_lines") or "100"
            ),
            test_failures_threshold=int(
                get_config_value("watch.thresholds.test_failures") or "1"
            ),
            detect_todos=(get_config_value("watch.detect_todos") or "true") == "true",
            detect_fixmes=(get_config_value("watch.detect_fixmes") or "true") == "true",
            detect_hacks=(get_config_value("watch.detect_hacks") or "true") == "true",
        )

    def save(self) -> None:
        """Save watch configuration to config."""
        set_config_value("watch.enabled", str(self.enabled).lower())
        set_config_value("watch.debounce", str(self.debounce))
        set_config_value("watch.thresholds.files_changed", str(self.files_changed_threshold))
        set_config_value("watch.thresholds.uncommitted_lines", str(self.uncommitted_lines_threshold))
        set_config_value("watch.thresholds.test_failures", str(self.test_failures_threshold))
        set_config_value("watch.detect_todos", str(self.detect_todos).lower())
        set_config_value("watch.detect_fixmes", str(self.detect_fixmes).lower())
        set_config_value("watch.detect_hacks", str(self.detect_hacks).lower())


@dataclass
class WatchState:
    """Current watch state."""

    files_changed: Set[str] = field(default_factory=set)
    last_check: datetime = field(default_factory=datetime.now)
    last_prompt: Dict[str, datetime] = field(default_factory=dict)
    todo_count: int = 0
    fixme_count: int = 0
    hack_count: int = 0

    def should_prompt(self, prompt_type: str, debounce: int) -> bool:
        """Check if enough time has passed since last prompt.

        Args:
            prompt_type: Type of prompt (e.g., "commit", "todo", "test")
            debounce: Debounce time in seconds

        Returns:
            True if should prompt, False otherwise
        """
        last = self.last_prompt.get(prompt_type)
        if not last:
            return True

        elapsed = (datetime.now() - last).total_seconds()
        return elapsed >= debounce

    def record_prompt(self, prompt_type: str) -> None:
        """Record that a prompt was shown.

        Args:
            prompt_type: Type of prompt
        """
        self.last_prompt[prompt_type] = datetime.now()


class FileWatcher:
    """File system watcher for proactive knowledge capture."""

    def __init__(self, project_root: Optional[Path] = None, config: Optional[WatchConfig] = None):
        """Initialize file watcher.

        Args:
            project_root: Project root directory (default: current directory)
            config: Watch configuration (default: load from config)
        """
        self.project_root = project_root or Path.cwd()
        self.config = config or WatchConfig.load()
        self.state = WatchState()

    def _run_git(self, *args: str) -> tuple[int, str, str]:
        """Run git command and return (returncode, stdout, stderr).

        Args:
            *args: Git command arguments

        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        result = subprocess.run(
            ["git"] + list(args),
            cwd=str(self.project_root),
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout, result.stderr

    def check_uncommitted_changes(self) -> tuple[int, List[str]]:
        """Check for uncommitted changes.

        Returns:
            Tuple of (number of changed lines, list of changed files)
        """
        # Get modified files
        returncode, stdout, stderr = self._run_git("status", "--porcelain")
        if returncode != 0:
            return 0, []

        changed_files = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            # Format: " M file.py" or "?? file.py"
            status = line[:2]
            filename = line[3:]
            if status.strip():
                changed_files.append(filename)

        # Get number of changed lines
        returncode, stdout, stderr = self._run_git("diff", "--stat")
        if returncode != 0:
            return 0, changed_files

        # Parse changed lines from last line: "2 files changed, 45 insertions(+), 10 deletions(-)"
        lines = stdout.strip().split("\n")
        if not lines:
            return 0, changed_files

        last_line = lines[-1]
        match = re.search(r"(\d+) insertion", last_line)
        insertions = int(match.group(1)) if match else 0

        match = re.search(r"(\d+) deletion", last_line)
        deletions = int(match.group(1)) if match else 0

        total_changes = insertions + deletions

        return total_changes, changed_files

    def detect_code_markers(self) -> Dict[str, List[tuple[str, int, str]]]:
        """Detect TODO, FIXME, HACK comments in code.

        Returns:
            Dict of marker type to list of (filename, line_number, content) tuples
        """
        markers = {
            "TODO": [],
            "FIXME": [],
            "HACK": [],
        }

        # Patterns to detect
        patterns = []
        if self.config.detect_todos:
            patterns.append(("TODO", re.compile(r"#\s*TODO:?\s*(.+)", re.IGNORECASE)))
            patterns.append(("TODO", re.compile(r"//\s*TODO:?\s*(.+)", re.IGNORECASE)))
            patterns.append(("TODO", re.compile(r"/\*\s*TODO:?\s*(.+)", re.IGNORECASE)))

        if self.config.detect_fixmes:
            patterns.append(("FIXME", re.compile(r"#\s*FIXME:?\s*(.+)", re.IGNORECASE)))
            patterns.append(("FIXME", re.compile(r"//\s*FIXME:?\s*(.+)", re.IGNORECASE)))
            patterns.append(("FIXME", re.compile(r"/\*\s*FIXME:?\s*(.+)", re.IGNORECASE)))

        if self.config.detect_hacks:
            patterns.append(("HACK", re.compile(r"#\s*HACK:?\s*(.+)", re.IGNORECASE)))
            patterns.append(("HACK", re.compile(r"//\s*HACK:?\s*(.+)", re.IGNORECASE)))
            patterns.append(("HACK", re.compile(r"/\*\s*HACK:?\s*(.+)", re.IGNORECASE)))

        # Search in common code files
        for ext in ["*.py", "*.js", "*.ts", "*.tsx", "*.java", "*.c", "*.cpp", "*.rs", "*.go"]:
            for filepath in self.project_root.rglob(ext):
                # Skip common ignore patterns
                if any(
                    part in filepath.parts
                    for part in [".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"]
                ):
                    continue

                try:
                    content = filepath.read_text(encoding="utf-8")
                    for line_num, line in enumerate(content.split("\n"), 1):
                        for marker_type, pattern in patterns:
                            match = pattern.search(line)
                            if match:
                                markers[marker_type].append((
                                    str(filepath.relative_to(self.project_root)),
                                    line_num,
                                    match.group(1).strip()
                                ))
                except Exception:
                    # Skip files that can't be read
                    continue

        return markers

    def check_for_prompts(self) -> List[str]:
        """Check if any prompts should be shown.

        Returns:
            List of prompt messages
        """
        prompts = []

        # Check uncommitted changes
        changed_lines, changed_files = self.check_uncommitted_changes()

        # Prompt for commit if threshold exceeded
        if (
            len(changed_files) >= self.config.files_changed_threshold
            and self.state.should_prompt("commit", self.config.debounce)
        ):
            prompts.append(
                f"💡 {len(changed_files)} files changed. Commit now?\n"
                f"   idlergear git commit"
            )
            self.state.record_prompt("commit")

        # Prompt for large uncommitted changes
        if (
            changed_lines >= self.config.uncommitted_lines_threshold
            and self.state.should_prompt("large_commit", self.config.debounce)
        ):
            prompts.append(
                f"💡 {changed_lines} lines changed. Consider committing!\n"
                f"   idlergear git commit"
            )
            self.state.record_prompt("large_commit")

        # Check for TODO/FIXME/HACK comments
        markers = self.detect_code_markers()

        # Detect new TODOs
        new_todo_count = len(markers["TODO"])
        if (
            new_todo_count > self.state.todo_count
            and self.state.should_prompt("todo", self.config.debounce)
        ):
            new_todos = new_todo_count - self.state.todo_count
            prompts.append(
                f"💡 {new_todos} new TODO comment(s) detected. Create task(s)?\n"
                f"   idlergear task create \"...\""
            )
            self.state.record_prompt("todo")

        self.state.todo_count = new_todo_count

        # Detect new FIXMEs
        new_fixme_count = len(markers["FIXME"])
        if (
            new_fixme_count > self.state.fixme_count
            and self.state.should_prompt("fixme", self.config.debounce)
        ):
            new_fixmes = new_fixme_count - self.state.fixme_count
            prompts.append(
                f"💡 {new_fixmes} new FIXME comment(s) detected. Create bug(s)?\n"
                f"   idlergear task create \"...\" --label bug"
            )
            self.state.record_prompt("fixme")

        self.state.fixme_count = new_fixme_count

        # Detect new HACKs
        new_hack_count = len(markers["HACK"])
        if (
            new_hack_count > self.state.hack_count
            and self.state.should_prompt("hack", self.config.debounce)
        ):
            new_hacks = new_hack_count - self.state.hack_count
            prompts.append(
                f"💡 {new_hacks} new HACK comment(s) detected. Create technical debt task(s)?\n"
                f"   idlergear task create \"...\" --label technical-debt"
            )
            self.state.record_prompt("hack")

        self.state.hack_count = new_hack_count

        return prompts

    def watch(self, interval: int = 10) -> None:
        """Start watching for changes.

        Args:
            interval: Check interval in seconds
        """
        print(f"👀 Watching for changes (interval: {interval}s, debounce: {self.config.debounce}s)...")
        print("Press Ctrl+C to stop\n")

        try:
            while True:
                prompts = self.check_for_prompts()

                if prompts:
                    print("\n" + "=" * 60)
                    for prompt in prompts:
                        print(prompt)
                        print()
                    print("=" * 60 + "\n")

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n✓ Watch mode stopped")


def get_watch_stats() -> Dict:
    """Get current watch statistics.

    Returns:
        Dictionary of watch statistics
    """
    watcher = FileWatcher()

    changed_lines, changed_files = watcher.check_uncommitted_changes()
    markers = watcher.detect_code_markers()

    return {
        "changed_files": len(changed_files),
        "changed_lines": changed_lines,
        "files": changed_files,
        "todos": len(markers["TODO"]),
        "fixmes": len(markers["FIXME"]),
        "hacks": len(markers["HACK"]),
    }
