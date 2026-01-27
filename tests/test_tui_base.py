"""Tests for TUI base components (BaseView and ViewManager)."""

import pytest
from textual.widgets import Tree
from textual.app import App

from idlergear.tui.base_view import BaseView, ViewManager


class MockView(BaseView):
    """Mock view for testing."""

    def __init__(self, view_id, view_name, project_root=None, **kwargs):
        super().__init__(view_id, view_name, project_root, **kwargs)
        self.compose_tree_called = False
        self.refresh_data_called = False

    def compose_tree(self) -> Tree:
        """Mock tree composition."""
        self.compose_tree_called = True
        tree = Tree("Mock Tree")
        tree.data = {}
        tree.root.add_leaf("Mock Data")
        return tree

    async def refresh_data(self) -> None:
        """Mock data refresh."""
        self.refresh_data_called = True
        self.data = {"mock": "data"}


def test_base_view_initialization():
    """Test BaseView initialization."""
    view = MockView(
        view_id=1,
        view_name="Test View",
        project_root=None
    )

    assert view.view_id == 1
    assert view.view_name == "Test View"
    assert view.project_root is None
    assert view._tree is None


def test_base_view_compose_tree():
    """Test that compose_tree must be implemented."""
    view = MockView(view_id=1, view_name="Test")

    tree = view.compose_tree()

    assert isinstance(tree, Tree)
    assert view.compose_tree_called


def test_base_view_not_implemented_error():
    """Test that BaseView raises NotImplementedError for abstract methods."""
    class IncompleteView(BaseView):
        """View that doesn't implement required methods."""
        pass

    view = IncompleteView(view_id=1, view_name="Incomplete")

    with pytest.raises(NotImplementedError):
        view.compose_tree()

    with pytest.raises(NotImplementedError):
        import asyncio
        asyncio.run(view.refresh_data())


@pytest.mark.skip(reason="Requires mounted widget - reactive properties only work in app context")
def test_base_view_reactive_data():
    """Test that BaseView has reactive data attribute."""
    view = MockView(view_id=1, view_name="Test")

    # Initial data should be empty dict
    assert view.data == {}

    # Should be able to set data
    view.data = {"test": "value"}
    assert view.data == {"test": "value"}


@pytest.mark.skip(reason="Requires mounted widget - refresh() calls run_worker which needs app context")
def test_base_view_refresh_accepts_kwargs():
    """Test that refresh method accepts kwargs (for Textual compatibility)."""
    view = MockView(view_id=1, view_name="Test")

    # Should not raise error with kwargs
    try:
        view.refresh(repaint=True, layout=False)
    except TypeError:
        pytest.fail("refresh() should accept **kwargs")


def test_view_manager_initialization():
    """Test ViewManager initialization."""
    from textual.containers import Container

    container = Container()
    manager = ViewManager(container)

    assert manager.container is container
    assert manager.views == {}
    assert manager.current_view_id is None
    assert manager._view_states == {}


def test_view_manager_register_view():
    """Test registering views with ViewManager."""
    from textual.containers import Container

    container = Container()
    manager = ViewManager(container)

    view1 = MockView(view_id=1, view_name="View 1")
    view2 = MockView(view_id=2, view_name="View 2")

    manager.register_view(view1)
    manager.register_view(view2)

    assert 1 in manager.views
    assert 2 in manager.views
    assert manager.views[1] is view1
    assert manager.views[2] is view2


@pytest.mark.skip(reason="Requires mounted widgets - switch_to_view sets display property which needs app context")
def test_view_manager_switch_to_view():
    """Test switching between views."""
    from textual.containers import Container

    container = Container()
    manager = ViewManager(container)

    view1 = MockView(view_id=1, view_name="View 1")
    view2 = MockView(view_id=2, view_name="View 2")

    manager.register_view(view1)
    manager.register_view(view2)

    # Switch to view 1
    success = manager.switch_to_view(1)

    assert success is True
    assert manager.current_view_id == 1


def test_view_manager_switch_to_invalid_view():
    """Test switching to non-existent view."""
    from textual.containers import Container

    container = Container()
    manager = ViewManager(container)

    # Try to switch to view that doesn't exist
    success = manager.switch_to_view(999)

    assert success is False
    assert manager.current_view_id is None


@pytest.mark.skip(reason="Requires mounted widgets - depends on switch_to_view which needs app context")
def test_view_manager_get_current_view():
    """Test getting the current view."""
    from textual.containers import Container

    container = Container()
    manager = ViewManager(container)

    view1 = MockView(view_id=1, view_name="View 1")
    manager.register_view(view1)
    manager.switch_to_view(1)

    current = manager.get_current_view()

    assert current is view1


def test_view_manager_get_current_view_when_none():
    """Test getting current view when none is active."""
    from textual.containers import Container

    container = Container()
    manager = ViewManager(container)

    current = manager.get_current_view()

    assert current is None


@pytest.mark.skip(reason="Requires mounted widgets - depends on switch_to_view and reactive data")
def test_view_manager_state_persistence():
    """Test that view state is saved when switching."""
    from textual.containers import Container

    container = Container()
    manager = ViewManager(container)

    view1 = MockView(view_id=1, view_name="View 1")
    view2 = MockView(view_id=2, view_name="View 2")

    manager.register_view(view1)
    manager.register_view(view2)

    # Set some data in view 1
    manager.switch_to_view(1)
    view1.data = {"saved": "state"}

    # Switch to view 2
    manager.switch_to_view(2)

    # State should be saved
    assert 1 in manager._view_states
    assert manager._view_states[1]["data"] == {"saved": "state"}


@pytest.mark.skip(reason="Requires mounted widgets - depends on switch_to_view and reactive data")
def test_view_manager_state_restoration():
    """Test that view state is restored when switching back."""
    from textual.containers import Container

    container = Container()
    manager = ViewManager(container)

    view1 = MockView(view_id=1, view_name="View 1")
    view2 = MockView(view_id=2, view_name="View 2")

    manager.register_view(view1)
    manager.register_view(view2)

    # Set data in view 1
    manager.switch_to_view(1)
    view1.data = {"original": "data"}

    # Switch to view 2
    manager.switch_to_view(2)

    # Switch back to view 1
    manager.switch_to_view(1)

    # State should be restored
    assert view1.data == {"original": "data"}


@pytest.mark.skip(reason="Requires mounted widgets - refresh() calls run_worker which needs app context")
def test_view_manager_refresh_current_view():
    """Test refreshing the current view."""
    from textual.containers import Container

    container = Container()
    manager = ViewManager(container)

    view1 = MockView(view_id=1, view_name="View 1")
    manager.register_view(view1)
    manager.switch_to_view(1)

    # Refresh should not crash
    manager.refresh_current_view()

    # MockView.refresh() triggers run_worker which we can't easily test
    # Just verify it doesn't crash


def test_view_manager_refresh_when_no_view_active():
    """Test refreshing when no view is active."""
    from textual.containers import Container

    container = Container()
    manager = ViewManager(container)

    # Should not crash
    manager.refresh_current_view()


def test_base_view_project_root_parameter():
    """Test that project_root is passed through correctly."""
    from pathlib import Path

    project_path = Path("/test/project")
    view = MockView(
        view_id=1,
        view_name="Test",
        project_root=project_path
    )

    assert view.project_root == project_path


@pytest.mark.skip(reason="Requires mounted widgets - display property only works in app context")
def test_view_manager_hides_previous_view():
    """Test that previous view is hidden when switching."""
    from textual.containers import Container

    container = Container()
    manager = ViewManager(container)

    view1 = MockView(view_id=1, view_name="View 1")
    view2 = MockView(view_id=2, view_name="View 2")

    manager.register_view(view1)
    manager.register_view(view2)

    # Switch to view 1
    manager.switch_to_view(1)
    assert view1.display is True

    # Switch to view 2
    manager.switch_to_view(2)

    # View 1 should be hidden
    assert view1.display is False
    assert view2.display is True
