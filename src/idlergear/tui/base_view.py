"""Base view classes for TUI redesign.

Provides abstract base class for all views and view manager for switching between views.
"""

from __future__ import annotations

from typing import Any

from textual.reactive import reactive
from textual.widgets import Static, Tree
from textual.containers import Container


class BaseView(Static):
    """Abstract base class for all TUI views.

    Each view provides a different organizational lens on the knowledge base:
    - View 1: By Type (tasks, notes, references, files)
    - View 2: By Project (grouped by milestone/project)
    - View 3: By Time (today, this week, this month)
    - View 4: Gaps (knowledge gaps by severity)
    - View 5: Activity (recent events feed)
    - View 6: AI Monitor (real-time AI state)
    """

    # Reactive data that triggers refresh when changed
    data: reactive[dict[str, Any]] = reactive({})

    def __init__(self, view_id: int, view_name: str, project_root=None, **kwargs):
        """Initialize base view.

        Args:
            view_id: Numeric ID (1-6) for view switching
            view_name: Display name for the view
            project_root: Optional project root path (auto-detected if not provided)
        """
        super().__init__(**kwargs)
        self.view_id = view_id
        self.view_name = view_name
        self.project_root = project_root
        self._tree: Tree[dict] | None = None

    def compose_tree(self) -> Tree[dict]:
        """Compose the tree structure for this view.

        Each view must implement this to define how data is organized.

        Returns:
            Tree widget with view-specific organization
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement compose_tree()"
        )

    async def refresh_data(self) -> None:
        """Refresh data from backend.

        Each view must implement this to load its required data.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement refresh_data()"
        )

    def on_mount(self) -> None:
        """Called when view is mounted."""
        # Initialize with empty tree immediately so something shows
        if self._tree is None:
            self._tree = self.compose_tree()
            self._tree.show_root = True
            self._tree.show_guides = True
            self.mount(self._tree)

        # Then load data asynchronously
        self.run_worker(self._async_refresh(), exclusive=True)

    async def _async_refresh(self) -> None:
        """Async helper to refresh data."""
        try:
            await self.refresh_data()
            # Schedule tree rebuild on main thread after data is loaded
            self.call_from_thread(self._rebuild_tree)
        except Exception as e:
            # Log error but don't crash the view
            self.app.log.error(f"Error refreshing {self.view_name}: {e}")
            # Set empty data to show something
            self.data = {}

    def _rebuild_tree(self) -> None:
        """Rebuild tree from current data (must be called from main thread)."""
        if self._tree is not None:
            # Remove old tree
            try:
                self._tree.remove()
            except:
                pass

        # Create new tree
        self._tree = self.compose_tree()
        self._tree.show_root = True
        self._tree.show_guides = True

        # Mount new tree (safe because called from main thread)
        self.mount(self._tree)

    def watch_data(self, data: dict[str, Any]) -> None:
        """React to data changes."""
        self._rebuild_tree()

    def refresh(self, **kwargs) -> None:
        """Trigger a refresh (can be called from key bindings)."""
        self.run_worker(self._async_refresh(), exclusive=True)


class ViewManager:
    """Manages switching between different views.

    Handles:
    - View registration
    - View activation/deactivation
    - View state persistence
    - View transitions
    """

    def __init__(self, container: Container):
        """Initialize view manager.

        Args:
            container: Container widget to mount views in
        """
        self.container = container
        self.views: dict[int, BaseView] = {}
        self.current_view_id: int | None = None
        self._view_states: dict[int, dict[str, Any]] = {}

    def register_view(self, view: BaseView) -> None:
        """Register a view with the manager.

        Args:
            view: View instance to register
        """
        self.views[view.view_id] = view

    def switch_to_view(self, view_id: int) -> bool:
        """Switch to a different view.

        Args:
            view_id: ID of view to switch to (1-6)

        Returns:
            True if switch successful, False otherwise
        """
        if view_id not in self.views:
            return False

        # Save state of current view
        if self.current_view_id is not None:
            current_view = self.views.get(self.current_view_id)
            if current_view:
                self._view_states[self.current_view_id] = {
                    "data": current_view.data,
                    # Can add more state here (scroll position, selected item, etc.)
                }
                # Hide current view
                current_view.display = False

        # Show new view
        new_view = self.views[view_id]
        new_view.display = True

        # Restore state if exists
        if view_id in self._view_states:
            state = self._view_states[view_id]
            new_view.data = state.get("data", {})

        self.current_view_id = view_id

        # Trigger refresh of new view
        new_view.refresh()

        return True

    def get_current_view(self) -> BaseView | None:
        """Get currently active view.

        Returns:
            Current view or None if no view active
        """
        if self.current_view_id is None:
            return None
        return self.views.get(self.current_view_id)

    def refresh_current_view(self) -> None:
        """Refresh the currently active view."""
        view = self.get_current_view()
        if view:
            view.refresh()
