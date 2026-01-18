"""Task context provider."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CurrentTask:
    """Current task information."""

    id: int
    title: str
    started_at: Optional[str]


class TaskContext:
    """Provides current task context."""

    def __init__(self):
        self._current_task: Optional[CurrentTask] = None
        self._last_refresh: Optional[datetime] = None

    def get_current(self) -> Optional[CurrentTask]:
        """Get current task (refreshes if stale)."""
        now = datetime.now()

        # Refresh every 5 seconds
        if not self._last_refresh or (now - self._last_refresh).seconds > 5:
            self._refresh()
            self._last_refresh = now

        return self._current_task

    def _refresh(self):
        """Refresh current task from session state."""
        try:
            from idlergear.sessions import capture_session_state

            state = capture_session_state()

            if state.current_task:
                self._current_task = CurrentTask(
                    id=state.current_task.get("id"),
                    title=state.current_task.get("title", "Unknown"),
                    started_at=state.saved_at,
                )
            else:
                self._current_task = None
        except Exception:
            self._current_task = None
