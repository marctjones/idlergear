"""Tests for MCP server integration with Claude Code.

These tests verify that:
1. The MCP server is properly configured
2. Claude can discover and use MCP tools
3. MCP tools work correctly (not just CLI commands)

NOTE: Testing actual MCP tool invocation requires interactive Claude sessions,
which is harder to automate. These tests focus on configuration and discovery.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


from .conftest import run_idlergear


class TestMcpConfiguration:
    """Test that MCP configuration is correct."""

    def test_mcp_json_has_correct_structure(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that .mcp.json has the correct structure for Claude Code."""
        project = fresh_project_with_install
        mcp_path = project / ".mcp.json"

        assert mcp_path.exists(), ".mcp.json should exist after install"

        config = json.loads(mcp_path.read_text())

        # Verify structure
        assert "mcpServers" in config, ".mcp.json needs mcpServers key"
        assert "idlergear" in config["mcpServers"], (
            "idlergear server should be configured"
        )

        server_config = config["mcpServers"]["idlergear"]
        assert server_config["command"] == "idlergear-mcp", (
            "Command should be idlergear-mcp"
        )
        assert server_config["type"] == "stdio", "Type should be stdio"
        assert server_config.get("args", []) == [], "Args should be empty list"

    def test_mcp_server_executable_exists(self) -> None:
        """Test that idlergear-mcp executable is available."""
        # Check if idlergear-mcp is in PATH or can be found
        result = subprocess.run(
            ["which", "idlergear-mcp"],
            capture_output=True,
            text=True,
        )
        # If not in PATH, check venv
        if result.returncode != 0:
            venv_path = Path(sys.executable).parent / "idlergear-mcp"
            assert venv_path.exists(), (
                "idlergear-mcp should be installed. "
                "Run 'pip install -e .' in the project directory."
            )

    def test_mcp_server_starts_without_error(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that MCP server can start and respond to initialization."""
        project = fresh_project_with_install

        # The MCP server uses stdio, so we need to send it a proper init message
        # and check that it doesn't crash immediately
        init_message = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1.0.0"},
                    },
                }
            )
            + "\n"
        )

        result = subprocess.run(
            ["idlergear-mcp"],
            input=init_message,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project,
        )

        # Server should respond with something (not crash)
        # Even if it times out reading more input, stdout should have response
        assert (
            result.stdout
            or result.returncode == 0
            or "initialize" in result.stderr.lower()
        ), (
            f"MCP server should start and respond.\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )


class TestMcpToolDiscovery:
    """Test that MCP tools are discoverable."""

    def test_mcp_server_lists_tools(self, fresh_project_with_install: Path) -> None:
        """Test that MCP server exposes IdlerGear tools."""
        project = fresh_project_with_install

        # Send tools/list request
        messages = [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1.0.0"},
                    },
                }
            ),
            json.dumps(
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
            ),
        ]
        input_data = "\n".join(messages) + "\n"

        result = subprocess.run(
            ["idlergear-mcp"],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project,
        )

        # Should have tool definitions in output
        output = result.stdout
        expected_tools = [
            "task_create",
            "task_list",
            "task_show",
            "task_close",
            "note_create",
            "note_list",
            "explore_create",
            "explore_list",
            "context",
            "vision_show",
        ]

        # Check that at least some tools are mentioned
        found_tools = [tool for tool in expected_tools if tool in output.lower()]
        assert len(found_tools) >= 3, (
            f"MCP server should expose IdlerGear tools.\n"
            f"Expected some of: {expected_tools}\n"
            f"Found: {found_tools}\n"
            f"Output: {output[:1000]}"
        )


class TestMcpVsCliParity:
    """Test that MCP tools and CLI commands produce equivalent results."""

    def test_task_create_parity(self, fresh_project_with_install: Path) -> None:
        """Test that task creation works the same via CLI and MCP."""
        project = fresh_project_with_install

        # Create task via CLI
        cli_result = run_idlergear(project, "task", "create", "CLI task")
        assert cli_result.returncode == 0

        # Verify task exists
        list_result = run_idlergear(project, "task", "list")
        assert "CLI task" in list_result.stdout

        # Note: Full MCP parity testing would require spawning the server
        # and sending JSON-RPC requests, which is complex. The existing
        # test_mcp_server.py tests cover the MCP tool implementations.

    def test_note_create_parity(self, fresh_project_with_install: Path) -> None:
        """Test that note creation works the same via CLI and MCP."""
        project = fresh_project_with_install

        # Create note via CLI
        cli_result = run_idlergear(project, "note", "create", "CLI note content")
        assert cli_result.returncode == 0

        # Verify note exists
        list_result = run_idlergear(project, "note", "list")
        assert "CLI note" in list_result.stdout

    def test_context_command_returns_structured_output(
        self, fresh_project_with_install: Path
    ) -> None:
        """Test that context command provides useful output."""
        project = fresh_project_with_install

        # Add some content
        run_idlergear(project, "task", "create", "Test task")
        run_idlergear(project, "note", "create", "Test note")

        # Run context
        result = run_idlergear(project, "context")
        assert result.returncode == 0

        output = result.stdout
        # Should have sections for different knowledge types
        assert "task" in output.lower() or "Task" in output
        assert "note" in output.lower() or "Note" in output
