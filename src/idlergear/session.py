"""Session state management for IdlerGear.

Tracks session state across AI assistant sessions to provide continuity.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from idlergear.config import find_idlergear_root


class SessionState:
    """Manages session state persistence."""

    def __init__(self, root: Optional[Path] = None):
        """Initialize session state manager.

        Args:
            root: IdlerGear root directory. If None, auto-detect.
        """
        self.root = root or find_idlergear_root()
        if not self.root:
            raise ValueError("Not in an IdlerGear project")
        self.state_file = self.root / ".idlergear" / "session_state.json"

    def save(
        self,
        current_task_id: Optional[int] = None,
        context_mode: str = "minimal",
        working_files: Optional[list[str]] = None,
        notes: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Save current session state.

        Args:
            current_task_id: ID of task currently being worked on
            context_mode: Last used context mode (minimal, standard, detailed, full)
            working_files: List of files currently being worked on
            notes: Free-form notes about current session
            metadata: Additional metadata to store

        Returns:
            The saved state dict
        """
        state = {
            "current_task_id": current_task_id,
            "context_mode": context_mode,
            "working_files": working_files or [],
            "notes": notes,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }

        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, indent=2))
        return state

    def load(self) -> Optional[dict[str, Any]]:
        """Load session state.

        Returns:
            Session state dict or None if no state exists
        """
        if not self.state_file.exists():
            return None

        try:
            return json.loads(self.state_file.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def clear(self) -> bool:
        """Clear session state.

        Returns:
            True if state was cleared, False if no state existed
        """
        if self.state_file.exists():
            self.state_file.unlink()
            return True
        return False

    def get_summary(self) -> str:
        """Get human-readable summary of session state.

        Returns:
            Formatted summary string
        """
        state = self.load()
        if not state:
            return "No session state saved."

        lines = ["# Session State"]
        lines.append(f"**Last Updated:** {state['timestamp']}")
        lines.append("")

        if state.get("current_task_id"):
            lines.append(f"**Current Task:** #{state['current_task_id']}")

        if state.get("context_mode"):
            lines.append(f"**Context Mode:** {state['context_mode']}")

        if state.get("working_files"):
            lines.append(f"**Working Files:** ({len(state['working_files'])} files)")
            for f in state["working_files"][:5]:  # Show first 5
                lines.append(f"  - {f}")
            if len(state["working_files"]) > 5:
                lines.append(f"  - ... and {len(state['working_files']) - 5} more")

        if state.get("notes"):
            lines.append("")
            lines.append("**Notes:**")
            lines.append(state["notes"])

        if state.get("metadata"):
            lines.append("")
            lines.append("**Metadata:**")
            for key, value in state["metadata"].items():
                lines.append(f"  - {key}: {value}")

        return "\n".join(lines)


def start_session(
    context_mode: str = "minimal",
    load_state: bool = True,
) -> dict[str, Any]:
    """Start a new session, optionally loading previous state.

    This is the recommended first call in any AI assistant session.

    Args:
        context_mode: Context mode to use (minimal, standard, detailed, full)
        load_state: Whether to load previous session state

    Returns:
        Dict containing:
            - context: Project context (vision, plan, tasks, notes)
            - session_state: Previous session state (if load_state=True)
            - recommendations: What to work on based on state
    """
    from idlergear.context import gather_context

    result: dict[str, Any] = {}

    # Load project context
    result["context"] = gather_context(mode=context_mode)

    # Load session state if requested
    if load_state:
        session = SessionState()
        state = session.load()
        result["session_state"] = state

        # Generate recommendations
        recommendations = []
        if state:
            if state.get("current_task_id"):
                recommendations.append(
                    f"Continue working on task #{state['current_task_id']}"
                )
            if state.get("working_files"):
                recommendations.append(
                    f"Resume editing {len(state['working_files'])} files"
                )
            if state.get("notes"):
                recommendations.append(f"Review notes: {state['notes'][:100]}")
        else:
            recommendations.append("No previous session found - starting fresh!")

        result["recommendations"] = recommendations

    return result


def end_session(
    current_task_id: Optional[int] = None,
    working_files: Optional[list[str]] = None,
    notes: Optional[str] = None,
    auto_suggest: bool = True,
) -> dict[str, Any]:
    """End current session and save state.

    Args:
        current_task_id: ID of task being worked on
        working_files: Files being worked on
        notes: Session notes
        auto_suggest: Whether to generate suggestions for next session

    Returns:
        Dict containing saved state and suggestions
    """
    session = SessionState()

    # Save state
    state = session.save(
        current_task_id=current_task_id,
        working_files=working_files,
        notes=notes,
    )

    result = {"state": state}

    # Generate suggestions for next session
    if auto_suggest:
        suggestions = []
        if current_task_id:
            suggestions.append(f"Next session: Continue task #{current_task_id}")
        if working_files:
            suggestions.append(
                f"Next session: Resume editing {len(working_files)} files"
            )

        result["suggestions"] = suggestions

    return result
