"""Tests for status module - project status dashboard."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from idlergear.status import (
    ProjectStatus,
    format_detailed_status,
    get_daemon_status,
    get_git_status,
    get_last_release,
    get_project_status,
)


class TestProjectStatus:
    """Tests for ProjectStatus dataclass."""

    def test_project_status_creation(self):
        """Test creating a ProjectStatus instance."""
        status = ProjectStatus(
            tasks_open=5,
            tasks_high_priority=2,
            tasks_recent=[{"id": 1, "title": "Test"}],
            notes_total=10,
            notes_recent=[{"id": 1, "content": "Note"}],
            runs_active=1,
            runs_details=[{"name": "dev"}],
            git_uncommitted=3,
            git_files=[{"status": "M", "path": "file.py"}],
            git_branch="main",
            git_last_commit="abc123 Initial commit",
            project_name="test-project",
            last_release="v1.0.0",
        )
        assert status.tasks_open == 5
        assert status.tasks_high_priority == 2
        assert status.git_branch == "main"

    def test_project_status_to_dict(self):
        """Test converting ProjectStatus to dict."""
        status = ProjectStatus(
            tasks_open=5,
            tasks_high_priority=2,
            tasks_recent=[],
            notes_total=10,
            notes_recent=[],
            runs_active=1,
            runs_details=[],
            git_uncommitted=3,
            git_files=[],
            git_branch="main",
            git_last_commit="abc123",
            project_name="test",
            last_release="v1.0",
            daemon_running=True,
            daemon_pid=12345,
            agents_count=2,
            agents_list=[{"agent_id": "a1"}],
        )
        data = status.to_dict()

        assert data["tasks"]["open"] == 5
        assert data["tasks"]["high_priority"] == 2
        assert data["notes"]["total"] == 10
        assert data["runs"]["active"] == 1
        assert data["git"]["branch"] == "main"
        assert data["project"]["name"] == "test"
        assert data["daemon"]["running"] is True
        assert data["daemon"]["pid"] == 12345
        assert data["daemon"]["agents"] == 2

    def test_project_status_summary_with_tasks(self):
        """Test summary with open tasks."""
        status = ProjectStatus(
            tasks_open=5,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=0,
            notes_recent=[],
            runs_active=0,
            runs_details=[],
            git_uncommitted=0,
            git_files=[],
            git_branch="main",
            git_last_commit=None,
            project_name="test",
            last_release=None,
        )
        assert "5 open tasks" in status.summary()

    def test_project_status_summary_with_notes(self):
        """Test summary with notes."""
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=10,
            notes_recent=[],
            runs_active=0,
            runs_details=[],
            git_uncommitted=0,
            git_files=[],
            git_branch="main",
            git_last_commit=None,
            project_name="test",
            last_release=None,
        )
        assert "10 notes" in status.summary()

    def test_project_status_summary_with_runs(self):
        """Test summary with active runs."""
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=0,
            notes_recent=[],
            runs_active=2,
            runs_details=[],
            git_uncommitted=0,
            git_files=[],
            git_branch="main",
            git_last_commit=None,
            project_name="test",
            last_release=None,
        )
        assert "2 runs active" in status.summary()

    def test_project_status_summary_with_git(self):
        """Test summary with uncommitted files."""
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=0,
            notes_recent=[],
            runs_active=0,
            runs_details=[],
            git_uncommitted=5,
            git_files=[],
            git_branch="main",
            git_last_commit=None,
            project_name="test",
            last_release=None,
        )
        assert "5 uncommitted files" in status.summary()

    def test_project_status_summary_with_agents(self):
        """Test summary with agents."""
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=0,
            notes_recent=[],
            runs_active=0,
            runs_details=[],
            git_uncommitted=0,
            git_files=[],
            git_branch="main",
            git_last_commit=None,
            project_name="test",
            last_release=None,
            agents_count=3,
        )
        assert "3 agents" in status.summary()

    def test_project_status_summary_all_clear(self):
        """Test summary when everything is clear."""
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=0,
            notes_recent=[],
            runs_active=0,
            runs_details=[],
            git_uncommitted=0,
            git_files=[],
            git_branch="main",
            git_last_commit=None,
            project_name="test",
            last_release=None,
        )
        assert status.summary() == "All clear"


class TestGetGitStatus:
    """Tests for get_git_status function."""

    def test_get_git_status_not_a_repo(self):
        """Test when not in a git repo."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")
            files, branch, commit = get_git_status()
            assert files == []
            assert branch is None
            assert commit is None

    def test_get_git_status_git_not_found(self):
        """Test when git is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")
            files, branch, commit = get_git_status()
            assert files == []
            assert branch is None
            assert commit is None

    def test_get_git_status_clean(self):
        """Test clean git status."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # rev-parse --git-dir
                MagicMock(returncode=0, stdout="main\n"),  # branch
                MagicMock(returncode=0, stdout="abc123 Last commit\n"),  # log
                MagicMock(returncode=0, stdout=""),  # status --short
            ]
            files, branch, commit = get_git_status()
            assert files == []
            assert branch == "main"
            assert commit == "abc123 Last commit"

    def test_get_git_status_with_changes(self):
        """Test git status with uncommitted changes."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # rev-parse --git-dir
                MagicMock(returncode=0, stdout="feature\n"),  # branch
                MagicMock(returncode=0, stdout="def456 Feature work\n"),  # log
                MagicMock(returncode=0, stdout=" M file1.py\n?? new.txt\nA  added.py\n"),  # status
            ]
            files, branch, commit = get_git_status()
            assert len(files) == 3
            assert files[0] == {"status": " M", "path": "file1.py"}
            assert files[1] == {"status": "??", "path": "new.txt"}
            assert files[2] == {"status": "A ", "path": "added.py"}
            assert branch == "feature"

    def test_get_git_status_branch_failed(self):
        """Test when branch detection fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # rev-parse --git-dir
                MagicMock(returncode=1, stdout=""),  # branch failed
                MagicMock(returncode=0, stdout="abc123\n"),  # log
                MagicMock(returncode=0, stdout=""),  # status
            ]
            files, branch, commit = get_git_status()
            assert branch is None

    def test_get_git_status_status_failed(self):
        """Test when status command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # rev-parse --git-dir
                MagicMock(returncode=0, stdout="main\n"),  # branch
                MagicMock(returncode=0, stdout="abc123\n"),  # log
                MagicMock(returncode=1, stdout=""),  # status failed
            ]
            files, branch, commit = get_git_status()
            assert files == []


class TestGetLastRelease:
    """Tests for get_last_release function."""

    def test_get_last_release_success(self):
        """Test getting last release tag."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="v1.2.3\n")
            result = get_last_release()
            assert result == "v1.2.3"

    def test_get_last_release_no_tags(self):
        """Test when no tags exist."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=128, stdout="")
            result = get_last_release()
            assert result is None

    def test_get_last_release_error(self):
        """Test error during tag retrieval."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")
            result = get_last_release()
            assert result is None

    def test_get_last_release_git_not_found(self):
        """Test when git is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")
            result = get_last_release()
            assert result is None


class TestGetDaemonStatus:
    """Tests for get_daemon_status function."""

    def test_get_daemon_status_no_root(self):
        """Test when schema has no root."""
        schema = MagicMock()
        schema.root = None
        running, pid, agents = get_daemon_status(schema)
        assert running is False
        assert pid is None
        assert agents is None

    def test_get_daemon_status_no_idlergear_dir(self, tmp_path):
        """Test when .idlergear dir doesn't exist."""
        schema = MagicMock()
        schema.root = tmp_path
        running, pid, agents = get_daemon_status(schema)
        assert running is False
        assert pid is None
        assert agents is None

    def test_get_daemon_status_pid_file_missing(self, tmp_path):
        """Test when daemon.pid file is missing."""
        idlergear_dir = tmp_path / ".idlergear"
        idlergear_dir.mkdir()
        schema = MagicMock()
        schema.root = tmp_path
        running, pid, agents = get_daemon_status(schema)
        assert running is False
        assert pid is None

    def test_get_daemon_status_pid_invalid(self, tmp_path):
        """Test when daemon.pid contains invalid value."""
        idlergear_dir = tmp_path / ".idlergear"
        idlergear_dir.mkdir()
        pid_file = idlergear_dir / "daemon.pid"
        pid_file.write_text("not-a-number")
        schema = MagicMock()
        schema.root = tmp_path
        running, pid, agents = get_daemon_status(schema)
        assert running is False
        assert pid is None

    def test_get_daemon_status_process_not_running(self, tmp_path):
        """Test when daemon process is not running."""
        idlergear_dir = tmp_path / ".idlergear"
        idlergear_dir.mkdir()
        pid_file = idlergear_dir / "daemon.pid"
        pid_file.write_text("99999999")  # Very high PID unlikely to exist
        schema = MagicMock()
        schema.root = tmp_path
        running, pid, agents = get_daemon_status(schema)
        assert running is False

    def test_get_daemon_status_with_agents(self, tmp_path):
        """Test reading agent presence files."""
        idlergear_dir = tmp_path / ".idlergear"
        idlergear_dir.mkdir()
        agents_dir = idlergear_dir / "agents"
        agents_dir.mkdir()

        # Create agent presence files
        agent1 = agents_dir / "agent1.json"
        agent1.write_text('{"agent_id": "agent1", "agent_type": "claude-code"}')

        agent2 = agents_dir / "agent2.json"
        agent2.write_text('{"agent_id": "agent2", "agent_type": "goose"}')

        # Create the registry file that should be skipped
        registry = agents_dir / "agents.json"
        registry.write_text('{}')

        schema = MagicMock()
        schema.root = tmp_path
        running, pid, agents = get_daemon_status(schema)

        assert agents is not None
        assert len(agents) == 2
        agent_ids = {a["agent_id"] for a in agents}
        assert "agent1" in agent_ids
        assert "agent2" in agent_ids

    def test_get_daemon_status_invalid_agent_file(self, tmp_path):
        """Test handling invalid agent JSON."""
        idlergear_dir = tmp_path / ".idlergear"
        idlergear_dir.mkdir()
        agents_dir = idlergear_dir / "agents"
        agents_dir.mkdir()

        # Create invalid JSON file
        invalid = agents_dir / "invalid.json"
        invalid.write_text("not valid json")

        schema = MagicMock()
        schema.root = tmp_path
        running, pid, agents = get_daemon_status(schema)
        # Should not crash, just skip invalid file
        assert agents is None or agents == []


class TestFormatDetailedStatus:
    """Tests for format_detailed_status function."""

    def test_format_detailed_status_basic(self):
        """Test basic status formatting."""
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=0,
            notes_recent=[],
            runs_active=0,
            runs_details=[],
            git_uncommitted=0,
            git_files=[],
            git_branch="main",
            git_last_commit=None,
            project_name="test-project",
            last_release=None,
        )
        result = format_detailed_status(status)
        assert "=== Status: test-project ===" in result
        assert "Tasks: None open" in result
        assert "Notes: None" in result
        assert "Runs: None active" in result
        assert "Git: Working tree clean" in result
        assert "Branch: main" in result

    def test_format_detailed_status_with_tasks(self):
        """Test status with tasks."""
        status = ProjectStatus(
            tasks_open=2,
            tasks_high_priority=1,
            tasks_recent=[
                {"id": 1, "title": "Urgent task", "priority": "high"},
                {"id": 2, "title": "Normal task"},
            ],
            notes_total=0,
            notes_recent=[],
            runs_active=0,
            runs_details=[],
            git_uncommitted=0,
            git_files=[],
            git_branch="main",
            git_last_commit=None,
            project_name="test",
            last_release=None,
        )
        result = format_detailed_status(status)
        assert "Tasks (2 open)" in result
        assert "#1 [high] Urgent task" in result
        assert "#2" in result

    def test_format_detailed_status_with_notes(self):
        """Test status with notes."""
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=5,
            notes_recent=[
                {"content": "Short note", "tags": ["explore"]},
                {"content": "Very long note that should be truncated" + "x" * 100, "tags": []},
            ],
            runs_active=0,
            runs_details=[],
            git_uncommitted=0,
            git_files=[],
            git_branch="main",
            git_last_commit=None,
            project_name="test",
            last_release=None,
        )
        result = format_detailed_status(status)
        assert "Notes (5 total" in result
        assert "Short note" in result
        assert "[explore]" in result
        assert "..." in result  # Truncation

    def test_format_detailed_status_with_runs(self):
        """Test status with active runs."""
        started = (datetime.now() - timedelta(minutes=30)).isoformat()
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=0,
            notes_recent=[],
            runs_active=1,
            runs_details=[{"name": "dev-server", "started": started}],
            git_uncommitted=0,
            git_files=[],
            git_branch="main",
            git_last_commit=None,
            project_name="test",
            last_release=None,
        )
        result = format_detailed_status(status)
        assert "Runs (1 active)" in result
        assert "dev-server" in result
        assert "running" in result

    def test_format_detailed_status_with_daemon(self):
        """Test status with daemon running."""
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=0,
            notes_recent=[],
            runs_active=0,
            runs_details=[],
            git_uncommitted=0,
            git_files=[],
            git_branch="main",
            git_last_commit=None,
            project_name="test",
            last_release=None,
            daemon_running=True,
            daemon_pid=12345,
            agents_count=2,
            agents_list=[
                {"agent_id": "agent1", "agent_type": "claude-code"},
                {"agent_id": "agent2", "agent_type": "goose"},
            ],
        )
        result = format_detailed_status(status)
        assert "Daemon: Running (PID 12345, 2 agents)" in result
        assert "agent1" in result
        assert "claude-code" in result

    def test_format_detailed_status_daemon_not_running(self):
        """Test status without daemon."""
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=0,
            notes_recent=[],
            runs_active=0,
            runs_details=[],
            git_uncommitted=0,
            git_files=[],
            git_branch="main",
            git_last_commit=None,
            project_name="test",
            last_release=None,
            daemon_running=False,
        )
        result = format_detailed_status(status)
        assert "Daemon: Not running" in result

    def test_format_detailed_status_with_git_changes(self):
        """Test status with git changes."""
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=0,
            notes_recent=[],
            runs_active=0,
            runs_details=[],
            git_uncommitted=3,
            git_files=[
                {"status": " M", "path": "file1.py"},
                {"status": "??", "path": "new.txt"},
                {"status": "A ", "path": "added.py"},
            ],
            git_branch="feature",
            git_last_commit="abc123 Latest work",
            project_name="test",
            last_release="v1.0.0",
        )
        result = format_detailed_status(status)
        assert "Git (3 uncommitted)" in result
        assert " M file1.py" in result
        assert "?? new.txt" in result
        assert "Branch: feature" in result
        assert "Last commit: abc123 Latest work" in result
        assert "Last release: v1.0.0" in result

    def test_format_detailed_status_many_git_files(self):
        """Test status with many git files (truncated)."""
        files = [{"status": "M ", "path": f"file{i}.py"} for i in range(15)]
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=0,
            notes_recent=[],
            runs_active=0,
            runs_details=[],
            git_uncommitted=15,
            git_files=files,
            git_branch="main",
            git_last_commit=None,
            project_name="test",
            last_release=None,
        )
        result = format_detailed_status(status)
        assert "... and 5 more" in result

    def test_format_detailed_status_many_agents(self):
        """Test status with many agents (truncated)."""
        agents = [{"agent_id": f"agent{i}", "agent_type": "test"} for i in range(8)]
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=0,
            notes_recent=[],
            runs_active=0,
            runs_details=[],
            git_uncommitted=0,
            git_files=[],
            git_branch="main",
            git_last_commit=None,
            project_name="test",
            last_release=None,
            daemon_running=True,
            daemon_pid=123,
            agents_count=8,
            agents_list=agents,
        )
        result = format_detailed_status(status)
        assert "... and 3 more" in result

    def test_format_detailed_status_no_project_name(self):
        """Test status without project name."""
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=0,
            notes_recent=[],
            runs_active=0,
            runs_details=[],
            git_uncommitted=0,
            git_files=[],
            git_branch=None,
            git_last_commit=None,
            project_name=None,
            last_release=None,
        )
        result = format_detailed_status(status)
        assert "=== Status: Project ===" in result

    def test_format_detailed_status_run_invalid_timestamp(self):
        """Test status with invalid run timestamp."""
        status = ProjectStatus(
            tasks_open=0,
            tasks_high_priority=0,
            tasks_recent=[],
            notes_total=0,
            notes_recent=[],
            runs_active=1,
            runs_details=[{"name": "test-run", "started": "invalid-date"}],
            git_uncommitted=0,
            git_files=[],
            git_branch="main",
            git_last_commit=None,
            project_name="test",
            last_release=None,
        )
        # Should not crash
        result = format_detailed_status(status)
        assert "test-run" in result


class TestGetProjectStatus:
    """Tests for get_project_status function."""

    def test_get_project_status_basic(self, temp_project):
        """Test getting project status (requires fixture)."""
        # This test depends on the temp_project fixture setting up backends
        with patch("idlergear.status.get_backend") as mock_get_backend:
            # Mock task backend
            task_backend = MagicMock()
            task_backend.list.return_value = [
                {"id": 1, "title": "Test", "state": "open", "priority": "high", "created": "2025-01-01"},
            ]

            # Mock note backend
            note_backend = MagicMock()
            note_backend.list.return_value = []

            # Mock run backend
            run_backend = MagicMock()
            run_backend.list.return_value = []

            def get_backend_side_effect(type_):
                if type_ == "task":
                    return task_backend
                elif type_ == "note":
                    return note_backend
                elif type_ == "run":
                    return run_backend
                raise ValueError(f"Unknown backend: {type_}")

            mock_get_backend.side_effect = get_backend_side_effect

            with patch("idlergear.status.get_git_status") as mock_git:
                mock_git.return_value = ([], "main", "abc123")

                with patch("idlergear.status.get_last_release") as mock_release:
                    mock_release.return_value = "v1.0.0"

                    with patch("idlergear.status.get_daemon_status") as mock_daemon:
                        mock_daemon.return_value = (False, None, None)

                        status = get_project_status()

                        assert status.tasks_open == 1
                        assert status.tasks_high_priority == 1
                        assert status.git_branch == "main"
                        assert status.last_release == "v1.0.0"
