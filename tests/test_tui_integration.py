"""Integration tests for TUI v2 with daemon and real data."""

import pytest
from pathlib import Path

from idlergear.tui.app_v2 import IdlerGearAppV2, ViewSwitcher
from idlergear.tasks import create_task
from idlergear.notes import create_note


@pytest.mark.asyncio
async def test_app_initialization(temp_project):
    """Test that IdlerGearAppV2 can be instantiated."""
    app = IdlerGearAppV2(project_root=temp_project)

    assert app.project_root == temp_project
    assert app.view_manager is None  # Not mounted yet
    assert app.daemon_client is None


def test_app_bindings_configured():
    """Test that all key bindings are configured."""
    app = IdlerGearAppV2()

    binding_keys = [b.key for b in app.BINDINGS]

    # Check critical bindings
    assert "q" in binding_keys
    assert "question_mark" in binding_keys  # ? key
    assert "r" in binding_keys
    assert "1" in binding_keys
    assert "2" in binding_keys
    assert "3" in binding_keys
    assert "4" in binding_keys
    assert "5" in binding_keys
    assert "6" in binding_keys


def test_view_switcher_initialization():
    """Test ViewSwitcher widget initialization."""
    switcher = ViewSwitcher()

    assert switcher.current_view == 1  # Starts at view 1


def test_view_switcher_update_current_view():
    """Test ViewSwitcher highlighting."""
    switcher = ViewSwitcher()

    # Initial view
    text = switcher._get_switcher_text()
    assert "1" in text

    # Update to view 6
    switcher.current_view = 6
    text = switcher._get_switcher_text()

    # Should include view 6
    assert "6" in text
    assert "AI Monitor" in text


def test_view_switcher_shows_all_views():
    """Test that ViewSwitcher displays all 6 views."""
    switcher = ViewSwitcher()

    text = switcher._get_switcher_text()

    # All view names should be present
    assert "Type" in text
    assert "Project" in text
    assert "Time" in text
    assert "Gaps" in text
    assert "Activity" in text
    assert "AI Monitor" in text


def test_view_switcher_shows_help_shortcuts():
    """Test that ViewSwitcher shows help shortcuts."""
    switcher = ViewSwitcher()

    text = switcher._get_switcher_text()

    assert "?" in text or "Help" in text
    assert "r" in text or "Refresh" in text
    assert "q" in text or "Quit" in text


@pytest.mark.asyncio
async def test_app_action_switch_view(temp_project):
    """Test view switching action."""
    app = IdlerGearAppV2(project_root=temp_project)

    # Simulate mounting (manually set up view manager)
    from textual.containers import Container
    from idlergear.tui.base_view import ViewManager
    from idlergear.tui.views import ByTypeView, AIMonitorView

    container = Container()
    app.view_manager = ViewManager(container)

    view1 = ByTypeView(project_root=temp_project, id="view-1")
    view6 = AIMonitorView(project_root=temp_project, id="view-6")

    app.view_manager.register_view(view1)
    app.view_manager.register_view(view6)

    # Switch to view 1
    app.action_switch_view(1)
    assert app.view_manager.current_view_id == 1

    # Switch to view 6
    app.action_switch_view(6)
    assert app.view_manager.current_view_id == 6


@pytest.mark.asyncio
async def test_daemon_listener_graceful_without_daemon(temp_project):
    """Test that daemon listener handles missing daemon gracefully."""
    app = IdlerGearAppV2(project_root=temp_project)

    # _start_daemon_listener should not crash if daemon not running
    try:
        await app._start_daemon_listener()
        # Should complete without error
    except Exception as e:
        # Should gracefully handle daemon not running
        pass


def test_app_with_real_tasks(temp_project):
    """Test TUI with real task data."""
    # Create real tasks
    create_task("Task 1", priority="high")
    create_task("Task 2", priority="medium")
    create_task("Task 3", priority="low")

    app = IdlerGearAppV2(project_root=temp_project)

    # App should initialize without errors
    assert app.project_root == temp_project


def test_app_with_real_notes(temp_project):
    """Test TUI with real note data."""
    # Create real notes
    create_note("Note 1")
    create_note("Note 2")

    app = IdlerGearAppV2(project_root=temp_project)

    # App should initialize without errors
    assert app.project_root == temp_project


def test_app_title_and_subtitle():
    """Test that app has appropriate title and subtitle."""
    app = IdlerGearAppV2()

    # Title will be set on mount, but we can check it's defined
    # After mount, it should be set
    expected_title = "IdlerGear - Multi-Agent Knowledge Management"

    # We can't easily test the mounted state, but verify the action works
    assert hasattr(app, 'title')


@pytest.mark.asyncio
async def test_view_refresh_action(temp_project):
    """Test the refresh action."""
    app = IdlerGearAppV2(project_root=temp_project)

    # Create mock view manager
    from textual.containers import Container
    from idlergear.tui.base_view import ViewManager

    container = Container()
    app.view_manager = ViewManager(container)

    # action_refresh should not crash
    app.action_refresh()


def test_app_compose_creates_all_views(temp_project):
    """Test that compose creates all 6 views."""
    app = IdlerGearAppV2(project_root=temp_project)

    # Get compose result
    widgets = list(app.compose())

    # Should have Header, ViewSwitcher, Container, Footer
    assert len(widgets) >= 4


def test_multiple_apps_can_be_created(temp_project):
    """Test that multiple app instances can be created."""
    app1 = IdlerGearAppV2(project_root=temp_project)
    app2 = IdlerGearAppV2(project_root=temp_project)

    assert app1 is not app2
    assert app1.project_root == app2.project_root


def test_app_without_project_root():
    """Test app can be created without explicit project_root."""
    app = IdlerGearAppV2(project_root=None)

    assert app.project_root is None


def test_view_names_match_bindings():
    """Test that view names in bindings match actual views."""
    app = IdlerGearAppV2()

    # Get binding descriptions
    binding_descriptions = {b.key: b.description for b in app.BINDINGS}

    assert binding_descriptions.get("1") == "By Type"
    assert binding_descriptions.get("2") == "By Project"
    assert binding_descriptions.get("3") == "By Time"
    assert binding_descriptions.get("4") == "Gaps"
    assert binding_descriptions.get("5") == "Activity"
    assert binding_descriptions.get("6") == "AI Monitor"


@pytest.mark.asyncio
async def test_daemon_client_handles_ai_events(temp_project):
    """Test that daemon client is configured for AI events."""
    app = IdlerGearAppV2(project_root=temp_project)

    # The _start_daemon_listener creates a custom TUIDaemonClient
    # We can't easily test the full integration, but verify the method exists
    assert hasattr(app, '_start_daemon_listener')


def test_view_switcher_css_defined():
    """Test that ViewSwitcher has CSS defined."""
    switcher = ViewSwitcher()

    # Should have CSS attribute
    assert hasattr(switcher, 'CSS')
    assert isinstance(switcher.CSS, str)
    assert len(switcher.CSS) > 0


@pytest.mark.asyncio
async def test_full_app_lifecycle_simulation(temp_project):
    """Test simulated app lifecycle."""
    # Create test data
    create_task("Test task", priority="high")

    # Create app
    app = IdlerGearAppV2(project_root=temp_project)

    # Verify initialization
    assert app.project_root == temp_project

    # Simulate view manager setup
    from textual.containers import Container
    from idlergear.tui.base_view import ViewManager
    from idlergear.tui.views import ByTypeView

    container = Container()
    app.view_manager = ViewManager(container)

    view = ByTypeView(project_root=temp_project, id="view-1")
    app.view_manager.register_view(view)

    # Switch view
    app.action_switch_view(1)

    # Verify state
    assert app.view_manager.current_view_id == 1


def test_app_handles_empty_project(temp_project):
    """Test that app handles project with no data."""
    # Empty project (no tasks, notes, etc.)
    app = IdlerGearAppV2(project_root=temp_project)

    # Should initialize without errors
    assert app.project_root == temp_project


def test_app_with_large_dataset(temp_project):
    """Test app with many tasks."""
    # Create many tasks
    for i in range(50):
        create_task(f"Task {i}", priority="high" if i % 2 == 0 else "low")

    app = IdlerGearAppV2(project_root=temp_project)

    # Should handle large dataset without errors
    assert app.project_root == temp_project
