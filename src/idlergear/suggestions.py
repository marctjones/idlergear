"""Proactive suggestions module.

Generates intelligent suggestions based on project context:
- Task recommendations (which task to work on next)
- Knowledge harvesting (after completed sessions)
- Stale cleanup (archive old items)
- Test coverage (run tests)
- Documentation updates
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from .config import find_idlergear_root
from .tasks import list_tasks

SuggestionType = Literal[
    "task_recommendation",     # Suggest next task to work on
    "knowledge_harvest",       # Suggest harvesting session
    "stale_cleanup",           # Suggest archiving stale items
    "test_coverage",           # Suggest running tests
    "documentation_update",    # Suggest updating docs
]


@dataclass
class Suggestion:
    """Represents a proactive suggestion."""
    type: SuggestionType
    priority: int  # 1-10 (10 = highest)
    title: str
    description: str
    action: str  # Command to run
    reason: str  # Why suggesting this
    confidence: float  # 0.0-1.0


def generate_suggestions(project_path: Path | None = None) -> list[Suggestion]:
    """Generate proactive suggestions based on context.

    Args:
        project_path: Project root path (auto-detected if not provided)

    Returns:
        List of suggestions sorted by priority * confidence
    """
    if project_path is None:
        project_path = find_idlergear_root()
        if not project_path:
            return []

    suggestions = []

    # 1. Task recommendations (based on priority, dependencies)
    suggestions.extend(_suggest_tasks())

    # 2. Knowledge harvesting (after N completed sessions)
    # TODO: Implement when session tracking is available

    # 3. Stale cleanup (many low-relevance items)
    # TODO: Implement when relevance scoring is fully integrated

    # 4. Test coverage (files changed, tests not run)
    suggestions.extend(_suggest_tests(project_path))

    # Sort by priority * confidence
    suggestions.sort(
        key=lambda s: s.priority * s.confidence,
        reverse=True
    )

    return suggestions


def _suggest_tasks() -> list[Suggestion]:
    """Suggest which task to work on next."""
    suggestions = []

    try:
        tasks = list_tasks(state="open")
    except Exception:
        return suggestions

    if not tasks:
        return suggestions

    # Handle potential missing fields gracefully

    # Score tasks based on:
    # - Priority (high = 3, medium = 2, low = 1)
    # - No blockers (blocked tasks score 0)
    # - Recency (recently created score higher)

    scored_tasks = []
    now = datetime.now(timezone.utc)

    for task in tasks:
        try:
            score = 0

            # Check if blocked
            if task.get("blocked_by"):
                continue  # Skip blocked tasks

            # Priority weight
            priority = task.get("priority")
            if priority and priority.lower() == "high":
                score += 30
            elif priority and priority.lower() == "medium":
                score += 20
            else:
                score += 10

            # No blockers bonus (already checked above)
            score += 20

            # Recent creation bonus
            created_str = task.get("created")
            if created_str:
                try:
                    # Parse ISO format datetime
                    created = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                    days_ago = (now - created).total_seconds() / 86400
                    if days_ago < 7:
                        score += 15
                    elif days_ago < 30:
                        score += 5
                except:
                    pass

            scored_tasks.append((task, score))
        except Exception:
            # Skip this task if any error occurs
            continue

    if not scored_tasks:
        return suggestions

    # Sort by score and get top 3
    scored_tasks.sort(key=lambda x: x[1], reverse=True)

    for task, score in scored_tasks[:3]:
        try:
            confidence = min(score / 100, 1.0)
            priority = 8 if confidence > 0.6 else 6

            title = task.get("title", "Untitled")
            task_id = task.get("id", "?")
            body = task.get("body") or ""

            suggestions.append(Suggestion(
                type="task_recommendation",
                priority=priority,
                title=f"Work on: {title}",
                description=body[:200] if body else "",  # First 200 chars
                action=f"idlergear task show {task_id}",
                reason=f"High priority, unblocked, score: {score}",
                confidence=confidence,
            ))
        except Exception:
            # Skip this suggestion if any error occurs
            continue

    return suggestions


def _suggest_tests(project_path: Path) -> list[Suggestion]:
    """Suggest running tests if test files exist."""
    suggestions = []

    # Check if test files exist
    test_files = list(project_path.glob("tests/**/*.py")) + \
                 list(project_path.glob("test/**/*.py")) + \
                 list(project_path.glob("**/*_test.py"))

    if not test_files:
        return suggestions

    # Check if pytest is available
    import shutil
    pytest_available = shutil.which("pytest") is not None

    if pytest_available:
        suggestions.append(Suggestion(
            type="test_coverage",
            priority=6,
            title="Run test suite",
            description=f"Found {len(test_files)} test files",
            action="pytest",
            reason="Test files exist, ensure they pass",
            confidence=0.8,
        ))

    return suggestions


def suggestions_text(suggestions: list[Suggestion]) -> str:
    """Format suggestions as human-readable text.

    Args:
        suggestions: List of suggestions

    Returns:
        Formatted text suitable for context output
    """
    if not suggestions:
        return ""

    lines = ["## Suggested Next Steps\n"]

    for i, suggestion in enumerate(suggestions[:5], 1):  # Top 5
        conf_pct = int(suggestion.confidence * 100)
        lines.append(
            f"{i}. [{suggestion.priority}/10, {conf_pct}%] {suggestion.title}"
        )
        lines.append(f"   → {suggestion.action}")
        lines.append(f"   {suggestion.reason}\n")

    return "\n".join(lines)


def suggestions_report(suggestions: list[Suggestion]) -> str:
    """Generate detailed suggestions report.

    Args:
        suggestions: List of suggestions

    Returns:
        Formatted report string
    """
    if not suggestions:
        return "No suggestions at this time."

    lines = ["# Suggested Next Steps\n"]

    # Group by type
    by_type = {}
    for suggestion in suggestions:
        if suggestion.type not in by_type:
            by_type[suggestion.type] = []
        by_type[suggestion.type].append(suggestion)

    # Task recommendations first
    if "task_recommendation" in by_type:
        lines.append("## 📋 Recommended Tasks\n")
        for suggestion in by_type["task_recommendation"]:
            conf_pct = int(suggestion.confidence * 100)
            lines.append(
                f"**{suggestion.title}** "
                f"[Priority: {suggestion.priority}/10, Confidence: {conf_pct}%]"
            )
            if suggestion.description:
                lines.append(f"  {suggestion.description}")
            lines.append(f"  `{suggestion.action}`")
            lines.append(f"  _{suggestion.reason}_\n")

    # Other suggestions
    for suggestion_type, suggestions_of_type in by_type.items():
        if suggestion_type == "task_recommendation":
            continue  # Already handled

        emoji = {
            "knowledge_harvest": "🌾",
            "stale_cleanup": "🧹",
            "test_coverage": "🧪",
            "documentation_update": "📝",
        }.get(suggestion_type, "💡")

        type_name = suggestion_type.replace("_", " ").title()
        lines.append(f"## {emoji} {type_name}\n")

        for suggestion in suggestions_of_type:
            conf_pct = int(suggestion.confidence * 100)
            lines.append(
                f"**{suggestion.title}** "
                f"[Priority: {suggestion.priority}/10, Confidence: {conf_pct}%]"
            )
            lines.append(f"  `{suggestion.action}`")
            lines.append(f"  _{suggestion.reason}_\n")

    return "\n".join(lines)
