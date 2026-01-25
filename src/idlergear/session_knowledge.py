"""Session knowledge harvesting for IdlerGear.

Extracts lessons learned, patterns, and insights from completed sessions.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root
from idlergear.session_history import SessionHistory


class KnowledgeHarvester:
    """Harvest knowledge and insights from completed sessions."""

    def __init__(self, root: Path | None = None):
        """Initialize knowledge harvester.

        Args:
            root: IdlerGear root directory (auto-detect if None)
        """
        self.root = root or find_idlergear_root()
        if not self.root:
            raise ValueError("Not in an IdlerGear project")

        self.history = SessionHistory(self.root)
        self.notes_file = self.root / ".idlergear" / "notes.json"

    def harvest_session(self, session_id: str, branch: str = "main") -> dict[str, Any]:
        """Extract knowledge from a session.

        Args:
            session_id: Session ID to analyze
            branch: Branch name

        Returns:
            Dict with extracted knowledge

        Raises:
            ValueError: If session not found
        """
        snapshot = self.history.load_snapshot(session_id, branch)
        if not snapshot:
            raise ValueError(f"Session '{session_id}' not found in branch '{branch}'")

        knowledge = {
            "session_id": session_id,
            "branch": branch,
            "timestamp": snapshot.timestamp,
            "duration_minutes": snapshot.duration_seconds // 60,
            "insights": [],
        }

        # Extract insights from outcome
        outcome = snapshot.outcome
        state = snapshot.state

        # 1. Tasks created/completed
        tasks_created = outcome.get("tasks_created", [])
        tasks_completed = outcome.get("tasks_completed", [])

        if tasks_completed:
            knowledge["insights"].append({
                "type": "achievement",
                "content": f"Completed {len(tasks_completed)} task(s)",
                "tasks": tasks_completed,
            })

        # 2. Files modified
        working_files = state.get("working_files", [])
        if working_files:
            # Group by directory
            directories = {}
            for file in working_files:
                if "/" in file:
                    dir_name = file.rsplit("/", 1)[0]
                    directories[dir_name] = directories.get(dir_name, 0) + 1

            if directories:
                main_area = max(directories.items(), key=lambda x: x[1])
                knowledge["insights"].append({
                    "type": "focus_area",
                    "content": f"Primary work in {main_area[0]} ({main_area[1]} files)",
                    "directories": dict(directories),
                })

        # 3. Session outcome
        if outcome.get("status") == "success":
            knowledge["insights"].append({
                "type": "success_pattern",
                "content": "Session completed successfully",
                "duration_minutes": snapshot.duration_seconds // 60,
            })
        elif outcome.get("status") == "failed":
            knowledge["insights"].append({
                "type": "learning",
                "content": "Session encountered difficulties",
                "note": "Review session for lessons learned",
            })

        # 4. Tool usage patterns
        tool_usage = outcome.get("tool_usage", {})
        if tool_usage:
            total_calls = sum(tool_usage.values())
            most_used = max(tool_usage.items(), key=lambda x: x[1])

            knowledge["insights"].append({
                "type": "tool_pattern",
                "content": f"Primary tool: {most_used[0]} ({most_used[1]}/{total_calls} calls)",
                "tools": dict(tool_usage),
            })

        # 5. Current task context
        current_task = state.get("current_task_id")
        if current_task:
            knowledge["insights"].append({
                "type": "context",
                "content": f"Working on task #{current_task}",
                "task_id": current_task,
            })

        return knowledge

    def harvest_recent_sessions(
        self, days: int = 7, branch: str = "main"
    ) -> list[dict[str, Any]]:
        """Harvest knowledge from recent sessions.

        Args:
            days: Number of days to look back
            branch: Branch to analyze

        Returns:
            List of knowledge dicts from recent sessions
        """
        from datetime import timedelta

        sessions = self.history.list_sessions(branch=branch)
        cutoff = datetime.now() - timedelta(days=days)

        harvested = []
        for session in sessions:
            try:
                session_time = datetime.fromisoformat(session.timestamp)
                if session_time >= cutoff:
                    knowledge = self.harvest_session(session.session_id, branch)
                    harvested.append(knowledge)
            except (ValueError, KeyError):
                continue

        return harvested

    def save_as_note(
        self, knowledge: dict[str, Any], title: str | None = None
    ) -> dict[str, Any]:
        """Save harvested knowledge as a note.

        Args:
            knowledge: Knowledge dict from harvest_session
            title: Note title (auto-generated if None)

        Returns:
            Note dict with ID
        """
        # Load existing notes
        notes = []
        if self.notes_file.exists():
            try:
                notes = json.loads(self.notes_file.read_text())
            except json.JSONDecodeError:
                notes = []

        # Generate note ID
        note_id = len(notes) + 1

        # Create note title
        if title is None:
            session_id = knowledge.get("session_id", "unknown")
            title = f"Session insights: {session_id}"

        # Format insights as note body
        insights = knowledge.get("insights", [])
        body_lines = []
        for insight in insights:
            content = insight.get("content", "")
            body_lines.append(f"- {content}")

        note = {
            "id": note_id,
            "title": title,
            "body": "\n".join(body_lines),
            "tags": ["session-harvest", "insights"],
            "created": datetime.now().isoformat(),
            "session_id": knowledge.get("session_id"),
            "metadata": {
                "harvested_from": knowledge.get("session_id"),
                "branch": knowledge.get("branch"),
                "session_duration": knowledge.get("duration_minutes"),
            },
        }

        notes.append(note)

        # Save notes
        self.notes_file.parent.mkdir(parents=True, exist_ok=True)
        self.notes_file.write_text(json.dumps(notes, indent=2))

        return note

    def identify_patterns(
        self, days: int = 30, branch: str = "main"
    ) -> dict[str, Any]:
        """Identify patterns across multiple sessions.

        Args:
            days: Number of days to analyze
            branch: Branch to analyze

        Returns:
            Dict with identified patterns
        """
        harvested = self.harvest_recent_sessions(days=days, branch=branch)

        if not harvested:
            return {"patterns": [], "total_sessions": 0}

        # Aggregate patterns
        focus_areas = {}
        success_count = 0
        failed_count = 0
        total_duration = 0
        tool_usage = {}

        for knowledge in harvested:
            total_duration += knowledge.get("duration_minutes", 0)

            for insight in knowledge.get("insights", []):
                insight_type = insight.get("type")

                if insight_type == "focus_area":
                    dirs = insight.get("directories", {})
                    for dir_name, count in dirs.items():
                        focus_areas[dir_name] = focus_areas.get(dir_name, 0) + count

                elif insight_type == "success_pattern":
                    success_count += 1

                elif insight_type == "learning":
                    failed_count += 1

                elif insight_type == "tool_pattern":
                    tools = insight.get("tools", {})
                    for tool, count in tools.items():
                        tool_usage[tool] = tool_usage.get(tool, 0) + count

        # Identify top patterns
        patterns = []

        if focus_areas:
            top_area = max(focus_areas.items(), key=lambda x: x[1])
            patterns.append({
                "type": "focus_area",
                "description": f"Most work in {top_area[0]} ({top_area[1]} files)",
                "data": dict(sorted(focus_areas.items(), key=lambda x: x[1], reverse=True)[:5]),
            })

        if tool_usage:
            top_tool = max(tool_usage.items(), key=lambda x: x[1])
            patterns.append({
                "type": "tool_preference",
                "description": f"Primary tool: {top_tool[0]} ({top_tool[1]} calls)",
                "data": dict(sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:5]),
            })

        if success_count + failed_count > 0:
            success_rate = (success_count / (success_count + failed_count)) * 100
            patterns.append({
                "type": "success_rate",
                "description": f"Success rate: {success_rate:.1f}%",
                "data": {
                    "successful": success_count,
                    "failed": failed_count,
                    "rate": success_rate,
                },
            })

        avg_duration = total_duration / len(harvested) if harvested else 0
        patterns.append({
            "type": "session_duration",
            "description": f"Average session: {avg_duration:.0f} minutes",
            "data": {
                "average_minutes": avg_duration,
                "total_sessions": len(harvested),
            },
        })

        return {
            "patterns": patterns,
            "total_sessions": len(harvested),
            "time_period_days": days,
        }
