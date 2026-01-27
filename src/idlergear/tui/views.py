"""Implementations of all 6 organizational views."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from textual.widgets import Tree

from idlergear.config import find_idlergear_root
from idlergear.tasks import list_tasks, get_tasks_dir
from idlergear.notes import list_notes
from idlergear.reference import list_references
from idlergear.file_registry import FileRegistry

from .base_view import BaseView


class ByTypeView(BaseView):
    """View 1: Organize by knowledge type (tasks, notes, references, files)."""

    def __init__(self, project_root=None, **kwargs):
        super().__init__(
            view_id=1, view_name="By Type", project_root=project_root, **kwargs
        )

    def compose_tree(self) -> Tree[dict]:
        """Organize by type: tasks, notes, references, files."""
        root = Tree("📚 Knowledge Base (By Type)")
        root.data = {}
        root.root.expand()  # Expand root node by default

        # Tasks organized by priority
        tasks = self.data.get("tasks", [])
        if tasks:
            task_node = root.root.add("📋 Tasks", data={"type": "tasks"}, expand=True)

            # Group by priority
            by_priority = {
                "critical": [],
                "high": [],
                "medium": [],
                "low": [],
                "none": [],
            }
            for task in tasks:
                priority = task.get("priority") or "none"
                by_priority[priority].append(task)

            for priority in ["critical", "high", "medium", "low", "none"]:
                tasks_in_priority = by_priority[priority]
                if tasks_in_priority:
                    priority_label = (
                        priority.upper() if priority != "none" else "No Priority"
                    )
                    priority_node = task_node.add(
                        f"[{priority_label}] ({len(tasks_in_priority)})",
                        data={"type": "priority", "priority": priority},
                    )
                    for task in tasks_in_priority[:10]:  # Limit to 10 per priority
                        priority_node.add_leaf(
                            f"#{task['id']} {task['title']}",
                            data={"type": "task", "task": task},
                        )

        # Notes organized by tags
        notes = self.data.get("notes", [])
        if notes:
            note_node = root.root.add("📝 Notes", data={"type": "notes"}, expand=True)

            # Group by tags
            by_tag = {}
            for note in notes:
                tags = note.get("tags", [])
                if not tags:
                    tags = ["untagged"]
                for tag in tags:
                    if tag not in by_tag:
                        by_tag[tag] = []
                    by_tag[tag].append(note)

            for tag, tag_notes in sorted(by_tag.items()):
                tag_node = note_node.add(
                    f"#{tag} ({len(tag_notes)})", data={"type": "tag", "tag": tag}
                )
                for note in tag_notes[:10]:  # Limit to 10 per tag
                    # Extract first line of content as title
                    content = note.get('content', '')
                    title = content.split('\n')[0][:50] if content else f"Note {note['id']}"
                    tag_node.add_leaf(
                        f"#{note['id']} {title}",
                        data={"type": "note", "note": note},
                    )

        # References organized by category
        references = self.data.get("references", [])
        if references:
            ref_node = root.root.add(
                "📖 References", data={"type": "references"}, expand=False
            )
            for ref in references[:20]:  # Limit to 20
                ref_node.add_leaf(
                    ref.get("title", "Untitled"),
                    data={"type": "reference", "reference": ref},
                )

        # Files organized by directory
        files = self.data.get("files", [])
        if files:
            file_node = root.root.add(
                "📁 Annotated Files", data={"type": "files"}, expand=False
            )

            # Group by directory
            by_dir = {}
            for file_info in files:
                path = Path(file_info.get("path", ""))
                dir_name = str(path.parent) if path.parent != Path(".") else "root"
                if dir_name not in by_dir:
                    by_dir[dir_name] = []
                by_dir[dir_name].append(file_info)

            for dir_name, dir_files in sorted(by_dir.items()):
                dir_node = file_node.add(
                    f"{dir_name}/ ({len(dir_files)})",
                    data={"type": "directory", "path": dir_name},
                )
                for file_info in dir_files[:10]:
                    dir_node.add_leaf(
                        Path(file_info["path"]).name,
                        data={"type": "file", "file": file_info},
                    )

        return root

    async def refresh_data(self) -> None:
        """Load all knowledge types."""
        self.logger.info(f"refresh_data() - ByTypeView starting data load")
        project_path = self.project_root or find_idlergear_root()
        if not project_path:
            self.logger.warning(f"refresh_data() - No project_root found, skipping data load")
            return

        # Build complete data dict first, then assign once to avoid multiple tree rebuilds
        data = {}

        # Load tasks
        try:
            self.logger.debug(f"refresh_data() - Loading tasks from {project_path}")
            tasks = list_tasks(state="open", project_path=project_path)
            data["tasks"] = tasks
            self.logger.debug(f"refresh_data() - Loaded {len(tasks)} tasks")
        except Exception as e:
            self.logger.error(f"refresh_data() - Error loading tasks: {e}", exc_info=True)
            data["tasks"] = []

        # Load notes
        try:
            self.logger.debug(f"refresh_data() - Loading notes from {project_path}")
            notes = list_notes(project_path=project_path)
            data["notes"] = notes
            self.logger.debug(f"refresh_data() - Loaded {len(notes)} notes")
        except Exception as e:
            self.logger.error(f"refresh_data() - Error loading notes: {e}", exc_info=True)
            data["notes"] = []

        # Load references
        try:
            self.logger.debug(f"refresh_data() - Loading references from {project_path}")
            references = list_references(project_path=project_path)
            data["references"] = references
            self.logger.debug(f"refresh_data() - Loaded {len(references)} references")
        except Exception as e:
            self.logger.error(f"refresh_data() - Error loading references: {e}", exc_info=True)
            data["references"] = []

        # Load files
        try:
            self.logger.debug(f"refresh_data() - Loading files from registry")
            registry = FileRegistry()
            file_entries = registry.list_files()
            # Convert FileEntry objects to dicts for display
            files = [
                {
                    "path": entry.path,
                    "description": entry.description,
                    "tags": entry.tags,
                    "components": entry.components,
                }
                for entry in file_entries
            ]
            data["files"] = files
            self.logger.debug(f"refresh_data() - Loaded {len(files)} files")
        except Exception as e:
            self.logger.error(f"refresh_data() - Error loading files: {e}", exc_info=True)
            data["files"] = []

        # Assign complete data dict once to trigger single tree rebuild
        self.data = data
        self.logger.info(f"refresh_data() - ByTypeView data load complete")


class ByProjectView(BaseView):
    """View 2: Organize by project/milestone."""

    def __init__(self, project_root=None, **kwargs):
        super().__init__(
            view_id=2, view_name="By Project", project_root=project_root, **kwargs
        )

    def compose_tree(self) -> Tree[dict]:
        """Organize by project."""
        root = Tree("📊 Knowledge Base (By Project)")
        root.data = {}

        # Group tasks by milestone
        tasks = self.data.get("tasks", [])
        by_milestone = {}

        for task in tasks:
            milestone = task.get("milestone") or "No Milestone"
            if milestone not in by_milestone:
                by_milestone[milestone] = []
            by_milestone[milestone].append(task)

        for milestone, milestone_tasks in sorted(by_milestone.items()):
            milestone_node = root.root.add(
                f"{milestone} ({len(milestone_tasks)})",
                data={"type": "milestone", "milestone": milestone},
                expand=True if milestone != "No Milestone" else False,
            )
            for task in milestone_tasks[:20]:
                milestone_node.add_leaf(
                    f"#{task['id']} {task['title']}",
                    data={"type": "task", "task": task},
                )

        return root

    async def refresh_data(self) -> None:
        """Load project data."""
        self.logger.info(f"refresh_data() - ByProjectView starting data load")
        project_path = self.project_root or find_idlergear_root()
        if not project_path:
            self.logger.warning(f"refresh_data() - No project_root found, skipping data load")
            return

        try:
            self.logger.debug(f"refresh_data() - Loading tasks from {project_path}")
            tasks = list_tasks(state="open", project_path=project_path)
            self.data = {"tasks": tasks}
            self.logger.debug(f"refresh_data() - Loaded {len(tasks)} tasks")
        except Exception as e:
            self.logger.error(f"refresh_data() - Error loading tasks: {e}", exc_info=True)
            self.data = {"tasks": []}

        self.logger.info(f"refresh_data() - ByProjectView data load complete")


class ByTimeView(BaseView):
    """View 3: Organize by time (today, this week, this month)."""

    def __init__(self, project_root=None, **kwargs):
        super().__init__(
            view_id=3, view_name="By Time", project_root=project_root, **kwargs
        )

    def compose_tree(self) -> Tree[dict]:
        """Organize by time."""
        root = Tree("🕐 Knowledge Base (By Time)")
        root.data = {}

        now = datetime.now(timezone.utc)
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Categorize tasks by time
        today_items = []
        week_items = []
        month_items = []
        older_items = []

        tasks = self.data.get("tasks", [])
        for task in tasks:
            created_str = task.get("created")
            if not created_str:
                older_items.append(task)
                continue

            try:
                created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                if created.date() == today:
                    today_items.append(task)
                elif created >= week_ago:
                    week_items.append(task)
                elif created >= month_ago:
                    month_items.append(task)
                else:
                    older_items.append(task)
            except:
                older_items.append(task)

        # Add time-based nodes
        if today_items:
            today_node = root.root.add(f"Today ({len(today_items)})", expand=True)
            for task in today_items[:20]:
                today_node.add_leaf(
                    f"#{task['id']} {task['title']}",
                    data={"type": "task", "task": task},
                )

        if week_items:
            week_node = root.root.add(f"This Week ({len(week_items)})", expand=True)
            for task in week_items[:20]:
                week_node.add_leaf(
                    f"#{task['id']} {task['title']}",
                    data={"type": "task", "task": task},
                )

        if month_items:
            month_node = root.root.add(f"This Month ({len(month_items)})", expand=False)
            for task in month_items[:20]:
                month_node.add_leaf(
                    f"#{task['id']} {task['title']}",
                    data={"type": "task", "task": task},
                )

        if older_items:
            older_node = root.root.add(f"Older ({len(older_items)})", expand=False)
            for task in older_items[:20]:
                older_node.add_leaf(
                    f"#{task['id']} {task['title']}",
                    data={"type": "task", "task": task},
                )

        return root

    async def refresh_data(self) -> None:
        """Load time-based data."""
        self.logger.info(f"refresh_data() - ByTimeView starting data load")
        project_path = self.project_root or find_idlergear_root()
        if not project_path:
            self.logger.warning(f"refresh_data() - No project_root found, skipping data load")
            return

        try:
            self.logger.debug(f"refresh_data() - Loading tasks from {project_path}")
            tasks = list_tasks(state="open", project_path=project_path)
            self.data = {"tasks": tasks}
            self.logger.debug(f"refresh_data() - Loaded {len(tasks)} tasks")
        except Exception as e:
            self.logger.error(f"refresh_data() - Error loading tasks: {e}", exc_info=True)
            self.data = {"tasks": []}

        self.logger.info(f"refresh_data() - ByTimeView data load complete")


class GapsView(BaseView):
    """View 4: Knowledge gaps."""

    def __init__(self, project_root=None, **kwargs):
        super().__init__(
            view_id=4, view_name="Gaps", project_root=project_root, **kwargs
        )

    def compose_tree(self) -> Tree[dict]:
        """Show knowledge gaps."""
        root = Tree("🔍 Knowledge Gaps")
        root.data = {}

        gaps = self.data.get("gaps", [])
        if not gaps:
            root.root.add_leaf("No knowledge gaps detected")
        else:
            # Group by severity
            by_severity = {"high": [], "medium": [], "low": []}
            for gap in gaps:
                severity = gap.get("severity", "low")
                by_severity[severity].append(gap)

            for severity in ["high", "medium", "low"]:
                gaps_in_severity = by_severity[severity]
                if gaps_in_severity:
                    severity_node = root.root.add(
                        f"{severity.upper()} ({len(gaps_in_severity)})",
                        expand=(severity == "high"),
                    )
                    for gap in gaps_in_severity[:20]:
                        severity_node.add_leaf(
                            gap.get("description", "Unknown gap"),
                            data={"type": "gap", "gap": gap},
                        )

        return root

    async def refresh_data(self) -> None:
        """Load gap data."""
        self.logger.info(f"refresh_data() - GapsView starting gap detection")
        from idlergear.gaps import detect_gaps

        project_path = self.project_root or find_idlergear_root()
        if not project_path:
            self.logger.warning(f"refresh_data() - No project_root found, skipping gap detection")
            self.data = {"gaps": []}
            return

        # Detect knowledge gaps
        self.logger.debug(f"refresh_data() - Running gap detection on {project_path}")
        gaps = detect_gaps(project_path)
        self.logger.debug(f"refresh_data() - Detected {len(gaps)} gaps")

        # Convert to dict format for tree
        gap_dicts = [
            {
                "type": gap.type,
                "severity": gap.severity,
                "location": gap.location,
                "description": gap.description,
                "suggestion": gap.suggestion,
            }
            for gap in gaps
        ]

        self.data = {"gaps": gap_dicts}
        self.logger.info(f"refresh_data() - GapsView gap detection complete")


class ActivityView(BaseView):
    """View 5: Recent activity feed."""

    def __init__(self, project_root=None, **kwargs):
        super().__init__(
            view_id=5, view_name="Activity", project_root=project_root, **kwargs
        )

    def compose_tree(self) -> Tree[dict]:
        """Show recent activity and suggestions."""
        root = Tree("📅 Activity & Suggestions")
        root.data = {}

        # Show suggestions first (most important)
        suggestions = self.data.get("suggestions", [])
        if suggestions:
            sugg_node = root.root.add("💡 Suggested Next Steps", expand=True)
            for i, suggestion in enumerate(suggestions[:5], 1):
                priority = suggestion.get("priority", 0)
                confidence = int(suggestion.get("confidence", 0.0) * 100)
                title = suggestion.get("title", "")
                sugg_node.add_leaf(f"{i}. [{priority}/10, {confidence}%] {title}")
        else:
            root.root.add_leaf("No suggestions at this time")

        # TODO: Add recent events (task updates, note creation, etc.)

        return root

    async def refresh_data(self) -> None:
        """Load activity data and suggestions."""
        self.logger.info(f"refresh_data() - ActivityView starting suggestion generation")
        from idlergear.suggestions import generate_suggestions

        project_path = self.project_root or find_idlergear_root()
        if not project_path:
            self.logger.warning(f"refresh_data() - No project_root found, skipping suggestions")
            self.data = {"suggestions": []}
            return

        # Generate suggestions
        self.logger.debug(f"refresh_data() - Generating suggestions for {project_path}")
        suggestions = generate_suggestions(project_path)
        self.logger.debug(f"refresh_data() - Generated {len(suggestions)} suggestions")

        # Convert to dict format
        suggestion_dicts = [
            {
                "type": s.type,
                "priority": s.priority,
                "title": s.title,
                "description": s.description,
                "action": s.action,
                "reason": s.reason,
                "confidence": s.confidence,
            }
            for s in suggestions[:5]  # Top 5
        ]

        self.data = {"suggestions": suggestion_dicts}
        self.logger.info(f"refresh_data() - ActivityView suggestion generation complete")


class AIMonitorView(BaseView):
    """View 6: AI Activity Monitor - real-time AI state visibility."""

    def __init__(self, project_root=None, **kwargs):
        super().__init__(
            view_id=6, view_name="AI Monitor", project_root=project_root, **kwargs
        )
        self._daemon_client = None

    def compose_tree(self) -> Tree[dict]:
        """Show AI monitoring data."""
        root = Tree("🤖 AI Activity Monitor")
        root.data = {}

        agents = self.data.get("agents", [])
        if not agents:
            root.root.add_leaf("No active AI assistants")
            root.root.add_leaf("")
            root.root.add_leaf("Start an AI session to see real-time activity")
        else:
            for agent in agents:
                agent_node = root.root.add(
                    f"🤖 {agent.get('agent_type', 'Unknown')} - {agent.get('status', 'unknown')}",
                    expand=True,
                )

                # Current activity
                ai_state = agent.get("ai_state", {})
                current_activity = ai_state.get("current_activity")
                if current_activity:
                    activity_node = agent_node.add("📍 Current Activity", expand=True)
                    activity_node.add_leaf(
                        f"Phase: {current_activity.get('phase', 'unknown')}"
                    )
                    activity_node.add_leaf(
                        f"Action: {current_activity.get('action', 'unknown')}"
                    )
                    if current_activity.get("task_id"):
                        activity_node.add_leaf(f"Task: #{current_activity['task_id']}")
                    if current_activity.get("target"):
                        activity_node.add_leaf(f"Target: {current_activity['target']}")
                    if current_activity.get("reason"):
                        activity_node.add_leaf(f"Reason: {current_activity['reason']}")

                # Planned steps
                planned_steps = ai_state.get("planned_steps")
                if planned_steps and isinstance(planned_steps, dict):
                    steps = planned_steps.get("steps", [])
                    confidence = planned_steps.get("confidence", 1.0)

                    if steps:
                        plan_node = agent_node.add(
                            f"📋 Planned Steps (confidence: {confidence:.0%})",
                            expand=(confidence < 0.7),
                        )
                        for i, step in enumerate(steps[:5], 1):
                            step_text = f"{i}. {step.get('action', 'unknown')}"
                            if step.get("path"):
                                step_text += f": {step['path']}"
                            plan_node.add_leaf(step_text)

                        if confidence < 0.7:
                            plan_node.add_leaf(
                                "⚠️ LOW CONFIDENCE - Consider intervention"
                            )

                # Uncertainties
                uncertainties = ai_state.get("uncertainties", [])
                if uncertainties:
                    unc_node = agent_node.add(
                        f"❓ Uncertainties ({len(uncertainties)})", expand=True
                    )
                    for uncertainty in uncertainties[-3:]:  # Last 3
                        conf = uncertainty.get("confidence", 1.0)
                        question = uncertainty.get("question", "Unknown")
                        unc_node.add_leaf(f"[{conf:.0%}] {question}")
                        if conf < 0.5:
                            unc_node.add_leaf("  ⚠️ INTERVENTION RECOMMENDED")

                # Search history
                search_history = ai_state.get("search_history", [])
                if search_history:
                    search_node = agent_node.add(
                        f"🔍 Recent Searches ({len(search_history)})", expand=False
                    )

                    # Detect repeated searches
                    queries = [s.get("query") for s in search_history if s.get("query")]
                    query_counts = {}
                    for q in queries:
                        query_counts[q] = query_counts.get(q, 0) + 1

                    repeated = [q for q, count in query_counts.items() if count >= 2]
                    if repeated:
                        search_node.add_leaf(f"⚠️ Repeated: {', '.join(repeated[:3])}")

                    for search in search_history[-5:]:  # Last 5
                        query = search.get("query", "unknown")
                        results = search.get("results_found", 0)
                        search_node.add_leaf(f"{query} ({results} results)")

        return root

    async def refresh_data(self) -> None:
        """Load AI monitoring data from daemon."""
        self.logger.info(f"refresh_data() - AIMonitorView querying daemon for AI agents")
        from idlergear.daemon.client import get_daemon_client, DaemonNotRunning

        project_path = self.project_root or find_idlergear_root()
        if not project_path:
            self.logger.warning(f"refresh_data() - No project_root found, skipping daemon query")
            self.data = {"agents": []}
            return

        try:
            if self._daemon_client is None:
                self.logger.debug(f"refresh_data() - Creating daemon client")
                self._daemon_client = get_daemon_client(project_path)

            # Get list of active agents
            self.logger.debug(f"refresh_data() - Calling agent.list on daemon")
            response = await self._daemon_client.call("agent.list", {})
            agents = response.get("agents", [])
            self.logger.debug(f"refresh_data() - Received {len(agents)} active AI agents")
            self.data = {"agents": agents}
            self.logger.info(f"refresh_data() - AIMonitorView daemon query complete")
        except DaemonNotRunning:
            self.logger.warning(f"refresh_data() - Daemon not running")
            self.data = {"agents": [], "error": "Daemon not running"}
        except Exception as e:
            self.logger.error(f"refresh_data() - Error querying daemon: {e}", exc_info=True)
            self.data = {"agents": [], "error": str(e)}

    def on_mount(self) -> None:
        """Subscribe to AI state updates when mounted."""
        super().on_mount()

        # Note: Daemon broadcast subscription is handled at the app level (app_v2.py:245-277)
        # The app listens for ai.activity_changed, ai.plan_updated, ai.uncertainty_detected,
        # and ai.search_repeated events, then refreshes this view automatically.
        # Manual refresh is also available via 'r' key.
