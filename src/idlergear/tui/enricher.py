"""Event enricher - adds IdlerGear context to raw events."""

from typing import Any
from pathlib import Path

from .contexts import GitContext, TaskContext, FileContext


class EventEnricher:
    """Enriches raw Claude events with IdlerGear context."""

    def __init__(self, repo_path: Path = None):
        self.git = GitContext(repo_path)
        self.tasks = TaskContext()
        self.files = FileContext()

    def enrich(self, event: dict[str, Any]) -> dict[str, Any]:
        """Add IdlerGear context to event.

        Returns enriched event with additional fields:
        - git_context: Current git state
        - current_task: Current task (if any)
        - file_info: File metadata (for file operations)
        """
        enriched = event.copy()

        # Add git context
        git_ctx = self.git.get()
        enriched["git_context"] = {
            "branch": git_ctx.branch,
            "commit": git_ctx.commit_short,
            "dirty": git_ctx.dirty,
            "uncommitted": git_ctx.uncommitted_count,
        }

        # Add current task
        task = self.tasks.get_current()
        if task:
            enriched["current_task"] = {
                "id": task.id,
                "title": task.title,
            }

        # Enrich tool calls
        if event.get("type") == "tool_use":
            self._enrich_tool(enriched)

        return enriched

    def _enrich_tool(self, event: dict[str, Any]):
        """Enrich tool use event with additional context."""
        tool_name = event.get("name", "")
        tool_input = event.get("input", {})

        # Enrich file operations
        if tool_name in ["Read", "Write", "Edit"]:
            file_path = tool_input.get("file_path") or tool_input.get("path")
            if file_path:
                event["file_info"] = self.files.get_info(file_path)
                event["file_git_status"] = self.git.file_status(file_path)

        # Detect task operations
        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            if "idlergear task" in command or "ig task" in command:
                event["is_task_operation"] = True
                if "create" in command:
                    event["task_action"] = "create"
                elif "close" in command:
                    event["task_action"] = "close"

            # Detect git operations
            elif command.strip().startswith("git"):
                event["is_git_operation"] = True
                if "commit" in command:
                    event["git_operation"] = "commit"
                elif "push" in command:
                    event["git_operation"] = "push"
