"""Session analytics and statistics for IdlerGear.

Provides insights into session productivity, efficiency, and patterns.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root
from idlergear.session_history import SessionHistory, SessionSnapshot


class SessionStats:
    """Calculate statistics for sessions."""

    def __init__(self, root: Path | None = None):
        """Initialize session stats.

        Args:
            root: IdlerGear root directory (auto-detect if None)
        """
        self.root = root or find_idlergear_root()
        if self.root is None:
            raise RuntimeError("Not in an IdlerGear project")

        self.history = SessionHistory(self.root)
        self.tasks_file = self.root / ".idlergear" / "tasks.json"

    def get_overview_stats(
        self, days: int = 7, branch: str = "main"
    ) -> dict[str, Any]:
        """Get overview statistics for recent sessions.

        Args:
            days: Number of days to look back
            branch: Branch name to analyze

        Returns:
            Dictionary with overview stats
        """
        sessions = self.history.list_sessions(branch=branch)

        # Filter to recent sessions
        cutoff = datetime.now() - timedelta(days=days)
        recent_sessions = []
        for session in sessions:
            try:
                session_time = datetime.fromisoformat(session.timestamp)
                if session_time >= cutoff:
                    recent_sessions.append(session)
            except (ValueError, KeyError):
                continue

        if not recent_sessions:
            return {
                "total_sessions": 0,
                "total_time": 0,
                "days": days,
                "message": f"No sessions found in last {days} days",
            }

        # Calculate metrics
        total_time = sum(s.duration_seconds for s in recent_sessions)
        avg_time = total_time / len(recent_sessions) if recent_sessions else 0

        # Find longest and shortest
        longest = max(recent_sessions, key=lambda s: s.duration_seconds)
        shortest = min(recent_sessions, key=lambda s: s.duration_seconds)

        # Count tasks and files
        tasks_created = 0
        tasks_completed = 0
        files_modified = set()

        for session in recent_sessions:
            outcome = session.outcome
            if outcome:
                tasks_created += len(outcome.get("tasks_created", []))
                tasks_completed += len(outcome.get("tasks_completed", []))

            state = session.state
            if state and "working_files" in state:
                files_modified.update(state["working_files"])

        return {
            "days": days,
            "total_sessions": len(recent_sessions),
            "total_time_seconds": total_time,
            "total_time_formatted": self._format_duration(total_time),
            "average_time_seconds": int(avg_time),
            "average_time_formatted": self._format_duration(int(avg_time)),
            "longest_session": {
                "id": longest.session_id,
                "duration_seconds": longest.duration_seconds,
                "duration_formatted": self._format_duration(longest.duration_seconds),
            },
            "shortest_session": {
                "id": shortest.session_id,
                "duration_seconds": shortest.duration_seconds,
                "duration_formatted": self._format_duration(shortest.duration_seconds),
            },
            "productivity": {
                "tasks_created": tasks_created,
                "tasks_completed": tasks_completed,
                "completion_rate": (
                    f"{(tasks_completed / tasks_created * 100):.1f}%"
                    if tasks_created > 0
                    else "N/A"
                ),
                "files_modified": len(files_modified),
            },
        }

    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string like "2h 34m" or "45m"
        """
        if seconds < 60:
            return f"{seconds}s"

        minutes = seconds // 60
        hours = minutes // 60
        remaining_minutes = minutes % 60

        if hours > 0:
            return f"{hours}h {remaining_minutes}m"
        else:
            return f"{minutes}m"

    def get_tool_usage_stats(
        self, days: int = 7, branch: str = "main"
    ) -> dict[str, Any]:
        """Get tool usage statistics.

        Args:
            days: Number of days to look back
            branch: Branch name to analyze

        Returns:
            Dictionary with tool usage counts and percentages
        """
        sessions = self.history.list_sessions(branch=branch)

        # Filter to recent sessions
        cutoff = datetime.now() - timedelta(days=days)
        tool_counts: dict[str, int] = {}
        total_calls = 0

        for session in sessions:
            try:
                session_time = datetime.fromisoformat(session.timestamp)
                if session_time < cutoff:
                    continue

                outcome = session.outcome
                if outcome and "tool_usage" in outcome:
                    for tool, count in outcome["tool_usage"].items():
                        tool_counts[tool] = tool_counts.get(tool, 0) + count
                        total_calls += count
            except (ValueError, KeyError):
                continue

        # Calculate percentages
        tool_stats = []
        for tool, count in sorted(
            tool_counts.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (count / total_calls * 100) if total_calls > 0 else 0
            tool_stats.append(
                {"tool": tool, "calls": count, "percentage": f"{percentage:.1f}%"}
            )

        return {
            "total_calls": total_calls,
            "tools": tool_stats,
        }

    def get_success_rate(self, days: int = 7, branch: str = "main") -> dict[str, Any]:
        """Get session success rate.

        Args:
            days: Number of days to look back
            branch: Branch name to analyze

        Returns:
            Dictionary with success rate statistics
        """
        sessions = self.history.list_sessions(branch=branch)

        # Filter to recent sessions
        cutoff = datetime.now() - timedelta(days=days)
        successful = 0
        total = 0

        for session in sessions:
            try:
                session_time = datetime.fromisoformat(session.timestamp)
                if session_time < cutoff:
                    continue

                total += 1
                outcome = session.outcome
                if outcome and outcome.get("status") == "success":
                    successful += 1
            except (ValueError, KeyError):
                continue

        success_rate = (successful / total * 100) if total > 0 else 0

        return {
            "total_sessions": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": f"{success_rate:.1f}%",
        }


def format_stats_output(stats: dict[str, Any]) -> str:
    """Format statistics into a human-readable string.

    Args:
        stats: Statistics dictionary from get_overview_stats

    Returns:
        Formatted multi-line string
    """
    lines = []
    lines.append(f"\nSession Statistics (Last {stats['days']} days)\n")
    lines.append("📊 Overview:")
    lines.append(f"  Total Sessions: {stats['total_sessions']}")

    if stats["total_sessions"] > 0:
        lines.append(f"  Total Time: {stats['total_time_formatted']}")
        lines.append(f"  Average Session: {stats['average_time_formatted']}")
        lines.append(
            f"  Longest Session: {stats['longest_session']['duration_formatted']} "
            f"({stats['longest_session']['id']})"
        )
        lines.append(
            f"  Shortest Session: {stats['shortest_session']['duration_formatted']} "
            f"({stats['shortest_session']['id']})"
        )

        lines.append("\n📈 Productivity:")
        prod = stats["productivity"]
        lines.append(f"  Tasks Created: {prod['tasks_created']}")
        lines.append(f"  Tasks Completed: {prod['tasks_completed']}")
        lines.append(f"  Completion Rate: {prod['completion_rate']}")
        lines.append(f"  Files Modified: {prod['files_modified']}")

    return "\n".join(lines)
