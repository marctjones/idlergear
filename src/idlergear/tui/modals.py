"""Modal widgets for TUI interactive features."""

from __future__ import annotations

from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, TextArea, Checkbox


class TaskEditModal(ModalScreen[dict[str, Any] | None]):
    """Modal for editing task details."""

    CSS = """
    TaskEditModal {
        align: center middle;
    }
    
    #dialog {
        width: 80;
        height: 30;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #buttons {
        height: 3;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
    }
    """

    def __init__(self, task: dict[str, Any]) -> None:
        super().__init__()
        self.task = task
        self.result: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Create modal widgets."""
        with Container(id="dialog"):
            yield Label(f"Edit Task #{self.task.get('id', 'New')}", classes="header")
            yield Label("Title:")
            yield Input(
                value=self.task.get("title", ""),
                placeholder="Task title",
                id="title-input",
            )
            yield Label("Description:")
            yield TextArea(
                text=self.task.get("body", ""),
                id="description-input",
            )

            # State selection
            yield Label("State:")
            state_options = [
                ("Open", "open"),
                ("In Progress", "in_progress"),
                ("In Review", "in_review"),
                ("Completed", "completed"),
                ("Blocked", "blocked"),
            ]
            current_state = self.task.get("state", "open")
            yield Select(
                options=state_options,
                value=current_state,
                id="state-select",
            )

            # Priority selection
            yield Label("Priority:")
            priority_options = [
                ("🔴 Critical", "critical"),
                ("🟠 High", "high"),
                ("🟡 Medium", "medium"),
                ("🟢 Low", "low"),
                ("⚪ Backlog", "backlog"),
            ]
            current_priority = self.task.get("priority", "medium")
            yield Select(
                options=priority_options,
                value=current_priority,
                id="priority-select",
            )

            # Labels input
            yield Label("Labels (comma-separated):")
            labels_str = ", ".join(self.task.get("labels", []))
            yield Input(
                value=labels_str,
                placeholder="enhancement, bug, docs",
                id="labels-input",
            )

            # Buttons
            with Grid(id="buttons"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    @on(Button.Pressed, "#save-btn")
    def save_task(self) -> None:
        """Save task changes."""
        title_input = self.query_one("#title-input", Input)
        description_input = self.query_one("#description-input", TextArea)
        state_select = self.query_one("#state-select", Select)
        priority_select = self.query_one("#priority-select", Select)
        labels_input = self.query_one("#labels-input", Input)

        self.result = {
            "id": self.task.get("id"),
            "title": title_input.value,
            "body": description_input.text,
            "state": state_select.value,
            "priority": priority_select.value,
            "labels": [
                label.strip()
                for label in labels_input.value.split(",")
                if label.strip()
            ],
        }
        self.dismiss(self.result)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        """Cancel editing."""
        self.dismiss(None)


class ReferenceEditModal(ModalScreen[dict[str, Any] | None]):
    """Modal for creating/editing reference documents."""

    CSS = """
    ReferenceEditModal {
        align: center middle;
    }
    
    #dialog {
        width: 90;
        height: 35;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #content-area {
        height: 15;
    }
    
    #buttons {
        height: 3;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
    }
    """

    def __init__(self, reference: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.reference = reference or {}
        self.result: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Create modal widgets."""
        with Container(id="dialog"):
            title = "Edit Reference" if self.reference else "New Reference"
            yield Label(title, classes="header")

            yield Label("Title:")
            yield Input(
                value=self.reference.get("title", ""),
                placeholder="Reference title",
                id="title-input",
            )

            yield Label("Tags (comma-separated):")
            tags = self.reference.get("tags", [])
            tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
            yield Input(
                value=tags_str,
                placeholder="api, auth, documentation",
                id="tags-input",
            )

            yield Label("Content (Markdown):")
            yield TextArea(
                text=self.reference.get("content", ""),
                id="content-area",
            )

            with Grid(id="buttons"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Preview", variant="default", id="preview-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    @on(Button.Pressed, "#save-btn")
    def save_reference(self) -> None:
        """Save reference."""
        title_input = self.query_one("#title-input", Input)
        tags_input = self.query_one("#tags-input", Input)
        content_area = self.query_one("#content-area", TextArea)

        self.result = {
            "title": title_input.value,
            "tags": [t.strip() for t in tags_input.value.split(",") if t.strip()],
            "content": content_area.text,
        }
        self.dismiss(self.result)

    @on(Button.Pressed, "#preview-btn")
    def preview_reference(self) -> None:
        """Preview markdown (future enhancement)."""
        self.app.notify("Preview not yet implemented", severity="information")

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        """Cancel editing."""
        self.dismiss(None)


class NotePromoteModal(ModalScreen[dict[str, Any] | None]):
    """Modal for promoting a note to task or reference."""

    CSS = """
    NotePromoteModal {
        align: center middle;
    }
    
    #dialog {
        width: 70;
        height: 25;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #buttons {
        height: 3;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
    }
    """

    def __init__(self, note: dict[str, Any]) -> None:
        super().__init__()
        self.note = note
        self.result: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Create modal widgets."""
        with Container(id="dialog"):
            yield Label(f"Promote Note #{self.note.get('id', '')}", classes="header")

            # Show note preview
            content = self.note.get("title", "") or self.note.get("body", "")
            preview = content[:200] + "..." if len(content) > 200 else content
            yield Label(f"Note: {preview}")
            yield Label("")

            yield Label("Promote to:")
            promote_options = [
                ("Task - Create actionable task", "task"),
                ("Reference - Create documentation", "reference"),
            ]
            yield Select(
                options=promote_options,
                value="task",
                id="promote-type",
            )

            yield Label("")
            yield Label("Title:")
            # Extract title from note
            title = self.note.get("title", "") or content.split("\n")[0][:100]
            yield Input(
                value=title,
                placeholder="Title for task/reference",
                id="title-input",
            )

            with Grid(id="buttons"):
                yield Button("Promote", variant="primary", id="promote-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    @on(Button.Pressed, "#promote-btn")
    def promote_note(self) -> None:
        """Promote the note."""
        promote_type = self.query_one("#promote-type", Select)
        title_input = self.query_one("#title-input", Input)

        self.result = {
            "type": promote_type.value,
            "title": title_input.value,
            "note_id": self.note.get("id"),
            "content": self.note.get("body", ""),
        }
        self.dismiss(self.result)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        """Cancel promotion."""
        self.dismiss(None)


class MessageModal(ModalScreen[dict[str, Any] | None]):
    """Modal for sending messages to agents."""

    CSS = """
    MessageModal {
        align: center middle;
    }
    
    #dialog {
        width: 70;
        height: 20;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #buttons {
        height: 3;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
    }
    """

    def __init__(self, agents: list[dict[str, Any]]) -> None:
        super().__init__()
        self.agents = agents
        self.result: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Create modal widgets."""
        with Container(id="dialog"):
            yield Label("📢 Broadcast Message to Agents", classes="header")

            # Recipient selection
            yield Label("Send to:")
            recipient_options = [("All Agents", "all")]
            recipient_options.extend(
                [
                    (
                        f"{a.get('agent_type', 'unknown').upper()} ({a.get('agent_id', '')[:8]})",
                        a.get("agent_id", ""),
                    )
                    for a in self.agents
                ]
            )
            yield Select(
                options=recipient_options,
                value="all",
                id="recipient-select",
            )

            yield Label("Message:")
            yield TextArea(
                placeholder="Enter message to send to agents...",
                id="message-input",
            )

            # Priority checkbox
            yield Checkbox("High Priority", id="priority-check")

            with Grid(id="buttons"):
                yield Button("Send", variant="primary", id="send-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    @on(Button.Pressed, "#send-btn")
    def send_message(self) -> None:
        """Send the message."""
        recipient_select = self.query_one("#recipient-select", Select)
        message_input = self.query_one("#message-input", TextArea)
        priority_check = self.query_one("#priority-check", Checkbox)

        self.result = {
            "recipient": recipient_select.value,
            "message": message_input.text,
            "priority": "high" if priority_check.value else "normal",
        }
        self.dismiss(self.result)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        """Cancel sending."""
        self.dismiss(None)


class CommandPalette(ModalScreen[dict[str, Any] | None]):
    """Command palette for quick actions."""

    CSS = """
    CommandPalette {
        align: center top;
    }
    
    #dialog {
        width: 70;
        height: 25;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
        margin-top: 2;
    }
    
    #search {
        margin-bottom: 1;
    }
    
    #results {
        height: 18;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.commands = [
            ("Create Task", "create_task"),
            ("Create Reference", "create_reference"),
            ("Create Note", "create_note"),
            ("Assign Task to Agent", "assign_task"),
            ("Broadcast Message", "broadcast_message"),
            ("Set Priority", "set_priority"),
            ("Change Task State", "change_state"),
            ("Add Labels", "add_labels"),
            ("View Knowledge Gaps", "view_gaps"),
            ("Refresh Data", "refresh"),
            ("Show Daemon Status", "show_daemon"),
        ]
        self.filtered_commands = self.commands[:]

    def compose(self) -> ComposeResult:
        """Create modal widgets."""
        with Container(id="dialog"):
            yield Label("⚡ Quick Actions", classes="header")
            yield Input(
                placeholder="Type to search commands...",
                id="search",
            )
            with Vertical(id="results"):
                for label, command in self.commands:
                    yield Button(label, id=f"cmd-{command}", classes="command-btn")

    @on(Input.Changed, "#search")
    def filter_commands(self, event: Input.Changed) -> None:
        """Filter commands based on search."""
        query = event.value.lower()
        results = self.query_one("#results", Vertical)
        results.remove_children()

        self.filtered_commands = [
            (label, cmd) for label, cmd in self.commands if query in label.lower()
        ]

        for label, command in self.filtered_commands:
            results.mount(Button(label, id=f"cmd-{command}", classes="command-btn"))

    @on(Button.Pressed, ".command-btn")
    def execute_command(self, event: Button.Pressed) -> None:
        """Execute selected command."""
        command_id = event.button.id
        if command_id and command_id.startswith("cmd-"):
            command = command_id[4:]  # Remove "cmd-" prefix
            self.dismiss({"command": command})
