"""Tests for session history management."""

import json
from pathlib import Path

import pytest

from idlergear.session_history import SessionHistory, SessionIndex, SessionSnapshot


@pytest.fixture
def temp_root(tmp_path):
    """Create temporary IdlerGear root."""
    idlergear_dir = tmp_path / ".idlergear"
    idlergear_dir.mkdir()
    return tmp_path


def test_session_index_initialization(temp_root):
    """Test session index initialization."""
    index = SessionIndex(temp_root)
    data = index.load()

    assert data["version"] == "2.0"
    assert data["current_branch"] == "main"
    assert "main" in data["branches"]
    assert data["branches"]["main"]["sessions"] == []


def test_session_index_add_session(temp_root):
    """Test adding session to index."""
    index = SessionIndex(temp_root)

    index.add_session("s001", "main")
    data = index.load()

    assert "s001" in data["branches"]["main"]["sessions"]
    assert data["branches"]["main"]["latest"] == "s001"
    assert data["current_session"] == "s001"


def test_create_snapshot(temp_root):
    """Test creating a session snapshot."""
    history = SessionHistory(temp_root)

    snapshot = history.create_snapshot(
        state={
            "current_task_id": 270,
            "working_files": ["test.py"],
            "notes": "Test session",
        },
        duration_seconds=1800,
    )

    assert snapshot.session_id == "s001"
    assert snapshot.branch == "main"
    assert snapshot.parent is None
    assert snapshot.state["current_task_id"] == 270
    assert snapshot.duration_seconds == 1800


def test_create_multiple_snapshots(temp_root):
    """Test creating multiple snapshots with parent tracking."""
    history = SessionHistory(temp_root)

    # Create first snapshot
    s1 = history.create_snapshot(
        state={"current_task_id": 270, "notes": "First session"}
    )
    assert s1.session_id == "s001"
    assert s1.parent is None

    # Create second snapshot (should have s001 as parent)
    s2 = history.create_snapshot(
        state={"current_task_id": 271, "notes": "Second session"}
    )
    assert s2.session_id == "s002"
    assert s2.parent == "s001"

    # Verify parent's children list was updated
    s1_reloaded = history.load_snapshot("s001")
    assert "s002" in s1_reloaded.data.get("children", [])


def test_list_sessions(temp_root):
    """Test listing session history."""
    history = SessionHistory(temp_root)

    # Create multiple snapshots
    history.create_snapshot(state={"notes": "Session 1"})
    history.create_snapshot(state={"notes": "Session 2"})
    history.create_snapshot(state={"notes": "Session 3"})

    # List sessions
    sessions = history.list_sessions("main")
    assert len(sessions) == 3
    assert sessions[0].session_id == "s001"
    assert sessions[1].session_id == "s002"
    assert sessions[2].session_id == "s003"


def test_get_latest_snapshot(temp_root):
    """Test getting latest snapshot."""
    history = SessionHistory(temp_root)

    history.create_snapshot(state={"notes": "Session 1"})
    history.create_snapshot(state={"notes": "Session 2"})
    s3 = history.create_snapshot(state={"notes": "Session 3"})

    latest = history.get_latest_snapshot("main")
    assert latest.session_id == s3.session_id
    assert latest.state["notes"] == "Session 3"


def test_get_session_history(temp_root):
    """Test getting full session history (ancestry chain)."""
    history = SessionHistory(temp_root)

    s1 = history.create_snapshot(state={"notes": "Session 1"})
    s2 = history.create_snapshot(state={"notes": "Session 2"})
    s3 = history.create_snapshot(state={"notes": "Session 3"})

    # Get history for s003
    ancestry = history.get_session_history("s003", "main")
    assert len(ancestry) == 3
    assert ancestry[0].session_id == "s001"
    assert ancestry[1].session_id == "s002"
    assert ancestry[2].session_id == "s003"


def test_session_snapshot_properties(temp_root):
    """Test SessionSnapshot properties."""
    history = SessionHistory(temp_root)

    snapshot = history.create_snapshot(
        state={
            "current_task_id": 270,
            "working_files": ["test.py"],
            "git_branch": "main",
            "git_commit": "abc123",
            "notes": "Test",
        },
        code_changes={
            "files_modified": ["test.py"],
            "lines_added": 10,
            "lines_removed": 2,
        },
        statistics={
            "tool_calls": 5,
            "errors_encountered": 0,
        },
        outcome={
            "status": "success",
            "goals_achieved": ["Implemented feature"],
        },
        duration_seconds=900,
    )

    assert snapshot.session_id == "s001"
    assert snapshot.branch == "main"
    assert snapshot.duration_seconds == 900
    assert snapshot.state["current_task_id"] == 270
    assert snapshot.outcome["status"] == "success"


def test_generate_session_id_increments(temp_root):
    """Test that session IDs increment correctly."""
    history = SessionHistory(temp_root)

    s1 = history.create_snapshot(state={})
    s2 = history.create_snapshot(state={})
    s3 = history.create_snapshot(state={})

    assert s1.session_id == "s001"
    assert s2.session_id == "s002"
    assert s3.session_id == "s003"


def test_snapshot_persistence(temp_root):
    """Test that snapshots persist to disk correctly."""
    history = SessionHistory(temp_root)

    # Create snapshot
    s1 = history.create_snapshot(
        state={"current_task_id": 270, "notes": "Test"}
    )

    # Verify file was created
    session_file = temp_root / ".idlergear" / "sessions" / "main" / "s001.json"
    assert session_file.exists()

    # Verify content
    data = json.loads(session_file.read_text())
    assert data["session_id"] == "s001"
    assert data["state"]["current_task_id"] == 270

    # Reload and verify
    loaded = history.load_snapshot("s001")
    assert loaded.session_id == "s001"
    assert loaded.state["current_task_id"] == 270


def test_multiple_branches(temp_root):
    """Test creating snapshots in different branches."""
    history = SessionHistory(temp_root)

    # Create snapshot in main
    main_s1 = history.create_snapshot(state={"branch": "main"}, branch="main")
    assert main_s1.branch == "main"
    assert main_s1.session_id == "s001"

    # Create snapshot in experiment branch
    # Note: session IDs are independent per branch, so experiment also starts at s001
    exp_s1 = history.create_snapshot(state={"branch": "experiment"}, branch="experiment")
    assert exp_s1.branch == "experiment"
    # Session ID should be s001 for the new branch (independent counter)
    assert exp_s1.session_id == "s001"

    # Verify they're in separate directories
    main_file = temp_root / ".idlergear" / "sessions" / "main" / "s001.json"
    exp_file = temp_root / ".idlergear" / "sessions" / "experiment" / "s001.json"

    assert main_file.exists()
    assert exp_file.exists()


def test_load_nonexistent_snapshot(temp_root):
    """Test loading a snapshot that doesn't exist."""
    history = SessionHistory(temp_root)

    snapshot = history.load_snapshot("s999")
    assert snapshot is None
