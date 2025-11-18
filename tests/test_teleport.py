"""
Tests for TeleportTracker and teleport session management.
"""
import json
from pathlib import Path
from unittest.mock import patch
from src.teleport import TeleportTracker


def test_initialization_creates_directories(tmp_path):
    """Test that initialization creates the teleport-sessions directory."""
    tracker = TeleportTracker(tmp_path)

    teleport_dir = tmp_path / ".idlergear" / "teleport-sessions"
    assert teleport_dir.exists()

    metadata_file = teleport_dir / "metadata.json"
    assert metadata_file.exists()

    metadata = json.loads(metadata_file.read_text())
    assert metadata == {"sessions": []}


def test_log_session_creates_record(tmp_path):
    """Test logging a new teleport session."""
    tracker = TeleportTracker(tmp_path)

    result = tracker.log_session(
        session_id="abc-123-def-456",
        description="Test session",
        files_changed=["src/main.py", "tests/test_main.py"],
        branch="feature/test"
    )

    assert result["status"] == "created"
    assert result["session"]["session_id"] == "abc-123-def-456"
    assert result["session"]["description"] == "Test session"
    assert result["session"]["branch"] == "feature/test"
    assert result["session"]["files_count"] == 2
    assert "timestamp" in result["session"]

    # Check individual session file was created
    session_file = tmp_path / ".idlergear" / "teleport-sessions" / "abc-123-def-456.json"
    assert session_file.exists()

    session = json.loads(session_file.read_text())
    assert session["session_id"] == "abc-123-def-456"


def test_log_session_updates_existing(tmp_path):
    """Test that logging the same session ID updates the existing record."""
    tracker = TeleportTracker(tmp_path)

    # First log
    tracker.log_session(
        session_id="abc-123",
        description="First description",
        files_changed=["file1.py"],
        branch="main"
    )

    # Update with same session_id
    result = tracker.log_session(
        session_id="abc-123",
        description="Updated description",
        files_changed=["file1.py", "file2.py"],
        branch="main"
    )

    assert result["status"] == "updated"
    assert result["session"]["description"] == "Updated description"
    assert result["session"]["files_count"] == 2

    # Should still only have one session in metadata
    sessions = tracker.list_sessions()
    assert len(sessions) == 1


def test_log_session_auto_detects_branch(tmp_path):
    """Test that branch is auto-detected if not provided."""
    tracker = TeleportTracker(tmp_path)

    # Mock git command
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "feature/auto-detected\n"
        mock_run.return_value.returncode = 0

        result = tracker.log_session(
            session_id="xyz-789",
            description="Auto branch test",
            files_changed=[]
        )

        assert result["session"]["branch"] == "feature/auto-detected"


def test_list_sessions_returns_sorted(tmp_path):
    """Test listing sessions returns them in reverse chronological order."""
    tracker = TeleportTracker(tmp_path)

    # Log multiple sessions
    tracker.log_session(session_id="first", description="First", files_changed=[], branch="main")
    tracker.log_session(session_id="second", description="Second", files_changed=[], branch="main")
    tracker.log_session(session_id="third", description="Third", files_changed=[], branch="main")

    sessions = tracker.list_sessions()

    # Most recent first
    assert len(sessions) == 3
    assert sessions[0]["session_id"] == "third"
    assert sessions[1]["session_id"] == "second"
    assert sessions[2]["session_id"] == "first"


def test_list_sessions_with_limit(tmp_path):
    """Test listing sessions with a limit."""
    tracker = TeleportTracker(tmp_path)

    for i in range(5):
        tracker.log_session(
            session_id=f"session-{i}",
            description=f"Session {i}",
            files_changed=[],
            branch="main"
        )

    sessions = tracker.list_sessions(limit=3)
    assert len(sessions) == 3


def test_list_sessions_filter_by_branch(tmp_path):
    """Test filtering sessions by branch."""
    tracker = TeleportTracker(tmp_path)

    tracker.log_session(session_id="main-1", description="Main 1", files_changed=[], branch="main")
    tracker.log_session(session_id="feature-1", description="Feature 1", files_changed=[], branch="feature/x")
    tracker.log_session(session_id="main-2", description="Main 2", files_changed=[], branch="main")

    main_sessions = tracker.list_sessions(branch="main")
    assert len(main_sessions) == 2
    assert all(s["branch"] == "main" for s in main_sessions)

    feature_sessions = tracker.list_sessions(branch="feature/x")
    assert len(feature_sessions) == 1
    assert feature_sessions[0]["session_id"] == "feature-1"


def test_get_session_exact_match(tmp_path):
    """Test getting a session by exact ID."""
    tracker = TeleportTracker(tmp_path)

    tracker.log_session(session_id="abc-123-def", description="Test", files_changed=[], branch="main")

    session = tracker.get_session("abc-123-def")
    assert session is not None
    assert session["session_id"] == "abc-123-def"


def test_get_session_partial_match(tmp_path):
    """Test getting a session by partial ID."""
    tracker = TeleportTracker(tmp_path)

    tracker.log_session(session_id="abc-123-def-456", description="Test", files_changed=[], branch="main")

    session = tracker.get_session("abc-123")
    assert session is not None
    assert session["session_id"] == "abc-123-def-456"


def test_get_session_not_found(tmp_path):
    """Test getting a non-existent session returns None."""
    tracker = TeleportTracker(tmp_path)

    session = tracker.get_session("non-existent")
    assert session is None


def test_get_session_ambiguous_raises(tmp_path):
    """Test that ambiguous partial match raises ValueError."""
    tracker = TeleportTracker(tmp_path)

    tracker.log_session(session_id="abc-111", description="First", files_changed=[], branch="main")
    tracker.log_session(session_id="abc-222", description="Second", files_changed=[], branch="main")

    try:
        tracker.get_session("abc")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Ambiguous" in str(e)


def test_export_session_json(tmp_path):
    """Test exporting a session as JSON."""
    tracker = TeleportTracker(tmp_path)

    tracker.log_session(
        session_id="export-test",
        description="Export test",
        files_changed=["file.py"],
        branch="main"
    )

    result = tracker.export_session("export-test", "json")

    assert result["format"] == "json"
    exported = json.loads(result["content"])
    assert exported["session_id"] == "export-test"
    assert exported["description"] == "Export test"


def test_export_session_markdown(tmp_path):
    """Test exporting a session as markdown."""
    tracker = TeleportTracker(tmp_path)

    tracker.log_session(
        session_id="markdown-test",
        description="Markdown test",
        files_changed=["src/app.py", "tests/test_app.py"],
        branch="feature/export"
    )

    result = tracker.export_session("markdown-test", "markdown")

    assert result["format"] == "markdown"
    content = result["content"]

    assert "# Teleport Session:" in content
    assert "markdown-test" in content
    assert "Markdown test" in content
    assert "`src/app.py`" in content
    assert "`tests/test_app.py`" in content


def test_export_session_not_found_raises(tmp_path):
    """Test that exporting non-existent session raises ValueError."""
    tracker = TeleportTracker(tmp_path)

    try:
        tracker.export_session("non-existent", "json")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "not found" in str(e)


def test_format_session_list(tmp_path):
    """Test formatting a list of sessions for display."""
    tracker = TeleportTracker(tmp_path)

    tracker.log_session(session_id="session-1-abc", description="First", files_changed=["a.py"], branch="main")
    tracker.log_session(session_id="session-2-def", description="Second", files_changed=["b.py", "c.py"], branch="main")

    sessions = tracker.list_sessions()
    output = tracker.format_session_list(sessions)

    assert "Found 2 teleport session(s)" in output
    # Session IDs are truncated to 8 characters in display
    assert "session-" in output
    assert "First" in output
    assert "Second" in output


def test_format_session_list_empty(tmp_path):
    """Test formatting an empty session list."""
    tracker = TeleportTracker(tmp_path)

    output = tracker.format_session_list([])
    assert "No teleport sessions found" in output


def test_format_session_detail(tmp_path):
    """Test formatting a single session for detailed display."""
    tracker = TeleportTracker(tmp_path)

    tracker.log_session(
        session_id="detail-test",
        description="Detailed view",
        files_changed=["src/main.py", "README.md"],
        branch="feature/detail"
    )

    session = tracker.get_session("detail-test")
    output = tracker.format_session(session)

    assert "detail-test" in output
    assert "Detailed view" in output
    assert "feature/detail" in output
    assert "src/main.py" in output
    assert "README.md" in output
    assert "2 file(s)" in output


def test_metadata_persistence(tmp_path):
    """Test that metadata persists across tracker instances."""
    # First tracker instance
    tracker1 = TeleportTracker(tmp_path)
    tracker1.log_session(session_id="persist-test", description="Test", files_changed=[], branch="main")

    # Second tracker instance
    tracker2 = TeleportTracker(tmp_path)
    sessions = tracker2.list_sessions()

    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "persist-test"


def test_log_session_with_empty_files(tmp_path):
    """Test logging a session with no files changed."""
    tracker = TeleportTracker(tmp_path)

    result = tracker.log_session(
        session_id="empty-files",
        description="No files",
        files_changed=[],
        branch="main"
    )

    assert result["session"]["files_count"] == 0
    assert result["session"]["files_changed"] == []


def test_default_description(tmp_path):
    """Test that default description is generated when not provided."""
    tracker = TeleportTracker(tmp_path)

    result = tracker.log_session(
        session_id="default-desc-test",
        files_changed=[],
        branch="main"
    )

    # Default description uses first 8 chars of session ID
    assert "default-" in result["session"]["description"]
    assert "Teleport session" in result["session"]["description"]
