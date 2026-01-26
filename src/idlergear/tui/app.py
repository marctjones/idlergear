"""Main IdlerGear TUI application."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.reactive import reactive
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)

# Import modals
from .modals import (
    TaskEditModal,
    ReferenceEditModal,
    MessageModal,
    CommandPalette,
    NoteViewModal,
    NotePromoteModal,
    ConfirmDeleteModal,
    BulkActionModal,
    QuickSelectModal,
)

# Import logging
from .logging_config import setup_tui_logging, get_logger


class KnowledgeOverview(Static):
    """Dashboard showing overview of all knowledge types."""

    stats: reactive[dict[str, Any]] = reactive({})

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("📊 Knowledge Base Overview", classes="header")
        yield Static(id="stats-display")

    def watch_stats(self, stats: dict[str, Any]) -> None:
        """Update stats display when stats change."""
        if not stats:
            return

        lines = [
            "┌─────────────────────────────────────────────┐",
            "│ [bold cyan]Knowledge Type[/]      "
            "[bold yellow]Count[/]   [bold green]Status[/]   │",
            "├─────────────────────────────────────────────┤",
        ]

        items = [
            (
                "📋 Tasks",
                stats.get("tasks", 0),
                "open" if stats.get("tasks", 0) > 0 else "none",
            ),
            (
                "📝 Notes",
                stats.get("notes", 0),
                "active" if stats.get("notes", 0) > 0 else "none",
            ),
            (
                "🎯 Vision",
                "1" if stats.get("has_vision") else "0",
                "set" if stats.get("has_vision") else "missing",
            ),
            (
                "📊 Projects",
                stats.get("projects", 0),
                "active" if stats.get("projects", 0) > 0 else "none",
            ),
            (
                "📖 References",
                stats.get("references", 0),
                "docs" if stats.get("references", 0) > 0 else "empty",
            ),
            (
                "📁 Annotated Files",
                stats.get("files", 0),
                "tracked" if stats.get("files", 0) > 0 else "none",
            ),
            (
                "🕸️  Graph Nodes",
                stats.get("graph_nodes", 0),
                "populated" if stats.get("graph_nodes", 0) > 0 else "empty",
            ),
            (
                "🔄 Daemon",
                "1" if stats.get("daemon_running") else "0",
                "[green]running[/]"
                if stats.get("daemon_running")
                else "[red]stopped[/]",
            ),
        ]

        for name, count, status in items:
            lines.append(f"│ {name:<20} {str(count):>6}   {status:<8} │")

        lines.append("└─────────────────────────────────────────────┘")

        # Add gap detection summary
        gaps = stats.get("gaps", {})
        if gaps:
            total = gaps.get("total", 0)
            critical = gaps.get("critical", 0)
            high = gaps.get("high", 0)

            lines.append("")
            if critical > 0:
                lines.append(f"⚠️  [bold red]{critical} CRITICAL gaps detected![/]")
            elif high > 0:
                lines.append(f"⚠️  [bold yellow]{high} HIGH priority gaps detected[/]")
            elif total > 0:
                lines.append(f"ℹ️  {total} knowledge gaps detected")
            else:
                lines.append("✅ [green]No critical knowledge gaps![/]")

        display = self.query_one("#stats-display", Static)
        display.update("\n".join(lines))


class TaskBrowser(Static):
    """Browse and filter tasks."""

    tasks: reactive[list[dict[str, Any]]] = reactive([])
    selected_tasks: reactive[set[int]] = reactive(set())

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label(
            "📋 Task Browser - [Enter] Edit [s] State [p] Priority "
            "[a] Assign [n] New [Space] Select",
            classes="header",
        )
        yield DataTable(id="task-table")

    def on_mount(self) -> None:
        """Set up the task table."""
        table = self.query_one("#task-table", DataTable)
        table.add_columns("✓", "ID", "Title", "Priority", "State", "Labels")
        table.cursor_type = "row"
        table.zebra_stripes = True

    def watch_tasks(self, tasks: list[dict[str, Any]]) -> None:
        """Update task display when tasks change."""
        table = self.query_one("#task-table", DataTable)
        table.clear()

        for task in tasks:
            task_id = task.get("id", "")
            is_selected = task_id in self.selected_tasks

            priority = task.get("priority", "medium")
            priority_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
                "backlog": "⚪",
            }.get(priority, "⚫")

            labels = task.get("labels", [])
            labels_str = ", ".join(labels[:3])
            if len(labels) > 3:
                labels_str += f" (+{len(labels) - 3})"

            table.add_row(
                "☑" if is_selected else "☐",
                str(task_id),
                task.get("title", ""),
                f"{priority_icon} {priority}",
                task.get("state", "open"),
                labels_str,
            )

    def get_selected_task(self) -> dict[str, Any] | None:
        """Get the currently highlighted task."""
        table = self.query_one("#task-table", DataTable)
        if table.cursor_row < len(self.tasks):
            return self.tasks[table.cursor_row]
        return None

    def toggle_selection(self) -> None:
        """Toggle selection of current task."""
        task = self.get_selected_task()
        if task:
            task_id = task.get("id")
            if task_id in self.selected_tasks:
                self.selected_tasks.remove(task_id)
            else:
                self.selected_tasks.add(task_id)
            self.watch_tasks(self.tasks)  # Refresh display


class NoteBrowser(Static):
    """Browse notes and explorations."""

    notes: reactive[list[dict[str, Any]]] = reactive([])

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label(
            "📝 Notes & Explorations - [Enter] View [p] Promote [n] New [x] Delete",
            classes="header",
        )
        yield DataTable(id="note-table")

    def on_mount(self) -> None:
        """Set up the note table."""
        table = self.query_one("#note-table", DataTable)
        table.add_columns("ID", "Type", "Content Preview", "Tags", "Created")
        table.cursor_type = "row"
        table.zebra_stripes = True

    def watch_notes(self, notes: list[dict[str, Any]]) -> None:
        """Update note display when notes change."""
        table = self.query_one("#note-table", DataTable)
        table.clear()

        for note in notes:
            content = note.get("title", "") or note.get("body", "")
            preview = content[:50] + "..." if len(content) > 50 else content

            labels = [
                label for label in note.get("labels", []) if label.startswith("tag:")
            ]
            tags = ", ".join([label.replace("tag:", "") for label in labels])

            note_type = (
                "🔍 Explore" if "tag:explore" in note.get("labels", []) else "💡 Note"
            )

            created = note.get("created", "")
            if created:
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    created = dt.strftime("%Y-%m-%d")
                except Exception:
                    pass

            table.add_row(
                str(note.get("id", "")),
                note_type,
                preview,
                tags,
                created,
            )

    def get_selected_note(self) -> dict[str, Any] | None:
        """Get the currently highlighted note."""
        table = self.query_one("#note-table", DataTable)
        if table.cursor_row < len(self.notes):
            return self.notes[table.cursor_row]
        return None


class KnowledgeGraph(Static):
    """Visualize knowledge graph structure."""

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("🕸️  Knowledge Graph Explorer", classes="header")
        yield Tree("Knowledge Graph")

    def on_mount(self) -> None:
        """Initialize the graph tree."""
        tree = self.query_one(Tree)
        tree.show_root = True
        tree.show_guides = True


class GapAlerts(Static):
    """Show knowledge gap alerts and suggestions."""

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("⚠️  Knowledge Gaps & Suggestions", classes="header")
        yield VerticalScroll(Static(id="gaps-content"))

    def update_gaps(self, gaps: list[dict[str, Any]]) -> None:
        """Update gap display."""
        content = self.query_one("#gaps-content", Static)

        if not gaps:
            content.update(
                "[green]✅ No knowledge gaps detected!\n\n"
                "Your project knowledge base is healthy.[/]"
            )
            return

        lines = []
        for gap in gaps[:10]:  # Show top 10
            severity = gap.get("severity", "info")
            message = gap.get("message", "")
            suggestion = gap.get("suggestion", "")

            icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🔵",
                "info": "ℹ️ ",
            }.get(severity, "•")

            color = {
                "critical": "red",
                "high": "yellow",
                "medium": "yellow",
                "low": "blue",
                "info": "cyan",
            }.get(severity, "white")

            lines.append(f"{icon} [{color}]{message}[/]")
            lines.append(f"   → {suggestion}")
            lines.append("")

        content.update("\n".join(lines))


class DaemonMonitor(Static):
    """Monitor daemon status, active AI assistants, and MCP sessions."""

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("🔄 Multi-Agent Coordination", classes="header")
        yield VerticalScroll(Static(id="daemon-status"))

    def update_daemon_status(self, status: dict[str, Any]) -> None:
        """Update daemon status and agent details display."""
        container = self.query_one(VerticalScroll)
        display = container.query_one("#daemon-status", Static)

        if not status.get("running"):
            display.update(
                "[red]● Daemon not running[/]\n\n"
                "Start with: [cyan]idlergear daemon start[/]\n\n"
                "The daemon enables:\n"
                "  • Multi-agent coordination\n"
                "  • Session monitoring across AI assistants\n"
                "  • Command queue for background tasks\n"
                "  • Message broadcasting between agents"
            )
            return

        lines = [
            "[green bold]● Daemon Running[/]",
            "",
            f"[dim]PID:[/] {status.get('pid', 'unknown')}",
            f"[dim]Uptime:[/] {status.get('uptime', 'unknown')}",
            f"[dim]Socket:[/] {status.get('socket_path', 'unknown')}",
            "",
            "━" * 60,
            "",
        ]

        agents = status.get("agents", [])
        queue = status.get("queue", [])

        # Show active AI assistants
        lines.append(f"[bold cyan]Active AI Assistants ({len(agents)}):[/]")
        lines.append("")

        if agents:
            for agent in agents:
                agent_type = agent.get("agent_type", "unknown")
                agent_id = agent.get("agent_id", "unknown")
                agent_status = agent.get("status", "unknown")

                # Status color
                status_colors = {
                    "active": "green",
                    "idle": "yellow",
                    "busy": "cyan",
                }
                status_color = status_colors.get(agent_status, "white")

                lines.append(f"[bold white]{agent_type.upper()}[/] ({agent_id})")
                lines.append(
                    f"  [dim]Status:[/] [{status_color}]{agent_status}[/{status_color}]"
                )

                # Session information
                session_id = agent.get("session_id")
                session_name = agent.get("session_name")
                if session_id:
                    lines.append(
                        f"  [dim]Session:[/] {session_name or session_id[:12]}"
                    )

                # Current task
                task_id = agent.get("current_task_id")
                if task_id:
                    lines.append(f"  [dim]Working on task:[/] #{task_id}")

                # Working files
                working_files = agent.get("working_files", [])
                if working_files:
                    files_preview = ", ".join([Path(f).name for f in working_files[:3]])
                    if len(working_files) > 3:
                        files_preview += f" (+{len(working_files) - 3} more)"
                    lines.append(f"  [dim]Files:[/] {files_preview}")

                # Capabilities (MCP tools, etc.)
                capabilities = agent.get("capabilities", [])
                if capabilities:
                    caps_preview = ", ".join(capabilities[:3])
                    if len(capabilities) > 3:
                        caps_preview += f" (+{len(capabilities) - 3} more)"
                    lines.append(f"  [dim]Capabilities:[/] {caps_preview}")

                # Connection info
                connected_at = agent.get("connected_at", "unknown")
                if connected_at and connected_at != "unknown":
                    # Format timestamp nicely
                    try:
                        from datetime import datetime

                        dt = datetime.fromisoformat(connected_at.replace("Z", "+00:00"))
                        time_str = dt.strftime("%H:%M:%S")
                        lines.append(f"  [dim]Connected:[/] {time_str}")
                    except Exception:
                        lines.append(f"  [dim]Connected:[/] {connected_at}")

                lines.append("")

        else:
            lines.append("[dim]  No AI assistants currently connected[/]")
            lines.append("")
            lines.append("  Connect an AI assistant with IdlerGear MCP integration:")
            lines.append("    • Claude Code (automatic)")
            lines.append("    • Goose (if configured)")
            lines.append("    • Other MCP-enabled assistants")
            lines.append("")

        # Show command queue
        lines.append("━" * 60)
        lines.append("")
        lines.append(f"[bold cyan]Command Queue ({len(queue)}):[/]")
        lines.append("")

        if queue:
            for cmd in queue[:5]:  # Show first 5
                cmd_status = cmd.get("status", "unknown")
                priority = cmd.get("priority", 0)
                command = cmd.get("command", "")

                # Truncate long commands
                if len(command) > 50:
                    command = command[:47] + "..."

                status_icons = {
                    "pending": "⏳",
                    "in_progress": "▶️",
                    "completed": "✅",
                    "failed": "❌",
                }
                icon = status_icons.get(cmd_status, "❓")

                lines.append(f"  {icon} [priority={priority}] {command}")

            if len(queue) > 5:
                lines.append(f"  [dim]... and {len(queue) - 5} more[/]")
        else:
            lines.append("[dim]  No queued commands[/]")

        lines.append("")
        lines.append("━" * 60)
        lines.append("")
        lines.append("[dim]Press 'r' to refresh[/]")

        display.update("\n".join(lines))


class IdlerGearApp(App):
    """IdlerGear TUI - Interactive knowledge base explorer."""

    CSS = """
    Screen {
        background: $surface;
    }

    .header {
        background: $primary;
        color: $text;
        padding: 1;
        text-align: center;
        text-style: bold;
    }

    TabbedContent {
        height: 100%;
    }

    TabPane {
        padding: 1 2;
    }

    DataTable {
        height: 100%;
    }

    Tree {
        height: 100%;
    }

    #stats-display {
        padding: 1 2;
    }

    #gaps-content {
        height: 100%;
        padding: 1 2;
    }

    #daemon-status {
        padding: 1 2;
    }
    """

    BINDINGS = [
        # Global actions
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh", "Refresh"),
        Binding("/", "command_palette", "Commands"),
        Binding("?", "help", "Help"),
        # Navigation
        Binding("g", "show_gaps", "Gaps"),
        Binding("d", "show_daemon", "Daemon"),
        Binding("t", "show_tasks", "Tasks"),
        Binding("n", "show_notes", "Notes"),
        # Task actions (context-sensitive)
        Binding("enter", "edit_task", "Edit Task", show=False),
        Binding("space", "toggle_selection", "Select", show=False),
        Binding("s", "change_state", "State", show=False),
        Binding("p", "change_priority", "Priority", show=False),
        Binding("a", "assign_agent", "Assign", show=False),
        Binding("l", "edit_labels", "Labels", show=False),
        Binding("x", "delete_item", "Delete", show=False),
        # Creation actions
        Binding("ctrl+n", "create_task", "New Task"),
        Binding("ctrl+r", "create_reference", "New Reference"),
        Binding("ctrl+e", "create_note", "New Note"),
        # Bulk operations
        Binding("ctrl+b", "bulk_actions", "Bulk Actions", show=False),
        # Agent coordination
        Binding("b", "broadcast_message", "Broadcast", show=False),
        Binding("m", "send_message", "Message", show=False),
    ]

    TITLE = "IdlerGear TUI - Knowledge Base Explorer"

    def __init__(self, project_root: Path | None = None):
        """Initialize app.

        Args:
            project_root: Project root directory (defaults to cwd)
        """
        super().__init__()
        self.project_root = project_root or Path.cwd()

        # Initialize logging with project name
        project_name = self.project_root.name
        self.logger = setup_tui_logging(project_name=project_name)
        self.logger.info(f"TUI initialized for project root: {self.project_root}")

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Container(
            KnowledgeOverview(),
            id="overview-container",
        )
        with TabbedContent(id="main-tabs"):
            with TabPane("Tasks", id="tasks-tab"):
                yield TaskBrowser()
            with TabPane("Notes", id="notes-tab"):
                yield NoteBrowser()
            with TabPane("Graph", id="graph-tab"):
                yield KnowledgeGraph()
            with TabPane("Gaps", id="gaps-tab"):
                yield GapAlerts()
            with TabPane("Daemon", id="daemon-tab"):
                yield DaemonMonitor()
        yield Footer()

    def on_mount(self) -> None:
        """Load initial data when app starts."""
        self.load_all_data()

    def load_all_data(self) -> None:
        """Load data from IdlerGear project."""
        # Load statistics
        stats = self.load_stats()
        overview = self.query_one(KnowledgeOverview)
        overview.stats = stats

        # Load tasks
        self.load_tasks()

        # Load notes
        self.load_notes()

        # Load knowledge graph
        self.load_graph()

        # Load gaps
        self.load_gaps()

        # Load daemon status
        self.load_daemon_status()

    def load_stats(self) -> dict[str, Any]:
        """Load knowledge base statistics."""
        logger = get_logger()
        stats = {}

        try:
            logger.debug("Loading knowledge base statistics")
            from idlergear.backends.registry import get_backend
            from idlergear.config import find_idlergear_root

            root = find_idlergear_root()
            if root is None:
                return stats

            # Count tasks
            try:
                task_backend = get_backend("task", project_path=root)
                tasks = task_backend.list(state="open")
                stats["tasks"] = len(tasks)
            except Exception:
                stats["tasks"] = 0

            # Count notes
            try:
                note_backend = get_backend("note", project_path=root)
                notes = note_backend.list()
                stats["notes"] = len([n for n in notes if n.get("state") == "open"])
            except Exception:
                stats["notes"] = 0

            # Check vision
            vision_file = root / "VISION.md"
            stats["has_vision"] = vision_file.exists()

            # Count projects
            try:
                from idlergear.projects import list_projects

                projects = list_projects(project_path=root)
                stats["projects"] = len(projects)
            except Exception:
                stats["projects"] = 0

            # Count references (wiki pages)
            wiki_dir = root / ".wiki"
            if wiki_dir.exists():
                stats["references"] = len(list(wiki_dir.glob("*.md")))
            else:
                stats["references"] = 0

            # Count annotated files
            try:
                from idlergear.file_registry import FileRegistry

                registry = FileRegistry()
                entries = registry.list_files()
                stats["files"] = len([e for e in entries if e.get("description")])
            except Exception:
                stats["files"] = 0

            # Count graph nodes
            try:
                from idlergear.graph import get_database

                graph = get_database()
                result = graph.execute("MATCH (n) RETURN count(n) AS count")
                rows = result.get_as_df()
                if not rows.empty:
                    stats["graph_nodes"] = int(rows.iloc[0]["count"])
                else:
                    stats["graph_nodes"] = 0
            except Exception as e:
                get_logger().debug(f"Failed to count graph nodes: {e}")
                stats["graph_nodes"] = 0

            # Check daemon status
            try:
                from idlergear.daemon.lifecycle import DaemonLifecycle

                lifecycle = DaemonLifecycle(root)
                stats["daemon_running"] = lifecycle.is_running()
            except Exception:
                stats["daemon_running"] = False

            # Get gap summary
            try:
                from idlergear.gap_detector import GapDetector, GapSeverity

                detector = GapDetector(project_root=root)
                gaps = detector.detect_gaps()

                stats["gaps"] = {
                    "total": len(gaps),
                    "critical": len(
                        [g for g in gaps if g.severity == GapSeverity.CRITICAL]
                    ),
                    "high": len([g for g in gaps if g.severity == GapSeverity.HIGH]),
                    "medium": len(
                        [g for g in gaps if g.severity == GapSeverity.MEDIUM]
                    ),
                }
            except Exception as e:
                logger.debug(f"Failed to detect gaps: {e}")
                stats["gaps"] = {}

        except Exception as e:
            logger.error(f"Error loading stats: {e}", exc_info=True)
            self.notify(f"Error loading stats: {e}", severity="error")

        logger.info(
            f"Loaded stats: {stats.get('tasks', 0)} tasks, "
            f"{stats.get('notes', 0)} notes, "
            f"{stats.get('graph_nodes', 0)} graph nodes"
        )
        return stats

    def load_tasks(self) -> None:
        """Load tasks into the task browser."""
        logger = get_logger()
        try:
            logger.debug("Loading tasks")
            from idlergear.backends.registry import get_backend
            from idlergear.config import find_idlergear_root

            root = find_idlergear_root()
            if root is None:
                logger.warning("No IdlerGear root found")
                return

            task_backend = get_backend("task", project_path=root)
            tasks = task_backend.list(state="open")

            # Store tasks in TaskBrowser reactive variable
            task_browser = self.query_one(TaskBrowser)
            task_browser.tasks = tasks[:50]  # Limit to 50 for performance

            logger.info(f"Loaded {len(tasks[:50])} tasks (of {len(tasks)} total open)")

        except Exception as e:
            logger.error(f"Error loading tasks: {e}", exc_info=True)
            self.notify(f"Error loading tasks: {e}", severity="error")

    def load_notes(self) -> None:
        """Load notes into the note browser."""
        logger = get_logger()
        try:
            logger.debug("Loading notes")
            from idlergear.backends.registry import get_backend
            from idlergear.config import find_idlergear_root

            root = find_idlergear_root()
            if root is None:
                logger.warning("No IdlerGear root found")
                return

            note_backend = get_backend("note", project_path=root)
            notes = note_backend.list()

            # Filter open notes and store in NoteBrowser reactive variable
            open_notes = [n for n in notes if n.get("state") == "open"]
            note_browser = self.query_one(NoteBrowser)
            note_browser.notes = open_notes[:50]  # Limit to 50 for performance

            logger.info(
                f"Loaded {len(open_notes[:50])} notes (of {len(open_notes)} total open)"
            )

        except Exception as e:
            logger.error(f"Error loading notes: {e}", exc_info=True)
            self.notify(f"Error loading notes: {e}", severity="error")

    def load_graph(self) -> None:
        """Load knowledge graph structure."""
        logger = get_logger()
        try:
            from idlergear.config import find_idlergear_root
            from idlergear.graph import get_database

            root = find_idlergear_root()
            if root is None:
                return

            graph = get_database()

            tree = self.query_one(Tree)
            tree.clear()
            tree.root.label = "Knowledge Graph"

            # Add node type branches
            try:
                # Count each node type
                result = graph.execute(
                    "MATCH (n) RETURN labels(n) AS labels, count(n) AS count"
                )

                rows = result.get_as_df()
                for _, row in rows.iterrows():
                    labels = row["labels"]
                    count = row["count"]
                    if labels:
                        label_str = (
                            labels[0] if isinstance(labels, list) else str(labels)
                        )
                        tree.root.add_leaf(f"{label_str}: {count} nodes")

            except Exception as e:
                logger.debug(f"Empty graph or error: {e}")
                tree.root.add_leaf(
                    "(empty - populate with: idlergear graph populate-all)"
                )

            logger.info("Loaded knowledge graph structure")

        except Exception as e:
            logger.error(f"Error loading graph: {e}", exc_info=True)
            self.notify(f"Error loading graph: {e}", severity="error")

    def load_gaps(self) -> None:
        """Load knowledge gaps."""
        logger = get_logger()
        try:
            logger.debug("Loading knowledge gaps")
            from idlergear.config import find_idlergear_root
            from idlergear.gap_detector import GapDetector

            root = find_idlergear_root()
            if root is None:
                logger.warning("No IdlerGear root found")
                return

            detector = GapDetector(project_root=root)
            gaps = detector.detect_gaps()

            gap_alerts = self.query_one(GapAlerts)
            gap_alerts.update_gaps([g.to_dict() for g in gaps])

            logger.info(f"Loaded {len(gaps)} knowledge gaps")

        except Exception as e:
            logger.error(f"Error loading gaps: {e}", exc_info=True)
            self.notify(f"Error loading gaps: {e}", severity="error")

    def load_daemon_status(self) -> None:
        """Load daemon status."""
        logger = get_logger()

        async def _load_async() -> None:
            """Async helper to load daemon data."""
            try:
                from idlergear.config import find_idlergear_root
                from idlergear.daemon.client import DaemonClient

                root = find_idlergear_root()
                if root is None:
                    status = {"running": False}
                    daemon_monitor = self.query_one(DaemonMonitor)
                    daemon_monitor.update_daemon_status(status)
                    return

                # Check if daemon is running
                socket_path = root / ".idlergear" / "daemon" / "daemon.sock"
                if not socket_path.exists():
                    status = {"running": False}
                    daemon_monitor = self.query_one(DaemonMonitor)
                    daemon_monitor.update_daemon_status(status)
                    return

                # Connect and get full status
                try:
                    client = DaemonClient(socket_path)
                    await client.connect()

                    # Get daemon status (includes PID, uptime)
                    daemon_status = await client.status()

                    # Get list of active agents with session details
                    agents = await client.list_agents()

                    # Get command queue
                    queue = await client.queue_list()

                    await client.disconnect()

                    status = {
                        "running": True,
                        "pid": daemon_status.get("pid", "unknown"),
                        "uptime": daemon_status.get("uptime", "unknown"),
                        "socket_path": str(socket_path),
                        "agents": agents,
                        "queue": queue,
                    }

                    daemon_monitor = self.query_one(DaemonMonitor)
                    daemon_monitor.update_daemon_status(status)

                except Exception as e:
                    # Daemon socket exists but can't connect
                    logger.warning(f"Failed to connect to daemon: {e}")
                    status = {
                        "running": False,
                        "error": str(e),
                    }
                    daemon_monitor = self.query_one(DaemonMonitor)
                    daemon_monitor.update_daemon_status(status)

            except Exception as e:
                logger.error(f"Error loading daemon status: {e}", exc_info=True)
                status = {
                    "running": False,
                    "error": str(e),
                }
                daemon_monitor = self.query_one(DaemonMonitor)
                daemon_monitor.update_daemon_status(status)

        # Use run_worker to execute async code without blocking
        self.run_worker(_load_async(), exclusive=False)

    def action_refresh(self) -> None:
        """Refresh all data."""
        self.load_all_data()
        self.notify("Data refreshed", severity="information")

    def action_show_gaps(self) -> None:
        """Switch to gaps tab."""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "gaps-tab"

    def action_show_daemon(self) -> None:
        """Switch to daemon tab."""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "daemon-tab"

    def action_show_tasks(self) -> None:
        """Switch to tasks tab."""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "tasks-tab"

    def action_show_notes(self) -> None:
        """Switch to notes tab."""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "notes-tab"

    async def action_command_palette(self) -> None:
        """Show command palette for quick actions."""
        result = await self.push_screen(CommandPalette(), wait_for_dismiss=True)
        if result:
            command = result.get("command")
            if command == "create_task":
                await self.action_create_task()
            elif command == "create_reference":
                await self.action_create_reference()
            elif command == "create_note":
                await self.action_create_note()
            elif command == "assign_task":
                await self.action_assign_agent()
            elif command == "broadcast_message":
                await self.action_broadcast_message()
            elif command == "set_priority":
                await self.action_change_priority()
            elif command == "change_state":
                await self.action_change_state()
            elif command == "view_gaps":
                self.action_show_gaps()
            elif command == "refresh":
                self.action_refresh()
            elif command == "show_daemon":
                self.action_show_daemon()

    async def action_edit_task(self) -> None:
        """Edit the selected task or note (context-sensitive)."""
        logger = get_logger()
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)

            if tabs.active == "tasks-tab":
                # Edit task
                task_browser = self.query_one(TaskBrowser)
                task = task_browser.get_selected_task()

                if not task:
                    self.notify("No task selected", severity="warning")
                    return

                logger.info(f"Opening edit modal for task #{task.get('id')}")
                result = await self.push_screen(
                    TaskEditModal(task), wait_for_dismiss=True
                )

                if result:
                    try:
                        from idlergear.backends.registry import get_backend

                        backend = get_backend("task", project_path=self.project_root)
                        backend.update(task_id=result["id"], **result)

                        logger.info(
                            f"Task #{result['id']} updated: {result.get('title')}"
                        )
                        self.notify(
                            f"Task #{result['id']} updated", severity="information"
                        )
                        self.action_refresh()
                    except Exception as e:
                        logger.error(f"Failed to update task: {e}", exc_info=True)
                        self.notify(f"Failed to update task: {e}", severity="error")
                else:
                    logger.debug("Task edit cancelled")

            elif tabs.active == "notes-tab":
                # View/edit note
                note_browser = self.query_one(NoteBrowser)
                note = note_browser.get_selected_note()

                if not note:
                    self.notify("No note selected", severity="warning")
                    return

                logger.info(f"Opening view/edit modal for note #{note.get('id')}")
                result = await self.push_screen(
                    NoteViewModal(note, editable=True), wait_for_dismiss=True
                )

                if result:
                    action = result.get("action")

                    if action == "save":
                        # Save note edits
                        try:
                            from idlergear.backends.registry import get_backend

                            backend = get_backend(
                                "note", project_path=self.project_root
                            )
                            backend.update(note_id=result["id"], body=result["content"])

                            logger.info(f"Note #{result['id']} updated")
                            self.notify(
                                f"Note #{result['id']} updated", severity="information"
                            )
                            self.action_refresh()
                        except Exception as e:
                            logger.error(f"Failed to update note: {e}", exc_info=True)
                            self.notify(f"Failed to update note: {e}", severity="error")

                    elif action == "promote":
                        # Handle note promotion
                        await self._handle_note_promotion(note)

                    elif action == "delete":
                        # Handle note deletion
                        confirmed = await self.push_screen(
                            ConfirmDeleteModal(
                                "note", result["id"], result.get("content", "")
                            ),
                            wait_for_dismiss=True,
                        )
                        if confirmed:
                            try:
                                from idlergear.backends.registry import get_backend

                                backend = get_backend(
                                    "note", project_path=self.project_root
                                )
                                backend.delete(note_id=result["id"])

                                logger.info(f"Note #{result['id']} deleted")
                                self.notify(
                                    f"Note #{result['id']} deleted",
                                    severity="information",
                                )
                                self.action_refresh()
                            except Exception as e:
                                logger.error(
                                    f"Failed to delete note: {e}", exc_info=True
                                )
                                self.notify(
                                    f"Failed to delete note: {e}", severity="error"
                                )

        except Exception as e:
            logger.error(f"Error editing item: {e}", exc_info=True)
            self.notify(f"Error editing item: {e}", severity="error")

    def action_toggle_selection(self) -> None:
        """Toggle selection of current task."""
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            if tabs.active == "tasks-tab":
                task_browser = self.query_one(TaskBrowser)
                task_browser.toggle_selection()
        except Exception as e:
            self.notify(f"Error toggling selection: {e}", severity="error")

    async def _handle_note_promotion(self, note: dict[str, Any]) -> None:
        """Handle promoting a note to task or reference.

        Args:
            note: Note to promote
        """
        logger = get_logger()
        try:
            logger.info(f"Opening promotion modal for note #{note.get('id')}")
            result = await self.push_screen(
                NotePromoteModal(note), wait_for_dismiss=True
            )

            if result:
                promote_type = result.get("type")
                title = result.get("title")
                content = result.get("content")
                note_id = result.get("note_id")

                from idlergear.backends.registry import get_backend

                if promote_type == "task":
                    # Promote to task
                    task_backend = get_backend("task", project_path=self.project_root)
                    task_id = task_backend.create(title=title, body=content)

                    # Close the note
                    note_backend = get_backend("note", project_path=self.project_root)
                    note_backend.update(note_id=note_id, state="closed")

                    logger.info(f"Note #{note_id} promoted to task #{task_id}")
                    self.notify(
                        f"Note promoted to task #{task_id}", severity="information"
                    )

                elif promote_type == "reference":
                    # Promote to reference
                    ref_backend = get_backend(
                        "reference", project_path=self.project_root
                    )
                    ref_backend.create(title=title, content=content)

                    # Close the note
                    note_backend = get_backend("note", project_path=self.project_root)
                    note_backend.update(note_id=note_id, state="closed")

                    logger.info(f"Note #{note_id} promoted to reference '{title}'")
                    self.notify("Note promoted to reference", severity="information")

                self.action_refresh()

        except Exception as e:
            logger.error(f"Error promoting note: {e}", exc_info=True)
            self.notify(f"Error promoting note: {e}", severity="error")

    async def action_change_state(self) -> None:
        """Change state of selected task(s) without full edit modal."""
        logger = get_logger()
        try:
            task_browser = self.query_one(TaskBrowser)
            task = task_browser.get_selected_task()

            if not task:
                self.notify("No task selected", severity="warning")
                return

            # Quick state selector - cycle through states
            current_state = task.get("state", "open")
            state_cycle = ["open", "in_progress", "in_review", "completed", "blocked"]

            try:
                current_idx = state_cycle.index(current_state)
                next_idx = (current_idx + 1) % len(state_cycle)
                new_state = state_cycle[next_idx]
            except ValueError:
                new_state = "open"

            from idlergear.backends.registry import get_backend

            backend = get_backend("task", project_path=self.project_root)
            backend.update(task_id=task.get("id"), state=new_state)

            logger.info(
                f"Task #{task.get('id')} state changed: {current_state} → {new_state}"
            )
            self.notify(
                f"Task state: {current_state} → {new_state}", severity="information"
            )
            self.action_refresh()

        except Exception as e:
            logger.error(f"Error changing state: {e}", exc_info=True)
            self.notify(f"Error changing state: {e}", severity="error")

    async def action_change_priority(self) -> None:
        """Change priority of selected task(s) without full edit modal."""
        logger = get_logger()
        try:
            task_browser = self.query_one(TaskBrowser)
            task = task_browser.get_selected_task()

            if not task:
                self.notify("No task selected", severity="warning")
                return

            # Quick priority cycling
            current_priority = task.get("priority", "medium")
            priority_cycle = ["critical", "high", "medium", "low", "backlog"]

            try:
                current_idx = priority_cycle.index(current_priority)
                next_idx = (current_idx + 1) % len(priority_cycle)
                new_priority = priority_cycle[next_idx]
            except ValueError:
                new_priority = "medium"

            from idlergear.backends.registry import get_backend

            backend = get_backend("task", project_path=self.project_root)
            backend.update(task_id=task.get("id"), priority=new_priority)

            logger.info(
                f"Task #{task.get('id')} priority changed: "
                f"{current_priority} → {new_priority}"
            )
            self.notify(
                f"Task priority: {current_priority} → {new_priority}",
                severity="information",
            )
            self.action_refresh()

        except Exception as e:
            logger.error(f"Error changing priority: {e}", exc_info=True)
            self.notify(f"Error changing priority: {e}", severity="error")

    async def action_assign_agent(self) -> None:
        """Assign task to an AI agent."""
        try:
            task_browser = self.query_one(TaskBrowser)
            task = task_browser.get_selected_task()

            if not task:
                self.notify("No task selected", severity="warning")
                return

            # Get active agents
            from idlergear.config import find_idlergear_root
            from idlergear.daemon.client import DaemonClient

            root = find_idlergear_root()
            if not root:
                self.notify("Not in IdlerGear project", severity="error")
                return

            socket_path = root / ".idlergear" / "daemon" / "daemon.sock"
            if not socket_path.exists():
                self.notify(
                    "Daemon not running. Start with: idlergear daemon start",
                    severity="warning",
                )
                return

            client = DaemonClient(socket_path)
            await client.connect()
            agents = await client.list_agents()
            await client.disconnect()

            if not agents:
                self.notify(
                    "No active agents. Connect an AI assistant first.",
                    severity="warning",
                )
                return

            # For now, just broadcast task assignment
            agent_names = ", ".join([a.get("agent_type", "unknown") for a in agents])
            self.notify(
                f"Task #{task.get('id')} - Available agents: {agent_names}",
                severity="information",
            )
            self.notify("Full assignment UI coming soon", severity="information")

        except Exception as e:
            self.notify(f"Error assigning task: {e}", severity="error")

    async def action_edit_labels(self) -> None:
        """Edit labels for selected item."""
        self.notify("Label editing - Use Edit (Enter) for now", severity="information")

    async def action_delete_item(self) -> None:
        """Delete selected item (task or note based on active tab)."""
        logger = get_logger()
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)

            if tabs.active == "tasks-tab":
                # Delete task
                task_browser = self.query_one(TaskBrowser)
                task = task_browser.get_selected_task()

                if not task:
                    self.notify("No task selected", severity="warning")
                    return

                task_id = task.get("id")
                task_title = task.get("title", "")

                # Show confirmation
                confirmed = await self.push_screen(
                    ConfirmDeleteModal("task", task_id, task_title),
                    wait_for_dismiss=True,
                )

                if confirmed:
                    from idlergear.backends.registry import get_backend

                    backend = get_backend("task", project_path=self.project_root)
                    backend.delete(task_id=task_id)

                    logger.info(f"Task #{task_id} deleted: {task_title}")
                    self.notify(f"Task #{task_id} deleted", severity="information")
                    self.action_refresh()

            elif tabs.active == "notes-tab":
                # Delete note
                note_browser = self.query_one(NoteBrowser)
                note = note_browser.get_selected_note()

                if not note:
                    self.notify("No note selected", severity="warning")
                    return

                note_id = note.get("id")
                note_content = note.get("body", "") or note.get("title", "")

                # Show confirmation
                confirmed = await self.push_screen(
                    ConfirmDeleteModal("note", note_id, note_content),
                    wait_for_dismiss=True,
                )

                if confirmed:
                    from idlergear.backends.registry import get_backend

                    backend = get_backend("note", project_path=self.project_root)
                    backend.delete(note_id=note_id)

                    logger.info(f"Note #{note_id} deleted")
                    self.notify(f"Note #{note_id} deleted", severity="information")
                    self.action_refresh()

        except Exception as e:
            logger.error(f"Error deleting item: {e}", exc_info=True)
            self.notify(f"Error deleting item: {e}", severity="error")

    async def action_create_task(self) -> None:
        """Create a new task."""
        logger = get_logger()
        try:
            new_task = {
                "title": "",
                "body": "",
                "state": "open",
                "priority": "medium",
                "labels": [],
            }

            logger.info("Opening task creation modal")
            result = await self.push_screen(
                TaskEditModal(new_task), wait_for_dismiss=True
            )

            if result:
                try:
                    from idlergear.backends.registry import get_backend

                    backend = get_backend("task", project_path=self.project_root)
                    task_id = backend.create(
                        title=result["title"],
                        body=result.get("body", ""),
                        labels=result.get("labels", []),
                    )

                    # Update priority and state if not defaults
                    if (
                        result.get("priority") != "medium"
                        or result.get("state") != "open"
                    ):
                        backend.update(
                            task_id=task_id,
                            priority=result.get("priority"),
                            state=result.get("state"),
                        )

                    logger.info(f"Task #{task_id} created: {result.get('title')}")
                    self.notify(f"Task #{task_id} created", severity="information")
                    self.action_refresh()
                except Exception as e:
                    logger.error(f"Failed to create task: {e}", exc_info=True)
                    self.notify(f"Failed to create task: {e}", severity="error")
            else:
                logger.debug("Task creation cancelled")

        except Exception as e:
            logger.error(f"Error creating task: {e}", exc_info=True)
            self.notify(f"Error creating task: {e}", severity="error")

    async def action_create_reference(self) -> None:
        """Create a new reference document."""
        logger = get_logger()
        try:
            logger.info("Opening reference creation modal")
            result = await self.push_screen(ReferenceEditModal(), wait_for_dismiss=True)

            if result:
                try:
                    from idlergear.backends.registry import get_backend

                    backend = get_backend("reference", project_path=self.project_root)
                    backend.create(
                        title=result["title"],
                        content=result["content"],
                        tags=result.get("tags", []),
                    )

                    logger.info(f"Reference created: {result['title']}")
                    self.notify(
                        f"Reference '{result['title']}' created", severity="information"
                    )
                    self.action_refresh()
                except Exception as e:
                    logger.error(f"Failed to create reference: {e}", exc_info=True)
                    self.notify(f"Failed to create reference: {e}", severity="error")
            else:
                logger.debug("Reference creation cancelled")

        except Exception as e:
            logger.error(f"Error creating reference: {e}", exc_info=True)
            self.notify(f"Error creating reference: {e}", severity="error")

    async def action_create_note(self) -> None:
        """Create a new note."""
        self.notify(
            "Note creation - Use: idlergear note create '<content>'",
            severity="information",
        )

    async def action_broadcast_message(self) -> None:
        """Broadcast message to all agents."""
        logger = get_logger()
        try:
            # Get active agents
            from idlergear.config import find_idlergear_root
            from idlergear.daemon.client import DaemonClient

            root = find_idlergear_root()
            if not root:
                logger.warning("Not in IdlerGear project")
                self.notify("Not in IdlerGear project", severity="error")
                return

            socket_path = root / ".idlergear" / "daemon" / "daemon.sock"
            if not socket_path.exists():
                logger.warning("Daemon not running")
                self.notify("Daemon not running", severity="warning")
                return

            logger.debug("Connecting to daemon for message broadcast")
            client = DaemonClient(socket_path)
            await client.connect()
            agents = await client.list_agents()

            if not agents:
                await client.disconnect()
                logger.warning("No active agents to send message to")
                self.notify("No active agents", severity="warning")
                return

            logger.info(f"Opening message modal for {len(agents)} agents")
            result = await self.push_screen(MessageModal(agents), wait_for_dismiss=True)

            if result:
                message = result.get("message")
                priority = result.get("priority", "normal")

                logger.info(
                    f"Broadcasting {priority} priority message: {message[:50]}..."
                )
                await client.broadcast_message(
                    message=message,
                    event_type="high_priority" if priority == "high" else "message",
                )

                await client.disconnect()

                recipient = result.get("recipient")
                if recipient == "all":
                    logger.info(f"Message broadcast to {len(agents)} agents")
                    self.notify(
                        "Message broadcast to all agents", severity="information"
                    )
                else:
                    logger.info(f"Message sent to agent {recipient[:8]}")
                    self.notify(
                        f"Message sent to {recipient[:8]}", severity="information"
                    )
            else:
                logger.debug("Message broadcast cancelled")
                await client.disconnect()

        except Exception as e:
            logger.error(f"Error broadcasting message: {e}", exc_info=True)
            self.notify(f"Error broadcasting message: {e}", severity="error")

    async def action_send_message(self) -> None:
        """Send message to specific agent."""
        await self.action_broadcast_message()  # Use same modal for now

    async def action_bulk_actions(self) -> None:
        """Perform bulk actions on selected tasks."""
        logger = get_logger()
        try:
            task_browser = self.query_one(TaskBrowser)
            selected = task_browser.selected_tasks

            if not selected:
                self.notify("No tasks selected", severity="warning")
                return

            logger.info(f"Opening bulk actions modal for {len(selected)} tasks")
            result = await self.push_screen(
                BulkActionModal(len(selected)), wait_for_dismiss=True
            )

            if result:
                action = result.get("action")

                from idlergear.backends.registry import get_backend

                backend = get_backend("task", project_path=self.project_root)

                if action == "state":
                    # Show state selector
                    new_state = await self.push_screen(
                        QuickSelectModal(
                            "Select State",
                            [
                                ("Open", "open"),
                                ("In Progress", "in_progress"),
                                ("In Review", "in_review"),
                                ("Completed", "completed"),
                                ("Blocked", "blocked"),
                            ],
                        ),
                        wait_for_dismiss=True,
                    )
                    if new_state:
                        for task_id in selected:
                            backend.update(task_id=task_id, state=new_state)
                        logger.info(
                            f"Updated {len(selected)} tasks to state={new_state}"
                        )
                        self.notify(
                            f"Updated {len(selected)} tasks", severity="information"
                        )

                elif action == "priority":
                    # Show priority selector
                    new_priority = await self.push_screen(
                        QuickSelectModal(
                            "Select Priority",
                            [
                                ("🔴 Critical", "critical"),
                                ("🟠 High", "high"),
                                ("🟡 Medium", "medium"),
                                ("🟢 Low", "low"),
                                ("⚪ Backlog", "backlog"),
                            ],
                        ),
                        wait_for_dismiss=True,
                    )
                    if new_priority:
                        for task_id in selected:
                            backend.update(task_id=task_id, priority=new_priority)
                        logger.info(
                            f"Updated {len(selected)} tasks to priority={new_priority}"
                        )
                        self.notify(
                            f"Updated {len(selected)} tasks", severity="information"
                        )

                elif action == "complete":
                    # Mark all as completed
                    for task_id in selected:
                        backend.update(task_id=task_id, state="completed")
                    logger.info(f"Marked {len(selected)} tasks as completed")
                    self.notify(
                        f"Marked {len(selected)} tasks as completed",
                        severity="information",
                    )

                elif action == "delete":
                    # Confirm bulk delete
                    confirmed = await self.push_screen(
                        ConfirmDeleteModal(
                            "tasks",
                            f"{len(selected)}",
                            f"{len(selected)} selected tasks",
                        ),
                        wait_for_dismiss=True,
                    )
                    if confirmed:
                        for task_id in selected:
                            backend.delete(task_id=task_id)
                        logger.info(f"Deleted {len(selected)} tasks")
                        self.notify(
                            f"Deleted {len(selected)} tasks", severity="information"
                        )

                # Clear selection and refresh
                task_browser.selected_tasks = set()
                self.action_refresh()

        except Exception as e:
            logger.error(f"Error performing bulk action: {e}", exc_info=True)
            self.notify(f"Error performing bulk action: {e}", severity="error")

    def action_help(self) -> None:
        """Show help message."""
        self.notify(
            "Keys: [q]uit [r]efresh [g]aps [d]aemon [?]help",
            severity="information",
            timeout=5,
        )


def run_tui(project_root: Path | None = None) -> None:
    """Run the TUI application.

    Args:
        project_root: Project root directory (defaults to cwd)
    """
    app = IdlerGearApp(project_root=project_root)
    app.run()
