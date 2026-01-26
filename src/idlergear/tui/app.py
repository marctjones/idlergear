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
            "│ [bold cyan]Knowledge Type[/]      [bold yellow]Count[/]   [bold green]Status[/]   │",
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

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("📋 Task Browser", classes="header")
        yield DataTable(id="task-table")

    def on_mount(self) -> None:
        """Set up the task table."""
        table = self.query_one("#task-table", DataTable)
        table.add_columns("ID", "Title", "Priority", "State", "Labels")
        table.cursor_type = "row"
        table.zebra_stripes = True


class NoteBrowser(Static):
    """Browse notes and explorations."""

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("📝 Notes & Explorations", classes="header")
        yield DataTable(id="note-table")

    def on_mount(self) -> None:
        """Set up the note table."""
        table = self.query_one("#note-table", DataTable)
        table.add_columns("ID", "Content Preview", "Tags", "Created")
        table.cursor_type = "row"
        table.zebra_stripes = True


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
                "[green]✅ No knowledge gaps detected!\n\nYour project knowledge base is healthy.[/]"
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
    """Monitor daemon status and active agents."""

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("🔄 Daemon & Agent Monitor", classes="header")
        yield Static(id="daemon-status")

    def update_daemon_status(self, status: dict[str, Any]) -> None:
        """Update daemon status display."""
        display = self.query_one("#daemon-status", Static)

        if not status.get("running"):
            display.update(
                "[red]● Daemon not running[/]\n\nStart with: idlergear daemon start"
            )
            return

        lines = [
            "[green]● Daemon running[/]",
            "",
            f"PID: {status.get('pid', 'unknown')}",
            f"Uptime: {status.get('uptime', 'unknown')}",
            "",
            "Active Agents:",
        ]

        agents = status.get("agents", [])
        if agents:
            for agent in agents:
                lines.append(
                    f"  • {agent.get('id', 'unknown')} ({agent.get('type', 'unknown')})"
                )
        else:
            lines.append("  (none)")

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
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh", "Refresh"),
        Binding("g", "show_gaps", "Gaps"),
        Binding("d", "show_daemon", "Daemon"),
        Binding("?", "help", "Help"),
    ]

    TITLE = "IdlerGear TUI - Knowledge Base Explorer"

    def __init__(self, project_root: Path | None = None):
        """Initialize app.

        Args:
            project_root: Project root directory (defaults to cwd)
        """
        super().__init__()
        self.project_root = project_root or Path.cwd()

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
        stats = {}

        try:
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
                from idlergear.graph import GraphDB

                graph = GraphDB()
                result = graph.query("MATCH (n) RETURN count(n) AS count")
                if result:
                    stats["graph_nodes"] = result[0].get("count", 0)
                else:
                    stats["graph_nodes"] = 0
            except Exception:
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
            except Exception:
                stats["gaps"] = {}

        except Exception as e:
            self.notify(f"Error loading stats: {e}", severity="error")

        return stats

    def load_tasks(self) -> None:
        """Load tasks into the task browser."""
        try:
            from idlergear.backends.registry import get_backend
            from idlergear.config import find_idlergear_root

            root = find_idlergear_root()
            if root is None:
                return

            task_backend = get_backend("task", project_path=root)
            tasks = task_backend.list(state="open")

            table = self.query_one("#task-table", DataTable)
            table.clear()

            for task in tasks[:50]:  # Limit to 50 for performance
                table.add_row(
                    str(task.get("id", "")),
                    task.get("title", "")[:60],
                    task.get("priority", "")[:10],
                    task.get("state", ""),
                    ", ".join(task.get("labels", []))[:30],
                )

        except Exception as e:
            self.notify(f"Error loading tasks: {e}", severity="error")

    def load_notes(self) -> None:
        """Load notes into the note browser."""
        try:
            from idlergear.backends.registry import get_backend
            from idlergear.config import find_idlergear_root

            root = find_idlergear_root()
            if root is None:
                return

            note_backend = get_backend("note", project_path=root)
            notes = note_backend.list()

            table = self.query_one("#note-table", DataTable)
            table.clear()

            for note in notes[:50]:
                if note.get("state") != "open":
                    continue

                content = note.get("title", "") or note.get("body", "")
                preview = content[:50] + "..." if len(content) > 50 else content

                labels = [
                    label
                    for label in note.get("labels", [])
                    if label.startswith("tag:")
                ]
                tags = ", ".join([label.replace("tag:", "") for label in labels])

                table.add_row(
                    str(note.get("id", "")),
                    preview,
                    tags[:30],
                    note.get("created_at", "")[:10],
                )

        except Exception as e:
            self.notify(f"Error loading notes: {e}", severity="error")

    def load_graph(self) -> None:
        """Load knowledge graph structure."""
        try:
            from idlergear.config import find_idlergear_root
            from idlergear.graph import GraphDB

            root = find_idlergear_root()
            if root is None:
                return

            graph = GraphDB()

            tree = self.query_one(Tree)
            tree.clear()
            tree.root.label = "Knowledge Graph"

            # Add node type branches
            try:
                # Count each node type
                result = graph.query(
                    "MATCH (n) RETURN labels(n) AS labels, count(n) AS count"
                )

                for row in result:
                    labels = row.get("labels", [])
                    count = row.get("count", 0)
                    if labels:
                        label_str = (
                            labels[0] if isinstance(labels, list) else str(labels)
                        )
                        tree.root.add_leaf(f"{label_str}: {count} nodes")

            except Exception:
                tree.root.add_leaf(
                    "(empty - populate with: idlergear graph populate-all)"
                )

        except Exception as e:
            self.notify(f"Error loading graph: {e}", severity="error")

    def load_gaps(self) -> None:
        """Load knowledge gaps."""
        try:
            from idlergear.config import find_idlergear_root
            from idlergear.gap_detector import GapDetector

            root = find_idlergear_root()
            if root is None:
                return

            detector = GapDetector(project_root=root)
            gaps = detector.detect_gaps()

            gap_alerts = self.query_one(GapAlerts)
            gap_alerts.update_gaps([g.to_dict() for g in gaps])

        except Exception as e:
            self.notify(f"Error loading gaps: {e}", severity="error")

    def load_daemon_status(self) -> None:
        """Load daemon status."""
        try:
            from idlergear.config import find_idlergear_root
            from idlergear.daemon.lifecycle import DaemonLifecycle

            root = find_idlergear_root()
            if root is None:
                return

            lifecycle = DaemonLifecycle(root)
            running = lifecycle.is_running()

            status = {"running": running}

            if running:
                # Get more details if daemon is running
                try:
                    from idlergear.daemon.client import get_daemon_client

                    with get_daemon_client() as client:
                        agents = client.list_agents()
                        status["agents"] = agents
                        status["pid"] = "unknown"  # Would need to get from daemon
                        status["uptime"] = "unknown"
                except Exception:
                    pass

            daemon_monitor = self.query_one(DaemonMonitor)
            daemon_monitor.update_daemon_status(status)

        except Exception as e:
            self.notify(f"Error loading daemon status: {e}", severity="error")

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
