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
        self._rebuilding = False  # Flag to prevent recursive rebuilds

        # Setup logging
        import logging
        self.logger = logging.getLogger(f'TUI.View.{view_name}')
        self.logger.info(f"View {view_id} ({view_name}) initialized with project_root={project_root}")

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
        self.logger.info(f"on_mount() - View {self.view_id} ({self.view_name}) mounting")

        # Load data asynchronously - tree will be created when data arrives via watch_data()
        self.logger.debug(f"on_mount() - Starting async refresh worker for {self.view_name}")
        self.run_worker(self._async_refresh(), exclusive=True)

    async def _async_refresh(self) -> None:
        """Async helper to refresh data."""
        self.logger.debug(f"_async_refresh() - Starting data refresh for {self.view_name}")
        try:
            await self.refresh_data()
            self.logger.debug(f"_async_refresh() - Data loaded for {self.view_name}")
            # Note: Setting self.data in refresh_data() triggers watch_data() automatically
            # which will rebuild the tree, so no need to call _rebuild_tree() here
        except Exception as e:
            # Log error but don't crash the view
            self.logger.error(f"_async_refresh() - Error refreshing {self.view_name}: {e}", exc_info=True)
            self.app.log.error(f"Error refreshing {self.view_name}: {e}")
            # Set empty data to show something
            self.data = {}

    def _rebuild_tree(self) -> None:
        """Rebuild tree from current data (must be called from main thread)."""
        # Prevent recursive rebuilds
        if self._rebuilding:
            self.logger.debug(f"_rebuild_tree() - Already rebuilding, skipping")
            return

        self._rebuilding = True
        try:
            self.logger.debug(f"_rebuild_tree() - Rebuilding tree for {self.view_name}")

            if self._tree is None:
                # First time - create and mount tree
                self.logger.debug(f"_rebuild_tree() - Creating initial tree for {self.view_name}")
                self._tree = self.compose_tree()
                self._tree.show_root = True
                self._tree.show_guides = True
                self._tree.can_focus = True
                self.mount(self._tree)
            else:
                # Subsequent updates - remove old tree and mount new one
                self.logger.debug(f"_rebuild_tree() - Rebuilding existing tree for {self.view_name}")

                # Remove old tree
                try:
                    self._tree.remove()
                except Exception as e:
                    self.logger.warning(f"_rebuild_tree() - Error removing tree: {e}")

                # Create and mount new tree
                self._tree = self.compose_tree()
                self._tree.show_root = True
                self._tree.show_guides = True
                self._tree.can_focus = True
                self.mount(self._tree)

                # Focus is handled by ViewManager.switch_to_view() - don't focus here
                # to avoid triggering additional refresh cycles

            self.logger.info(f"_rebuild_tree() - Tree rebuild complete for {self.view_name}")
        finally:
            self._rebuilding = False

    def watch_data(self, data: dict[str, Any]) -> None:
        """React to data changes."""
        if self._rebuilding:
            self.logger.debug(f"watch_data() - Rebuild in progress, skipping")
            return

        self.logger.debug(f"watch_data() - Data changed for {self.view_name}, triggering rebuild")
        self._rebuild_tree()

    def reload_data(self) -> None:
        """Reload data from backend (can be called from key bindings)."""
        self.logger.info(f"reload_data() - Manual data reload triggered for {self.view_name}")
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

        # Focus the tree in the new view so arrow keys work
        if new_view._tree is not None:
            new_view._tree.focus()

        # Don't trigger refresh - view already has data from:
        # 1. Initial mount (on_mount calls _async_refresh)
        # 2. Restored state (line 222)
        # 3. Tree rebuilt when display=True or data changes

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
        """Reload data for the currently active view."""
        view = self.get_current_view()
        if view:
            view.reload_data()
