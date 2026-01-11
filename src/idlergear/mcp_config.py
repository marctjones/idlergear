"""MCP configuration management for AI assistant integrations."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class McpServerConfig:
    """Configuration for an MCP server."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    type: str = "stdio"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"command": self.command, "type": self.type}
        if self.args:
            result["args"] = self.args
        if self.env:
            result["env"] = self.env
        return result


@dataclass
class McpConfig:
    """Complete MCP configuration."""

    servers: dict[str, McpServerConfig] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"mcpServers": {name: srv.to_dict() for name, srv in self.servers.items()}}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "McpConfig":
        """Create from dictionary."""
        servers = {}
        for name, config in data.get("mcpServers", {}).items():
            servers[name] = McpServerConfig(
                name=name,
                command=config.get("command", ""),
                args=config.get("args", []),
                env=config.get("env", {}),
                type=config.get("type", "stdio"),
            )
        return cls(servers=servers)

    @classmethod
    def from_file(cls, path: Path) -> Optional["McpConfig"]:
        """Load from JSON file."""
        if not path.exists():
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def save(self, path: Path) -> None:
        """Save to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
            f.write("\n")


def get_idlergear_mcp_config() -> McpServerConfig:
    """Get the standard IdlerGear MCP server configuration."""
    return McpServerConfig(
        name="idlergear",
        command="idlergear-mcp",
        args=[],
        type="stdio",
    )


def get_project_mcp_path(project_path: Path | None = None) -> Path:
    """Get path to project-level .mcp.json."""
    if project_path is None:
        from idlergear.config import find_idlergear_root

        project_path = find_idlergear_root() or Path.cwd()
    return project_path / ".mcp.json"


def get_claude_code_config_path() -> Path:
    """Get path to Claude Code's global MCP configuration.

    Location varies by platform:
    - macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
    - Linux: ~/.config/Claude/claude_desktop_config.json
    - Windows: %APPDATA%/Claude/claude_desktop_config.json
    """
    system = platform.system()

    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    else:  # Linux and others
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def load_project_mcp_config(project_path: Path | None = None) -> Optional[McpConfig]:
    """Load project-level MCP configuration."""
    path = get_project_mcp_path(project_path)
    return McpConfig.from_file(path)


def load_claude_code_config() -> Optional[McpConfig]:
    """Load Claude Code's global MCP configuration."""
    path = get_claude_code_config_path()
    return McpConfig.from_file(path)


@dataclass
class ConfigValidationResult:
    """Result of MCP configuration validation."""

    valid: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_mcp_config(config: McpConfig) -> ConfigValidationResult:
    """Validate MCP configuration."""
    issues = []
    warnings = []

    for name, server in config.servers.items():
        # Check command exists
        if not server.command:
            issues.append(f"Server '{name}' has no command specified")
            continue

        # Check if command is executable
        import shutil

        if not shutil.which(server.command):
            # Check if it's a path
            if not Path(server.command).exists():
                warnings.append(f"Server '{name}': command '{server.command}' not found in PATH")

        # Validate type
        if server.type not in ("stdio", "sse", "http"):
            issues.append(f"Server '{name}': invalid type '{server.type}' (must be stdio, sse, or http)")

    return ConfigValidationResult(
        valid=len(issues) == 0,
        issues=issues,
        warnings=warnings,
    )


def generate_project_mcp_config(
    project_path: Path | None = None,
    include_idlergear: bool = True,
    additional_servers: list[McpServerConfig] | None = None,
) -> McpConfig:
    """Generate MCP configuration for a project."""
    config = McpConfig()

    if include_idlergear:
        ig_config = get_idlergear_mcp_config()
        config.servers["idlergear"] = ig_config

    if additional_servers:
        for server in additional_servers:
            config.servers[server.name] = server

    return config


def add_server_to_config(
    config_path: Path,
    server: McpServerConfig,
    overwrite: bool = False,
) -> tuple[bool, str]:
    """Add a server to an existing MCP configuration.

    Returns (success, message).
    """
    if config_path.exists():
        config = McpConfig.from_file(config_path)
        if config is None:
            return False, f"Could not parse {config_path}"
    else:
        config = McpConfig()

    if server.name in config.servers and not overwrite:
        return False, f"Server '{server.name}' already exists. Use --overwrite to replace."

    config.servers[server.name] = server
    config.save(config_path)

    return True, f"Added '{server.name}' to {config_path}"


def remove_server_from_config(
    config_path: Path,
    server_name: str,
) -> tuple[bool, str]:
    """Remove a server from an MCP configuration.

    Returns (success, message).
    """
    if not config_path.exists():
        return False, f"Configuration file not found: {config_path}"

    config = McpConfig.from_file(config_path)
    if config is None:
        return False, f"Could not parse {config_path}"

    if server_name not in config.servers:
        return False, f"Server '{server_name}' not found in configuration"

    del config.servers[server_name]
    config.save(config_path)

    return True, f"Removed '{server_name}' from {config_path}"


@dataclass
class McpTestResult:
    """Result of testing an MCP connection."""

    server_name: str
    success: bool
    error: Optional[str] = None
    response_time_ms: Optional[float] = None
    server_info: Optional[dict] = None


async def test_mcp_server(server: McpServerConfig, timeout: float = 5.0) -> McpTestResult:
    """Test if an MCP server is working by attempting to initialize it.

    This spawns the server process and sends an initialize request.
    """
    import asyncio
    import time

    try:
        start = time.time()

        # Start the server process
        process = await asyncio.create_subprocess_exec(
            server.command,
            *server.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Send initialize request (JSON-RPC)
        init_request = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "idlergear-test", "version": "1.0.0"},
                },
            }
        )

        # Write with content-length header (MCP uses LSP-style framing)
        message = f"Content-Length: {len(init_request)}\r\n\r\n{init_request}"
        process.stdin.write(message.encode())
        await process.stdin.drain()

        # Read response with timeout
        try:
            response_data = await asyncio.wait_for(
                process.stdout.read(4096),
                timeout=timeout,
            )
            elapsed = (time.time() - start) * 1000

            # Try to parse response
            response_str = response_data.decode()
            # Skip Content-Length header
            if "\r\n\r\n" in response_str:
                response_str = response_str.split("\r\n\r\n", 1)[1]

            response = json.loads(response_str)

            process.terminate()
            await process.wait()

            return McpTestResult(
                server_name=server.name,
                success=True,
                response_time_ms=elapsed,
                server_info=response.get("result", {}).get("serverInfo"),
            )

        except asyncio.TimeoutError:
            process.terminate()
            await process.wait()
            return McpTestResult(
                server_name=server.name,
                success=False,
                error=f"Timeout after {timeout}s",
            )

    except FileNotFoundError:
        return McpTestResult(
            server_name=server.name,
            success=False,
            error=f"Command not found: {server.command}",
        )
    except Exception as e:
        return McpTestResult(
            server_name=server.name,
            success=False,
            error=str(e),
        )
