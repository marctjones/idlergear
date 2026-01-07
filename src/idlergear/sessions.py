"""Session state persistence - save and restore work context across AI sessions."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from idlergear.backends.registry import get_backend
from idlergear.schema import IdlerGearSchema
from idlergear.status import get_git_status


@dataclass
class SessionState:
    """Complete session state snapshot."""

    saved_at: str
    name: str | None
    current_task: dict[str, Any] | None
    recent_notes: list[dict[str, Any]]
    uncommitted_changes: list[str]
    active_runs: list[dict[str, Any]]
    next_steps: str | None
    blockers: str | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "saved_at": self.saved_at,
            "name": self.name,
            "current_task": self.current_task,
            "recent_notes": self.recent_notes,
            "uncommitted_changes": self.uncommitted_changes,
            "active_runs": self.active_runs,
            "next_steps": self.next_steps,
            "blockers": self.blockers,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
        """Create SessionState from dictionary."""
        return cls(
            saved_at=data["saved_at"],
            name=data.get("name"),
            current_task=data.get("current_task"),
            recent_notes=data.get("recent_notes", []),
            uncommitted_changes=data.get("uncommitted_changes", []),
            active_runs=data.get("active_runs", []),
            next_steps=data.get("next_steps"),
            blockers=data.get("blockers"),
        )


def get_sessions_dir() -> Path:
    """Get the sessions directory, creating it if needed."""
    schema = IdlerGearSchema(root=Path.cwd())
    sessions_dir = schema.idlergear_dir / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


def capture_session_state(
    name: str | None = None, next_steps: str | None = None, blockers: str | None = None
) -> SessionState:
    """Capture current session state.

    Args:
        name: Optional name for the session
        next_steps: Optional description of what to do next
        blockers: Optional description of what's blocking progress

    Returns:
        SessionState object with captured state
    """
    # Get current task (if any task is marked in_progress)
    task_backend = get_backend("task")
    tasks = task_backend.list()
    in_progress_tasks = [t for t in tasks if t.get("status") == "in_progress"]
    current_task = in_progress_tasks[0] if in_progress_tasks else None

    # Get recent notes (last 5)
    note_backend = get_backend("note")
    notes = note_backend.list()
    notes.sort(key=lambda n: n.get("created", ""), reverse=True)
    recent_notes = notes[:5]

    # Get git uncommitted files
    git_files, _, _ = get_git_status()
    uncommitted_changes = [f["path"] for f in git_files]

    # Get active runs (if run backend exists)
    try:
        run_backend = get_backend("run")
        runs = run_backend.list()
        active_runs = [r for r in runs if r.get("status") == "running"]
    except ValueError:
        active_runs = []

    return SessionState(
        saved_at=datetime.utcnow().isoformat() + "Z",
        name=name,
        current_task=current_task,
        recent_notes=recent_notes,
        uncommitted_changes=uncommitted_changes,
        active_runs=active_runs,
        next_steps=next_steps,
        blockers=blockers,
    )


def save_session(
    name: str | None = None, next_steps: str | None = None, blockers: str | None = None
) -> Path:
    """Save current session state to disk.

    Args:
        name: Optional name for the session. If not provided, uses timestamp.
        next_steps: Optional description of what to do next
        blockers: Optional description of what's blocking progress

    Returns:
        Path to the saved session file
    """
    state = capture_session_state(name=name, next_steps=next_steps, blockers=blockers)
    sessions_dir = get_sessions_dir()

    # Generate filename
    if name:
        # Named session
        filename = f"{name}.json"
    else:
        # Timestamp session
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
        filename = f"{timestamp}.json"

    session_file = sessions_dir / filename

    # Save to file
    with open(session_file, "w") as f:
        json.dump(state.to_dict(), f, indent=2)

    # Update latest symlink
    latest_link = sessions_dir / "latest.json"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(filename)

    return session_file


def load_session(name: str | None = None) -> SessionState | None:
    """Load a session state from disk.

    Args:
        name: Session name or timestamp. If None, loads the latest session.

    Returns:
        SessionState object, or None if session doesn't exist
    """
    sessions_dir = get_sessions_dir()

    if name is None:
        # Load latest
        latest_link = sessions_dir / "latest.json"
        if not latest_link.exists():
            return None
        session_file = latest_link
    else:
        # Load by name or timestamp
        # Try exact match first
        session_file = sessions_dir / f"{name}.json"
        if not session_file.exists():
            # Try with .json extension if not provided
            if not name.endswith(".json"):
                session_file = sessions_dir / name
            if not session_file.exists():
                return None

    try:
        with open(session_file, "r") as f:
            data = json.load(f)
        return SessionState.from_dict(data)
    except (json.JSONDecodeError, KeyError, FileNotFoundError):
        return None


def list_sessions() -> list[dict[str, Any]]:
    """List all saved sessions.

    Returns:
        List of session metadata dicts with name, saved_at, etc.
    """
    sessions_dir = get_sessions_dir()
    if not sessions_dir.exists():
        return []

    sessions = []
    for session_file in sessions_dir.glob("*.json"):
        # Skip the latest symlink
        if session_file.name == "latest.json":
            continue

        try:
            with open(session_file, "r") as f:
                data = json.load(f)

            sessions.append(
                {
                    "name": session_file.stem,  # Filename without extension
                    "saved_at": data.get("saved_at"),
                    "current_task": data.get("current_task", {}).get("title")
                    if data.get("current_task")
                    else None,
                    "next_steps": data.get("next_steps"),
                    "file": str(session_file),
                }
            )
        except (json.JSONDecodeError, KeyError):
            # Skip corrupt files
            continue

    # Sort by saved_at descending (newest first)
    sessions.sort(key=lambda s: s.get("saved_at", ""), reverse=True)
    return sessions


def format_session_state(state: SessionState, verbose: bool = False) -> str:
    """Format session state for display.

    Args:
        state: SessionState to format
        verbose: Whether to show full details

    Returns:
        Formatted string
    """
    lines = []

    # Header
    saved_time = state.saved_at
    try:
        dt = datetime.fromisoformat(saved_time.replace("Z", "+00:00"))
        # Calculate time ago
        elapsed = datetime.now() - dt.replace(tzinfo=None)
        hours = int(elapsed.total_seconds() / 3600)
        if hours < 1:
            minutes = int(elapsed.total_seconds() / 60)
            time_ago = f"{minutes} minutes ago"
        elif hours < 24:
            time_ago = f"{hours} hours ago"
        else:
            days = hours // 24
            time_ago = f"{days} days ago"
    except (ValueError, TypeError):
        time_ago = "unknown time ago"

    lines.append(f"=== Session State ===")
    if state.name:
        lines.append(f"Name: {state.name}")
    lines.append(f"Saved: {time_ago}")
    lines.append("")

    # Current task
    if state.current_task:
        task_id = state.current_task.get("id", "?")
        task_title = state.current_task.get("title", "Untitled")
        lines.append(f"Working on: #{task_id} {task_title}")
    else:
        lines.append("Working on: No task in progress")

    # Next steps
    if state.next_steps:
        lines.append(f"Next steps: {state.next_steps}")

    # Blockers
    if state.blockers:
        lines.append(f"Blockers: {state.blockers}")

    lines.append("")

    # Recent notes
    if state.recent_notes:
        lines.append(f"Recent notes ({len(state.recent_notes)}):")
        for note in state.recent_notes[:3]:  # Show max 3 in summary
            content = note.get("content", "")
            first_line = content.split("\n")[0]
            if len(first_line) > 60:
                first_line = first_line[:57] + "..."
            tags = note.get("tags", [])
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            lines.append(f'  - "{first_line}"{tag_str}')
        lines.append("")

    # Uncommitted changes
    if state.uncommitted_changes:
        lines.append(f"Uncommitted files ({len(state.uncommitted_changes)}):")
        for path in state.uncommitted_changes[:5]:  # Show max 5
            lines.append(f"  - {path}")
        if len(state.uncommitted_changes) > 5:
            lines.append(f"  ... and {len(state.uncommitted_changes) - 5} more")
        lines.append("")

    # Active runs
    if state.active_runs:
        lines.append(f"Active runs ({len(state.active_runs)}):")
        for run in state.active_runs:
            name = run.get("name", "unnamed")
            lines.append(f"  - {name}")
        lines.append("")

    return "\n".join(lines)
