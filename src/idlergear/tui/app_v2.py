"""IdlerGear TUI v2 - Multi-view architecture with AI observability.

This is the redesigned TUI with 6 organizational views:
1. By Type - Tasks, notes, references by category
2. By Project - Organized by milestone/project
3. By Time - Today, this week, this month
4. Gaps - Knowledge gaps by severity
5. Activity - Recent events feed
6. AI Monitor - Real-time AI state (CRITICAL)
"""

import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static, Label

from .base_view import ViewManager
from .views import (
    ByTypeView,
    ByProjectView,
    ByTimeView,
    GapsView,
    ActivityView,
    AIMonitorView,
)
from .help_screen import HelpScreen


class ViewSwitcher(Static):
    """Header showing available views."""

    CSS = """
    ViewSwitcher {
        height: 3;
        background: $surface;
        border-bottom: solid $primary;
        padding: 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_view = 1

    def compose(self) -> ComposeResult:
        """Compose view switcher."""
        yield Label(self._get_switcher_text(), id="switcher-label")

    def _get_switcher_text(self) -> str:
        """Get switcher text with current view highlighted."""
        views = [
            ("1", "Type"),
            ("2", "Project"),
            ("3", "Time"),
            ("4", "Gaps"),
            ("5", "Activity"),
            ("6", "AI Monitor"),
        ]

        parts = []
        for num, name in views:
            if int(num) == self.current_view:
                parts.append(f"[bold cyan reverse] {num} {name} [/]")
            else:
                parts.append(f" [dim]{num}[/] {name} ")

        return "  ".join(parts) + "  │  [dim]? Help  r Refresh  q Quit[/]"

    def update_current_view(self, view_id: int) -> None:
        """Update highlighted view."""
        self.current_view = view_id
        label = self.query_one("#switcher-label", Label)
        label.update(self._get_switcher_text())


class IdlerGearAppV2(App):
    """IdlerGear TUI v2 with multi-view architecture."""

    BINDINGS = [
        Binding("q", "quit", "Quit", show=False),
        Binding("question_mark", "show_help", "Help", show=False, key_display="?"),
        Binding("r", "refresh", "Refresh", show=False),
        Binding("1", "switch_view(1)", "By Type", show=False),
        Binding("2", "switch_view(2)", "By Project", show=False),
        Binding("3", "switch_view(3)", "By Time", show=False),
        Binding("4", "switch_view(4)", "Gaps", show=False),
        Binding("5", "switch_view(5)", "Activity", show=False),
        Binding("6", "switch_view(6)", "AI Monitor", show=False),
    ]

    def __init__(self, project_root=None, **kwargs):
        super().__init__(**kwargs)
        self.project_root = project_root
        self.view_manager: ViewManager | None = None
        self.view_switcher: ViewSwitcher | None = None
        self.daemon_client = None
        self._daemon_listener_task = None

    def compose(self) -> ComposeResult:
        """Compose app layout."""
        yield Header()

        # View switcher header
        self.view_switcher = ViewSwitcher()
        yield self.view_switcher

        # Main container for views
        with Container(id="main-container"):
            # Create all 6 views with project_root (initially hidden except view 1)
            yield ByTypeView(project_root=self.project_root, id="view-1")
            yield ByProjectView(project_root=self.project_root, id="view-2").add_class(
                "hidden"
            )
            yield ByTimeView(project_root=self.project_root, id="view-3").add_class(
                "hidden"
            )
            yield GapsView(project_root=self.project_root, id="view-4").add_class(
                "hidden"
            )
            yield ActivityView(project_root=self.project_root, id="view-5").add_class(
                "hidden"
            )
            yield AIMonitorView(project_root=self.project_root, id="view-6").add_class(
                "hidden"
            )

        yield Footer()

    def on_mount(self) -> None:
        """Initialize view manager after mounting."""
        container = self.query_one("#main-container", Container)

        # Initialize view manager
        self.view_manager = ViewManager(container)

        # Register all views
        self.view_manager.register_view(self.query_one("#view-1", ByTypeView))
        self.view_manager.register_view(self.query_one("#view-2", ByProjectView))
        self.view_manager.register_view(self.query_one("#view-3", ByTimeView))
        self.view_manager.register_view(self.query_one("#view-4", GapsView))
        self.view_manager.register_view(self.query_one("#view-5", ActivityView))
        self.view_manager.register_view(self.query_one("#view-6", AIMonitorView))

        # Switch to default view (By Type)
        self.view_manager.switch_to_view(1)

        # Set app title
        self.title = "IdlerGear - Multi-Agent Knowledge Management"
        self.sub_title = "View 1: By Type"

        # Start daemon listener for real-time updates
        self.run_worker(self._start_daemon_listener(), exclusive=True)

    def action_switch_view(self, view_id: int) -> None:
        """Switch to a different view.

        Args:
            view_id: View ID (1-6) to switch to
        """
        if self.view_manager:
            success = self.view_manager.switch_to_view(view_id)
            if success:
                # Update view switcher highlight
                if self.view_switcher:
                    self.view_switcher.update_current_view(view_id)

                # Update subtitle
                view_names = {
                    1: "By Type",
                    2: "By Project",
                    3: "By Time",
                    4: "Gaps",
                    5: "Activity",
                    6: "AI Monitor",
                }
                self.sub_title = f"View {view_id}: {view_names.get(view_id, 'Unknown')}"

    def action_show_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())

    def action_refresh(self) -> None:
        """Refresh current view."""
        if self.view_manager:
            self.view_manager.refresh_current_view()
            self.notify("View refreshed")

    async def _start_daemon_listener(self) -> None:
        """Start listening for daemon broadcasts."""
        try:
            from idlergear.daemon.client import DaemonClient
            from idlergear.config import find_idlergear_root

            # Find socket path
            project_root = self.project_root or find_idlergear_root()
            if not project_root:
                return

            socket_path = Path.home() / ".idlergear" / "daemon.sock"
            if not socket_path.exists():
                return

            # Create custom client that handles notifications
            class TUIDaemonClient(DaemonClient):
                def __init__(self, socket_path, app):
                    super().__init__(socket_path)
                    self.app = app

                async def _handle_notification(self, notification):
                    """Handle daemon broadcast notifications."""
                    method = notification.method

                    # Handle AI state updates
                    if method in [
                        "ai.activity_changed",
                        "ai.plan_updated",
                        "ai.uncertainty_detected",
                        "ai.search_repeated",
                    ]:
                        # Refresh AI Monitor view
                        view = self.app.view_manager.views.get(6)
                        if view:
                            view.refresh()

                    # Handle knowledge updates
                    elif method in [
                        "knowledge.task_created",
                        "knowledge.task_updated",
                        "knowledge.task_closed",
                        "knowledge.note_created",
                        "knowledge.note_updated",
                        "knowledge.reference_created",
                        "knowledge.reference_updated",
                    ]:
                        # Refresh current view
                        self.app.action_refresh()

            # Initialize client
            self.daemon_client = TUIDaemonClient(socket_path, self)
            await self.daemon_client.connect()

            # Subscribe to AI events
            await self.daemon_client.subscribe("ai.activity_changed")
            await self.daemon_client.subscribe("ai.plan_updated")
            await self.daemon_client.subscribe("ai.uncertainty_detected")
            await self.daemon_client.subscribe("ai.search_repeated")

            # Subscribe to knowledge events
            await self.daemon_client.subscribe("knowledge.task_created")
            await self.daemon_client.subscribe("knowledge.task_updated")
            await self.daemon_client.subscribe("knowledge.task_closed")
            await self.daemon_client.subscribe("knowledge.note_created")
            await self.daemon_client.subscribe("knowledge.note_updated")

            # Keep listening
            await self.daemon_client.listen()

        except Exception as e:
            # Daemon not running - graceful degradation
            pass


def run_tui_v2():
    """Run the TUI v2 application."""
    app = IdlerGearAppV2()
    app.run()


if __name__ == "__main__":
    run_tui_v2()
