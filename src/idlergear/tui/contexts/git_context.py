"""Git context provider with caching."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from idlergear.git import GitServer


@dataclass
class GitContextSnapshot:
    """Cached git context snapshot."""

    branch: str
    commit_short: str
    dirty: bool
    uncommitted_count: int
    ahead: int
    behind: int
    timestamp: datetime


class GitContext:
    """Provides git context with TTL caching."""

    def __init__(self, repo_path: Optional[Path] = None, ttl_seconds: float = 2.0):
        self.repo_path = repo_path or Path.cwd()
        self.git = GitServer()
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: Optional[GitContextSnapshot] = None
        self._cache_time: Optional[datetime] = None

    def get(self) -> GitContextSnapshot:
        """Get current git context (cached with TTL)."""
        now = datetime.now()

        # Return cached if still valid
        if self._cache and self._cache_time:
            if now - self._cache_time < self.ttl:
                return self._cache

        # Refresh cache
        try:
            status = self.git.status(str(self.repo_path))

            # Get short commit hash
            commit_result = self.git._run_git(
                ["rev-parse", "--short", "HEAD"], cwd=str(self.repo_path)
            )
            commit_short = commit_result.stdout.strip()[:7]

            self._cache = GitContextSnapshot(
                branch=status.branch,
                commit_short=commit_short,
                dirty=len(status.modified) + len(status.staged) + len(status.untracked)
                > 0,
                uncommitted_count=len(status.modified)
                + len(status.staged)
                + len(status.untracked),
                ahead=status.ahead,
                behind=status.behind,
                timestamp=now,
            )
            self._cache_time = now
        except Exception:
            # Gracefully handle git errors
            if not self._cache:
                self._cache = GitContextSnapshot(
                    branch="unknown",
                    commit_short="unknown",
                    dirty=False,
                    uncommitted_count=0,
                    ahead=0,
                    behind=0,
                    timestamp=now,
                )
                self._cache_time = now

        return self._cache

    def file_status(self, file_path: str) -> str:
        """Get git status for a specific file."""
        try:
            # Read from cached status
            status = self.git.status(str(self.repo_path))

            if file_path in status.staged:
                return "staged"
            elif file_path in status.modified:
                return "modified"
            elif file_path in status.untracked:
                return "untracked"
            else:
                return "unchanged"
        except Exception:
            return "unknown"
