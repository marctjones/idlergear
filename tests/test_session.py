"""Tests for session state management."""

import json
from pathlib import Path

import pytest

from idlergear.session import SessionState, end_session, start_session


@pytest.fixture
def session_state(tmp_path):
    """Create a SessionState in a temporary directory."""
    # Create a mock .idlergear directory
    idlergear_dir = tmp_path / ".idlergear"
    idlergear_dir.mkdir()

    # Patch find_idlergear_root to return tmp_path
    import idlergear.session
    original_find = idlergear.session.find_idlergear_root
    idlergear.session.find_idlergear_root = lambda: tmp_path

    session = SessionState(root=tmp_path)

    yield session

    # Restore original
    idlergear.session.find_idlergear_root = original_find


def test_session_save_and_load(session_state):
    """Test saving and loading session state."""
    # Save state
    state = session_state.save(
        current_task_id=42,
        context_mode="standard",
        working_files=["file1.py", "file2.py"],
        notes="Working on authentication",
    )

    assert state["current_task_id"] == 42
    assert state["context_mode"] == "standard"
    assert state["working_files"] == ["file1.py", "file2.py"]
    assert state["notes"] == "Working on authentication"
    assert "timestamp" in state

    # Load state
    loaded = session_state.load()
    assert loaded == state


def test_session_load_nonexistent(session_state):
    """Test loading when no state exists."""
    result = session_state.load()
    assert result is None


def test_session_clear(session_state):
    """Test clearing session state."""
    # Save state
    session_state.save(current_task_id=42)

    # Clear
    result = session_state.clear()
    assert result is True

    # Verify cleared
    assert session_state.load() is None

    # Clear again (should return False)
    result = session_state.clear()
    assert result is False


def test_session_summary_no_state(session_state):
    """Test summary when no state exists."""
    summary = session_state.get_summary()
    assert "No session state saved" in summary


def test_session_summary_with_state(session_state):
    """Test summary with saved state."""
    session_state.save(
        current_task_id=42,
        context_mode="standard",
        working_files=["file1.py", "file2.py", "file3.py"],
        notes="Test notes",
    )

    summary = session_state.get_summary()
    assert "Session State" in summary
    assert "#42" in summary
    assert "standard" in summary
    assert "3 files" in summary
    assert "Test notes" in summary


def test_session_summary_truncates_long_file_list(session_state):
    """Test that long file lists are truncated in summary."""
    files = [f"file{i}.py" for i in range(10)]
    session_state.save(working_files=files)

    summary = session_state.get_summary()
    assert "... and 5 more" in summary


def test_start_session_without_state(tmp_path):
    """Test starting session with no previous state."""
    # Create mock .idlergear
    idlergear_dir = tmp_path / ".idlergear"
    idlergear_dir.mkdir()

    # Patch
    import idlergear.session
    original_find = idlergear.session.find_idlergear_root
    idlergear.session.find_idlergear_root = lambda: tmp_path

    try:
        result = start_session(load_state=True)

        assert "context" in result
        assert result["session_state"] is None
        assert len(result["recommendations"]) > 0
        assert "No previous session" in result["recommendations"][0]
    finally:
        idlergear.session.find_idlergear_root = original_find


def test_start_session_with_state(session_state):
    """Test starting session with previous state."""
    # Save state first
    session_state.save(
        current_task_id=42,
        working_files=["file1.py"],
        notes="Previous work",
    )

    # Patch for start_session
    import idlergear.session
    original_find = idlergear.session.find_idlergear_root
    idlergear.session.find_idlergear_root = lambda: session_state.root

    try:
        result = start_session(load_state=True)

        assert "context" in result
        assert result["session_state"] is not None
        assert result["session_state"]["current_task_id"] == 42
        assert len(result["recommendations"]) > 0
        assert "task #42" in result["recommendations"][0]
    finally:
        idlergear.session.find_idlergear_root = original_find


def test_end_session(session_state):
    """Test ending session with save."""
    # Patch
    import idlergear.session
    original_find = idlergear.session.find_idlergear_root
    idlergear.session.find_idlergear_root = lambda: session_state.root

    try:
        result = end_session(
            current_task_id=42,
            working_files=["file1.py", "file2.py"],
            notes="Completed feature X",
        )

        assert "state" in result
        assert result["state"]["current_task_id"] == 42
        assert len(result["suggestions"]) > 0
        assert "task #42" in result["suggestions"][0]

        # Verify state was saved
        loaded = session_state.load()
        assert loaded["current_task_id"] == 42
    finally:
        idlergear.session.find_idlergear_root = original_find


def test_session_state_file_location(tmp_path):
    """Test that session state is stored in .idlergear directory."""
    idlergear_dir = tmp_path / ".idlergear"
    idlergear_dir.mkdir()

    session = SessionState(root=tmp_path)
    session.save(current_task_id=42)

    expected_file = idlergear_dir / "session_state.json"
    assert expected_file.exists()

    # Verify content
    data = json.loads(expected_file.read_text())
    assert data["current_task_id"] == 42
