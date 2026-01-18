"""IdleWatch TUI - Real-time session monitoring app."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.table import Table
from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import DataTable, Footer, Header, Static

from idlergear.tui.monitor import SessionTailer, parse_event
from idlergear.tui.session_finder import find_claude_session_file, get_session_metadata


class IdleWatchApp(App):
    """IdleWatch - Real-time session monitoring for IdlerGear."""

    CSS = """
    #header {
        background: $primary;
        color: $text;
        padding: 1;
        text-align: center;
    }

    #activity {
        height: 100%;
    }

    .error {
        color: $error;
    }

    .success {
        color: $success;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("h", "help", "Help"),
        ("c", "clear", "Clear"),
    ]

    def __init__(self, session_file: Optional[Path] = None):
        """Initialize IdleWatch app.

        Args:
            session_file: Optional path to session file. If None, auto-detect.
        """
        super().__init__()
        self.session_file = session_file or find_claude_session_file()
        self.tailer: Optional[SessionTailer] = None
        self.monitor_task: Optional[asyncio.Task] = None
        self.event_count = 0

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        if not self.session_file:
            yield Header()
            yield Static(
                "❌ No active Claude Code session found.\n\n"
                "Start Claude Code in another terminal, then run idlewatch again.",
                id="header",
            )
            yield Footer()
            return

        metadata = get_session_metadata(self.session_file)
        project = metadata.get("project", "unknown")

        yield Header()
        yield Static(f"🟢 idlewatch - Monitoring session: {project}", id="header")
        yield ScrollableContainer(DataTable(id="activity"))
        yield Footer()

    def on_mount(self) -> None:
        """Set up the UI when mounted."""
        if not self.session_file:
            return

        # Set up table
        table = self.query_one("#activity", DataTable)
        table.add_columns("Time", "Type", "Details")
        table.cursor_type = "row"

        # Start monitoring
        self.tailer = SessionTailer(self.session_file, start_from_end=False)
        self.monitor_task = asyncio.create_task(self.monitor_loop())

    async def monitor_loop(self) -> None:
        """Background task to monitor session file."""
        if not self.tailer:
            return

        def handle_event(event: dict) -> None:
            """Handle a new event from the session file."""
            parsed = parse_event(event)

            # Format timestamp
            timestamp = parsed.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    time_str = dt.strftime("%H:%M:%S")
                except (ValueError, TypeError):
                    time_str = timestamp[:8]
            else:
                time_str = "N/A"

            # Add row to table
            table = self.query_one("#activity", DataTable)

            event_type = parsed["type"]
            details = parsed.get("details", "")

            # Color code by type
            if parsed.get("error"):
                type_display = f"[red]{event_type}[/red]"
            elif event_type == "user":
                type_display = f"[cyan]{event_type}[/cyan]"
            elif event_type == "tool_use":
                type_display = f"[yellow]{event_type}[/yellow]"
            else:
                type_display = event_type

            table.add_row(time_str, type_display, details)

            # Auto-scroll to bottom
            table.scroll_end(animate=False)

            self.event_count += 1

            # Update header
            self.update_header()

        # Run tailer in background
        await asyncio.to_thread(self.tailer.tail, handle_event, interval=0.5)

    def update_header(self) -> None:
        """Update the header with event count."""
        if not self.session_file:
            return

        metadata = get_session_metadata(self.session_file)
        project = metadata.get("project", "unknown")

        header = self.query_one("#header", Static)
        header.update(
            f"🟢 idlewatch - Monitoring session: {project} "
            f"({self.event_count} events)"
        )

    def action_refresh(self) -> None:
        """Refresh the display."""
        self.event_count = 0
        table = self.query_one("#activity", DataTable)
        table.clear()
        self.update_header()

    def action_clear(self) -> None:
        """Clear the event log."""
        table = self.query_one("#activity", DataTable)
        table.clear()
        self.event_count = 0
        self.update_header()

    def action_help(self) -> None:
        """Show help message."""
        self.push_screen(HelpScreen())


class HelpScreen(Static):
    """Help screen showing keyboard shortcuts."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the help screen."""
        yield Static(
            """
# IdleWatch Help

## Keyboard Shortcuts

- **q** - Quit idlewatch
- **r** - Refresh display (re-read session file)
- **c** - Clear event log
- **h** - Show this help
- **ESC** - Close help

## What am I seeing?

IdleWatch monitors your Claude Code session in real-time,
showing:

- **User messages** - Your prompts to Claude
- **Tool calls** - Claude using tools (Read, Write, Edit, etc.)
- **Tool results** - Success/error status of tool calls
- **Assistant responses** - Claude's text responses

## Tips

- Events appear within 0.5 seconds of occurring
- Use arrow keys to scroll through history
- The event count shows total events since start
- Session file is monitored continuously

## Learn More

For more information:
- GitHub: https://github.com/marctjones/idlergear
- Documentation: See README.md
            """,
            id="help",
        )

    def action_dismiss(self) -> None:
        """Dismiss the help screen."""
        self.app.pop_screen()


def run_monitor(session_file: Optional[Path] = None) -> None:
    """Run the IdleWatch TUI.

    Args:
        session_file: Optional path to session file. If None, auto-detect.
    """
    app = IdleWatchApp(session_file=session_file)
    app.run()
