"""Proactive suggestion system for IdlerGear.

Surfaces actionable insights without being asked, making AI a more active
development partner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class SuggestionType(str, Enum):
    """Types of proactive suggestions."""

    KNOWLEDGE_GAP = "knowledge_gap"  # From gap detector
    TOKEN_EFFICIENCY = "token_efficiency"  # Save tokens
    WORKFLOW = "workflow"  # Improve development flow
    CLEANUP = "cleanup"  # Clean up stale data
    AUTOMATION = "automation"  # Automate repetitive tasks


class SuggestionPriority(str, Enum):
    """Priority levels for suggestions."""

    CRITICAL = "critical"  # Blocking issue
    HIGH = "high"  # Should address soon
    MEDIUM = "medium"  # Worth considering
    LOW = "low"  # Nice to have


@dataclass
class Suggestion:
    """Represents a proactive suggestion."""

    type: SuggestionType
    priority: SuggestionPriority
    title: str
    description: str
    action: str  # What to do
    command: str | None = None  # Command to run
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "action": self.action,
            "command": self.command,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
        }


class ProactiveEngine:
    """Generates proactive suggestions."""

    def __init__(self, project_root: Path | None = None):
        """Initialize proactive engine.

        Args:
            project_root: Project root directory (defaults to cwd)
        """
        self.project_root = project_root or Path.cwd()

    def get_suggestions(self) -> list[Suggestion]:
        """Get all proactive suggestions.

        Returns:
            List of suggestions, sorted by priority
        """
        suggestions: list[Suggestion] = []

        # Get gap-based suggestions
        suggestions.extend(self._get_gap_suggestions())

        # Get token efficiency suggestions
        suggestions.extend(self._get_token_suggestions())

        # Get workflow suggestions
        suggestions.extend(self._get_workflow_suggestions())

        # Sort by priority
        priority_order = {
            SuggestionPriority.CRITICAL: 0,
            SuggestionPriority.HIGH: 1,
            SuggestionPriority.MEDIUM: 2,
            SuggestionPriority.LOW: 3,
        }
        return sorted(suggestions, key=lambda s: priority_order[s.priority])

    def _get_gap_suggestions(self) -> list[Suggestion]:
        """Get suggestions from knowledge gap detection."""
        suggestions: list[Suggestion] = []

        try:
            from idlergear.gap_detector import GapDetector, GapSeverity

            detector = GapDetector(self.project_root)
            gaps = detector.detect_gaps()

            # Convert high/critical gaps to suggestions
            for gap in gaps:
                if gap.severity in (GapSeverity.CRITICAL, GapSeverity.HIGH):
                    priority = (
                        SuggestionPriority.CRITICAL
                        if gap.severity == GapSeverity.CRITICAL
                        else SuggestionPriority.HIGH
                    )

                    suggestions.append(
                        Suggestion(
                            type=SuggestionType.KNOWLEDGE_GAP,
                            priority=priority,
                            title=gap.message,
                            description=gap.suggestion,
                            action=gap.suggestion,
                            command=gap.fix_command if gap.fixable else None,
                            context=gap.context,
                        )
                    )

        except Exception:
            # Gap detection failed - continue
            pass

        return suggestions

    def _get_token_suggestions(self) -> list[Suggestion]:
        """Get token efficiency improvement suggestions."""
        suggestions: list[Suggestion] = []

        try:
            from idlergear.backends.registry import get_backend

            # Check if using preview mode for task list
            backend = get_backend("task", project_path=self.project_root)
            tasks = backend.list()

            # If many tasks, suggest using preview mode
            if len(tasks) > 20:
                total_chars = sum(len(str(t.get("body") or "")) for t in tasks)
                if total_chars > 10000:  # ~2500 tokens
                    suggestions.append(
                        Suggestion(
                            type=SuggestionType.TOKEN_EFFICIENCY,
                            priority=SuggestionPriority.MEDIUM,
                            title=f"High token usage: {len(tasks)} tasks with large bodies",
                            description="Task list bodies are consuming significant tokens. Use preview mode for efficiency.",
                            action="Use: idlergear task list --preview --limit 10",
                            command=None,
                            context={
                                "task_count": len(tasks),
                                "estimated_chars": total_chars,
                                "estimated_tokens": total_chars // 4,
                            },
                        )
                    )

        except Exception:
            # Backend not available
            pass

        return suggestions

    def _get_workflow_suggestions(self) -> list[Suggestion]:
        """Get workflow improvement suggestions."""
        suggestions: list[Suggestion] = []

        try:
            from idlergear.daemon.lifecycle import DaemonLifecycle

            # Check if daemon is running
            lifecycle = DaemonLifecycle(self.project_root)
            if not lifecycle.is_running():
                suggestions.append(
                    Suggestion(
                        type=SuggestionType.WORKFLOW,
                        priority=SuggestionPriority.LOW,
                        title="Daemon not running",
                        description="Start daemon for multi-agent coordination and background gap detection",
                        action="Run: idlergear daemon start",
                        command="idlergear daemon start",
                        context={},
                    )
                )

        except Exception:
            # Daemon not available
            pass

        return suggestions


def get_session_start_suggestions(
    project_root: Path | None = None,
) -> list[Suggestion]:
    """Get suggestions to show at session start.

    Args:
        project_root: Project root (defaults to cwd)

    Returns:
        List of high-priority suggestions
    """
    engine = ProactiveEngine(project_root)
    suggestions = engine.get_suggestions()

    # Filter to high/critical only at session start
    return [
        s
        for s in suggestions
        if s.priority in (SuggestionPriority.CRITICAL, SuggestionPriority.HIGH)
    ]
