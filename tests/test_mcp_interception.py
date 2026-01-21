"""Tests for MCP file registry interception."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project with IdlerGear initialized."""
    (tmp_path / ".idlergear").mkdir()
    (tmp_path / ".idlergear" / "config.toml").write_text("")
    # FileRegistry expects {files: {}, patterns: {}} format
    (tmp_path / ".idlergear" / "file_registry.json").write_text(
        json.dumps({"files": {}, "patterns": {}})
    )
    return tmp_path


@pytest.fixture
def test_file(tmp_path):
    """Create a test file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    return test_file


@pytest.fixture
def deprecated_file(tmp_path):
    """Create and register a deprecated file."""
    from idlergear.file_registry import FileRegistry

    old_file = tmp_path / "old_data.csv"
    old_file.write_text("old,data\n1,2")

    new_file = tmp_path / "new_data.csv"
    new_file.write_text("new,data\n3,4")

    # Initialize registry and deprecate the old file
    registry_path = tmp_path / ".idlergear" / "file_registry.json"
    registry = FileRegistry(registry_path=registry_path)
    registry.deprecate_file(
        str(old_file),
        successor=str(new_file),
        reason="Outdated schema"
    )

    return old_file, new_file


@pytest.fixture
def archived_file(tmp_path):
    """Create and register an archived file."""
    from idlergear.file_registry import FileRegistry, FileStatus

    archived = tmp_path / "archived_2023.json"
    archived.write_text("{}")

    registry_path = tmp_path / ".idlergear" / "file_registry.json"
    registry = FileRegistry(registry_path=registry_path)
    registry.register_file(
        str(archived),
        status=FileStatus.ARCHIVED,
        reason="Historical data only"
    )

    return archived


@pytest.fixture
def problematic_file(tmp_path):
    """Create and register a problematic file."""
    from idlergear.file_registry import FileRegistry, FileStatus

    problematic = tmp_path / "buggy_script.py"
    problematic.write_text("# Known memory leak")

    registry_path = tmp_path / ".idlergear" / "file_registry.json"
    registry = FileRegistry(registry_path=registry_path)
    registry.register_file(
        str(problematic),
        status=FileStatus.PROBLEMATIC,
        reason="Memory leak in line 42"
    )

    return problematic


class TestCheckFileAccess:
    """Test _check_file_access function."""

    def test_allows_unregistered_files(self, temp_project, test_file):
        """Files not in registry are allowed."""
        from idlergear.mcp_server import _check_file_access

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            allowed, warning = _check_file_access(str(test_file), "read")

            assert allowed is True
            assert warning is None

    def test_blocks_deprecated_file_read(self, temp_project, deprecated_file):
        """Reading deprecated files is blocked."""
        from idlergear.mcp_server import _check_file_access

        old_file, new_file = deprecated_file

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            allowed, warning = _check_file_access(str(old_file), "read")

            assert allowed is False
            assert "deprecated" in warning.lower()
            assert str(new_file) in warning

    def test_warns_but_allows_deprecated_file_write(self, temp_project, deprecated_file):
        """Writing to deprecated files is allowed with warning."""
        from idlergear.mcp_server import _check_file_access

        old_file, _ = deprecated_file

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            allowed, warning = _check_file_access(str(old_file), "write")

            assert allowed is True
            assert "deprecated" in warning.lower()
            assert "write operation allowed" in warning.lower()

    def test_blocks_archived_file(self, temp_project, archived_file):
        """Archived files are blocked."""
        from idlergear.mcp_server import _check_file_access

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            allowed, warning = _check_file_access(str(archived_file), "read")

            assert allowed is False
            assert "archived" in warning.lower()
            assert "historical" in warning.lower()

    def test_blocks_problematic_file(self, temp_project, problematic_file):
        """Problematic files are blocked."""
        from idlergear.mcp_server import _check_file_access

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            allowed, warning = _check_file_access(str(problematic_file), "read")

            assert allowed is False
            assert "known issues" in warning.lower()
            assert "memory leak" in warning.lower()

    def test_override_allows_deprecated_access(self, temp_project, deprecated_file):
        """Override flag allows deprecated file access."""
        from idlergear.mcp_server import _check_file_access

        old_file, _ = deprecated_file

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            allowed, warning = _check_file_access(
                str(old_file), "read", allow_override=True
            )

            assert allowed is True
            assert warning is None

    def test_skips_urls(self, temp_project):
        """URLs are not checked (false positive avoidance)."""
        from idlergear.mcp_server import _check_file_access

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            # HTTP URL
            allowed, warning = _check_file_access("https://example.com/data.csv", "read")
            assert allowed is True

            # Git URL
            allowed, warning = _check_file_access("git@github.com:user/repo.git", "read")
            assert allowed is True

    def test_skips_command_flags(self, temp_project):
        """Command flags are not checked (false positive avoidance)."""
        from idlergear.mcp_server import _check_file_access

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            allowed, warning = _check_file_access("-rf /tmp", "read")
            assert allowed is True

            allowed, warning = _check_file_access("command -v python", "read")
            assert allowed is True


class TestFileAccessLogging:
    """Test _log_file_access function."""

    def test_logs_blocked_access(self, temp_project, deprecated_file):
        """Blocked file access is logged."""
        from idlergear.mcp_server import _log_file_access

        old_file, _ = deprecated_file
        log_file = temp_project / ".idlergear" / "access_log.jsonl"

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            _log_file_access("Read", str(old_file), "deprecated", False, "test-agent")

        assert log_file.exists()
        log_entries = [json.loads(line) for line in log_file.read_text().strip().split("\n")]

        assert len(log_entries) == 1
        entry = log_entries[0]
        assert entry["tool"] == "Read"
        assert str(old_file) in entry["file_path"]
        assert entry["status"] == "deprecated"
        assert entry["allowed"] is False
        assert entry["agent_id"] == "test-agent"
        assert "timestamp" in entry

    def test_logs_allowed_access(self, temp_project, test_file):
        """Allowed file access is logged."""
        from idlergear.mcp_server import _log_file_access

        log_file = temp_project / ".idlergear" / "access_log.jsonl"

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            _log_file_access("Read", str(test_file), "current", True)

        assert log_file.exists()
        log_entries = [json.loads(line) for line in log_file.read_text().strip().split("\n")]

        assert len(log_entries) == 1
        entry = log_entries[0]
        assert entry["allowed"] is True
        assert entry["status"] == "current"


class TestMCPToolInterception:
    """Test actual MCP tool interception."""

    @pytest.mark.asyncio
    async def test_read_file_blocks_deprecated(self, temp_project, deprecated_file):
        """idlergear_fs_read_file blocks deprecated files."""
        from idlergear.mcp_server import call_tool

        old_file, new_file = deprecated_file

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            result = await call_tool("idlergear_fs_read_file", {"path": str(old_file)})

            # Should return error message, not raise exception (MCP convention)
            assert len(result) == 1
            assert result[0].type == "text"
            assert "deprecated" in result[0].text.lower()
            assert str(new_file) in result[0].text

    @pytest.mark.asyncio
    async def test_read_file_allows_unregistered(self, temp_project, test_file):
        """idlergear_fs_read_file allows unregistered files."""
        from idlergear.mcp_server import call_tool

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            # Should not raise
            result = await call_tool("idlergear_fs_read_file", {"path": str(test_file)})
            assert result is not None

    @pytest.mark.asyncio
    async def test_read_file_override_allows_deprecated(self, temp_project, deprecated_file):
        """idlergear_fs_read_file with override allows deprecated files."""
        from idlergear.mcp_server import call_tool

        old_file, _ = deprecated_file

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            # Should not raise with override
            result = await call_tool(
                "idlergear_fs_read_file",
                {"path": str(old_file), "_allow_deprecated": True}
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_write_file_warns_on_deprecated(self, temp_project, deprecated_file):
        """idlergear_fs_write_file warns but allows deprecated files."""
        from idlergear.mcp_server import call_tool

        old_file, _ = deprecated_file

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            # Should not raise, but may include warning
            result = await call_tool(
                "idlergear_fs_write_file",
                {"path": str(old_file), "content": "updated content"}
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_read_multiple_blocks_any_deprecated(self, temp_project, deprecated_file, test_file):
        """idlergear_fs_read_multiple blocks if any file is deprecated."""
        from idlergear.mcp_server import call_tool

        old_file, _ = deprecated_file

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            result = await call_tool(
                "idlergear_fs_read_multiple",
                {"paths": [str(test_file), str(old_file)]}
            )

            # Should return error message
            assert len(result) == 1
            assert result[0].type == "text"
            assert "blocked" in result[0].text.lower() or "deprecated" in result[0].text.lower()
            assert str(old_file) in result[0].text

    @pytest.mark.asyncio
    async def test_move_file_blocks_deprecated(self, temp_project, deprecated_file):
        """idlergear_fs_move_file blocks moving deprecated files."""
        from idlergear.mcp_server import call_tool

        old_file, _ = deprecated_file
        dest = temp_project / "moved.csv"

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            result = await call_tool(
                "idlergear_fs_move_file",
                {"source": str(old_file), "destination": str(dest)}
            )

            # Should return error message
            assert len(result) == 1
            assert result[0].type == "text"
            assert "deprecated" in result[0].text.lower()
            assert str(old_file) in result[0].text


class TestAccessLog:
    """Test access log functionality."""

    def test_access_log_created(self, temp_project, deprecated_file):
        """Access log file is created on first use."""
        from idlergear.mcp_server import _check_file_access

        old_file, _ = deprecated_file
        log_file = temp_project / ".idlergear" / "access_log.jsonl"

        assert not log_file.exists()

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            _check_file_access(str(old_file), "read")

        assert log_file.exists()

    def test_access_log_multiple_entries(self, temp_project, deprecated_file, archived_file):
        """Multiple access attempts are logged."""
        from idlergear.mcp_server import _check_file_access

        old_file, _ = deprecated_file
        log_file = temp_project / ".idlergear" / "access_log.jsonl"

        with patch("idlergear.mcp_server.find_idlergear_root", return_value=temp_project):
            _check_file_access(str(old_file), "read")
            _check_file_access(str(archived_file), "read")

        log_entries = [json.loads(line) for line in log_file.read_text().strip().split("\n")]
        assert len(log_entries) == 2
