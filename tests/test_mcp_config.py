"""Tests for MCP configuration management."""

import json
from unittest.mock import patch

from idlergear.mcp_config import (
    McpConfig,
    McpServerConfig,
    add_server_to_config,
    generate_project_mcp_config,
    get_claude_code_config_path,
    get_idlergear_mcp_config,
    load_project_mcp_config,
    remove_server_from_config,
    validate_mcp_config,
)


class TestMcpServerConfig:
    """Tests for McpServerConfig."""

    def test_basic_config(self):
        """Basic server config has required fields."""
        config = McpServerConfig(name="test", command="test-cmd")
        assert config.name == "test"
        assert config.command == "test-cmd"
        assert config.args == []
        assert config.env == {}
        assert config.type == "stdio"

    def test_to_dict_minimal(self):
        """to_dict with minimal config."""
        config = McpServerConfig(name="test", command="test-cmd")
        result = config.to_dict()
        assert result == {"command": "test-cmd", "type": "stdio"}

    def test_to_dict_with_args(self):
        """to_dict includes args when present."""
        config = McpServerConfig(
            name="test", command="test-cmd", args=["--flag", "value"]
        )
        result = config.to_dict()
        assert result["args"] == ["--flag", "value"]

    def test_to_dict_with_env(self):
        """to_dict includes env when present."""
        config = McpServerConfig(name="test", command="test-cmd", env={"FOO": "bar"})
        result = config.to_dict()
        assert result["env"] == {"FOO": "bar"}


class TestMcpConfig:
    """Tests for McpConfig."""

    def test_empty_config(self):
        """Empty config has no servers."""
        config = McpConfig()
        assert config.servers == {}

    def test_to_dict(self):
        """to_dict produces valid JSON structure."""
        config = McpConfig(
            servers={
                "test": McpServerConfig(name="test", command="test-cmd"),
            }
        )
        result = config.to_dict()
        assert "mcpServers" in result
        assert "test" in result["mcpServers"]

    def test_from_dict(self):
        """from_dict parses JSON structure."""
        data = {
            "mcpServers": {
                "server1": {"command": "cmd1", "args": ["--flag"]},
                "server2": {"command": "cmd2", "type": "sse"},
            }
        }
        config = McpConfig.from_dict(data)
        assert len(config.servers) == 2
        assert config.servers["server1"].command == "cmd1"
        assert config.servers["server1"].args == ["--flag"]
        assert config.servers["server2"].type == "sse"

    def test_from_file_not_exists(self, tmp_path):
        """from_file returns None for missing file."""
        result = McpConfig.from_file(tmp_path / "missing.json")
        assert result is None

    def test_from_file_invalid_json(self, tmp_path):
        """from_file returns None for invalid JSON."""
        path = tmp_path / "invalid.json"
        path.write_text("not json")
        result = McpConfig.from_file(path)
        assert result is None

    def test_from_file_valid(self, tmp_path):
        """from_file loads valid JSON."""
        path = tmp_path / "config.json"
        path.write_text('{"mcpServers": {"test": {"command": "cmd"}}}')
        result = McpConfig.from_file(path)
        assert result is not None
        assert "test" in result.servers

    def test_save(self, tmp_path):
        """save writes valid JSON."""
        config = McpConfig(
            servers={"test": McpServerConfig(name="test", command="cmd")}
        )
        path = tmp_path / "out.json"
        config.save(path)

        assert path.exists()
        data = json.loads(path.read_text())
        assert "mcpServers" in data

    def test_save_creates_parent_dirs(self, tmp_path):
        """save creates parent directories."""
        config = McpConfig()
        path = tmp_path / "subdir" / "config.json"
        config.save(path)
        assert path.exists()


class TestIdlergearMcpConfig:
    """Tests for IdlerGear-specific MCP config."""

    def test_get_idlergear_mcp_config(self):
        """Get standard IdlerGear config."""
        config = get_idlergear_mcp_config()
        assert config.name == "idlergear"
        assert config.command == "idlergear-mcp"
        assert config.type == "stdio"


class TestClaudeCodeConfigPath:
    """Tests for Claude Code config path detection."""

    @patch("platform.system")
    def test_macos_path(self, mock_system):
        """macOS uses Library/Application Support."""
        mock_system.return_value = "Darwin"
        path = get_claude_code_config_path()
        assert "Library/Application Support/Claude" in str(path)
        assert path.name == "claude_desktop_config.json"

    @patch("platform.system")
    def test_linux_path(self, mock_system):
        """Linux uses .config."""
        mock_system.return_value = "Linux"
        path = get_claude_code_config_path()
        assert ".config/Claude" in str(path)

    @patch("platform.system")
    @patch.dict("os.environ", {"APPDATA": "/fake/appdata"})
    def test_windows_path(self, mock_system):
        """Windows uses APPDATA."""
        mock_system.return_value = "Windows"
        path = get_claude_code_config_path()
        assert "appdata" in str(path).lower()


class TestValidation:
    """Tests for MCP config validation."""

    def test_valid_config(self, tmp_path):
        """Valid config passes validation."""
        # Create a fake executable
        exe = tmp_path / "test-cmd"
        exe.touch()
        exe.chmod(0o755)

        config = McpConfig(
            servers={"test": McpServerConfig(name="test", command=str(exe))}
        )

        with patch("shutil.which", return_value=str(exe)):
            result = validate_mcp_config(config)

        assert result.valid
        assert len(result.issues) == 0

    def test_empty_command(self):
        """Empty command is an error."""
        config = McpConfig(servers={"test": McpServerConfig(name="test", command="")})
        result = validate_mcp_config(config)
        assert not result.valid
        assert any("no command" in issue for issue in result.issues)

    def test_invalid_type(self):
        """Invalid type is an error."""
        config = McpConfig(
            servers={
                "test": McpServerConfig(name="test", command="cmd", type="invalid")
            }
        )
        result = validate_mcp_config(config)
        assert not result.valid
        assert any("invalid type" in issue for issue in result.issues)

    def test_missing_command_warning(self):
        """Missing command in PATH is a warning."""
        config = McpConfig(
            servers={"test": McpServerConfig(name="test", command="nonexistent-cmd")}
        )
        with patch("shutil.which", return_value=None):
            result = validate_mcp_config(config)

        assert result.valid  # Still valid, just a warning
        assert any("not found in PATH" in w for w in result.warnings)


class TestGenerateConfig:
    """Tests for config generation."""

    def test_generate_with_idlergear(self):
        """Generate includes IdlerGear by default."""
        config = generate_project_mcp_config(include_idlergear=True)
        assert "idlergear" in config.servers
        assert config.servers["idlergear"].command == "idlergear-mcp"

    def test_generate_without_idlergear(self):
        """Generate can exclude IdlerGear."""
        config = generate_project_mcp_config(include_idlergear=False)
        assert "idlergear" not in config.servers


class TestAddServer:
    """Tests for adding servers to config."""

    def test_add_to_new_file(self, tmp_path):
        """Add server to new config file."""
        path = tmp_path / ".mcp.json"
        server = McpServerConfig(name="new", command="new-cmd")

        success, message = add_server_to_config(path, server)

        assert success
        assert path.exists()
        config = McpConfig.from_file(path)
        assert "new" in config.servers

    def test_add_to_existing(self, tmp_path):
        """Add server to existing config."""
        path = tmp_path / ".mcp.json"
        path.write_text('{"mcpServers": {"existing": {"command": "old-cmd"}}}')

        server = McpServerConfig(name="new", command="new-cmd")
        success, message = add_server_to_config(path, server)

        assert success
        config = McpConfig.from_file(path)
        assert "existing" in config.servers
        assert "new" in config.servers

    def test_add_duplicate_fails(self, tmp_path):
        """Adding duplicate server fails without overwrite."""
        path = tmp_path / ".mcp.json"
        path.write_text('{"mcpServers": {"test": {"command": "old-cmd"}}}')

        server = McpServerConfig(name="test", command="new-cmd")
        success, message = add_server_to_config(path, server, overwrite=False)

        assert not success
        assert "already exists" in message

    def test_add_duplicate_with_overwrite(self, tmp_path):
        """Adding duplicate server succeeds with overwrite."""
        path = tmp_path / ".mcp.json"
        path.write_text('{"mcpServers": {"test": {"command": "old-cmd"}}}')

        server = McpServerConfig(name="test", command="new-cmd")
        success, message = add_server_to_config(path, server, overwrite=True)

        assert success
        config = McpConfig.from_file(path)
        assert config.servers["test"].command == "new-cmd"


class TestRemoveServer:
    """Tests for removing servers from config."""

    def test_remove_existing(self, tmp_path):
        """Remove existing server."""
        path = tmp_path / ".mcp.json"
        path.write_text('{"mcpServers": {"test": {"command": "cmd"}}}')

        success, message = remove_server_from_config(path, "test")

        assert success
        config = McpConfig.from_file(path)
        assert "test" not in config.servers

    def test_remove_nonexistent(self, tmp_path):
        """Remove nonexistent server fails."""
        path = tmp_path / ".mcp.json"
        path.write_text('{"mcpServers": {}}')

        success, message = remove_server_from_config(path, "test")

        assert not success
        assert "not found" in message

    def test_remove_from_missing_file(self, tmp_path):
        """Remove from missing file fails."""
        path = tmp_path / "missing.json"

        success, message = remove_server_from_config(path, "test")

        assert not success
        assert "not found" in message


class TestLoadProjectConfig:
    """Tests for loading project MCP config."""

    def test_load_from_project(self, tmp_path):
        """Load config from project directory."""
        mcp_file = tmp_path / ".mcp.json"
        mcp_file.write_text('{"mcpServers": {"test": {"command": "cmd"}}}')

        config = load_project_mcp_config(tmp_path)
        assert config is not None
        assert "test" in config.servers

    def test_load_missing(self, tmp_path):
        """Load returns None for missing config."""
        config = load_project_mcp_config(tmp_path)
        assert config is None
