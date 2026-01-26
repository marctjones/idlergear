"""Knowledge gap detection for proactive context management.

Detects patterns indicating missing or incomplete knowledge:
- Missing references for high-activity topics
- Undocumented code changes
- Unanswered questions
- Structural issues in task management
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class GapType(str, Enum):
    """Types of knowledge gaps."""

    MISSING_REFERENCE = "missing_reference"
    UNDOCUMENTED_COMMITS = "undocumented_commits"
    UNANSWERED_QUESTION = "unanswered_question"
    FREQUENT_QUERY = "frequent_query"
    ORPHANED_TASKS = "orphaned_tasks"
    STALE_TASK = "stale_task"
    UNANNOTATED_FILES = "unannotated_files"


class GapSeverity(str, Enum):
    """Severity levels for gaps."""

    CRITICAL = "critical"  # Actively blocking work
    HIGH = "high"  # Should address soon
    MEDIUM = "medium"  # Worth addressing
    LOW = "low"  # Nice to have
    INFO = "info"  # Informational only


@dataclass
class Gap:
    """Represents a detected knowledge gap."""

    type: GapType
    severity: GapSeverity
    message: str
    suggestion: str
    context: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    fixable: bool = False  # Can be auto-fixed
    fix_command: str | None = None  # Command to fix

    @property
    def priority_score(self) -> int:
        """Numeric score for sorting (higher = more urgent)."""
        severity_scores = {
            GapSeverity.CRITICAL: 100,
            GapSeverity.HIGH: 75,
            GapSeverity.MEDIUM: 50,
            GapSeverity.LOW: 25,
            GapSeverity.INFO: 10,
        }
        return severity_scores.get(self.severity, 0)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "context": self.context,
            "detected_at": self.detected_at.isoformat(),
            "fixable": self.fixable,
            "fix_command": self.fix_command,
            "priority_score": self.priority_score,
        }


class GapDetector:
    """Detects knowledge gaps in the project."""

    # Detection thresholds (configurable)
    MIN_TASKS_FOR_REFERENCE = 5  # Tasks on same topic → need reference
    MIN_COMMIT_COUNT = 5  # Undocumented commits → need task linking
    STALE_TASK_DAYS = 30  # Open task age threshold
    STALE_QUESTION_DAYS = 14  # Unanswered explore age threshold
    MIN_QUERY_COUNT = 3  # Frequent queries → need reference
    MIN_ORPHANED_TASKS = 10  # Tasks without plan → need organization

    def __init__(self, project_root: Path | None = None):
        """Initialize gap detector.

        Args:
            project_root: Project root directory (defaults to cwd)
        """
        self.project_root = project_root or Path.cwd()

    def detect_gaps(self, gap_types: list[GapType] | None = None) -> list[Gap]:
        """Detect all knowledge gaps.

        Args:
            gap_types: Optional list of gap types to check (default: all)

        Returns:
            List of detected gaps, sorted by priority
        """
        gaps: list[Gap] = []

        # Run all detectors or specific ones
        if gap_types is None or GapType.MISSING_REFERENCE in gap_types:
            gaps.extend(self._detect_missing_references())

        if gap_types is None or GapType.UNDOCUMENTED_COMMITS in gap_types:
            gaps.extend(self._detect_undocumented_commits())

        if gap_types is None or GapType.UNANSWERED_QUESTION in gap_types:
            gaps.extend(self._detect_unanswered_questions())

        if gap_types is None or GapType.STALE_TASK in gap_types:
            gaps.extend(self._detect_stale_tasks())

        if gap_types is None or GapType.ORPHANED_TASKS in gap_types:
            gaps.extend(self._detect_orphaned_tasks())

        if gap_types is None or GapType.UNANNOTATED_FILES in gap_types:
            gaps.extend(self._detect_unannotated_files())

        # Sort by priority (highest first)
        return sorted(gaps, key=lambda g: g.priority_score, reverse=True)

    def _detect_missing_references(self) -> list[Gap]:
        """Detect topics with many tasks but no reference documentation.

        Pattern: If N+ tasks mention the same topic, should have reference docs.
        """
        from idlergear.backends.registry import get_backend

        gaps: list[Gap] = []

        try:
            backend = get_backend("task", project_path=self.project_root)
            tasks = backend.list()

            # Extract topics from task titles/bodies
            topic_counts: dict[str, list[int]] = {}
            common_topics = [
                "auth",
                "authentication",
                "cache",
                "caching",
                "database",
                "api",
                "logging",
                "error",
                "test",
                "deploy",
                "config",
                "performance",
                "security",
            ]

            for task in tasks:
                if task.get("state") == "closed":
                    continue

                title = task.get("title", "").lower()
                body = task.get("body") or ""
                text = f"{title} {body}".lower()

                for topic in common_topics:
                    if topic in text:
                        if topic not in topic_counts:
                            topic_counts[topic] = []
                        topic_counts[topic].append(task["id"])

            # Check which topics need references
            for topic, task_ids in topic_counts.items():
                if len(task_ids) >= self.MIN_TASKS_FOR_REFERENCE:
                    # Check if reference exists
                    if not self._has_reference(topic):
                        gaps.append(
                            Gap(
                                type=GapType.MISSING_REFERENCE,
                                severity=GapSeverity.HIGH,
                                message=f"{len(task_ids)} tasks mention '{topic}' but no reference documentation exists",
                                suggestion=f"Create reference: idlergear reference add '{topic.title()} System' --body '...'",
                                context={
                                    "topic": topic,
                                    "task_count": len(task_ids),
                                    "task_ids": task_ids,
                                },
                                fixable=False,  # Requires manual content
                            )
                        )

        except Exception:
            # Backend not available or error
            pass

        return gaps

    def _detect_undocumented_commits(self) -> list[Gap]:
        """Detect recent commits not linked to any task.

        Pattern: If N+ commits in past week have no task reference, need tracking.
        """
        gaps: list[Gap] = []

        try:
            # Get commits from past week
            since = datetime.now(timezone.utc) - timedelta(days=7)
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"--since={since.isoformat()}",
                    "--format=%H %s",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return gaps

            commits = result.stdout.strip().split("\n")
            if not commits or commits == [""]:
                return gaps

            # Check which commits lack task references
            undocumented = []
            for commit_line in commits:
                if not commit_line:
                    continue

                # Look for task references like #123, GH-123, task 123
                if not any(
                    pattern in commit_line.lower()
                    for pattern in ["#", "task", "issue", "closes", "fixes"]
                ):
                    undocumented.append(commit_line.split()[0][:7])

            if len(undocumented) >= self.MIN_COMMIT_COUNT:
                gaps.append(
                    Gap(
                        type=GapType.UNDOCUMENTED_COMMITS,
                        severity=GapSeverity.MEDIUM,
                        message=f"{len(undocumented)} recent commits without task references",
                        suggestion="Link commits to tasks or create tasks for significant changes",
                        context={
                            "commit_count": len(undocumented),
                            "commits": undocumented[:10],  # First 10
                        },
                        fixable=False,  # Requires manual task creation
                    )
                )

        except Exception:
            # Git not available or error
            pass

        return gaps

    def _detect_unanswered_questions(self) -> list[Gap]:
        """Detect old explore notes that haven't been resolved.

        Pattern: Explore notes older than N days → answer not captured.
        """
        from idlergear.backends.registry import get_backend

        gaps: list[Gap] = []

        try:
            backend = get_backend("note", project_path=self.project_root)
            notes = backend.list()

            # Filter for explore/question notes
            threshold = datetime.now(timezone.utc) - timedelta(
                days=self.STALE_QUESTION_DAYS
            )

            unanswered = []
            for note in notes:
                if note.get("state") == "closed":
                    continue

                labels = [label.lower() for label in note.get("labels", [])]
                if "tag:explore" not in labels:
                    continue

                created = datetime.fromisoformat(
                    note["created_at"].replace("Z", "+00:00")
                )
                if created < threshold:
                    unanswered.append(note)

            # Create gap for each old question
            for note in unanswered[:5]:  # Limit to 5 most urgent
                age_days = (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(note["created_at"].replace("Z", "+00:00"))
                ).days

                gaps.append(
                    Gap(
                        type=GapType.UNANSWERED_QUESTION,
                        severity=GapSeverity.MEDIUM,
                        message=f"Explore note #{note['id']} unanswered for {age_days} days",
                        suggestion=f"Convert to reference or close: idlergear note promote {note['id']} --to reference",
                        context={
                            "note_id": note["id"],
                            "title": note.get("title", ""),
                            "age_days": age_days,
                        },
                        fixable=True,
                        fix_command=f"idlergear task close {note['id']}",
                    )
                )

        except Exception:
            # Backend not available
            pass

        return gaps

    def _detect_stale_tasks(self) -> list[Gap]:
        """Detect tasks open for too long without updates.

        Pattern: Tasks open > N days → likely stale or blocked.
        """
        from idlergear.backends.registry import get_backend

        gaps: list[Gap] = []

        try:
            backend = get_backend("task", project_path=self.project_root)
            tasks = backend.list()

            threshold = datetime.now(timezone.utc) - timedelta(
                days=self.STALE_TASK_DAYS
            )

            stale_tasks = []
            for task in tasks:
                if task.get("state") == "closed":
                    continue

                created = datetime.fromisoformat(
                    task["created_at"].replace("Z", "+00:00")
                )
                updated = datetime.fromisoformat(
                    task["updated_at"].replace("Z", "+00:00")
                )

                # Stale if created long ago and not updated recently
                if created < threshold and updated < threshold:
                    age_days = (datetime.now(timezone.utc) - created).days
                    stale_tasks.append((task, age_days))

            # Report top 5 stalest tasks
            stale_tasks.sort(key=lambda x: x[1], reverse=True)
            for task, age_days in stale_tasks[:5]:
                severity = GapSeverity.HIGH if age_days > 60 else GapSeverity.MEDIUM

                gaps.append(
                    Gap(
                        type=GapType.STALE_TASK,
                        severity=severity,
                        message=f"Task #{task['id']} open for {age_days} days: {task.get('title', '')}",
                        suggestion=f"Update status or close: idlergear task update {task['id']} --state ...",
                        context={
                            "task_id": task["id"],
                            "title": task.get("title", ""),
                            "age_days": age_days,
                        },
                        fixable=True,
                        fix_command=f"idlergear task close {task['id']}",
                    )
                )

        except Exception:
            # Backend not available
            pass

        return gaps

    def _detect_orphaned_tasks(self) -> list[Gap]:
        """Detect tasks not associated with any plan.

        Pattern: Many unorganized tasks → need project planning.
        """
        from idlergear.backends.registry import get_backend

        gaps: list[Gap] = []

        try:
            backend = get_backend("task", project_path=self.project_root)
            tasks = backend.list()

            # Count tasks without milestone
            orphaned = [
                t for t in tasks if t.get("state") == "open" and not t.get("milestone")
            ]

            if len(orphaned) >= self.MIN_ORPHANED_TASKS:
                gaps.append(
                    Gap(
                        type=GapType.ORPHANED_TASKS,
                        severity=GapSeverity.LOW,
                        message=f"{len(orphaned)} open tasks without milestone/plan",
                        suggestion="Organize work: create milestones or projects",
                        context={
                            "count": len(orphaned),
                            "task_ids": [t["id"] for t in orphaned[:10]],
                        },
                        fixable=False,  # Requires planning
                    )
                )

        except Exception:
            # Backend not available
            pass

        return gaps

    def _detect_unannotated_files(self) -> list[Gap]:
        """Detect recently created files without annotations.

        Pattern: New files without annotations → harder to discover.
        """
        from idlergear.file_registry import FileRegistry

        gaps: list[Gap] = []

        try:
            registry = FileRegistry()

            # Get files created in past week
            since = datetime.now(timezone.utc) - timedelta(days=7)
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--diff-filter=A",
                    f"--since={since.isoformat()}",
                    "--name-only",
                    "--format=",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return gaps

            new_files = [
                f for f in result.stdout.strip().split("\n") if f and f.endswith(".py")
            ]

            if not new_files:
                return gaps

            # Check which files lack annotations
            unannotated = []
            for file_path in new_files:
                full_path = self.project_root / file_path
                if full_path.exists():
                    entry = registry.get_file(file_path)
                    if not entry or not entry.get("description"):
                        unannotated.append(file_path)

            if len(unannotated) >= 3:  # Threshold: 3+ files
                gaps.append(
                    Gap(
                        type=GapType.UNANNOTATED_FILES,
                        severity=GapSeverity.INFO,
                        message=f"{len(unannotated)} new files without annotations",
                        suggestion="Annotate files for better discovery: idlergear file annotate <file> --description '...'",
                        context={
                            "count": len(unannotated),
                            "files": unannotated[:5],
                        },
                        fixable=False,  # Requires manual annotation
                    )
                )

        except Exception:
            # Git or registry not available
            pass

        return gaps

    def _has_reference(self, topic: str) -> bool:
        """Check if reference documentation exists for topic.

        Args:
            topic: Topic to search for

        Returns:
            True if reference exists
        """
        try:
            # Check wiki for references
            wiki_dir = self.project_root / ".wiki"
            if not wiki_dir.exists():
                return False

            # Search markdown files for topic
            for md_file in wiki_dir.glob("**/*.md"):
                content = md_file.read_text().lower()
                if topic in content:
                    return True

        except Exception:
            pass

        return False
