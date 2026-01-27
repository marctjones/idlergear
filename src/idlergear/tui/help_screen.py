"""Help screen modal showing all keyboard shortcuts."""

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class HelpScreen(ModalScreen):
    """Modal screen showing keyboard shortcuts and help."""

    CSS = """
    HelpScreen {
        align: center middle;
    }
    
    #help-dialog {
        width: 80;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
    }
    
    #help-content {
        padding: 1 2;
    }
    
    .help-section {
        margin-top: 1;
    }
    
    .help-header {
        text-style: bold;
        color: $accent;
    }
    
    .shortcut {
        color: $warning;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose help screen."""
        with Container(id="help-dialog"):
            yield Label("⌨️  IdlerGear Keyboard Shortcuts", classes="help-header")
            with VerticalScroll(id="help-content"):
                yield Static(self._build_help_text())
            yield Button("Close (Esc)", variant="primary", id="close-help")

    def _build_help_text(self) -> str:
        """Build help text with all shortcuts."""
        return """
[bold cyan]═══ Navigation ═══[/]

[yellow]↑↓←→[/] or [yellow]hjkl[/]    Navigate tree (vi-style)
[yellow]Tab[/]              Cycle focus between panes
[yellow]Enter[/]            Select/open item details
[yellow]Esc[/]              Back/cancel/close
[yellow]Space[/]            Toggle expand/collapse node

[bold cyan]═══ Views (Press number to switch) ═══[/]

[yellow]1[/]   By Type       Tasks, notes, references by category
[yellow]2[/]   By Project    Organized by milestone/project
[yellow]3[/]   By Time       Today, this week, this month
[yellow]4[/]   Gaps          Knowledge gaps by severity
[yellow]5[/]   Activity      Recent events feed
[yellow]6[/]   AI Monitor    Real-time AI state (CRITICAL)

[bold cyan]═══ Actions ═══[/]

[yellow]c[/]   Create        Create new item (task/note/ref)
[yellow]e[/]   Edit          Edit selected item
[yellow]d[/]   Delete        Delete selected item
[yellow]r[/]   Refresh       Reload current view data
[yellow]s[/]   Search        Search across all knowledge
[yellow]/[/]   Quick Find    Search overlay (coming soon)

[bold cyan]═══ System ═══[/]

[yellow]?[/]   Help          Show this help screen
[yellow]q[/]   Quit          Exit application
[yellow]ctrl+c[/]            Force quit

[bold cyan]═══ AI Monitor (View 6) ═══[/]

The AI Monitor shows real-time visibility into:
  • Current Activity - What AI is doing right now
  • Planned Steps - What AI plans to do next
  • Uncertainties - Questions AI hasn't asked yet
  • Search Activity - Detect repeated/inefficient searches

[bold yellow]Intervention Opportunities:[/]
  • Low confidence (<70%) - Consider providing guidance
  • Repeated searches - AI might be stuck, provide answer
  • High uncertainties - Answer questions before asked

[bold cyan]═══ Tips ═══[/]

• Use number keys 1-6 to quickly switch between views
• View 6 (AI Monitor) is the "killer feature" - use it!
• Press 'r' to refresh data in any view
• Arrow keys work everywhere for navigation
• All views show the same data, just organized differently

[dim]IdlerGear v0.8.0 - Multi-Agent Collaboration & AI Observability[/]
"""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "close-help":
            self.dismiss()

    def on_key(self, event) -> None:
        """Handle key press."""
        if event.key == "escape":
            self.dismiss()
            event.prevent_default()
        elif event.key == "question_mark":
            self.dismiss()  # Close help if ? pressed again
            event.prevent_default()
