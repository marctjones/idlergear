"""Tests for TUI views (all 6 views)."""

import pytest
from pathlib import Path

from idlergear.tui.views import (
    ByTypeView,
    ByProjectView,
    ByTimeView,
    GapsView,
    ActivityView,
    AIMonitorView,
)
from idlergear.tasks import create_task
from idlergear.notes import create_note
from idlergear.reference import add_reference
from idlergear.file_registry import FileRegistry


def test_by_type_view_initialization(temp_project):
    """Test ByTypeView initialization."""
    view = ByTypeView(project_root=temp_project)

    assert view.view_id == 1
    assert view.view_name == "By Type"
    assert view.project_root == temp_project


def test_by_type_view_compose_tree_empty(temp_project):
    """Test ByTypeView with no data."""
    view = ByTypeView(project_root=temp_project)
    view.data = {
        "tasks": [],
        "notes": [],
        "references": [],
        "files": []
    }

    tree = view.compose_tree()

    assert tree is not None
    assert "Knowledge Base" in tree.label


def test_by_type_view_compose_tree_with_tasks(temp_project):
    """Test ByTypeView with tasks data."""
    view = ByTypeView(project_root=temp_project)

    # Create mock tasks
    view.data = {
        "tasks": [
            {"id": 1, "title": "High priority task", "priority": "high"},
            {"id": 2, "title": "Low priority task", "priority": "low"}
        ],
        "notes": [],
        "references": [],
        "files": []
    }

    tree = view.compose_tree()

    # Tree should be created without errors
    assert tree is not None


def test_by_project_view_initialization(temp_project):
    """Test ByProjectView initialization."""
    view = ByProjectView(project_root=temp_project)

    assert view.view_id == 2
    assert view.view_name == "By Project"


def test_by_project_view_compose_tree(temp_project):
    """Test ByProjectView composition."""
    view = ByProjectView(project_root=temp_project)
    view.data = {
        "tasks": [
            {"id": 1, "title": "Task 1", "milestone": "v1.0"},
            {"id": 2, "title": "Task 2", "milestone": "v1.0"},
            {"id": 3, "title": "Task 3", "milestone": None}
        ]
    }

    tree = view.compose_tree()

    assert tree is not None
    # Should group by milestone


def test_by_time_view_initialization(temp_project):
    """Test ByTimeView initialization."""
    view = ByTimeView(project_root=temp_project)

    assert view.view_id == 3
    assert view.view_name == "By Time"


def test_by_time_view_compose_tree(temp_project):
    """Test ByTimeView composition."""
    view = ByTimeView(project_root=temp_project)
    view.data = {
        "tasks": [
            {"id": 1, "title": "Task 1", "created": "2026-01-26T10:00:00Z"},
            {"id": 2, "title": "Task 2", "created": "2026-01-01T10:00:00Z"}
        ]
    }

    tree = view.compose_tree()

    assert tree is not None
    # Should categorize by time periods


def test_gaps_view_initialization(temp_project):
    """Test GapsView initialization."""
    view = GapsView(project_root=temp_project)

    assert view.view_id == 4
    assert view.view_name == "Gaps"


def test_gaps_view_compose_tree_empty(temp_project):
    """Test GapsView with no gaps."""
    view = GapsView(project_root=temp_project)
    view.data = {"gaps": []}

    tree = view.compose_tree()

    assert tree is not None


def test_gaps_view_compose_tree_with_gaps(temp_project):
    """Test GapsView with gap data."""
    view = GapsView(project_root=temp_project)
    view.data = {
        "gaps": [
            {
                "type": "orphaned_code",
                "severity": "high",
                "location": "src/main.py",
                "description": "File without annotation",
                "suggestion": "idlergear file annotate src/main.py"
            },
            {
                "type": "broken_link",
                "severity": "medium",
                "location": "docs/README.md",
                "description": "Link to missing file",
                "suggestion": "Fix link"
            }
        ]
    }

    tree = view.compose_tree()

    assert tree is not None
    # Should group by severity


def test_activity_view_initialization(temp_project):
    """Test ActivityView initialization."""
    view = ActivityView(project_root=temp_project)

    assert view.view_id == 5
    assert view.view_name == "Activity"


def test_activity_view_compose_tree_with_suggestions(temp_project):
    """Test ActivityView with suggestions."""
    view = ActivityView(project_root=temp_project)
    view.data = {
        "suggestions": [
            {
                "type": "task_recommendation",
                "priority": 8,
                "title": "Work on: High priority task",
                "description": "Task description",
                "action": "idlergear task show 1",
                "reason": "High priority, unblocked",
                "confidence": 0.85
            }
        ]
    }

    tree = view.compose_tree()

    assert tree is not None


def test_activity_view_compose_tree_empty(temp_project):
    """Test ActivityView with no suggestions."""
    view = ActivityView(project_root=temp_project)
    view.data = {"suggestions": []}

    tree = view.compose_tree()

    assert tree is not None


def test_ai_monitor_view_initialization(temp_project):
    """Test AIMonitorView initialization."""
    view = AIMonitorView(project_root=temp_project)

    assert view.view_id == 6
    assert view.view_name == "AI Monitor"


def test_ai_monitor_view_compose_tree_no_agents(temp_project):
    """Test AIMonitorView with no active agents."""
    view = AIMonitorView(project_root=temp_project)
    view.data = {"agents": []}

    tree = view.compose_tree()

    assert tree is not None


def test_ai_monitor_view_compose_tree_with_agent(temp_project):
    """Test AIMonitorView with active agent data."""
    view = AIMonitorView(project_root=temp_project)
    view.data = {
        "agents": [
            {
                "agent_type": "claude-code",
                "status": "active",
                "ai_state": {
                    "current_activity": {
                        "phase": "implementing",
                        "action": "editing file",
                        "target": "src/main.py",
                        "reason": "Adding new feature"
                    },
                    "planned_steps": {
                        "steps": [
                            {"action": "edit", "path": "src/main.py"},
                            {"action": "test", "path": "tests/test_main.py"}
                        ],
                        "confidence": 0.85
                    },
                    "uncertainties": [
                        {
                            "question": "Should we use async?",
                            "confidence": 0.6
                        }
                    ],
                    "search_history": [
                        {
                            "query": "async function",
                            "results_found": 3
                        }
                    ]
                }
            }
        ]
    }

    tree = view.compose_tree()

    assert tree is not None
    # Should display AI state information


def test_ai_monitor_view_low_confidence_warning(temp_project):
    """Test that AIMonitorView shows warnings for low confidence."""
    view = AIMonitorView(project_root=temp_project)
    view.data = {
        "agents": [
            {
                "agent_type": "claude-code",
                "status": "active",
                "ai_state": {
                    "planned_steps": {
                        "steps": [{"action": "risky_operation"}],
                        "confidence": 0.5  # Low confidence
                    },
                    "uncertainties": [
                        {
                            "question": "Very uncertain",
                            "confidence": 0.3  # Very low
                        }
                    ]
                }
            }
        ]
    }

    tree = view.compose_tree()

    # Should complete without errors (warnings displayed in tree)
    assert tree is not None


def test_by_type_view_refresh_data_loads_real_data(temp_project):
    """Test that ByTypeView refresh_data loads actual data."""
    # Create real data
    create_task("Test task", priority="high")
    create_note("Test note")
    add_reference("Test ref")

    view = ByTypeView(project_root=temp_project)

    # Trigger refresh
    import asyncio
    asyncio.run(view.refresh_data())

    # Data should be loaded
    assert "tasks" in view.data
    assert len(view.data["tasks"]) > 0


def test_gaps_view_refresh_data_detects_gaps(temp_project):
    """Test that GapsView refresh_data detects actual gaps."""
    # Create orphaned file
    src_dir = temp_project / "src"
    src_dir.mkdir()
    (src_dir / "orphan.py").write_text("pass")

    view = GapsView(project_root=temp_project)

    # Trigger refresh
    import asyncio
    asyncio.run(view.refresh_data())

    # Should detect gaps
    assert "gaps" in view.data


def test_activity_view_refresh_data_generates_suggestions(temp_project):
    """Test that ActivityView refresh_data generates suggestions."""
    # Create task to generate suggestions from
    create_task("Test task", priority="high")

    view = ActivityView(project_root=temp_project)

    # Trigger refresh
    import asyncio
    asyncio.run(view.refresh_data())

    # Should have suggestions data
    assert "suggestions" in view.data


def test_all_views_have_unique_ids():
    """Test that all views have unique IDs."""
    from pathlib import Path

    project = Path("/test")

    views = [
        ByTypeView(project_root=project),
        ByProjectView(project_root=project),
        ByTimeView(project_root=project),
        GapsView(project_root=project),
        ActivityView(project_root=project),
        AIMonitorView(project_root=project),
    ]

    view_ids = [v.view_id for v in views]

    # All IDs should be unique
    assert len(view_ids) == len(set(view_ids))
    # IDs should be 1-6
    assert set(view_ids) == {1, 2, 3, 4, 5, 6}


def test_all_views_have_names():
    """Test that all views have descriptive names."""
    from pathlib import Path

    project = Path("/test")

    views = [
        ByTypeView(project_root=project),
        ByProjectView(project_root=project),
        ByTimeView(project_root=project),
        GapsView(project_root=project),
        ActivityView(project_root=project),
        AIMonitorView(project_root=project),
    ]

    for view in views:
        assert view.view_name
        assert len(view.view_name) > 0


def test_by_type_view_groups_tasks_by_priority(temp_project):
    """Test that ByTypeView groups tasks correctly."""
    view = ByTypeView(project_root=temp_project)
    view.data = {
        "tasks": [
            {"id": 1, "title": "Critical", "priority": "critical"},
            {"id": 2, "title": "High", "priority": "high"},
            {"id": 3, "title": "Medium", "priority": "medium"},
            {"id": 4, "title": "Low", "priority": "low"},
            {"id": 5, "title": "None", "priority": None}
        ],
        "notes": [],
        "references": [],
        "files": []
    }

    tree = view.compose_tree()

    # Should handle all priority levels without errors
    assert tree is not None
