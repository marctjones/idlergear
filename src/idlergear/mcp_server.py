"""MCP Server for IdlerGear - exposes knowledge management as AI tools."""

import asyncio
import json
import os
import signal
import sys
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from idlergear import __version__
from idlergear.config import find_idlergear_root, get_config_value, set_config_value
from idlergear.git import GitServer
from idlergear.pm import ProcessManager

# Global flag for reload request
_reload_requested = False

# Registered agent ID for this MCP server session
# Set when idlergear_daemon_register_agent is called successfully
_registered_agent_id: str | None = None

# Current session ID (set when session starts, cleared when it ends)
_current_session_id: str | None = None

# FileRegistry cache for performance (invalidated by daemon events)
# Key: registry_path (str), Value: FileRegistry instance
_registry_cache: dict[str, Any] = {}
_registry_cache_lock = asyncio.Lock()


def _get_cached_registry(registry_path: Path | None = None) -> Any:
    """Get cached FileRegistry instance or create new one.

    Args:
        registry_path: Path to registry file (defaults to .idlergear/file_registry.json)

    Returns:
        FileRegistry instance
    """
    from idlergear.file_registry import FileRegistry

    # Determine path
    if registry_path is None:
        try:
            root = find_idlergear_root()
            if root:
                registry_path = Path(root) / ".idlergear" / "file_registry.json"
            else:
                registry_path = Path.cwd() / ".idlergear" / "file_registry.json"
        except Exception:
            registry_path = Path.cwd() / ".idlergear" / "file_registry.json"

    path_str = str(registry_path)

    # Return cached instance if available
    if path_str in _registry_cache:
        return _registry_cache[path_str]

    # Create new instance and cache it
    registry = FileRegistry(registry_path=registry_path)
    _registry_cache[path_str] = registry
    return registry


def _invalidate_registry_cache(registry_path: Path | None = None) -> None:
    """Invalidate FileRegistry cache.

    Called when daemon broadcasts registry change events to ensure
    all agents see the latest registry state.

    Args:
        registry_path: Specific registry to invalidate, or None for all
    """
    if registry_path is None:
        # Invalidate all caches
        _registry_cache.clear()
    else:
        # Invalidate specific cache
        path_str = str(registry_path)
        _registry_cache.pop(path_str, None)


async def _broadcast_registry_change(
    action: str, file_path: str, data: dict[str, Any] | None = None
) -> None:
    """Broadcast file registry change to daemon.

    This notifies all connected agents when the registry changes,
    allowing them to invalidate their caches and stay synchronized.

    Args:
        action: Action type (registered, deprecated, etc.)
        file_path: File path that was modified
        data: Additional data to include in broadcast
    """
    try:
        from idlergear.daemon.client import DaemonNotRunning, get_daemon_client

        # Try to find idlergear root
        try:
            idlergear_root = find_idlergear_root()
            if not idlergear_root:
                return  # No daemon to broadcast to
        except Exception:
            return

        # Try to connect and broadcast (non-blocking, fail gracefully)
        try:
            client = get_daemon_client(idlergear_root)
            await client.connect()

            # Construct broadcast message
            message = {
                "type": "registry_changed",
                "action": action,
                "file_path": file_path,
                **(data or {}),
            }

            # Broadcast via daemon
            await client.notify("event", {"event": f"file.{action}", "data": message})

            await client.disconnect()
        except DaemonNotRunning:
            # Daemon not running - this is OK, broadcast is optional
            pass
    except Exception:
        # Don't let broadcast failures break registry operations
        pass


# PID file for external reload triggers
def _get_pid_file() -> Path:
    """Get path to PID file for this MCP server."""
    return Path("/tmp") / f"idlergear-mcp-{os.getpid()}.pid"


def _write_pid_file() -> None:
    """Write PID file for external reload triggers."""
    pid_file = _get_pid_file()
    pid_file.write_text(str(os.getpid()))


def _cleanup_pid_file() -> None:
    """Remove PID file on exit."""
    try:
        _get_pid_file().unlink(missing_ok=True)
    except Exception:
        pass


def _ensure_daemon_running() -> None:
    """Ensure IdlerGear daemon is running.

    Starts the daemon automatically if it's not already running.
    This enables real-time TUI monitoring and multi-agent coordination.
    """
    from idlergear.daemon.client import DaemonNotRunning, get_daemon_client, start_daemon_process

    try:
        # Check if daemon is already running
        root = find_idlergear_root()
        if root:
            client = get_daemon_client(root)
            # Try to ping daemon - if this succeeds, daemon is running
            try:
                # Quick check - daemon.ping is fast
                import asyncio
                asyncio.run(client.call("daemon.ping", {}))
                # Daemon is running, we're good
                return
            except Exception:
                # Daemon not responding, start it
                pass
    except (DaemonNotRunning, Exception):
        # Daemon not running or error checking
        pass

    # Start daemon in background
    try:
        root = find_idlergear_root()
        if root:
            # Start daemon process (already runs in background via start_new_session=True)
            start_daemon_process(root)
            # Give it a moment to start up
            import time
            time.sleep(0.5)
    except Exception as e:
        # Daemon start failed - not fatal, continue without it
        # AI state reporting will gracefully degrade
        print(f"Warning: Could not start daemon: {e}", file=sys.stderr)


async def _auto_register_agent() -> None:
    """Automatically register this MCP server as an agent with the daemon.

    This enables the AI Monitor to show this assistant's activity in real-time.
    Registers with unique agent_id and capabilities list.
    """
    global _registered_agent_id

    from datetime import datetime
    from idlergear.daemon.client import get_daemon_client, DaemonNotRunning

    try:
        root = find_idlergear_root()
        if not root:
            return

        # Generate unique agent ID
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        agent_id = f"claude-code-{timestamp}"

        # Get daemon client and connect
        client = get_daemon_client(root)

        # Register with daemon (must be within async context to connect)
        capabilities = [
            "task_management",
            "file_operations",
            "code_analysis",
            "ai_state_reporting",
            "knowledge_management",
        ]

        async with client:
            response = await client.call("agent.register", {
                "agent_id": agent_id,
                "agent_type": "claude-code",
                "capabilities": capabilities,
                "metadata": {
                    "version": __version__,
                    "pid": os.getpid(),
                    "started_at": datetime.now().isoformat(),
                }
            })

        # Store agent_id globally for use in AI state reporting
        _registered_agent_id = agent_id

        print(f"Registered as agent: {agent_id}", file=sys.stderr)

    except (DaemonNotRunning, Exception) as e:
        # Graceful degradation - AI reporting will still work, just won't show in daemon
        print(f"Note: Could not register with daemon: {e}", file=sys.stderr)


def _activate_project_environment() -> None:
    """Detect and activate project development environments.

    This runs when the MCP server starts to ensure subprocess calls
    use the correct interpreters and toolchains (Python, Rust, .NET).
    """
    import sys

    from idlergear.env import activate_project_env

    try:
        # Try to find idlergear root first
        project_root = find_idlergear_root()
        if project_root:
            env_info = activate_project_env(project_root)
        else:
            # Fall back to current directory
            env_info = activate_project_env()

        if not env_info:
            return

        # Handle multiple environments
        if env_info.get("multiple"):
            envs = env_info.get("environments", [])
            print(
                f"[IdlerGear MCP] Detected {len(envs)} project environment(s):",
                file=sys.stderr,
            )
            for env in envs:
                lang = env.get("language", "unknown")
                if env.get("activated"):
                    if lang == "python":
                        print(
                            f"  ✓ Python: {env['type']} at {env.get('path', 'N/A')}",
                            file=sys.stderr,
                        )
                    elif lang == "rust":
                        print(
                            f"  ✓ Rust: toolchain '{env.get('toolchain')}' from {env.get('file')}",
                            file=sys.stderr,
                        )
                    elif lang == "dotnet":
                        print(
                            f"  ✓ .NET: SDK {env.get('sdk_version')} from {env.get('file')}",
                            file=sys.stderr,
                        )
                else:
                    print(
                        f"  ℹ {lang.capitalize()}: {env.get('note', 'detected')}",
                        file=sys.stderr,
                    )
        else:
            # Single environment
            lang = env_info.get("language", "unknown")
            if env_info.get("activated"):
                if lang == "python":
                    print(
                        f"[IdlerGear MCP] Activated Python {env_info['type']}: {env_info.get('path')}",
                        file=sys.stderr,
                    )
                elif lang == "rust":
                    print(
                        f"[IdlerGear MCP] Activated Rust toolchain '{env_info.get('toolchain')}' from {env_info.get('file')}",
                        file=sys.stderr,
                    )
                elif lang == "dotnet":
                    print(
                        f"[IdlerGear MCP] Detected .NET SDK {env_info.get('sdk_version')} from {env_info.get('file')}",
                        file=sys.stderr,
                    )
            else:
                print(
                    f"[IdlerGear MCP] Detected {lang} environment: {env_info.get('note', '')}",
                    file=sys.stderr,
                )
    except Exception as e:
        # Don't crash the server if environment detection fails
        print(
            f"[IdlerGear MCP] Warning: Failed to detect project environment: {e}",
            file=sys.stderr,
        )


def _signal_handler(signum: int, frame: Any) -> None:
    """Handle reload signal (SIGUSR1).

    When we receive SIGUSR1, we flush all output and exec ourselves.
    This replaces the current process with a fresh one, inheriting
    the stdin/stdout file descriptors.
    """
    import sys

    # Flush all output before exec
    sys.stdout.flush()
    sys.stderr.flush()

    # Clean up
    _cleanup_pid_file()

    # Re-execute ourselves
    _do_reload()


def _setup_reload_signal() -> None:
    """Set up signal handler for reload."""
    if hasattr(signal, "SIGUSR1"):
        signal.signal(signal.SIGUSR1, _signal_handler)


def _do_reload() -> None:
    """Reload the MCP server by re-executing the process."""
    # Clean up PID file
    _cleanup_pid_file()

    # Get the executable and arguments
    python = sys.executable

    # Re-execute with the same arguments
    # This replaces the current process completely
    os.execv(python, [python, "-m", "idlergear.mcp_server"] + sys.argv[1:])


# Notes now use backend system via get_backend("note")
from idlergear.projects import (
    add_task_to_project,
    create_project,
    delete_project,
    get_project,
    link_to_github_project,
    list_github_projects,
    list_projects,
    move_task,
    remove_task_from_project,
    sync_project_to_github,
)

# Plans now use backend system via get_backend("plan")
# References now use backend system via get_backend("reference")
from idlergear.runs import get_run_logs, get_run_status, list_runs, start_run, stop_run
from idlergear.search import search_all
from idlergear.backends.registry import get_backend
from idlergear.env import (
    detect_project_type,
    find_virtualenv,
    get_environment_info,
    which_enhanced,
)
from idlergear.fs import FilesystemServer
# Vision now uses backend system via get_backend("vision")

# Initialize filesystem server
fs_server = None


def _get_fs_server() -> FilesystemServer:
    """Get or create filesystem server instance."""
    global fs_server
    if fs_server is None:
        fs_server = FilesystemServer()
    return fs_server


# Initialize servers
git_server = None
pm_server = None


def _get_git_server() -> GitServer:
    """Get or create git server instance."""
    global git_server
    if git_server is None:
        git_server = GitServer()
    return git_server


def _get_pm_server() -> ProcessManager:
    """Get or create process manager instance."""
    global pm_server
    if pm_server is None:
        pm_server = ProcessManager()
    return pm_server


# Plugin registry singleton
plugin_registry = None


def _get_plugin_registry():
    """Get or create plugin registry instance."""
    from idlergear.plugins import PluginRegistry

    global plugin_registry
    if plugin_registry is None:
        plugin_registry = PluginRegistry()
    return plugin_registry


# Create the MCP server with enhanced instructions
server = Server(
    "idlergear",
    instructions="""IdlerGear is a knowledge management system for AI development sessions.

⚡ RECOMMENDED FIRST CALL: idlergear_session_start() ⚡

At the start of EVERY session, call idlergear_session_start() to:
- Load project context (vision, plan, tasks, notes)
- Restore previous session state (current task, working files)
- Get recommendations for what to work on

This ensures perfect session continuity and saves you from asking "where did we leave off?"

At the end of your session, call idlergear_session_end() to save state for next time.

Available tool categories:
- Session Management (4 tools) - Start/end sessions with state persistence
- Context & Knowledge (6 tools) - Vision, plans, tasks, notes, references
- Knowledge Graph (6 tools) - Token-efficient queries for tasks, files, symbols
- Filesystem (11 tools) - File operations with gitignore support
- Git Integration (18 tools) - Git operations + task linking
- Process Management (11 tools) - System info, process control
- Environment (4 tools) - Python/Node/Rust detection, venv finder
- OpenTelemetry (3 tools) - Log collection and querying

All tools return structured JSON for token efficiency.

Knowledge Graph Usage:
1. First-time setup: Call idlergear_graph_populate_git() and idlergear_graph_populate_code()
2. Query efficiently: Use idlergear_graph_query_symbols() instead of grep for finding functions
3. Get context: Use idlergear_graph_query_task() for token-efficient task context
4. Incremental updates: Re-run populate tools periodically to stay current""",
)


def _format_result(data: Any) -> list[TextContent]:
    """Format a result as JSON text content."""
    if data is None:
        return [TextContent(type="text", text="null")]
    return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


def _check_initialized() -> None:
    """Check if IdlerGear is initialized."""
    if find_idlergear_root() is None:
        raise ValueError("IdlerGear not initialized. Run 'idlergear init' first.")


def _log_file_access(
    tool: str,
    file_path: str,
    status: str | None,
    allowed: bool,
    agent_id: str | None = None,
) -> None:
    """Log file access attempts to .idlergear/access_log.jsonl.

    Args:
        tool: Tool name (Read, Write, Edit, Bash)
        file_path: Path to file being accessed
        status: File status from registry (deprecated, archived, problematic, current, None)
        allowed: Whether access was allowed
        agent_id: Agent ID if available
    """
    try:
        from datetime import datetime, UTC

        root = find_idlergear_root()
        if root is None:
            return  # Can't log if not initialized

        log_file = Path(root) / ".idlergear" / "access_log.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "tool": tool,
            "file_path": str(file_path),
            "status": status,
            "allowed": allowed,
            "agent_id": agent_id or _registered_agent_id,
        }

        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        # Don't fail tool calls if logging fails
        pass


def _check_file_access(
    file_path: str, operation: str, allow_override: bool = False
) -> tuple[bool, str | None]:
    """Check if file operation should be allowed based on file registry.

    Args:
        file_path: Path to file being accessed
        operation: Operation type (read, write, edit, bash)
        allow_override: If True, allow access even if deprecated

    Returns:
        Tuple of (allowed, warning_message)
        - allowed: True if operation should proceed
        - warning_message: Error message if not allowed, None otherwise
    """
    try:
        from idlergear.file_registry import FileRegistry

        # Allow override for intentional deprecated file access
        if allow_override:
            return (True, None)

        # Check if path looks like a file (not a URL, command, etc.)
        path_str = str(file_path)

        # Skip non-file-like strings
        if any(
            path_str.startswith(prefix)
            for prefix in ["http://", "https://", "ftp://", "git@"]
        ):
            return (True, None)

        # Skip if it looks like a command or flag
        if path_str.startswith("-") or " " in path_str:
            return (True, None)

        # Get registry from idlergear root
        root = find_idlergear_root()
        if root is None:
            # Not in an idlergear project - allow all access
            return (True, None)

        registry_path = Path(root) / ".idlergear" / "file_registry.json"
        registry = _get_cached_registry(registry_path)
        entry = registry.get_entry(file_path)

        if entry is None:
            # File not in registry - allow access
            return (True, None)

        status = entry.status.value  # FileStatus enum value

        if status == "deprecated":
            successor = entry.current_version
            reason = entry.reason or ""

            if successor:
                msg = f"⚠️  File '{file_path}' is deprecated. Use '{successor}' instead."
            else:
                msg = f"⚠️  File '{file_path}' is deprecated."

            if reason:
                msg += f"\nReason: {reason}"

            # For write operations, warn but allow (updates the file)
            if operation == "write":
                msg += "\n\nNote: Write operation allowed to update deprecated file."
                _log_file_access("Write", file_path, status, True)
                return (True, msg)  # Allow with warning

            # For read/edit, block access
            _log_file_access(operation.capitalize(), file_path, status, False)
            return (False, msg)

        elif status == "archived":
            reason = entry.reason or ""
            msg = f"⚠️  File '{file_path}' is archived."
            if reason:
                msg += f"\nReason: {reason}"
            msg += "\n\nVerify you need historical data before accessing."

            _log_file_access(operation.capitalize(), file_path, status, False)
            return (False, msg)

        elif status == "problematic":
            reason = entry.reason or "Known issues"
            msg = f"⚠️  File '{file_path}' has known issues: {reason}"

            _log_file_access(operation.capitalize(), file_path, status, False)
            return (False, msg)

        # File is current or unknown status - allow
        _log_file_access(operation.capitalize(), file_path, status or "current", True)
        return (True, None)

    except Exception as e:
        # Don't block operations if registry check fails
        # Log the failure but allow the operation
        return (True, f"Warning: File registry check failed: {e}")


# Define all tools
@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available IdlerGear tools."""
    return [
        # Task tools
        Tool(
            name="idlergear_task_create",
            description="MANDATORY: Create a task. You MUST call this when you: 1) Find a bug (add --label bug), 2) Make a design decision (add --label decision), 3) Leave technical debt (add --label tech-debt), 4) Identify work to be done. NEVER write TODO comments or create TODO.md files - use this tool instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "body": {"type": "string", "description": "Task body/description"},
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Labels for the task",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Task priority",
                    },
                    "due": {
                        "type": "string",
                        "description": "Due date (YYYY-MM-DD)",
                    },
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="idlergear_task_list",
            description="List tasks. CALL AT SESSION START to see open work items. Check this before starting any new work.",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "enum": ["open", "closed", "all"],
                        "description": "Filter by state",
                        "default": "open",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results (for token efficiency)",
                    },
                    "preview": {
                        "type": "boolean",
                        "description": "Strip task bodies for token efficiency (default: false)",
                        "default": False,
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Filter by priority",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_task_show",
            description="Show a task by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Task ID"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="idlergear_task_close",
            description="Close a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Task ID"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="idlergear_task_update",
            description="Update a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Task ID"},
                    "title": {"type": "string", "description": "New title"},
                    "body": {"type": "string", "description": "New body"},
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New labels",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low", ""],
                        "description": "Task priority (empty string to clear)",
                    },
                    "due": {
                        "type": "string",
                        "description": "Due date (YYYY-MM-DD, empty string to clear)",
                    },
                },
                "required": ["id"],
            },
        ),
        # Note tools
        Tool(
            name="idlergear_note_create",
            description="MANDATORY: Create a note to persist knowledge for future sessions. CALL THIS WHEN YOU: 1) Discover how something works, 2) Find a quirk or gotcha, 3) Learn an API behavior, 4) Have an idea worth remembering. Use tags: 'explore' for research questions, 'idea' for concepts. This note WILL be available in your next session. NEVER write to NOTES.md, SESSION_*.md - use this tool instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Note content"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags (e.g., ['explore'], ['idea'])",
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="idlergear_note_list",
            description="List notes, optionally filtered by tag",
            inputSchema={
                "type": "object",
                "properties": {
                    "tag": {
                        "type": "string",
                        "description": "Filter by tag (e.g., 'explore', 'idea')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results (for token efficiency)",
                    },
                    "preview": {
                        "type": "boolean",
                        "description": "Strip note content for token efficiency (default: false)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_note_show",
            description="Show a note by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Note ID"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="idlergear_note_delete",
            description="Delete a note",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Note ID"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="idlergear_note_promote",
            description="Promote a note to task or reference",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Note ID"},
                    "to": {
                        "type": "string",
                        "enum": ["task", "reference"],
                        "description": "Target type",
                    },
                },
                "required": ["id", "to"],
            },
        ),
        # Vision tools
        Tool(
            name="idlergear_vision_show",
            description="REQUIRED AT SESSION START: Show the project vision. You MUST call this or idlergear_context at the beginning of every session to understand project goals. Check this before making any major decisions.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_vision_edit",
            description="Update the project vision",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "New vision content"},
                },
                "required": ["content"],
            },
        ),
        # Plan tools
        Tool(
            name="idlergear_plan_create",
            description="Create a development plan. Plans track work from micro (minutes) to macro (months) scales. Use type='ephemeral' for AI multi-step workflows, 'feature' for small features, 'roadmap' for medium initiatives, 'initiative' for large projects.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Plan name (unique identifier)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Plan description/purpose",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["ephemeral", "feature", "roadmap", "initiative"],
                        "description": "Plan type (default: feature)",
                        "default": "feature",
                    },
                    "milestone": {
                        "type": "string",
                        "description": "Milestone name or date",
                    },
                    "parent": {
                        "type": "string",
                        "description": "Parent plan name for hierarchical plans",
                    },
                    "auto_archive": {
                        "type": "boolean",
                        "description": "Auto-archive when completed (default: true for ephemeral)",
                        "default": False,
                    },
                },
                "required": ["name", "description"],
            },
        ),
        Tool(
            name="idlergear_plan_list",
            description="List plans with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "completed", "deprecated", "archived"],
                        "description": "Filter by status",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["ephemeral", "feature", "roadmap", "initiative"],
                        "description": "Filter by type",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_plan_show",
            description="Show plan details including files, tasks, references, and hierarchy",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Plan name"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_plan_delete",
            description="Delete or archive a plan. By default, archives first for safety.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Plan name"},
                    "permanent": {
                        "type": "boolean",
                        "description": "Permanently delete without archiving (default: false)",
                        "default": False,
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_plan_complete",
            description="Mark a plan as completed with timestamp",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Plan name"},
                },
                "required": ["name"],
            },
        ),
        # Reference tools
        Tool(
            name="idlergear_reference_add",
            description="Store permanent documentation. USE THIS WHEN YOU: 1) Explain a design decision, 2) Document an API or protocol, 3) Describe architecture that others should understand. References persist across sessions and are searchable.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Reference title"},
                    "body": {"type": "string", "description": "Reference body"},
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="idlergear_reference_list",
            description="List all reference documents",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results",
                    },
                    "preview": {
                        "type": "boolean",
                        "default": False,
                        "description": "Strip bodies for token efficiency (default: false)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_reference_show",
            description="Show a reference document",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Reference title"},
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="idlergear_reference_search",
            description="Search reference documents",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        ),
        # Run tools
        Tool(
            name="idlergear_run_start",
            description="Start a script/command in the background",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to run"},
                    "name": {"type": "string", "description": "Run name"},
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="idlergear_run_list",
            description="List all runs with metadata (script_hash, terminal_type, timestamps)",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_run_status",
            description="Get detailed run status including metadata (script_hash, duration, exit_code, timestamps)",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Run name"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_run_logs",
            description="Get run logs",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Run name"},
                    "tail": {"type": "integer", "description": "Last N lines"},
                    "stream": {
                        "type": "string",
                        "enum": ["stdout", "stderr"],
                        "description": "Log stream",
                        "default": "stdout",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_run_stop",
            description="Stop a running process",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Run name"},
                },
                "required": ["name"],
            },
        ),
        # Config tools
        Tool(
            name="idlergear_config_get",
            description="Get a configuration value",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Config key (dot notation)",
                    },
                },
                "required": ["key"],
            },
        ),
        Tool(
            name="idlergear_config_set",
            description="Set a configuration value",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Config key (dot notation)",
                    },
                    "value": {"type": "string", "description": "Config value"},
                },
                "required": ["key", "value"],
            },
        ),
        # Context tool - session start
        Tool(
            name="idlergear_context",
            description="MANDATORY AT SESSION START: Get project context. You MUST call this at the beginning of EVERY session BEFORE doing any work. Returns vision, current plan, open tasks, explorations, and recent notes. Do NOT skip this step. Default mode is 'minimal' (~750 tokens) for efficiency.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "Context verbosity mode (default: minimal). Options: minimal (~750 tokens, session start), standard (~2500 tokens, general dev), detailed (~7000 tokens, deep planning), full (~17000+ tokens, rare use)",
                        "enum": ["minimal", "standard", "detailed", "full"],
                        "default": "minimal",
                    },
                    "include_refs": {
                        "type": "boolean",
                        "description": "Include reference documents (overridden by mode in minimal/standard)",
                        "default": False,
                    },
                },
            },
        ),
        # Status tool - quick project overview
        Tool(
            name="idlergear_status",
            description="Get quick project status dashboard (tasks, notes, runs, git). Use this for a quick overview of current state.",
            inputSchema={
                "type": "object",
                "properties": {
                    "detailed": {
                        "type": "boolean",
                        "description": "Show detailed dashboard",
                        "default": False,
                    },
                },
            },
        ),
        # Search tool
        Tool(
            name="idlergear_search",
            description="PREFER THIS over file search. Search across all IdlerGear knowledge (tasks, notes, references, plans). Use this BEFORE searching files when looking for project information, decisions, or context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["task", "note", "reference", "plan"],
                        },
                        "description": "Types to search (default: all)",
                    },
                },
                "required": ["query"],
            },
        ),
        # Backend configuration tool
        Tool(
            name="idlergear_backend_show",
            description="Show configured backends for all knowledge types",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_backend_set",
            description="Set the backend for a knowledge type",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["task", "note", "reference", "plan", "vision"],
                        "description": "Knowledge type to configure",
                    },
                    "backend": {
                        "type": "string",
                        "description": "Backend name (e.g., local, github)",
                    },
                },
                "required": ["type", "backend"],
            },
        ),
        # Knowledge graph tools
        Tool(
            name="idlergear_graph_query_task",
            description="Query knowledge graph for task context. Returns task info with related files, commits, and symbols. Token-efficient alternative to grep/file reads.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID to query"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="idlergear_graph_query_file",
            description="Query knowledge graph for file context. Returns file info with related tasks, imports, and symbols.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Relative file path (e.g., 'src/main.py')",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="idlergear_graph_query_symbols",
            description="Search knowledge graph for symbols by name pattern. Returns functions, classes, and methods matching the pattern with their locations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Symbol name pattern (case-insensitive contains)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["pattern"],
            },
        ),
        Tool(
            name="idlergear_graph_populate_git",
            description="Populate knowledge graph with git history. Indexes commits and file changes for token-efficient queries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_commits": {
                        "type": "integer",
                        "description": "Maximum number of commits to index (default: 100)",
                        "default": 100,
                    },
                    "since": {
                        "type": "string",
                        "description": "Only index commits since this date (e.g., '2025-01-01')",
                    },
                    "incremental": {
                        "type": "boolean",
                        "description": "Skip commits already in database (default: true)",
                        "default": True,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_graph_populate_code",
            description="Populate knowledge graph with code symbols from Python files. Indexes functions, classes, and methods for fast symbol lookup.",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to scan (relative to repo root, default: 'src')",
                        "default": "src",
                    },
                    "incremental": {
                        "type": "boolean",
                        "description": "Skip files that haven't changed (default: true)",
                        "default": True,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_graph_schema_info",
            description="Get knowledge graph schema information. Returns node types, relationship types, and counts.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_graph_query_documentation",
            description="Query knowledge graph for documentation by path. Returns documentation content with related files, symbols, and tasks. Searches wiki pages and reference files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Documentation path (e.g., 'wiki/Feature-Name.md')",
                    }
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="idlergear_graph_search_documentation",
            description="Search knowledge graph documentation by keyword. Returns matching wiki pages and references with related code elements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (searches titles and body text)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="idlergear_graph_populate_all",
            description="Populate entire knowledge graph in one command. Runs all populators: git history, code symbols, tasks, commit-task links, references, and wiki documentation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_commits": {
                        "type": "integer",
                        "description": "Maximum commits to index",
                        "default": 100,
                    },
                    "incremental": {
                        "type": "boolean",
                        "description": "Skip unchanged data",
                        "default": True,
                    },
                },
            },
        ),
        # Advanced graph query tools (Issue #335)
        Tool(
            name="idlergear_graph_impact_analysis",
            description="Analyze what would be affected if a symbol breaks or changes. Returns all files, symbols, and tasks that depend on this symbol. Provides 95%+ token efficiency vs grep.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol_name": {
                        "type": "string",
                        "description": "Name of symbol to analyze (function, class, method)",
                    }
                },
                "required": ["symbol_name"],
            },
        ),
        Tool(
            name="idlergear_graph_test_coverage",
            description="Find test files that cover a given file or symbol. Returns test files and test functions that exercise the target.",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "File path or symbol name to check coverage for",
                    },
                    "target_type": {
                        "type": "string",
                        "description": "Type of target: 'file' or 'symbol'",
                        "enum": ["file", "symbol"],
                        "default": "file",
                    },
                },
                "required": ["target"],
            },
        ),
        Tool(
            name="idlergear_graph_change_history",
            description="Get all commits that touched a specific symbol. Traces symbol across file changes and renames. Returns chronological commit history.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol_name": {
                        "type": "string",
                        "description": "Symbol name to trace",
                    }
                },
                "required": ["symbol_name"],
            },
        ),
        Tool(
            name="idlergear_graph_dependency_chain",
            description="Find transitive dependency chain for a file. Returns all files this file depends on recursively via imports. Useful for refactoring decisions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Source file path",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth to traverse (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="idlergear_graph_orphan_detection",
            description="Find orphaned/unused code - functions with no callers and files with no imports. Helps identify dead code for cleanup.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_graph_symbol_callers",
            description="Find all symbols that call a given symbol (reverse lookup). Returns caller functions, their locations, and files. 98% token efficiency vs grep.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol_name": {
                        "type": "string",
                        "description": "Symbol to find callers for",
                    }
                },
                "required": ["symbol_name"],
            },
        ),
        Tool(
            name="idlergear_graph_file_timeline",
            description="Get evolution of a file over time via commits. Returns chronological list of all commits that modified this file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "File to trace",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max commits to return (default: 20)",
                        "default": 20,
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="idlergear_graph_task_coverage",
            description="Find tasks with no associated commits (not yet implemented). Returns tasks that have no work done on them yet, with coverage percentage.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # Graph visualization tools
        Tool(
            name="idlergear_graph_visualize_export",
            description="Export knowledge graph to visualization format (GraphML for Gephi/Cytoscape, DOT for Graphviz, JSON for custom viz). Use this to create visual diagrams of your codebase structure.",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_path": {
                        "type": "string",
                        "description": "Output file path (.graphml, .dot, or .json)",
                    },
                    "format": {
                        "type": "string",
                        "description": "Format: graphml, dot, or json (auto-detected from extension)",
                        "enum": ["graphml", "dot", "json"],
                    },
                    "node_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by node types (e.g., ['Task', 'File', 'Symbol'])",
                    },
                    "relationship_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by relationship types (e.g., ['MODIFIES', 'CONTAINS'])",
                    },
                    "max_nodes": {
                        "type": "integer",
                        "description": "Maximum nodes to export (default: 1000)",
                        "default": 1000,
                    },
                    "d3_format": {
                        "type": "boolean",
                        "description": "Use D3.js format for JSON (default: false)",
                        "default": False,
                    },
                    "layout": {
                        "type": "string",
                        "description": "Graphviz layout for DOT format (dot, neato, fdp, circo, twopi)",
                        "enum": ["dot", "neato", "fdp", "circo", "twopi"],
                        "default": "dot",
                    },
                },
                "required": ["output_path"],
            },
        ),
        Tool(
            name="idlergear_graph_visualize_task",
            description="Visualize task and its connected nodes (commits, files, symbols). Shows the task's implementation network to understand what was changed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "Task ID to visualize",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output file path",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Relationship depth (1=direct, 2=2nd degree, default: 2)",
                        "default": 2,
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format (default: dot)",
                        "enum": ["graphml", "dot", "json"],
                        "default": "dot",
                    },
                },
                "required": ["task_id", "output_path"],
            },
        ),
        Tool(
            name="idlergear_graph_visualize_deps",
            description="Visualize file dependencies (imports, calls). Shows the dependency network to understand module relationships and potential circular dependencies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "File path to analyze",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output file path",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Import depth (how many hops to follow, default: 2)",
                        "default": 2,
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format (default: dot)",
                        "enum": ["graphml", "dot", "json"],
                        "default": "dot",
                    },
                },
                "required": ["file_path", "output_path"],
            },
        ),
        # Server management tools
        Tool(
            name="idlergear_version",
            description="Show IdlerGear MCP server version and PID",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_reload",
            description="Reload the IdlerGear MCP server to pick up code changes. Call this after IdlerGear has been updated (e.g., after git pull or pip install) to use the new version without restarting Claude Code. The server will re-execute itself with the latest code.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # Project tools (Kanban boards)
        Tool(
            name="idlergear_project_create",
            description="Create a Kanban project board for organizing tasks into columns. Use this to track work across stages (Backlog, In Progress, Review, Done). Optionally syncs to GitHub Projects v2.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Project title"},
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Custom columns (default: Backlog, In Progress, Review, Done)",
                    },
                    "create_on_github": {
                        "type": "boolean",
                        "description": "Also create on GitHub Projects v2",
                        "default": False,
                    },
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="idlergear_project_list",
            description="List all project boards",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_github": {
                        "type": "boolean",
                        "description": "Also list GitHub Projects",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_project_show",
            description="Show a project board with all columns and tasks",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name or slug"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_project_delete",
            description="Delete a project board",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name or slug"},
                    "delete_on_github": {
                        "type": "boolean",
                        "description": "Also delete from GitHub",
                        "default": False,
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_project_add_task",
            description="Add a task to a project board column",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Project name or slug",
                    },
                    "task_id": {"type": "string", "description": "Task ID to add"},
                    "column": {
                        "type": "string",
                        "description": "Target column (default: first column)",
                    },
                },
                "required": ["project_name", "task_id"],
            },
        ),
        Tool(
            name="idlergear_project_remove_task",
            description="Remove a task from a project board",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Project name or slug",
                    },
                    "task_id": {"type": "string", "description": "Task ID to remove"},
                },
                "required": ["project_name", "task_id"],
            },
        ),
        Tool(
            name="idlergear_project_move_task",
            description="Move a task to a different column in the project board",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Project name or slug",
                    },
                    "task_id": {"type": "string", "description": "Task ID to move"},
                    "column": {"type": "string", "description": "Target column"},
                },
                "required": ["project_name", "task_id", "column"],
            },
        ),
        Tool(
            name="idlergear_project_sync",
            description="Sync a local project to GitHub Projects v2",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name or slug"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_project_link",
            description="Link a local project to an existing GitHub Project",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Local project name or slug",
                    },
                    "github_project_number": {
                        "type": "integer",
                        "description": "GitHub Project number",
                    },
                },
                "required": ["name", "github_project_number"],
            },
        ),
        Tool(
            name="idlergear_project_sync_fields",
            description="Manually sync task metadata to GitHub Projects custom fields. Syncs priority, labels, and due date based on projects.field_mapping configuration. Automatically called on task create/update if configured.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "Task ID to sync",
                    },
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="idlergear_project_pull",
            description="Pull changes from GitHub Projects and update local IdlerGear tasks (bidirectional sync). Syncs issue state (closed), priority, due dates, and labels from GitHub Projects to IdlerGear. GitHub is treated as source of truth for conflicts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Project name or slug",
                    },
                },
                "required": ["name"],
            },
        ),
        # Daemon coordination tools
        Tool(
            name="idlergear_daemon_register_agent",
            description="Register an AI agent with the daemon for multi-agent coordination. Returns agent ID for future operations. Use this when starting work on a codebase to enable coordination with other AI assistants.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Agent name (e.g., 'Claude Code Session', 'Goose Terminal')",
                    },
                    "agent_type": {
                        "type": "string",
                        "description": "Agent type (e.g., 'claude-code', 'goose', 'aider')",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata (optional)",
                        "additionalProperties": True,
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_daemon_list_agents",
            description="List all active AI agents registered with the daemon. Use this to see what other AI assistants are working on the codebase.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_daemon_queue_command",
            description="Queue a command for execution by any available AI agent. Use this to delegate work to other agents or queue long-running tasks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"},
                    "priority": {
                        "type": "integer",
                        "description": "Priority (higher = more urgent, default: 1)",
                    },
                    "wait_for_result": {
                        "type": "boolean",
                        "description": "Wait for command completion (default: False)",
                    },
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="idlergear_daemon_broadcast",
            description="Broadcast a message to all active AI agents. Use this to coordinate work across multiple AI assistants. For sending to a specific agent, use idlergear_message_send instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to broadcast to all agents",
                    },
                    "delivery": {
                        "type": "string",
                        "enum": ["context", "notification", "deferred"],
                        "description": "Delivery type for all recipients (default: notification)",
                        "default": "notification",
                    },
                },
                "required": ["message"],
            },
        ),
        # Session monitoring tools (for multi-client coordination)
        Tool(
            name="idlergear_session_notify_start",
            description="Notify the daemon that a session has started. Enables multi-client coordination by tracking active sessions across all AI assistants. Call this when starting work to let other agents know what you're working on.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent ID (from registration)",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (unique identifier)",
                    },
                    "session_name": {
                        "type": "string",
                        "description": "Human-readable session name",
                    },
                    "working_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of files being worked on",
                    },
                    "current_task_id": {
                        "type": "integer",
                        "description": "Current task ID",
                    },
                },
                "required": ["agent_id", "session_id"],
            },
        ),
        Tool(
            name="idlergear_session_notify_end",
            description="Notify the daemon that a session has ended. Call this when finishing work to clear your session state.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent ID (from registration)",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session ID that is ending",
                    },
                },
                "required": ["agent_id", "session_id"],
            },
        ),
        Tool(
            name="idlergear_session_list_active",
            description="List all active sessions across all AI assistants. Use this to see what other agents are currently working on.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_session_get_agent_status",
            description="Get the current session status for a specific agent. Returns what they're working on (files, task, session name).",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent ID to query",
                    },
                },
                "required": ["agent_id"],
            },
        ),
        Tool(
            name="idlergear_daemon_update_status",
            description="Update agent status (active/idle/busy). Use this to signal your current state to other agents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent ID from registration",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "idle", "busy"],
                        "description": "New status",
                    },
                },
                "required": ["agent_id", "status"],
            },
        ),
        Tool(
            name="idlergear_daemon_list_queue",
            description="List queued commands awaiting execution. Shows what work is pending across all agents.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # Cross-agent messaging tools (inbox-based, works without persistent connections)
        Tool(
            name="idlergear_message_send",
            description="""Send a message to another AI agent's inbox. Messages are routed by delivery type:
- context: Injected into recipient's context (they will see and act on it)
- notification (default): Converted to a task with [message] label (informational)
- deferred: Queued for end-of-session review

Use 'all' as to_agent to broadcast to all registered agents.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "to_agent": {
                        "type": "string",
                        "description": "Target agent ID (e.g., 'claude-code-abc123') or 'all' to broadcast",
                    },
                    "message": {
                        "type": "string",
                        "description": "Message content - can be a request, question, or information",
                    },
                    "delivery": {
                        "type": "string",
                        "enum": ["context", "notification", "deferred"],
                        "description": "Delivery type: context=inject into context, notification=create task, deferred=queue for later (default: notification)",
                    },
                    "message_type": {
                        "type": "string",
                        "enum": ["info", "request", "alert", "question"],
                        "description": "Message type: info, request, alert, or question (default: info)",
                    },
                    "action_requested": {
                        "type": "boolean",
                        "description": "Whether you need the recipient to DO something (default: false)",
                    },
                    "context": {
                        "type": "object",
                        "description": "Related context (e.g., {task_id: 45, files: ['api.py']})",
                    },
                    "from_agent": {
                        "type": "string",
                        "description": "Your agent ID (optional, auto-detected if registered)",
                    },
                },
                "required": ["to_agent", "message"],
            },
        ),
        Tool(
            name="idlergear_message_process",
            description="""Process inbox messages and route by delivery type. Call this at session start to:
- Inject context messages into your context (returns them)
- Convert notification messages to tasks with [message] label
- Queue deferred messages for later review

This ensures messages don't derail your work - only context ones are shown immediately.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Your agent ID (optional, auto-detected)",
                    },
                    "create_tasks": {
                        "type": "boolean",
                        "description": "Create tasks for normal-priority messages (default: true)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_message_list",
            description="Check your inbox for messages from other AI agents. Call this at session start to see if other agents have sent you requests.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Your agent ID (optional, uses registered ID if available)",
                    },
                    "unread_only": {
                        "type": "boolean",
                        "description": "Only show unread messages (default: true)",
                        "default": True,
                    },
                    "delivery": {
                        "type": "string",
                        "enum": ["context", "notification", "deferred"],
                        "description": "Filter by delivery type",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results (for token efficiency)",
                    },
                    "preview": {
                        "type": "boolean",
                        "description": "Strip message content, show only metadata (default: false)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_message_mark_read",
            description="Mark messages as read after processing them.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Your agent ID"},
                    "message_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Message IDs to mark as read (omit to mark all)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_message_clear",
            description="Clear read messages from your inbox.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Your agent ID"},
                    "all_messages": {
                        "type": "boolean",
                        "description": "Clear all messages, not just read ones (default: false)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_message_test",
            description="Test messaging by sending a message to yourself and retrieving it. This exercises the full messaging pipeline: send_message() -> inbox storage -> list_messages(). Use this to verify messaging is working correctly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_message": {
                        "type": "string",
                        "description": "Custom test message content (optional, defaults to a timestamp-based message)",
                    },
                },
            },
        ),
        # Script generation tools
        Tool(
            name="idlergear_generate_dev_script",
            description="Generate a shell script that sets up a dev environment, registers with daemon, and streams logs. Use this to create standardized setup scripts for long-running processes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Script name (e.g., 'backend-server')",
                    },
                    "command": {
                        "type": "string",
                        "description": "Command to run (e.g., 'python manage.py runserver')",
                    },
                    "template": {
                        "type": "string",
                        "enum": [
                            "pytest",
                            "django-dev",
                            "flask-dev",
                            "jupyter",
                            "fastapi-dev",
                        ],
                        "description": "Use a pre-built template (optional)",
                    },
                    "venv_path": {
                        "type": "string",
                        "description": "Virtual environment path (e.g., './venv')",
                    },
                    "requirements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Python packages to install (e.g., ['flask', 'pytest'])",
                    },
                    "env_vars": {
                        "type": "object",
                        "description": "Environment variables to set (e.g., {'FLASK_ENV': 'development'})",
                        "additionalProperties": {"type": "string"},
                    },
                    "stream_logs": {
                        "type": "boolean",
                        "description": "Enable log streaming to daemon (default: False)",
                    },
                },
                "required": ["name", "command"],
            },
        ),
        Tool(
            name="idlergear_list_script_templates",
            description="List all available script templates with their descriptions. Use this to see what pre-built templates are available.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_get_script_template",
            description="Get details about a specific script template. Shows what the template includes and how to use it.",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_name": {"type": "string", "description": "Template name"},
                },
                "required": ["template_name"],
            },
        ),
        # Environment detection tools
        Tool(
            name="idlergear_env_info",
            description="Get consolidated environment information (Python, Node, Rust, .NET versions, virtual environments, PATH). This provides ~60% token savings vs running multiple commands separately! Use this to quickly understand the development environment.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_env_which",
            description="Enhanced 'which' command showing ALL matches for a command across PATH, not just the first one. Useful for debugging PATH issues and finding all installed versions of a tool.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command name to search for",
                    },
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="idlergear_env_detect",
            description="Detect project type based on files present (Python, Node, Rust, .NET, Go, Java, Ruby). Useful for understanding what kind of project you're working in.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory to analyze (default: current directory)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_env_find_venv",
            description="Find and identify virtual environments in the project directory. Detects venv, poetry, pipenv automatically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory to search (default: current directory)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_env_active",
            description="Show currently active development environments (Python venv, Rust toolchain, .NET SDK). Returns info about environments that were auto-detected and activated when the MCP server started. Use this to verify subprocess calls will use correct interpreters and toolchains.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # Filesystem tools
        Tool(
            name="idlergear_fs_read_file",
            description="Read file contents. Returns content, path, and size. Use this instead of cat or Read tool for better performance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to file"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="idlergear_fs_read_multiple",
            description="Read multiple files at once. More efficient than calling read_file multiple times.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths",
                    },
                },
                "required": ["paths"],
            },
        ),
        Tool(
            name="idlergear_fs_write_file",
            description="Write file contents. Creates parent directories if needed. Use this instead of Write tool.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to file"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="idlergear_fs_create_directory",
            description="Create directory and parent directories if needed. Use this instead of mkdir.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to directory"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="idlergear_fs_list_directory",
            description="List directory contents with metadata (size, modified time). Excludes common patterns (.git, __pycache__, etc) automatically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (default: current directory)",
                        "default": ".",
                    },
                    "exclude_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional patterns to exclude (gitignore-style)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_fs_directory_tree",
            description="Generate recursive directory tree structure. Returns nested JSON with file/directory metadata. Much more efficient than recursive ls.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Root directory (default: current)",
                        "default": ".",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum recursion depth (default: 3)",
                        "default": 3,
                    },
                    "exclude_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Patterns to exclude",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_fs_move_file",
            description="Move or rename file/directory. Use this instead of mv.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source path"},
                    "destination": {
                        "type": "string",
                        "description": "Destination path",
                    },
                },
                "required": ["source", "destination"],
            },
        ),
        Tool(
            name="idlergear_fs_search_files",
            description="Search for files matching glob pattern. Respects .gitignore automatically. Much faster than find.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Root directory to search (default: current)",
                        "default": ".",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g., '*.py', 'test_*.py')",
                        "default": "*",
                    },
                    "exclude_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional patterns to exclude",
                    },
                    "use_gitignore": {
                        "type": "boolean",
                        "description": "Respect .gitignore files (default: true)",
                        "default": True,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_fs_file_info",
            description="Get file metadata (size, timestamps, permissions). Use this instead of stat.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="idlergear_fs_file_checksum",
            description="Calculate file checksum (MD5, SHA1, SHA256). Useful for verifying file integrity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "algorithm": {
                        "type": "string",
                        "enum": ["md5", "sha1", "sha256"],
                        "description": "Hash algorithm (default: sha256)",
                        "default": "sha256",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="idlergear_fs_allowed_directories",
            description="List all directories that can be accessed by filesystem operations. Security boundary check.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        # Git tools
        Tool(
            name="idlergear_git_status",
            description="Get git repository status with structured output (branch, ahead/behind, staged/modified/untracked files). Much more efficient than parsing 'git status' output!",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Repository path (default: current directory)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_git_diff",
            description="Get git diff with configurable context lines and file filtering. Supports both staged and unstaged changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "staged": {
                        "type": "boolean",
                        "description": "Show staged changes (git diff --cached)",
                        "default": False,
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific files to diff",
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Number of context lines",
                        "default": 3,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_git_log",
            description="Get git commit history with structured output. Supports filtering by date, author, and commit message.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "max_count": {
                        "type": "integer",
                        "description": "Maximum number of commits",
                        "default": 10,
                    },
                    "since": {
                        "type": "string",
                        "description": "Show commits since date",
                    },
                    "until": {
                        "type": "string",
                        "description": "Show commits until date",
                    },
                    "author": {"type": "string", "description": "Filter by author"},
                    "grep": {
                        "type": "string",
                        "description": "Filter by commit message",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_git_add",
            description="Stage files for commit. Supports staging specific files or all changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to stage",
                    },
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "all": {
                        "type": "boolean",
                        "description": "Stage all changes (git add -A)",
                        "default": False,
                    },
                },
                "required": ["files"],
            },
        ),
        Tool(
            name="idlergear_git_commit",
            description="Create a commit. Optionally link to an IdlerGear task by providing task_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "task_id": {
                        "type": "integer",
                        "description": "Optional task ID to link",
                    },
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="idlergear_git_reset",
            description="Unstage files or reset repository. WARNING: Use hard=true with caution as it discards changes!",
            inputSchema={
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to unstage (None = all)",
                    },
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "hard": {
                        "type": "boolean",
                        "description": "Hard reset (WARNING: discards changes)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_git_show",
            description="Show commit details including diff. Use this to inspect a specific commit.",
            inputSchema={
                "type": "object",
                "properties": {
                    "commit": {
                        "type": "string",
                        "description": "Commit hash or reference (e.g., 'HEAD', 'abc123')",
                    },
                    "repo_path": {"type": "string", "description": "Repository path"},
                },
                "required": ["commit"],
            },
        ),
        Tool(
            name="idlergear_git_branch_list",
            description="List all branches with current branch indicator and upstream tracking info.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Repository path"},
                },
            },
        ),
        Tool(
            name="idlergear_git_branch_create",
            description="Create a new branch, optionally checking it out immediately.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Branch name"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "checkout": {
                        "type": "boolean",
                        "description": "Checkout after creation",
                        "default": True,
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_git_branch_checkout",
            description="Checkout (switch to) a branch.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Branch name"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_git_branch_delete",
            description="Delete a branch. Use force=true to delete unmerged branches.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Branch name"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "force": {
                        "type": "boolean",
                        "description": "Force delete (even if not merged)",
                        "default": False,
                    },
                },
                "required": ["name"],
            },
        ),
        # IdlerGear-specific git+task integration tools
        Tool(
            name="idlergear_git_commit_task",
            description="Commit with automatic task linking (IdlerGear-specific). Automatically stages all changes and links to a task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID to link"},
                    "message": {"type": "string", "description": "Commit message"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "auto_add": {
                        "type": "boolean",
                        "description": "Automatically stage all changes",
                        "default": True,
                    },
                },
                "required": ["task_id", "message"],
            },
        ),
        Tool(
            name="idlergear_git_status_for_task",
            description="Get git status filtered by task files (IdlerGear-specific). Uses knowledge graph to find files associated with a task and filters git status to show only those files. Returns staged, modified, and untracked files relevant to the task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="idlergear_git_task_commits",
            description="Find all commits linked to a task (IdlerGear-specific). Searches commit messages for task references.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "max_count": {
                        "type": "integer",
                        "description": "Maximum commits to search",
                        "default": 50,
                    },
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="idlergear_git_sync_tasks",
            description="Sync task status from commit messages (IdlerGear-specific). Finds tasks mentioned in commits and reports sync summary.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "since": {
                        "type": "string",
                        "description": "Only process commits since this date",
                    },
                },
            },
        ),
        # === Process Management Tools ===
        Tool(
            name="idlergear_pm_list_processes",
            description="List running processes with optional filtering and sorting. Returns structured JSON with PID, name, user, CPU%, memory%, and status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter_name": {
                        "type": "string",
                        "description": "Filter by process name (substring match)",
                    },
                    "filter_user": {
                        "type": "string",
                        "description": "Filter by username",
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["cpu", "memory", "pid", "name"],
                        "description": "Sort by field (default: cpu)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_pm_get_process",
            description="Get detailed information about a specific process by PID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pid": {"type": "integer", "description": "Process ID"},
                },
                "required": ["pid"],
            },
        ),
        Tool(
            name="idlergear_pm_kill_process",
            description="Kill a process by PID. Use SIGTERM by default or SIGKILL with force=true.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pid": {"type": "integer", "description": "Process ID"},
                    "force": {
                        "type": "boolean",
                        "description": "Use SIGKILL instead of SIGTERM",
                    },
                },
                "required": ["pid"],
            },
        ),
        Tool(
            name="idlergear_pm_system_info",
            description="Get system information including CPU, memory, and disk usage.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="idlergear_pm_start_run",
            description="Start a background run (IdlerGear-specific). Executes command in background with stdout/stderr logging.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"},
                    "name": {
                        "type": "string",
                        "description": "Run name (auto-generated if not provided)",
                    },
                    "task_id": {
                        "type": "integer",
                        "description": "Optional task ID to associate with run",
                    },
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="idlergear_pm_list_runs",
            description="List all IdlerGear background runs with their status (running/stopped/completed/failed).",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="idlergear_pm_get_run_status",
            description="Get detailed status of a specific run including timestamps and log sizes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Run name"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_pm_get_run_logs",
            description="Get logs from a run (stdout or stderr).",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Run name"},
                    "tail": {
                        "type": "integer",
                        "description": "Number of lines from end (all if not specified)",
                    },
                    "stream": {
                        "type": "string",
                        "enum": ["stdout", "stderr"],
                        "description": "Log stream (default: stdout)",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_pm_stop_run",
            description="Stop a running background process.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Run name"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_pm_task_runs",
            description="Get all runs associated with a specific task (IdlerGear-specific).",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="idlergear_pm_quick_start",
            description="Start a process in the foreground (not as a background run). Returns immediately with PID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "executable": {
                        "type": "string",
                        "description": "Path to executable or command name",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Command arguments",
                    },
                },
                "required": ["executable"],
            },
        ),
        # Tmux session management tools
        Tool(
            name="idlergear_tmux_create_session",
            description="Create a new tmux session for persistent terminal management. Useful for long-running processes that need interactive access.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Session name (must be unique)",
                    },
                    "command": {
                        "type": "string",
                        "description": "Optional command to run in the session",
                    },
                    "window_name": {
                        "type": "string",
                        "description": "Optional window name (defaults to session name)",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_tmux_list_sessions",
            description="List all tmux sessions. Shows session names, window counts, and attachment status.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="idlergear_tmux_get_session",
            description="Get detailed information about a specific tmux session including all windows and panes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Session name",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_tmux_kill_session",
            description="Kill a tmux session. All processes running in the session will be terminated.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Session name",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_tmux_send_keys",
            description="Send keys/commands to a specific pane in a tmux session. Useful for controlling running processes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_name": {
                        "type": "string",
                        "description": "Session name",
                    },
                    "keys": {
                        "type": "string",
                        "description": "Keys/command to send",
                    },
                    "window_index": {
                        "type": "integer",
                        "description": "Window index (default: 0)",
                        "default": 0,
                    },
                    "pane_index": {
                        "type": "integer",
                        "description": "Pane index (default: 0)",
                        "default": 0,
                    },
                },
                "required": ["session_name", "keys"],
            },
        ),
        Tool(
            name="idlergear_run_attach",
            description="Get tmux attach command for a run. Returns the command to attach to the run's tmux session for interactive access.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Run name",
                    },
                },
                "required": ["name"],
            },
        ),
        # === Container Management Tools (Podman/Docker) ===
        Tool(
            name="idlergear_container_list",
            description="List running containers (supports Podman and Docker). Shows container ID, name, image, status, and creation time.",
            inputSchema={
                "type": "object",
                "properties": {
                    "all": {
                        "type": "boolean",
                        "description": "Include stopped containers (default: false)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_container_start",
            description="Start a new container with specified image and configuration. Supports environment variables, volume mounts, port mappings, and resource limits. Uses Podman if available, falls back to Docker.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image": {
                        "type": "string",
                        "description": "Container image (e.g., 'python:3.11', 'postgres:15', 'redis:alpine')",
                    },
                    "name": {
                        "type": "string",
                        "description": "Container name (optional, auto-generated if not provided)",
                    },
                    "command": {
                        "type": "string",
                        "description": "Command to run in container (optional)",
                    },
                    "env": {
                        "type": "object",
                        "description": "Environment variables as key-value pairs (e.g., {\"DATABASE_URL\": \"postgres://...\"})",
                        "additionalProperties": {"type": "string"},
                    },
                    "volumes": {
                        "type": "object",
                        "description": "Volume mounts as host_path:container_path pairs (e.g., {\"/data\": \"/app/data\"})",
                        "additionalProperties": {"type": "string"},
                    },
                    "ports": {
                        "type": "object",
                        "description": "Port mappings as host_port:container_port pairs (e.g., {\"8080\": \"80\"})",
                        "additionalProperties": {"type": "string"},
                    },
                    "memory": {
                        "type": "string",
                        "description": "Memory limit (e.g., '512m', '2g')",
                    },
                    "cpus": {
                        "type": "string",
                        "description": "CPU limit (e.g., '1.5' for 1.5 CPUs)",
                    },
                    "detach": {
                        "type": "boolean",
                        "description": "Run in background (default: true)",
                        "default": True,
                    },
                },
                "required": ["image"],
            },
        ),
        Tool(
            name="idlergear_container_stop",
            description="Stop a running container. Can force-stop (kill) if needed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force stop (kill instead of graceful shutdown)",
                        "default": False,
                    },
                },
                "required": ["container_id"],
            },
        ),
        Tool(
            name="idlergear_container_remove",
            description="Remove a container. Can force-remove running containers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force removal even if running",
                        "default": False,
                    },
                },
                "required": ["container_id"],
            },
        ),
        Tool(
            name="idlergear_container_logs",
            description="Get logs from a container. Useful for debugging and monitoring containerized processes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name",
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Number of lines from end (optional, all lines if not specified)",
                    },
                },
                "required": ["container_id"],
            },
        ),
        Tool(
            name="idlergear_container_stats",
            description="Get real-time resource usage statistics for a container (CPU, memory, network, disk I/O).",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name",
                    },
                },
                "required": ["container_id"],
            },
        ),
        # === OpenTelemetry Log Tools ===
        Tool(
            name="idlergear_otel_query_logs",
            description="Query OpenTelemetry logs with filtering, full-text search, and time range. Returns structured log entries with severity, service, message, attributes, and trace context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "description": "Filter by severity (DEBUG, INFO, WARN, ERROR, FATAL)",
                        "enum": ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"],
                    },
                    "service": {
                        "type": "string",
                        "description": "Filter by service name (e.g., 'goose', 'claude-code')",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time (ISO format or relative like '1h', '30m', '24h')",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time (ISO format)",
                    },
                    "search": {
                        "type": "string",
                        "description": "Full-text search query (searches message field)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 100)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_otel_stats",
            description="Get statistics about collected OpenTelemetry logs including total count, severity breakdown, service breakdown, and recent activity.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="idlergear_otel_recent_errors",
            description="Get recent ERROR and FATAL logs (last N entries). Useful for quickly checking for problems.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent errors to return (default: 20)",
                    },
                    "service": {
                        "type": "string",
                        "description": "Filter by service name",
                    },
                },
            },
        ),
        # === Session Management Tools ===
        Tool(
            name="idlergear_session_start",
            description="⚡ RECOMMENDED FIRST CALL ⚡ Start a new session by loading project context AND previous session state (current task, working files, notes). This is the BEST way to begin any session - combines context loading with session continuity. Returns context + session state + recommendations for what to work on.",
            inputSchema={
                "type": "object",
                "properties": {
                    "context_mode": {
                        "type": "string",
                        "description": "Context verbosity (minimal=570 tokens [DEFAULT], standard=7K, detailed=11K, full=17K)",
                        "enum": ["minimal", "standard", "detailed", "full"],
                    },
                    "load_state": {
                        "type": "boolean",
                        "description": "Load previous session state (default: true)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_session_save",
            description="Save current session state (task, files, notes) for next session. Call this before ending work to enable session continuity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "current_task_id": {
                        "type": "integer",
                        "description": "ID of task currently being worked on",
                    },
                    "working_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of files currently being edited",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Free-form notes about current session (what was accomplished, next steps, etc.)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_session_end",
            description="End current session - saves state and provides suggestions for next session. Convenience wrapper for session_save with auto-suggestions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "current_task_id": {
                        "type": "integer",
                        "description": "ID of task being worked on",
                    },
                    "working_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files being worked on",
                    },
                    "notes": {"type": "string", "description": "Session notes"},
                },
            },
        ),
        Tool(
            name="idlergear_session_status",
            description="Get current session state summary (task, files, notes, timestamp).",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        # === Watch Mode Tools ===
        Tool(
            name="idlergear_watch_check",
            description="Analyze project for issues: TODO/FIXME/HACK comments in diff, uncommitted changes, stale references. Returns suggestions for knowledge capture. Use --act to automatically create tasks from TODOs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "act": {
                        "type": "boolean",
                        "description": "Automatically create tasks from TODO/FIXME/HACK comments (default: false)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_watch_act",
            description="Execute action for a specific suggestion from watch_check. Use this to selectively act on individual suggestions (e.g., create a task from a specific TODO comment).",
            inputSchema={
                "type": "object",
                "properties": {
                    "suggestion_id": {
                        "type": "string",
                        "description": "Suggestion ID from watch_check results (e.g., 's1', 's2')",
                    },
                },
                "required": ["suggestion_id"],
            },
        ),
        Tool(
            name="idlergear_watch_stats",
            description="Get quick watch statistics: changed files/lines, TODO/FIXME/HACK counts, time since last commit.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        # Doctor tool - installation health check
        Tool(
            name="idlergear_doctor",
            description="Check IdlerGear installation health. Detects: outdated files, missing configuration, legacy files from older versions, and unmanaged knowledge files (TODO.md, NOTES.md). Use this to diagnose installation issues or after upgrading IdlerGear.",
            inputSchema={
                "type": "object",
                "properties": {
                    "fix": {
                        "type": "boolean",
                        "description": "Automatically fix issues by running install --upgrade (default: false)",
                        "default": False,
                    },
                },
            },
        ),
        # === Test Tools ===
        Tool(
            name="idlergear_test_detect",
            description="Detect the test framework used in the project. Supports: pytest (Python), cargo test (Rust), dotnet test (.NET), jest/vitest (JavaScript), go test (Go), rspec (Ruby). Call this to understand what testing tools are available.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory to analyze (default: current directory)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_test_status",
            description="Show the status of the last test run. Returns cached results including pass/fail counts, duration, and failed test names. Use this to quickly check if tests are passing without running them again.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory (default: current directory)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_test_run",
            description="Run the project's tests and cache results. Automatically detects the test framework and parses output. Results are saved for quick status checks later.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory (default: current directory)",
                    },
                    "args": {
                        "type": "string",
                        "description": "Additional arguments to pass to test command (e.g., '-k auth' for pytest)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_test_history",
            description="Show test run history. Returns the last N test runs with their results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory (default: current directory)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to show (default: 10)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_test_list",
            description="List all tests in the project. Enumerates individual test functions/methods using the framework's collection mechanism (e.g., pytest --collect-only).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory (default: current directory)",
                    },
                    "files_only": {
                        "type": "boolean",
                        "description": "Return only test files, not individual tests (default: false)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_test_coverage",
            description="Show test coverage mapping. Maps source files to their test files using naming conventions. Use to find which tests cover a specific file or to identify untested code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory (default: current directory)",
                    },
                    "file": {
                        "type": "string",
                        "description": "Optional: specific source file to check coverage for",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_test_uncovered",
            description="List source files that don't have corresponding tests. Useful for identifying code that needs test coverage.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory (default: current directory)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_test_changed",
            description="Show or run tests affected by changed files. Uses git diff to find changed files, then identifies which tests cover them. Use with run=true to execute the tests.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory (default: current directory)",
                    },
                    "since": {
                        "type": "string",
                        "description": "Commit hash or ref to compare against (e.g., 'HEAD~3', 'main')",
                    },
                    "run": {
                        "type": "boolean",
                        "description": "Actually run the tests (default: false, just shows what would run)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_test_sync",
            description="Detect and import test runs from outside IdlerGear. Checks for tests run via IDE, command line, or CI/CD by monitoring cache directories (.pytest_cache, node_modules/.cache, etc) and imports results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory (default: current directory)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_test_staleness",
            description="Check how stale test results are. Reports when tests were last run and whether tests have run outside of IdlerGear since then.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory (default: current directory)",
                    },
                },
            },
        ),
        # Documentation generation tools (Python + Rust + .NET)
        Tool(
            name="idlergear_docs_check",
            description="Check if documentation generation is available. Returns availability for Python (pdoc), Rust (cargo), and .NET (dotnet).",
            inputSchema={
                "type": "object",
                "properties": {
                    "lang": {
                        "type": "string",
                        "enum": ["python", "rust", "dotnet", "all"],
                        "description": "Language to check (default: all)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_docs_module",
            description="Generate API documentation for a single Python module. Returns structured JSON with functions, classes, and docstrings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "module": {
                        "type": "string",
                        "description": "Python module name (e.g., 'json', 'idlergear.tasks')",
                    },
                },
                "required": ["module"],
            },
        ),
        Tool(
            name="idlergear_docs_generate",
            description="Generate API documentation for a Python package and all submodules. Returns comprehensive JSON or markdown documentation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "package": {
                        "type": "string",
                        "description": "Python package name (e.g., 'idlergear')",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "markdown"],
                        "description": "Output format (default: json)",
                    },
                    "include_private": {
                        "type": "boolean",
                        "description": "Include private modules (default: false)",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum submodule depth (default: unlimited)",
                    },
                },
                "required": ["package"],
            },
        ),
        Tool(
            name="idlergear_docs_summary",
            description="⚡ TOKEN-EFFICIENT: Generate a compact API summary for AI consumption. Supports Python, Rust, and .NET projects with auto-detection. Modes: minimal (~500 tokens), standard (~2k tokens), detailed (~5k tokens).",
            inputSchema={
                "type": "object",
                "properties": {
                    "package": {
                        "type": "string",
                        "description": "Python package name OR path to Rust/.NET project (auto-detects language)",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["minimal", "standard", "detailed"],
                        "description": "Summary mode: minimal (names only), standard (first-line docstrings), detailed (full docs)",
                    },
                    "lang": {
                        "type": "string",
                        "enum": ["python", "rust", "dotnet", "auto"],
                        "description": "Language (default: auto-detect from project)",
                    },
                    "include_private": {
                        "type": "boolean",
                        "description": "Include private modules (default: false)",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum submodule depth (default: unlimited)",
                    },
                },
                "required": ["package"],
            },
        ),
        Tool(
            name="idlergear_docs_build",
            description="Build documentation. Uses pdoc for Python, cargo doc for Rust, dotnet build for .NET. Auto-detects project type if not specified.",
            inputSchema={
                "type": "object",
                "properties": {
                    "package": {
                        "type": "string",
                        "description": "Package name or path (auto-detects if not provided)",
                    },
                    "lang": {
                        "type": "string",
                        "enum": ["python", "rust", "dotnet", "auto"],
                        "description": "Language (default: auto-detect)",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Output directory for HTML files (Python: docs/api, Rust: target/doc)",
                    },
                    "open_browser": {
                        "type": "boolean",
                        "description": "Open documentation in browser after build (default: false)",
                    },
                    "logo": {
                        "type": "string",
                        "description": "Path to logo image (Python only)",
                    },
                    "favicon": {
                        "type": "string",
                        "description": "Path to favicon (Python only)",
                    },
                    "configuration": {
                        "type": "string",
                        "description": "Build configuration (.NET only, default: Debug)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_docs_detect",
            description="Detect project configuration for documentation. Returns language, package name, version, and source directory. Supports Python, Rust, and .NET.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory to analyze (default: current directory)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_watch_versions",
            description="Check for stale file version references in Python code. Detects when Python scripts reference old versions of data files (CSV, JSON, YAML, etc.) and suggests using the current version instead. Useful for catching when AI creates better datasets but forgets to update scripts.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        # File Registry tools
        Tool(
            name="idlergear_file_register",
            description="Register a file with explicit status (current/deprecated/archived/problematic). Use this to mark files as current when creating new versions, or mark old files as deprecated/archived.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to project root",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["current", "deprecated", "archived", "problematic"],
                        "description": "File status",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional reason for status",
                    },
                },
                "required": ["path", "status"],
            },
        ),
        Tool(
            name="idlergear_file_deprecate",
            description="Mark a file as deprecated with an optional successor. Use this when you create a new version of a file to explicitly deprecate the old version.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to deprecate",
                    },
                    "successor": {
                        "type": "string",
                        "description": "Path to current version that should be used instead",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for deprecation",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="idlergear_file_status",
            description="Get the status of a file. Returns current/deprecated/archived/problematic status, the current version if deprecated, and the reason for the status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to check",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="idlergear_file_list",
            description="List all registered files. Can filter by status to see only current, deprecated, archived, or problematic files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["current", "deprecated", "archived", "problematic"],
                        "description": "Filter by status (optional)",
                    },
                },
            },
        ),
        # File annotation tools (NEW v0.6.0)
        Tool(
            name="idlergear_file_annotate",
            description="Annotate file with purpose description, tags, components, and related files for token-efficient discovery. USE THIS: After creating new files, after understanding existing files, when refactoring. This enables 93% token savings on future file searches.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to annotate",
                    },
                    "description": {
                        "type": "string",
                        "description": "What this file does (optional)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Searchable tags (optional)",
                    },
                    "components": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key classes/functions in file (optional)",
                    },
                    "related_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Related file paths (optional)",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="idlergear_file_search",
            description="Search files by description text, tags, components, or status. USE THIS FIRST before grep! Token-efficient alternative to grep + reading multiple files. Returns file descriptions and metadata in ~200 tokens vs 15,000 tokens for grep + reading files. Always search annotations before using grep.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Full-text search in descriptions (optional, case-insensitive)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags - matches if any tag matches (optional)",
                    },
                    "components": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by component names (optional)",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["current", "deprecated", "archived", "problematic"],
                        "description": "Filter by file status (optional)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_file_get_annotation",
            description="Get full annotation for a specific file including description, tags, components, and related files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to get annotation for",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="idlergear_file_list_tags",
            description="List all tags used in file annotations with usage counts and file lists. Useful for discovering tag vocabulary.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="idlergear_file_audit",
            description="Audit project for deprecated file usage. Scans access log for recent deprecated file access and optionally scans code for string references. Use this to detect when AI assistants or developers are using outdated files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "since_hours": {
                        "type": "integer",
                        "description": "Audit access log for last N hours (default: 24)",
                        "default": 24,
                    },
                    "include_code_scan": {
                        "type": "boolean",
                        "description": "Include static code analysis for deprecated file references (default: false)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_file_scan",
            description="Auto-detect versioned files and suggest registry entries. Scans project for git rename history, filename patterns (_old, _v1, .bak, timestamps), and archive directories. Returns suggestions with confidence levels (high/medium/low).",
            inputSchema={
                "type": "object",
                "properties": {
                    "min_confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Minimum confidence level to include (default: low)",
                        "default": "low",
                    },
                    "include_git_renames": {
                        "type": "boolean",
                        "description": "Use git rename history detection (default: true)",
                        "default": True,
                    },
                    "include_patterns": {
                        "type": "boolean",
                        "description": "Use filename pattern matching (default: true)",
                        "default": True,
                    },
                    "include_directories": {
                        "type": "boolean",
                        "description": "Use directory structure detection (default: true)",
                        "default": True,
                    },
                },
            },
        ),
        # Plugin tools (NEW v0.8.0)
        Tool(
            name="idlergear_plugin_list",
            description="List available and loaded plugins. Shows which integrations (Langfuse, LlamaIndex, Mem0) are registered and enabled.",
            inputSchema={
                "type": "object",
                "properties": {
                    "loaded_only": {
                        "type": "boolean",
                        "description": "Only show loaded plugins (default: false, show all available)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_plugin_status",
            description="Get detailed status of plugins including enabled state, loaded state, health check, and capabilities.",
            inputSchema={
                "type": "object",
                "properties": {
                    "plugin_name": {
                        "type": "string",
                        "description": "Optional plugin name to check (omit for all plugins)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_plugin_enable",
            description="Enable or disable a plugin in config.toml. Requires plugin to be registered first.",
            inputSchema={
                "type": "object",
                "properties": {
                    "plugin_name": {
                        "type": "string",
                        "description": "Plugin name (e.g., 'langfuse', 'llamaindex', 'mem0')",
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Enable (true) or disable (false) the plugin",
                        "default": True,
                    },
                },
                "required": ["plugin_name"],
            },
        ),
        Tool(
            name="idlergear_plugin_search",
            description="Semantic search over IdlerGear knowledge (references, notes) using LlamaIndex. Provides 40% faster retrieval than alternatives with relevance scoring.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)",
                        "default": 5,
                    },
                    "knowledge_type": {
                        "type": "string",
                        "enum": ["reference", "note"],
                        "description": "Optional filter for knowledge type",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="idlergear_plugin_index_reference",
            description="Index a reference document for semantic search using LlamaIndex. Call this after creating or updating references.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Reference title",
                    },
                    "body": {
                        "type": "string",
                        "description": "Reference body content",
                    },
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="idlergear_plugin_index_note",
            description="Index a note for semantic search using LlamaIndex. Call this after creating notes to make them searchable.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "integer",
                        "description": "Note ID",
                    },
                    "content": {
                        "type": "string",
                        "description": "Note content",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Note tags",
                    },
                },
                "required": ["note_id", "content"],
            },
        ),
        # Knowledge gap detection tools
        Tool(
            name="idlergear_knowledge_detect_gaps",
            description="Detect knowledge gaps in the project. Returns gaps like missing documentation, undocumented commits, stale tasks, etc. CALL PROACTIVELY to improve project knowledge base.",
            inputSchema={
                "type": "object",
                "properties": {
                    "gap_type": {
                        "type": "string",
                        "enum": [
                            "missing_reference",
                            "undocumented_commits",
                            "unanswered_question",
                            "stale_task",
                            "orphaned_tasks",
                            "unannotated_files",
                        ],
                        "description": "Filter by specific gap type (optional)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_knowledge_gap_summary",
            description="Get summary of knowledge gaps by severity. Quick health check of knowledge base.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # Proactive suggestions tool
        Tool(
            name="idlergear_get_suggestions",
            description="Get proactive suggestions for improving the project. CALL AT SESSION START to surface actionable insights. Returns high-priority suggestions like gaps to fix, workflow improvements, and token efficiency tips.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # AI State Reporting Tools (for AI observability - #374)
        Tool(
            name="idlergear_ai_report_activity",
            description="Report your current activity to enable real-time AI observability. CALL THIS BEFORE major actions (reading files, running commands, editing code) to let users see what you're doing and why. Enables users to intervene if you're going down the wrong path.",
            inputSchema={
                "type": "object",
                "properties": {
                    "phase": {
                        "type": "string",
                        "enum": ["researching", "planning", "implementing", "testing"],
                        "description": "Current phase of work",
                    },
                    "task_id": {
                        "type": "integer",
                        "description": "Task ID being worked on (optional)",
                    },
                    "action": {
                        "type": "string",
                        "description": "Current action (e.g., 'reading file', 'running command', 'editing file')",
                    },
                    "target": {
                        "type": "string",
                        "description": "Target of action (file path, command, etc.)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why you're doing this action - your reasoning",
                    },
                },
                "required": ["phase", "action", "target", "reason"],
            },
        ),
        Tool(
            name="idlergear_ai_report_plan",
            description="Report your planned next steps. CALL THIS when you have a multi-step plan to let users see what you'll do before you do it. Users can redirect you if the plan is wrong, saving time.",
            inputSchema={
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "description": "Action to take",
                                },
                                "target": {
                                    "type": "string",
                                    "description": "Target (file, command, etc.)",
                                },
                                "reason": {
                                    "type": "string",
                                    "description": "Why this step is needed",
                                },
                            },
                            "required": ["action", "target"],
                        },
                        "description": "List of planned steps (in order)",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Confidence in this plan (0.0-1.0). Report low confidence (<0.7) to get user input.",
                    },
                },
                "required": ["steps", "confidence"],
            },
        ),
        Tool(
            name="idlergear_ai_report_uncertainty",
            description="Report when you're uncertain or confused. CALL THIS when confidence < 0.7 or you can't find something. Lets users provide answers before you waste time searching. Be honest about what you don't know.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "What you're uncertain about or trying to figure out",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Confidence level (0.0-1.0). < 0.5 = very uncertain",
                    },
                    "context": {
                        "type": "object",
                        "description": "What you've tried or what you know",
                        "properties": {
                            "searched_files": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Files you've searched",
                            },
                            "searched_docs": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Documentation you've checked",
                            },
                            "not_found": {
                                "type": "string",
                                "description": "What you couldn't find",
                            },
                        },
                    },
                },
                "required": ["question", "confidence"],
            },
        ),
        Tool(
            name="idlergear_ai_report_search",
            description="Report search activity. CALL THIS after grep/file searches (especially repeated searches for the same thing). Helps detect search inefficiency and lets users provide answers directly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What you searched for",
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["grep", "file", "documentation", "web"],
                        "description": "Type of search performed",
                    },
                    "results_found": {
                        "type": "integer",
                        "description": "Number of results found",
                    },
                    "files_searched": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files or paths searched",
                    },
                },
                "required": ["query", "search_type", "results_found"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    global _registered_agent_id, _current_session_id

    try:
        _check_initialized()

        # Task handlers - use configured backend
        if name == "idlergear_task_create":
            backend = get_backend("task")
            task = backend.create(
                arguments["title"],
                body=arguments.get("body"),
                labels=arguments.get("labels"),
                priority=arguments.get("priority"),
                due=arguments.get("due"),
            )

            # Auto-add to project if configured
            from idlergear.projects import auto_add_task_if_configured

            added_to_project = auto_add_task_if_configured(task["id"])

            # Include in response
            result = {
                "task": task,
                "added_to_project": added_to_project,
            }
            return _format_result(result)

        elif name == "idlergear_task_list":
            backend = get_backend("task")
            result = backend.list(state=arguments.get("state", "open"))
            # Filter by priority if specified
            priority = arguments.get("priority")
            if priority:
                result = [t for t in result if t.get("priority") == priority]
            # Apply limit if specified
            limit = arguments.get("limit")
            if limit:
                result = result[:limit]
            # Strip bodies if preview mode (token-efficient)
            if arguments.get("preview", False):
                for task in result:
                    task["body"] = None
            return _format_result(result)

        elif name == "idlergear_task_show":
            from idlergear.git import GitServer

            backend = get_backend("task")
            result = backend.get(arguments["id"])
            if result is None:
                raise ValueError(f"Task #{arguments['id']} not found")

            # Add test coverage info if in a git repo
            try:
                git = GitServer()
                coverage = git.get_task_test_coverage(arguments["id"])
                result["test_coverage"] = coverage
            except Exception:
                # Not in a git repo or other error - continue without coverage info
                pass

            return _format_result(result)

        elif name == "idlergear_task_close":
            backend = get_backend("task")
            result = backend.close(arguments["id"])
            if result is None:
                raise ValueError(f"Task #{arguments['id']} not found")
            return _format_result(result)

        elif name == "idlergear_task_update":
            backend = get_backend("task")
            result = backend.update(
                arguments["id"],
                title=arguments.get("title"),
                body=arguments.get("body"),
                labels=arguments.get("labels"),
                priority=arguments.get("priority"),
                due=arguments.get("due"),
            )
            if result is None:
                raise ValueError(f"Task #{arguments['id']} not found")
            return _format_result(result)

        # Note handlers (using backend)
        elif name == "idlergear_note_create":
            backend = get_backend("note")
            result = backend.create(
                arguments["content"],
                tags=arguments.get("tags"),
            )
            return _format_result(result)

        elif name == "idlergear_note_list":
            backend = get_backend("note")
            result = backend.list(tag=arguments.get("tag"))
            limit = arguments.get("limit")
            preview = arguments.get("preview", False)
            if limit and len(result) > limit:
                result = result[:limit]
            if preview:
                result = [
                    {
                        "id": n.get("id"),
                        "tags": n.get("tags", []),
                        "created": n.get("created"),
                    }
                    for n in result
                ]
            return _format_result(result)

        elif name == "idlergear_note_show":
            backend = get_backend("note")
            result = backend.get(arguments["id"])
            if result is None:
                raise ValueError(f"Note #{arguments['id']} not found")
            return _format_result(result)

        elif name == "idlergear_note_delete":
            backend = get_backend("note")
            if not backend.delete(arguments["id"]):
                raise ValueError(f"Note #{arguments['id']} not found")
            return _format_result({"deleted": True, "id": arguments["id"]})

        elif name == "idlergear_note_promote":
            backend = get_backend("note")
            result = backend.promote(arguments["id"], arguments["to"])
            if result is None:
                raise ValueError(f"Note #{arguments['id']} not found")
            return _format_result(result)

        # Vision handlers (using backend)
        elif name == "idlergear_vision_show":
            backend = get_backend("vision")
            result = backend.get()
            return _format_result({"content": result})

        elif name == "idlergear_vision_edit":
            backend = get_backend("vision")
            backend.set(arguments["content"])
            return _format_result({"updated": True})

        # Plan handlers (using backend)
        elif name == "idlergear_plan_create":
            from datetime import datetime

            from idlergear.plans import create_plan

            plan = create_plan(
                name=arguments["name"],
                description=arguments["description"],
                root=root,
                type=arguments.get("type", "feature"),
                milestone=arguments.get("milestone"),
                parent_plan=arguments.get("parent"),
                auto_archive=arguments.get("auto_archive", False),
            )
            return _format_result(plan.to_dict())

        elif name == "idlergear_plan_list":
            from idlergear.plans import list_plans

            plans = list_plans(
                root=root,
                status=arguments.get("status"),
                type_filter=arguments.get("type"),
            )
            result = [p.to_dict() for p in plans]
            return _format_result(result)

        elif name == "idlergear_plan_show":
            from idlergear.plans import load_plan

            plan = load_plan(arguments["name"], root)
            return _format_result(plan.to_dict())

        elif name == "idlergear_plan_delete":
            from idlergear.plans import delete_plan

            delete_plan(
                arguments["name"],
                root,
                permanent=arguments.get("permanent", False),
            )
            return _format_result(
                {
                    "deleted": True,
                    "name": arguments["name"],
                    "permanent": arguments.get("permanent", False),
                }
            )

        elif name == "idlergear_plan_complete":
            from datetime import datetime

            from idlergear.plans import update_plan

            plan = update_plan(
                arguments["name"],
                root,
                status="completed",
                completed_at=datetime.now().isoformat(),
            )
            return _format_result(plan.to_dict())

        # Reference handlers (using backend)
        elif name == "idlergear_reference_add":
            backend = get_backend("reference")
            result = backend.add(
                arguments["title"],
                body=arguments.get("body"),
            )
            return _format_result(result)

        elif name == "idlergear_reference_list":
            backend = get_backend("reference")
            result = backend.list()
            # Apply limit if specified
            limit = arguments.get("limit")
            if limit:
                result = result[:limit]
            # Strip bodies if preview mode (token-efficient)
            if arguments.get("preview", False):
                for ref in result:
                    ref["body"] = None
            return _format_result(result)

        elif name == "idlergear_reference_show":
            backend = get_backend("reference")
            result = backend.get(arguments["title"])
            if result is None:
                raise ValueError(f"Reference '{arguments['title']}' not found")
            return _format_result(result)

        elif name == "idlergear_reference_search":
            backend = get_backend("reference")
            result = backend.search(arguments["query"])
            return _format_result(result)

        # Run handlers
        elif name == "idlergear_run_start":
            result = start_run(
                arguments["command"],
                name=arguments.get("name"),
            )
            return _format_result(result)

        elif name == "idlergear_run_list":
            result = list_runs()
            # Apply limit if specified
            limit = arguments.get("limit")
            if limit:
                result = result[:limit]
            return _format_result(result)

        elif name == "idlergear_run_status":
            result = get_run_status(arguments["name"])
            if result is None:
                raise ValueError(f"Run '{arguments['name']}' not found")
            return _format_result(result)

        elif name == "idlergear_run_logs":
            result = get_run_logs(
                arguments["name"],
                tail=arguments.get("tail"),
                stream=arguments.get("stream", "stdout"),
            )
            if result is None:
                raise ValueError(f"Run '{arguments['name']}' not found")
            return _format_result({"logs": result})

        elif name == "idlergear_run_stop":
            if not stop_run(arguments["name"]):
                raise ValueError(
                    f"Run '{arguments['name']}' is not running or not found"
                )
            return _format_result({"stopped": True, "name": arguments["name"]})

        # Config handlers
        elif name == "idlergear_config_get":
            result = get_config_value(arguments["key"])
            return _format_result({"key": arguments["key"], "value": result})

        elif name == "idlergear_config_set":
            set_config_value(arguments["key"], arguments["value"])
            return _format_result(
                {"key": arguments["key"], "value": arguments["value"], "set": True}
            )

        # Context handler
        elif name == "idlergear_context":
            from idlergear.context import format_context_json, gather_context

            ctx = gather_context(
                include_references=arguments.get("include_refs", False),
                mode=arguments.get("mode", "minimal"),
            )
            return _format_result(format_context_json(ctx))

        # Status handler
        elif name == "idlergear_status":
            from idlergear.status import get_project_status

            status = get_project_status()
            if arguments.get("detailed", False):
                from idlergear.status import format_detailed_status

                return _format_result({"detailed": format_detailed_status(status)})
            else:
                return _format_result({"summary": status.summary(), **status.to_dict()})

        # Search handler
        elif name == "idlergear_search":
            result = search_all(
                arguments["query"],
                types=arguments.get("types"),
            )
            return _format_result(result)

        # Backend handlers
        elif name == "idlergear_backend_show":
            from idlergear.backends import (
                get_configured_backend_name,
                list_available_backends,
            )

            all_types = ["task", "note", "reference", "plan", "vision"]
            result = {}
            for t in all_types:
                result[t] = {
                    "current": get_configured_backend_name(t),
                    "available": list_available_backends(t),
                }
            return _format_result(result)

        elif name == "idlergear_backend_set":
            from idlergear.backends import list_available_backends

            backend_type = arguments["type"]
            backend_name = arguments["backend"]

            available = list_available_backends(backend_type)
            if backend_name not in available:
                raise ValueError(
                    f"Unknown backend '{backend_name}' for {backend_type}. "
                    f"Available: {', '.join(available)}"
                )

            set_config_value(f"backends.{backend_type}", backend_name)
            return _format_result(
                {
                    "type": backend_type,
                    "backend": backend_name,
                    "set": True,
                }
            )

        # Knowledge graph handlers
        elif name == "idlergear_graph_query_task":
            from idlergear.graph import get_database, query_task_context
            from idlergear.graph.schema import initialize_schema

            db = get_database()
            # Ensure schema exists
            try:
                result = query_task_context(db, arguments["task_id"])
                if not result:
                    return _format_result(
                        {
                            "error": f"Task #{arguments['task_id']} not found in graph",
                            "hint": "Run idlergear_graph_populate_git to index task history",
                        }
                    )
                return _format_result(result)
            except Exception as e:
                if "does not exist" in str(e).lower():
                    # Schema not initialized
                    initialize_schema(db)
                    return _format_result(
                        {
                            "error": "Knowledge graph not initialized",
                            "hint": "Run idlergear_graph_populate_git and idlergear_graph_populate_code to build the graph",
                        }
                    )
                raise

        elif name == "idlergear_graph_query_file":
            from idlergear.graph import get_database, query_file_context
            from idlergear.graph.schema import initialize_schema

            db = get_database()
            try:
                result = query_file_context(db, arguments["file_path"])
                if not result:
                    return _format_result(
                        {
                            "error": f"File '{arguments['file_path']}' not found in graph",
                            "hint": "Run idlergear_graph_populate_code to index files",
                        }
                    )
                return _format_result(result)
            except Exception as e:
                if "does not exist" in str(e).lower():
                    initialize_schema(db)
                    return _format_result(
                        {
                            "error": "Knowledge graph not initialized",
                            "hint": "Run idlergear_graph_populate_git and idlergear_graph_populate_code",
                        }
                    )
                raise

        elif name == "idlergear_graph_query_symbols":
            from idlergear.graph import get_database
            from idlergear.graph.queries import query_symbols_by_name
            from idlergear.graph.schema import initialize_schema

            db = get_database()
            try:
                result = query_symbols_by_name(
                    db,
                    arguments["pattern"],
                    limit=arguments.get("limit", 10),
                )
                return _format_result({"symbols": result, "count": len(result)})
            except Exception as e:
                if "does not exist" in str(e).lower():
                    initialize_schema(db)
                    return _format_result(
                        {
                            "error": "Knowledge graph not initialized",
                            "hint": "Run idlergear_graph_populate_code to index symbols",
                        }
                    )
                raise

        elif name == "idlergear_graph_populate_git":
            from idlergear.graph import get_database
            from idlergear.graph.populators import GitPopulator
            from idlergear.graph.schema import initialize_schema

            db = get_database()
            # Ensure schema exists
            try:
                from idlergear.graph.schema import get_schema_info

                get_schema_info(db)
            except Exception:
                initialize_schema(db)

            populator = GitPopulator(db)
            result = populator.populate(
                max_commits=arguments.get("max_commits", 100),
                since=arguments.get("since"),
                incremental=arguments.get("incremental", True),
            )
            return _format_result(
                {
                    "status": "completed",
                    "commits_indexed": result["commits"],
                    "files_indexed": result["files"],
                    "relationships_created": result["relationships"],
                }
            )

        elif name == "idlergear_graph_populate_code":
            from idlergear.graph import get_database
            from idlergear.graph.populators import CodePopulator
            from idlergear.graph.schema import initialize_schema

            db = get_database()
            # Ensure schema exists
            try:
                from idlergear.graph.schema import get_schema_info

                get_schema_info(db)
            except Exception:
                initialize_schema(db)

            populator = CodePopulator(db)
            result = populator.populate_directory(
                directory=arguments.get("directory", "src"),
                incremental=arguments.get("incremental", True),
            )
            return _format_result(
                {
                    "status": "completed",
                    "files_processed": result["files"],
                    "symbols_indexed": result["symbols"],
                    "relationships_created": result["relationships"],
                }
            )

        elif name == "idlergear_graph_schema_info":
            from idlergear.graph import get_database
            from idlergear.graph.schema import get_schema_info, initialize_schema

            db = get_database()
            try:
                result = get_schema_info(db)
                return _format_result(result)
            except Exception as e:
                if "does not exist" in str(e).lower():
                    initialize_schema(db)
                    result = get_schema_info(db)
                    return _format_result(result)
                raise

        elif name == "idlergear_graph_query_documentation":
            from idlergear.graph import get_database
            from idlergear.graph.schema import initialize_schema

            db = get_database()
            conn = db.get_connection()

            try:
                # Get documentation node
                doc_result = conn.execute(
                    """
                    MATCH (d:Documentation {path: $path})
                    RETURN d.path, d.title, d.body, d.source, d.created_at, d.updated_at
                """,
                    {"path": arguments["path"]},
                )

                if not doc_result.has_next():
                    return _format_result(
                        {
                            "error": f"Documentation not found: {arguments['path']}",
                            "path": arguments["path"],
                        }
                    )

                doc = doc_result.get_next()
                result = {
                    "path": doc[0],
                    "title": doc[1],
                    "body": doc[2],
                    "source": doc[3],
                    "created_at": str(doc[4]) if doc[4] else None,
                    "updated_at": str(doc[5]) if doc[5] else None,
                    "related_files": [],
                    "related_symbols": [],
                    "related_tasks": [],
                }

                # Get related files
                files_result = conn.execute(
                    """
                    MATCH (d:Documentation {path: $path})-[:DOC_DOCUMENTS_FILE]->(f:File)
                    RETURN f.path
                    LIMIT 20
                """,
                    {"path": arguments["path"]},
                )
                result["related_files"] = [r[0] for r in files_result]

                # Get related symbols
                symbols_result = conn.execute(
                    """
                    MATCH (d:Documentation {path: $path})-[:DOC_DOCUMENTS_SYMBOL]->(s:Symbol)
                    RETURN s.name, s.type, s.file_path
                    LIMIT 20
                """,
                    {"path": arguments["path"]},
                )
                result["related_symbols"] = [
                    {"name": r[0], "type": r[1], "file": r[2]} for r in symbols_result
                ]

                # Get related tasks
                tasks_result = conn.execute(
                    """
                    MATCH (d:Documentation {path: $path})-[:DOC_REFERENCES_TASK]->(t:Task)
                    RETURN t.id, t.title, t.state
                    LIMIT 10
                """,
                    {"path": arguments["path"]},
                )
                result["related_tasks"] = [
                    {"id": r[0], "title": r[1], "state": r[2]} for r in tasks_result
                ]

                return _format_result(result)
            except Exception as e:
                if "does not exist" in str(e).lower():
                    return _format_result(
                        {
                            "error": "Knowledge graph not populated. Run idlergear_graph_populate_all() first."
                        }
                    )
                raise

        elif name == "idlergear_graph_search_documentation":
            from idlergear.graph import get_database
            from idlergear.graph.schema import initialize_schema

            db = get_database()
            conn = db.get_connection()
            limit = arguments.get("limit", 10)

            try:
                # Search documentation by title or body
                result = conn.execute(
                    """
                    MATCH (d:Documentation)
                    WHERE d.title CONTAINS $query OR d.body CONTAINS $query
                    RETURN d.path, d.title, d.source
                    LIMIT $limit
                """,
                    {"query": arguments["query"], "limit": limit},
                )

                docs = []
                for record in result:
                    docs.append(
                        {"path": record[0], "title": record[1], "source": record[2]}
                    )

                return _format_result(
                    {"query": arguments["query"], "count": len(docs), "documents": docs}
                )
            except Exception as e:
                if "does not exist" in str(e).lower():
                    return _format_result(
                        {
                            "error": "Knowledge graph not populated. Run idlergear_graph_populate_all() first."
                        }
                    )
                raise

        elif name == "idlergear_graph_populate_all":
            from idlergear.graph import populate_all

            max_commits = arguments.get("max_commits", 100)
            incremental = arguments.get("incremental", True)

            result = populate_all(
                max_commits=max_commits, incremental=incremental, verbose=False
            )

            return _format_result(result)

        # Advanced graph query handlers (Issue #335)
        elif name == "idlergear_graph_impact_analysis":
            from idlergear.graph import get_database
            from idlergear.graph.queries import query_impact_analysis

            db = get_database()
            result = query_impact_analysis(db, arguments["symbol_name"])
            return _format_result(result)

        elif name == "idlergear_graph_test_coverage":
            from idlergear.graph import get_database
            from idlergear.graph.queries import query_test_coverage

            db = get_database()
            result = query_test_coverage(
                db, arguments["target"], arguments.get("target_type", "file")
            )
            return _format_result(result)

        elif name == "idlergear_graph_change_history":
            from idlergear.graph import get_database
            from idlergear.graph.queries import query_change_history

            db = get_database()
            result = query_change_history(db, arguments["symbol_name"])
            return _format_result(
                {"symbol": arguments["symbol_name"], "commits": result}
            )

        elif name == "idlergear_graph_dependency_chain":
            from idlergear.graph import get_database
            from idlergear.graph.queries import query_dependency_chain

            db = get_database()
            result = query_dependency_chain(
                db, arguments["file_path"], arguments.get("max_depth", 5)
            )
            return _format_result(result)

        elif name == "idlergear_graph_orphan_detection":
            from idlergear.graph import get_database
            from idlergear.graph.queries import query_orphan_detection

            db = get_database()
            result = query_orphan_detection(db)
            return _format_result(result)

        elif name == "idlergear_graph_symbol_callers":
            from idlergear.graph import get_database
            from idlergear.graph.queries import query_symbol_callers

            db = get_database()
            result = query_symbol_callers(db, arguments["symbol_name"])
            return _format_result(result)

        elif name == "idlergear_graph_file_timeline":
            from idlergear.graph import get_database
            from idlergear.graph.queries import query_file_timeline

            db = get_database()
            result = query_file_timeline(
                db, arguments["file_path"], arguments.get("limit", 20)
            )
            return _format_result(result)

        elif name == "idlergear_graph_task_coverage":
            from idlergear.graph import get_database
            from idlergear.graph.queries import query_task_coverage

            db = get_database()
            result = query_task_coverage(db)
            return _format_result(result)

        # Graph visualization handlers
        elif name == "idlergear_graph_visualize_export":
            from idlergear.graph import get_database
            from idlergear.graph.visualize import GraphVisualizer
            from pathlib import Path

            output_path = Path(arguments.get("output_path"))
            format = arguments.get("format")
            node_types = arguments.get("node_types")
            relationship_types = arguments.get("relationship_types")
            max_nodes = arguments.get("max_nodes", 1000)
            d3_format = arguments.get("d3_format", False)
            layout = arguments.get("layout", "dot")

            # Auto-detect format from extension if not specified
            if format is None:
                suffix = output_path.suffix.lower()
                if suffix == ".graphml":
                    format = "graphml"
                elif suffix == ".dot":
                    format = "dot"
                elif suffix == ".json":
                    format = "json"
                else:
                    raise ValueError(
                        f"Unknown file extension: {suffix}. Please specify format parameter."
                    )

            db = get_database()
            viz = GraphVisualizer(db)

            # Export based on format
            if format == "graphml":
                result = viz.export_graphml(
                    output_path, node_types, relationship_types, max_nodes
                )
            elif format == "dot":
                result = viz.export_dot(
                    output_path, node_types, relationship_types, max_nodes, layout
                )
            elif format == "json":
                json_format = "d3" if d3_format else "raw"
                result = viz.export_json(
                    output_path, node_types, relationship_types, max_nodes, json_format
                )
            else:
                raise ValueError(f"Unknown format: {format}")

            return _format_result(result)

        elif name == "idlergear_graph_visualize_task":
            from idlergear.graph import get_database
            from idlergear.graph.visualize import GraphVisualizer
            from pathlib import Path

            task_id = arguments.get("task_id")
            output_path = Path(arguments.get("output_path"))
            depth = arguments.get("depth", 2)
            format = arguments.get("format", "dot")

            db = get_database()
            viz = GraphVisualizer(db)

            result = viz.visualize_task_network(task_id, output_path, depth, format)
            return _format_result(result)

        elif name == "idlergear_graph_visualize_deps":
            from idlergear.graph import get_database
            from idlergear.graph.visualize import GraphVisualizer
            from pathlib import Path

            file_path = arguments.get("file_path")
            output_path = Path(arguments.get("output_path"))
            depth = arguments.get("depth", 2)
            format = arguments.get("format", "dot")

            db = get_database()
            viz = GraphVisualizer(db)

            result = viz.visualize_dependency_graph(
                file_path, output_path, depth, format
            )
            return _format_result(result)

        # Server management handlers
        elif name == "idlergear_version":
            return _format_result(
                {
                    "version": __version__,
                    "pid": os.getpid(),
                    "python": sys.executable,
                }
            )

        elif name == "idlergear_reload":
            import threading
            import time

            def delayed_reload():
                """Send reload signal after a short delay to allow response to be sent."""
                time.sleep(0.1)  # Wait for response to be flushed
                if hasattr(signal, "SIGUSR1"):
                    os.kill(os.getpid(), signal.SIGUSR1)

            # Start delayed reload in background thread
            threading.Thread(target=delayed_reload, daemon=True).start()

            return _format_result(
                {
                    "status": "reload_triggered",
                    "message": "MCP server will reload in 100ms. The new version will be active for subsequent tool calls.",
                    "current_version": __version__,
                    "pid": os.getpid(),
                }
            )

        # Project handlers
        elif name == "idlergear_project_create":
            result = create_project(
                arguments["title"],
                columns=arguments.get("columns"),
                create_on_github=arguments.get("create_on_github", False),
            )
            return _format_result(result)

        elif name == "idlergear_project_list":
            projects = list_projects()
            result = {"projects": projects}
            if arguments.get("include_github"):
                result["github_projects"] = list_github_projects()
            return _format_result(result)

        elif name == "idlergear_project_show":
            result = get_project(arguments["name"])
            if result is None:
                raise ValueError(f"Project '{arguments['name']}' not found")
            return _format_result(result)

        elif name == "idlergear_project_delete":
            if not delete_project(
                arguments["name"],
                delete_on_github=arguments.get("delete_on_github", False),
            ):
                raise ValueError(f"Project '{arguments['name']}' not found")
            return _format_result({"deleted": True, "name": arguments["name"]})

        elif name == "idlergear_project_add_task":
            result = add_task_to_project(
                arguments["project_name"],
                arguments["task_id"],
                column=arguments.get("column"),
            )
            if result is None:
                raise ValueError(f"Project '{arguments['project_name']}' not found")
            return _format_result(result)

        elif name == "idlergear_project_remove_task":
            result = remove_task_from_project(
                arguments["project_name"],
                arguments["task_id"],
            )
            if result is None:
                raise ValueError(f"Project '{arguments['project_name']}' not found")
            return _format_result(result)

        elif name == "idlergear_project_move_task":
            result = move_task(
                arguments["project_name"],
                arguments["task_id"],
                arguments["column"],
            )
            if result is None:
                raise ValueError(f"Project '{arguments['project_name']}' not found")
            return _format_result(result)

        elif name == "idlergear_project_sync":
            result = sync_project_to_github(arguments["name"])
            if result is None:
                raise ValueError(f"Project '{arguments['name']}' not found")
            return _format_result(result)

        elif name == "idlergear_project_link":
            result = link_to_github_project(
                arguments["name"],
                arguments["github_project_number"],
            )
            if result is None:
                raise ValueError(f"Project '{arguments['name']}' not found")
            return _format_result(result)

        elif name == "idlergear_project_sync_fields":
            from idlergear.projects import sync_task_fields_to_github
            from idlergear.tasks import get_task

            task_id = arguments["task_id"]
            task = get_task(task_id)
            if task is None:
                raise ValueError(f"Task {task_id} not found")

            success = sync_task_fields_to_github(task_id, task)
            if success:
                return _format_result(
                    {
                        "success": True,
                        "message": f"Synced fields for task {task_id} to GitHub Projects",
                    }
                )
            else:
                return _format_result(
                    {
                        "success": False,
                        "message": f"Could not sync fields for task {task_id}. Check configuration and project setup.",
                    }
                )

        elif name == "idlergear_project_pull":
            from idlergear.projects import pull_project_from_github

            result = pull_project_from_github(arguments["name"])
            return _format_result(result)

        # Daemon coordination handlers
        elif name == "idlergear_daemon_register_agent":
            from idlergear.daemon.mcp_handlers import handle_register_agent

            result = handle_register_agent(arguments)
            # Store the agent_id for use in message operations
            if "agent_id" in result:
                _registered_agent_id = result["agent_id"]
            return _format_result(result)

        elif name == "idlergear_daemon_list_agents":
            from idlergear.daemon.mcp_handlers import handle_list_agents

            result = handle_list_agents()
            return _format_result(result)

        elif name == "idlergear_daemon_queue_command":
            from idlergear.daemon.mcp_handlers import handle_queue_command

            result = handle_queue_command(arguments)
            return _format_result(result)

        elif name == "idlergear_daemon_broadcast":
            from idlergear.daemon.mcp_handlers import handle_send_message

            result = handle_send_message(arguments)
            return _format_result(result)

        elif name == "idlergear_daemon_update_status":
            from idlergear.daemon.mcp_handlers import handle_update_status

            result = handle_update_status(arguments)
            return _format_result(result)

        elif name == "idlergear_daemon_list_queue":
            from idlergear.daemon.mcp_handlers import handle_list_queue

            result = handle_list_queue()
            return _format_result(result)

        # Session monitoring handlers (for multi-client coordination)
        elif name == "idlergear_session_notify_start":
            from idlergear.daemon.mcp_handlers import handle_session_notify_start

            result = handle_session_notify_start(arguments)
            return _format_result(result)

        elif name == "idlergear_session_notify_end":
            from idlergear.daemon.mcp_handlers import handle_session_notify_end

            result = handle_session_notify_end(arguments)
            return _format_result(result)

        elif name == "idlergear_session_list_active":
            from idlergear.daemon.mcp_handlers import handle_session_list_active

            result = handle_session_list_active()
            return _format_result(result)

        elif name == "idlergear_session_get_agent_status":
            from idlergear.daemon.mcp_handlers import handle_session_get_agent_status

            result = handle_session_get_agent_status(arguments)
            return _format_result(result)

        # Cross-agent messaging handlers (inbox-based)
        elif name == "idlergear_message_send":
            from idlergear.messaging import send_message

            root = find_idlergear_root()
            if not root:
                raise ValueError("IdlerGear not initialized")
            idlergear_dir = root / ".idlergear"

            # Auto-detect from_agent if not provided
            from_agent = arguments.get("from_agent")
            if not from_agent:
                # Use registered agent_id if available
                from_agent = _registered_agent_id
            if not from_agent:
                # Fallback: try to find from presence files
                agents_dir = idlergear_dir / "agents"
                if agents_dir.exists():
                    for f in agents_dir.glob("*.json"):
                        if f.name != "agents.json":
                            from_agent = f.stem
                            break

            result = send_message(
                idlergear_dir,
                to_agent=arguments["to_agent"],
                message=arguments["message"],
                from_agent=from_agent,
                delivery=arguments.get("delivery"),
                message_type=arguments.get("message_type", "info"),
                action_requested=arguments.get("action_requested", False),
                context=arguments.get("context"),
            )
            return _format_result(result)

        elif name == "idlergear_message_process":
            from idlergear.messaging import process_inbox, format_context_for_injection

            root = find_idlergear_root()
            if not root:
                raise ValueError("IdlerGear not initialized")
            idlergear_dir = root / ".idlergear"

            # Auto-detect agent_id
            agent_id = arguments.get("agent_id")
            if not agent_id:
                # Use registered agent_id if available
                agent_id = _registered_agent_id
            if not agent_id:
                # Fallback: try to find from presence files
                agents_dir = idlergear_dir / "agents"
                if agents_dir.exists():
                    for f in agents_dir.glob("*.json"):
                        if f.name != "agents.json":
                            agent_id = f.stem
                            break
            if not agent_id:
                return _format_result(
                    {
                        "error": "No agent_id provided or detected. Call idlergear_daemon_register_agent first."
                    }
                )

            # Create task callback if requested
            should_create_tasks = arguments.get("create_tasks", True)
            task_callback = None
            if should_create_tasks:
                from idlergear.tasks import create_task as _create_task_for_callback

                def task_callback(title: str, body: str, labels: list[str]) -> int:
                    task = _create_task_for_callback(
                        title, body=body, labels=labels, project_path=root
                    )
                    return task.get("id") if isinstance(task, dict) else task.id

            # Process inbox
            results = process_inbox(idlergear_dir, agent_id, task_callback)

            # Format context messages for injection
            context_text = ""
            if results["context"]:
                context_text = format_context_for_injection(results["context"])

            return _format_result(
                {
                    "agent_id": agent_id,
                    "context_count": len(results["context"]),
                    "context_messages": context_text,
                    "tasks_created": results["tasks_created"],
                    "queued_for_review": results["queued"],
                    "errors": results["errors"],
                    "note": "Context messages returned for immediate handling. Notification messages converted to tasks."
                    if results["context"]
                    else "No context messages. Notification messages converted to tasks.",
                }
            )

        elif name == "idlergear_message_list":
            from idlergear.messaging import (
                list_messages,
                get_inbox_summary,
                _get_delivery_type,
            )

            root = find_idlergear_root()
            if not root:
                raise ValueError("IdlerGear not initialized")
            idlergear_dir = root / ".idlergear"
            agent_id = arguments.get("agent_id")
            if not agent_id:
                # Use registered agent_id if available
                agent_id = _registered_agent_id
            if not agent_id:
                # Fallback: try to find agent_id from presence files
                agents_dir = idlergear_dir / "agents"
                if agents_dir.exists():
                    for f in agents_dir.glob("*.json"):
                        if f.name != "agents.json":
                            agent_id = f.stem
                            break
            if not agent_id:
                return _format_result(
                    {
                        "messages": [],
                        "note": "No agent_id provided or detected. Call idlergear_daemon_register_agent first.",
                    }
                )

            unread_only = arguments.get("unread_only", True)
            messages = list_messages(idlergear_dir, agent_id, unread_only=unread_only)

            # Filter by delivery type if specified
            delivery_filter = arguments.get("delivery")
            if delivery_filter:
                messages = [
                    m for m in messages if _get_delivery_type(m) == delivery_filter
                ]

            # Apply limit
            limit = arguments.get("limit")
            if limit and len(messages) > limit:
                messages = messages[:limit]

            # Apply preview mode
            preview = arguments.get("preview", False)
            if preview:
                messages = [
                    {
                        "id": m.get("id"),
                        "from": m.get("from"),
                        "delivery": _get_delivery_type(m),
                        "timestamp": m.get("timestamp"),
                        "read": m.get("read", False),
                    }
                    for m in messages
                ]

            summary = get_inbox_summary(idlergear_dir, agent_id)
            return _format_result(
                {
                    "messages": messages,
                    "summary": summary,
                    "agent_id": agent_id,
                }
            )

        elif name == "idlergear_message_mark_read":
            from idlergear.messaging import mark_as_read

            root = find_idlergear_root()
            if not root:
                raise ValueError("IdlerGear not initialized")
            idlergear_dir = root / ".idlergear"
            agent_id = arguments.get("agent_id")
            if not agent_id:
                # Use registered agent_id if available
                agent_id = _registered_agent_id
            if not agent_id:
                raise ValueError(
                    "agent_id is required. Call idlergear_daemon_register_agent first."
                )
            message_ids = arguments.get("message_ids")
            count = mark_as_read(idlergear_dir, agent_id, message_ids)
            return _format_result({"marked_read": count})

        elif name == "idlergear_message_clear":
            from idlergear.messaging import clear_inbox

            root = find_idlergear_root()
            if not root:
                raise ValueError("IdlerGear not initialized")
            idlergear_dir = root / ".idlergear"
            agent_id = arguments.get("agent_id")
            if not agent_id:
                # Use registered agent_id if available
                agent_id = _registered_agent_id
            if not agent_id:
                raise ValueError(
                    "agent_id is required. Call idlergear_daemon_register_agent first."
                )
            read_only = not arguments.get("all_messages", False)
            count = clear_inbox(idlergear_dir, agent_id, read_only=read_only)
            return _format_result({"cleared": count})

        elif name == "idlergear_message_test":
            # Test messaging round-trip: send to self, then retrieve
            from datetime import datetime, timezone
            from idlergear.messaging import (
                send_message,
                list_messages,
                mark_as_read,
                get_inbox_summary,
            )

            root = find_idlergear_root()
            if not root:
                raise ValueError("IdlerGear not initialized")
            idlergear_dir = root / ".idlergear"

            # Step 1: Use registered agent_id or detect from presence files
            agent_id = _registered_agent_id
            if not agent_id:
                # Fallback: try to find from presence files
                agents_dir = idlergear_dir / "agents"
                if agents_dir.exists():
                    for f in agents_dir.glob("*.json"):
                        if f.name != "agents.json":
                            agent_id = f.stem
                            break

            if not agent_id:
                return _format_result(
                    {
                        "success": False,
                        "error": "No agent registered. Call idlergear_daemon_register_agent first.",
                    }
                )

            # Step 2: Create test message
            test_content = arguments.get("test_message")
            if not test_content:
                timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                test_content = f"[TEST] Self-test message sent at {timestamp}"

            # Step 3: Send message to self using send_message()
            send_result = send_message(
                idlergear_dir,
                to_agent=agent_id,
                message=test_content,
                from_agent=agent_id,  # From self
                metadata={"test": True, "purpose": "messaging_self_test"},
            )

            # Step 4: Retrieve messages using list_messages()
            messages = list_messages(
                idlergear_dir, agent_id, unread_only=False, limit=10
            )

            # Step 5: Find our test message
            test_message_found = None
            for msg in messages:
                if msg.get("id") == send_result["message_id"]:
                    test_message_found = msg
                    break

            # Step 6: Get inbox summary using get_inbox_summary()
            summary = get_inbox_summary(idlergear_dir, agent_id)

            # Step 7: Mark test message as read using mark_as_read()
            if test_message_found:
                marked = mark_as_read(
                    idlergear_dir, agent_id, [send_result["message_id"]]
                )
            else:
                marked = 0

            # Return comprehensive results
            return _format_result(
                {
                    "success": test_message_found is not None,
                    "agent_id": agent_id,
                    "steps": {
                        "1_send": {
                            "function": "send_message()",
                            "result": send_result,
                        },
                        "2_list": {
                            "function": "list_messages()",
                            "messages_retrieved": len(messages),
                            "test_message_found": test_message_found is not None,
                        },
                        "3_summary": {
                            "function": "get_inbox_summary()",
                            "result": summary,
                        },
                        "4_mark_read": {
                            "function": "mark_as_read()",
                            "marked_count": marked,
                        },
                    },
                    "test_message": test_message_found,
                    "note": "All messaging functions exercised successfully"
                    if test_message_found
                    else "Test message not found after sending",
                }
            )

        # Script generation handlers
        elif name == "idlergear_generate_dev_script":
            from idlergear.daemon.script_handlers import handle_generate_script

            result = handle_generate_script(arguments)
            return _format_result(result)

        elif name == "idlergear_list_script_templates":
            from idlergear.daemon.script_handlers import handle_list_templates

            result = handle_list_templates()
            return _format_result(result)

        elif name == "idlergear_get_script_template":
            from idlergear.daemon.script_handlers import handle_get_template

            result = handle_get_template(arguments)
            return _format_result(result)

        # Environment detection handlers
        elif name == "idlergear_env_info":
            result = get_environment_info()
            return _format_result(result)

        elif name == "idlergear_env_which":
            result = which_enhanced(arguments["command"])
            return _format_result(result)

        elif name == "idlergear_env_detect":
            from pathlib import Path

            path = Path(arguments["path"]) if arguments.get("path") else None
            result = detect_project_type(path)
            return _format_result(result)

        elif name == "idlergear_env_find_venv":
            from pathlib import Path

            path = Path(arguments["path"]) if arguments.get("path") else None
            result = find_virtualenv(path)
            if result is None:
                result = {"found": False, "message": "No virtual environment detected"}
            return _format_result(result)

        elif name == "idlergear_env_active":
            # Show currently active environments (Python, Rust, .NET)
            import os
            import sys

            environments = []

            # Python environment
            python_env = {
                "language": "python",
                "executable": sys.executable,
                "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            }

            # Check if we're in a virtualenv
            if os.environ.get("VIRTUAL_ENV"):
                python_env["active"] = True
                python_env["type"] = "venv"
                python_env["path"] = os.environ["VIRTUAL_ENV"]
                python_env["activated_by"] = "idlergear"
            elif hasattr(sys, "real_prefix") or (
                hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
            ):
                # Running in a venv but VIRTUAL_ENV not set
                python_env["active"] = True
                python_env["type"] = "venv"
                python_env["path"] = sys.prefix
                python_env["activated_by"] = "external"
            else:
                python_env["active"] = False

            environments.append(python_env)

            # Rust environment
            if os.environ.get("RUSTUP_TOOLCHAIN"):
                rust_env = {
                    "language": "rust",
                    "active": True,
                    "toolchain": os.environ["RUSTUP_TOOLCHAIN"],
                    "activated_by": "idlergear",
                }
                environments.append(rust_env)

            # .NET environment (check if dotnet is available)
            import shutil

            if shutil.which("dotnet"):
                dotnet_env = {
                    "language": "dotnet",
                    "active": True,
                    "note": "dotnet CLI will automatically use SDK version from global.json if present",
                }
                # Try to get dotnet version
                try:
                    import subprocess

                    result = subprocess.run(
                        ["dotnet", "--version"],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    if result.returncode == 0:
                        dotnet_env["version"] = result.stdout.strip()
                except Exception:
                    pass

                environments.append(dotnet_env)

            result = {
                "environments": environments,
                "count": len(environments),
            }

            return _format_result(result)

        # Filesystem handlers
        elif name == "idlergear_fs_read_file":
            # Check file registry before reading
            file_path = arguments["path"]
            allow_override = arguments.get("_allow_deprecated", False)
            allowed, warning = _check_file_access(file_path, "read", allow_override)

            if not allowed:
                # Block access to deprecated/archived/problematic files
                raise ValueError(warning)

            fs = _get_fs_server()
            result = fs.read_file(file_path)

            # If there was a warning (e.g., write to deprecated), include it
            if warning:
                result["warning"] = warning

            return _format_result(result)

        elif name == "idlergear_fs_read_multiple":
            # Check each file before reading
            paths = arguments["paths"]
            allow_override = arguments.get("_allow_deprecated", False)
            blocked_files = []

            for path in paths:
                allowed, warning = _check_file_access(path, "read", allow_override)
                if not allowed:
                    blocked_files.append({"path": path, "reason": warning})

            if blocked_files:
                error_msg = "Some files are blocked:\n"
                for blocked in blocked_files:
                    error_msg += f"  - {blocked['path']}: {blocked['reason']}\n"
                raise ValueError(error_msg)

            fs = _get_fs_server()
            result = fs.read_multiple_files(paths)
            return _format_result(result)

        elif name == "idlergear_fs_write_file":
            # Check file registry (warn but allow writes to deprecated files)
            file_path = arguments["path"]
            allow_override = arguments.get("_allow_deprecated", False)
            allowed, warning = _check_file_access(file_path, "write", allow_override)

            fs = _get_fs_server()
            result = fs.write_file(file_path, arguments["content"])

            # Include warning if present
            if warning and isinstance(result, dict):
                result["warning"] = warning

            return _format_result(result)

        elif name == "idlergear_fs_create_directory":
            fs = _get_fs_server()
            result = fs.create_directory(arguments["path"])
            return _format_result(result)

        elif name == "idlergear_fs_list_directory":
            fs = _get_fs_server()
            result = fs.list_directory(
                path=arguments.get("path", "."),
                exclude_patterns=arguments.get("exclude_patterns"),
            )
            return _format_result(result)

        elif name == "idlergear_fs_directory_tree":
            fs = _get_fs_server()
            result = fs.directory_tree(
                path=arguments.get("path", "."),
                max_depth=arguments.get("max_depth", 3),
                exclude_patterns=arguments.get("exclude_patterns"),
            )
            return _format_result(result)

        elif name == "idlergear_fs_move_file":
            # Check source file before moving
            source = arguments["source"]
            allow_override = arguments.get("_allow_deprecated", False)
            allowed, warning = _check_file_access(source, "read", allow_override)

            if not allowed:
                raise ValueError(f"Cannot move file: {warning}")

            fs = _get_fs_server()
            result = fs.move_file(source, arguments["destination"])

            if warning and isinstance(result, dict):
                result["warning"] = warning

            return _format_result(result)

        elif name == "idlergear_fs_search_files":
            fs = _get_fs_server()
            result = fs.search_files(
                path=arguments.get("path", "."),
                pattern=arguments.get("pattern", "*"),
                exclude_patterns=arguments.get("exclude_patterns"),
                use_gitignore=arguments.get("use_gitignore", True),
            )
            return _format_result(result)

        elif name == "idlergear_fs_file_info":
            fs = _get_fs_server()
            result = fs.get_file_info(arguments["path"])
            return _format_result(result)

        elif name == "idlergear_fs_file_checksum":
            fs = _get_fs_server()
            result = fs.get_file_checksum(
                path=arguments["path"], algorithm=arguments.get("algorithm", "sha256")
            )
            return _format_result(result)

        elif name == "idlergear_fs_allowed_directories":
            fs = _get_fs_server()
            result = fs.list_allowed_directories()
            return _format_result(result)

        # Git handlers
        elif name == "idlergear_git_status":
            git = _get_git_server()
            status = git.status(repo_path=arguments.get("repo_path"))
            return _format_result(
                {
                    "branch": status.branch,
                    "ahead": status.ahead,
                    "behind": status.behind,
                    "staged": status.staged,
                    "modified": status.modified,
                    "untracked": status.untracked,
                    "conflicts": status.conflicts,
                    "last_commit": status.last_commit,
                }
            )

        elif name == "idlergear_git_diff":
            git = _get_git_server()
            result = git.diff(
                repo_path=arguments.get("repo_path"),
                staged=arguments.get("staged", False),
                files=arguments.get("files"),
                context_lines=arguments.get("context_lines", 3),
            )
            return _format_result({"diff": result})

        elif name == "idlergear_git_log":
            git = _get_git_server()
            commits = git.log(
                repo_path=arguments.get("repo_path"),
                max_count=arguments.get("max_count", 10),
                since=arguments.get("since"),
                until=arguments.get("until"),
                author=arguments.get("author"),
                grep=arguments.get("grep"),
            )
            return _format_result(
                {
                    "commits": [
                        {
                            "hash": c.hash,
                            "short_hash": c.short_hash,
                            "author": c.author,
                            "email": c.email,
                            "date": c.date,
                            "message": c.message,
                            "files": c.files,
                        }
                        for c in commits
                    ]
                }
            )

        elif name == "idlergear_git_add":
            git = _get_git_server()
            result = git.add(
                files=arguments["files"],
                repo_path=arguments.get("repo_path"),
                all=arguments.get("all", False),
            )
            return _format_result({"message": result})

        elif name == "idlergear_git_commit":
            git = _get_git_server()
            commit_hash = git.commit(
                message=arguments["message"],
                repo_path=arguments.get("repo_path"),
                task_id=arguments.get("task_id"),
            )
            return _format_result(
                {"commit_hash": commit_hash, "message": arguments["message"]}
            )

        elif name == "idlergear_git_reset":
            git = _get_git_server()
            result = git.reset(
                files=arguments.get("files"),
                repo_path=arguments.get("repo_path"),
                hard=arguments.get("hard", False),
            )
            return _format_result({"message": result})

        elif name == "idlergear_git_show":
            git = _get_git_server()
            result = git.show(
                commit=arguments["commit"],
                repo_path=arguments.get("repo_path"),
            )
            return _format_result(result)

        elif name == "idlergear_git_branch_list":
            git = _get_git_server()
            branches = git.branch_list(repo_path=arguments.get("repo_path"))
            return _format_result({"branches": branches})

        elif name == "idlergear_git_branch_create":
            git = _get_git_server()
            result = git.branch_create(
                name=arguments["name"],
                repo_path=arguments.get("repo_path"),
                checkout=arguments.get("checkout", True),
            )
            return _format_result({"message": result})

        elif name == "idlergear_git_branch_checkout":
            git = _get_git_server()
            result = git.branch_checkout(
                name=arguments["name"],
                repo_path=arguments.get("repo_path"),
            )
            return _format_result({"message": result})

        elif name == "idlergear_git_branch_delete":
            git = _get_git_server()
            result = git.branch_delete(
                name=arguments["name"],
                repo_path=arguments.get("repo_path"),
                force=arguments.get("force", False),
            )
            return _format_result({"message": result})

        # IdlerGear-specific git+task integration handlers
        elif name == "idlergear_git_commit_task":
            git = _get_git_server()
            commit_hash = git.commit_task(
                task_id=arguments["task_id"],
                message=arguments["message"],
                repo_path=arguments.get("repo_path"),
                auto_add=arguments.get("auto_add", True),
            )
            return _format_result(
                {
                    "commit_hash": commit_hash,
                    "task_id": arguments["task_id"],
                    "message": arguments["message"],
                }
            )

        elif name == "idlergear_git_status_for_task":
            git = _get_git_server()
            result = git.status_for_task(
                task_id=arguments["task_id"],
                repo_path=arguments.get("repo_path"),
            )
            return _format_result(result)

        elif name == "idlergear_git_task_commits":
            git = _get_git_server()
            commits = git.task_commits(
                task_id=arguments["task_id"],
                repo_path=arguments.get("repo_path"),
                max_count=arguments.get("max_count", 50),
            )
            return _format_result(
                {
                    "task_id": arguments["task_id"],
                    "commits": [
                        {
                            "hash": c.hash,
                            "short_hash": c.short_hash,
                            "author": c.author,
                            "email": c.email,
                            "date": c.date,
                            "message": c.message,
                            "files": c.files,
                        }
                        for c in commits
                    ],
                }
            )

        elif name == "idlergear_git_sync_tasks":
            git = _get_git_server()
            result = git.sync_tasks_from_commits(
                repo_path=arguments.get("repo_path"),
                since=arguments.get("since"),
            )
            return _format_result(result)

        # === Process Management Tools ===
        elif name == "idlergear_pm_list_processes":
            pm = _get_pm_server()
            processes = pm.list_processes(
                filter_name=arguments.get("filter_name"),
                filter_user=arguments.get("filter_user"),
                sort_by=arguments.get("sort_by", "cpu"),
            )
            return _format_result(processes)

        elif name == "idlergear_pm_get_process":
            pm = _get_pm_server()
            process = pm.get_process(arguments["pid"])
            if process is None:
                return [
                    TextContent(
                        type="text", text=f"Process not found: {arguments['pid']}"
                    )
                ]
            return _format_result(process)

        elif name == "idlergear_pm_kill_process":
            pm = _get_pm_server()
            success = pm.kill_process(
                arguments["pid"],
                force=arguments.get("force", False),
            )
            return _format_result({"success": success, "pid": arguments["pid"]})

        elif name == "idlergear_pm_system_info":
            pm = _get_pm_server()
            info = pm.system_info()
            return _format_result(info)

        elif name == "idlergear_pm_start_run":
            pm = _get_pm_server()
            run_data = pm.start_run(
                command=arguments["command"],
                name=arguments.get("name"),
                task_id=arguments.get("task_id"),
            )
            return _format_result(run_data)

        elif name == "idlergear_pm_list_runs":
            pm = _get_pm_server()
            runs_list = pm.list_runs()
            return _format_result(runs_list)

        elif name == "idlergear_pm_get_run_status":
            pm = _get_pm_server()
            status = pm.get_run_status(arguments["name"])
            if status is None:
                return [
                    TextContent(type="text", text=f"Run not found: {arguments['name']}")
                ]
            return _format_result(status)

        elif name == "idlergear_pm_get_run_logs":
            pm = _get_pm_server()
            logs = pm.get_run_logs(
                name=arguments["name"],
                tail=arguments.get("tail"),
                stream=arguments.get("stream", "stdout"),
            )
            if logs is None:
                return [
                    TextContent(type="text", text=f"Run not found: {arguments['name']}")
                ]
            return [TextContent(type="text", text=logs)]

        elif name == "idlergear_pm_stop_run":
            pm = _get_pm_server()
            success = pm.stop_run(arguments["name"])
            return _format_result({"success": success, "name": arguments["name"]})

        elif name == "idlergear_pm_task_runs":
            pm = _get_pm_server()
            runs_list = pm.task_runs(arguments["task_id"])
            return _format_result(runs_list)

        elif name == "idlergear_pm_quick_start":
            pm = _get_pm_server()
            process = pm.quick_start(
                executable=arguments["executable"],
                args=arguments.get("args"),
            )
            return _format_result(process)

        # === Tmux Session Management Tools ===
        elif name == "idlergear_tmux_create_session":
            pm = _get_pm_server()
            try:
                session_info = pm.create_tmux_session(
                    name=arguments["name"],
                    command=arguments.get("command"),
                    window_name=arguments.get("window_name"),
                )
                return _format_result(session_info)
            except (RuntimeError, ValueError) as e:
                return [
                    TextContent(type="text", text=f"Error creating tmux session: {e}")
                ]

        elif name == "idlergear_tmux_list_sessions":
            pm = _get_pm_server()
            sessions = pm.list_tmux_sessions()
            return _format_result(sessions)

        elif name == "idlergear_tmux_get_session":
            pm = _get_pm_server()
            session = pm.get_tmux_session(arguments["name"])
            if session is None:
                return [
                    TextContent(
                        type="text", text=f"Tmux session not found: {arguments['name']}"
                    )
                ]
            return _format_result(session)

        elif name == "idlergear_tmux_kill_session":
            pm = _get_pm_server()
            success = pm.kill_tmux_session(arguments["name"])
            return _format_result({"success": success, "name": arguments["name"]})

        elif name == "idlergear_tmux_send_keys":
            pm = _get_pm_server()
            success = pm.send_keys_to_tmux(
                session_name=arguments["session_name"],
                keys=arguments["keys"],
                window_index=arguments.get("window_index", 0),
                pane_index=arguments.get("pane_index", 0),
            )
            return _format_result(
                {"success": success, "session": arguments["session_name"]}
            )

        elif name == "idlergear_run_attach":
            from idlergear.runs import attach_to_run

            try:
                result = attach_to_run(arguments["name"])
                return _format_result(result)
            except RuntimeError as e:
                return [TextContent(type="text", text=f"Error: {e}")]

        # === Container Management Tool Handlers (Podman/Docker) ===
        elif name == "idlergear_container_list":
            pm = _get_pm_server()
            containers = pm.list_containers(all_containers=arguments.get("all", False))
            return _format_result(containers)

        elif name == "idlergear_container_start":
            pm = _get_pm_server()
            try:
                container_info = pm.start_container(
                    image=arguments["image"],
                    name=arguments.get("name"),
                    command=arguments.get("command"),
                    env=arguments.get("env"),
                    volumes=arguments.get("volumes"),
                    ports=arguments.get("ports"),
                    memory=arguments.get("memory"),
                    cpus=arguments.get("cpus"),
                    detach=arguments.get("detach", True),
                )
                return _format_result(container_info)
            except RuntimeError as e:
                return [TextContent(type="text", text=f"Error starting container: {e}")]

        elif name == "idlergear_container_stop":
            pm = _get_pm_server()
            success = pm.stop_container(
                container_id=arguments["container_id"],
                force=arguments.get("force", False),
            )
            return _format_result(
                {"success": success, "container_id": arguments["container_id"]}
            )

        elif name == "idlergear_container_remove":
            pm = _get_pm_server()
            success = pm.remove_container(
                container_id=arguments["container_id"],
                force=arguments.get("force", False),
            )
            return _format_result(
                {"success": success, "container_id": arguments["container_id"]}
            )

        elif name == "idlergear_container_logs":
            pm = _get_pm_server()
            logs = pm.get_container_logs(
                container_id=arguments["container_id"],
                tail=arguments.get("tail"),
            )
            if logs is None:
                return [
                    TextContent(
                        type="text",
                        text=f"Container not found: {arguments['container_id']}",
                    )
                ]
            return [TextContent(type="text", text=logs)]

        elif name == "idlergear_container_stats":
            pm = _get_pm_server()
            stats = pm.get_container_stats(arguments["container_id"])
            if stats is None:
                return [
                    TextContent(
                        type="text",
                        text=f"Container not found: {arguments['container_id']}",
                    )
                ]
            return _format_result(stats)

        # OpenTelemetry log query handlers
        elif name == "idlergear_otel_query_logs":
            from idlergear.otel_storage import OTelStorage
            from datetime import datetime, timedelta
            import re

            storage = OTelStorage()

            # Parse relative time strings like "1h", "30m", "24h"
            start_ns = None
            if "start_time" in arguments:
                start_str = arguments["start_time"]
                # Check for relative time
                relative_match = re.match(r"(\d+)([hm])", start_str)
                if relative_match:
                    value = int(relative_match.group(1))
                    unit = relative_match.group(2)
                    if unit == "h":
                        start_dt = datetime.now() - timedelta(hours=value)
                    else:  # m
                        start_dt = datetime.now() - timedelta(minutes=value)
                    start_ns = int(start_dt.timestamp() * 1e9)
                else:
                    # Assume ISO format
                    start_dt = datetime.fromisoformat(start_str)
                    start_ns = int(start_dt.timestamp() * 1e9)

            end_ns = None
            if "end_time" in arguments:
                end_dt = datetime.fromisoformat(arguments["end_time"])
                end_ns = int(end_dt.timestamp() * 1e9)

            # Query logs
            logs = storage.query(
                severity=arguments.get("severity"),
                service=arguments.get("service"),
                start_time=start_ns,
                end_time=end_ns,
                limit=arguments.get("limit", 100),
            )

            # Full-text search if requested
            if "search" in arguments:
                search_query = arguments["search"]
                logs = storage.search(search_query, limit=arguments.get("limit", 100))

            return _format_result({"logs": logs, "count": len(logs)})

        elif name == "idlergear_otel_stats":
            from idlergear.otel_storage import OTelStorage

            storage = OTelStorage()
            # Get basic stats using count()
            total = storage.count()

            # Get severity breakdown
            by_severity = {}
            for sev in ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]:
                count = storage.count(severity=[sev])
                if count > 0:
                    by_severity[sev] = count

            # Get service breakdown
            cursor = storage.conn.execute(
                "SELECT service, COUNT(*) as count FROM logs GROUP BY service"
            )
            by_service = {row[0]: row[1] for row in cursor.fetchall()}

            stats = {
                "total": total,
                "by_severity": by_severity,
                "by_service": by_service,
            }
            return _format_result(stats)

        elif name == "idlergear_otel_recent_errors":
            from idlergear.otel_storage import OTelStorage

            storage = OTelStorage()
            errors = storage.query(
                severity="ERROR",
                service=arguments.get("service"),
                limit=arguments.get("limit", 20),
            )
            fatals = storage.query(
                severity="FATAL",
                service=arguments.get("service"),
                limit=arguments.get("limit", 20),
            )

            all_errors = errors + fatals
            # Sort by timestamp (newest first)
            all_errors.sort(key=lambda x: x["timestamp"], reverse=True)

            return _format_result(
                {
                    "errors": all_errors[: arguments.get("limit", 20)],
                    "count": len(all_errors),
                }
            )

        # === Session Management Handlers ===
        elif name == "idlergear_session_start":
            from idlergear.session import start_session

            result = start_session(
                context_mode=arguments.get("context_mode", "minimal"),
                load_state=arguments.get("load_state", True),
                agent_id=_registered_agent_id,
                session_name=arguments.get("session_name"),
            )

            # Store session ID for use in session_end
            if "session_id" in result:
                _current_session_id = result["session_id"]

            return _format_result(result)

        elif name == "idlergear_session_save":
            from idlergear.session import SessionState

            session = SessionState()
            state = session.save(
                current_task_id=arguments.get("current_task_id"),
                working_files=arguments.get("working_files"),
                notes=arguments.get("notes"),
            )
            return _format_result({"state": state, "message": "Session state saved"})

        elif name == "idlergear_session_end":
            from idlergear.session import end_session

            result = end_session(
                current_task_id=arguments.get("current_task_id"),
                working_files=arguments.get("working_files"),
                notes=arguments.get("notes"),
                agent_id=_registered_agent_id,
                session_id=_current_session_id,
            )

            # Clear session ID after ending
            _current_session_id = None

            return _format_result(result)

        elif name == "idlergear_session_status":
            from idlergear.session import SessionState

            session = SessionState()
            summary = session.get_summary()
            state = session.load()
            return _format_result(
                {
                    "summary": summary,
                    "state": state,
                }
            )

        # === Watch Mode Handlers ===
        elif name == "idlergear_watch_check":
            from idlergear.watch import analyze, analyze_and_act

            if arguments.get("act", False):
                status, actions = analyze_and_act(auto_create_tasks=True)
                return _format_result(
                    {
                        "status": status.to_dict(),
                        "actions": [a.to_dict() for a in actions],
                    }
                )
            else:
                status = analyze()
                return _format_result(status.to_dict())

        elif name == "idlergear_watch_act":
            from idlergear.watch import analyze, act_on_suggestion

            suggestion_id = arguments["suggestion_id"]

            # Get current suggestions
            status = analyze()

            # Find the suggestion by ID
            suggestion = None
            for s in status.suggestions:
                if s.id == suggestion_id:
                    suggestion = s
                    break

            if suggestion is None:
                return _format_result(
                    {
                        "success": False,
                        "error": f"Suggestion '{suggestion_id}' not found. Available: {[s.id for s in status.suggestions]}",
                    }
                )

            result = act_on_suggestion(suggestion)
            return _format_result(result.to_dict())

        elif name == "idlergear_watch_stats":
            from idlergear.watch import get_watch_stats

            stats = get_watch_stats()
            return _format_result(stats)

        elif name == "idlergear_doctor":
            from idlergear.doctor import run_doctor
            from idlergear.upgrade import do_upgrade

            report = run_doctor()
            result = report.to_dict()

            # Auto-fix if requested
            if arguments.get("fix", False) and not report.is_healthy:
                upgrade_result = do_upgrade()
                result["fix_applied"] = True
                result["fix_result"] = upgrade_result

            return _format_result(result)

        # === Test Tool Handlers ===
        elif name == "idlergear_test_detect":
            from pathlib import Path

            from idlergear.testing import detect_framework

            path = arguments.get("path")
            project_path = Path(path) if path else None
            config = detect_framework(project_path)

            if config is None:
                return _format_result(
                    {
                        "framework": "unknown",
                        "detected": False,
                        "message": "No test framework detected",
                    }
                )

            return _format_result(
                {
                    "framework": config.framework,
                    "command": config.command,
                    "test_dir": config.test_dir,
                    "test_pattern": config.test_pattern,
                    "detected": True,
                }
            )

        elif name == "idlergear_test_status":
            from pathlib import Path

            from idlergear.testing import get_last_result

            path = arguments.get("path")
            project_path = Path(path) if path else None
            result = get_last_result(project_path)

            if result is None:
                return _format_result(
                    {
                        "status": "no_results",
                        "message": "No test results found. Run tests with idlergear_test_run.",
                    }
                )

            return _format_result(result.to_dict())

        elif name == "idlergear_test_run":
            from pathlib import Path

            from idlergear.testing import detect_framework, run_tests

            path = arguments.get("path")
            project_path = Path(path) if path else None
            extra_args = arguments.get("args")

            config = detect_framework(project_path)
            if config is None:
                return _format_result(
                    {
                        "success": False,
                        "error": "No test framework detected",
                    }
                )

            result, output = run_tests(project_path, config, extra_args)

            return _format_result(
                {
                    "success": result.exit_code == 0,
                    **result.to_dict(),
                    "output_lines": len(output.splitlines()),
                }
            )

        elif name == "idlergear_test_history":
            from pathlib import Path

            from idlergear.testing import get_history

            path = arguments.get("path")
            project_path = Path(path) if path else None
            limit = arguments.get("limit", 10)

            history = get_history(project_path, limit=limit)

            return _format_result(
                {
                    "count": len(history),
                    "runs": [r.to_dict() for r in history],
                }
            )

        elif name == "idlergear_test_list":
            from pathlib import Path

            from idlergear.testing import enumerate_tests, save_enumeration

            path = arguments.get("path")
            project_path = Path(path) if path else None
            files_only = arguments.get("files_only", False)

            enum = enumerate_tests(project_path)
            if enum is None:
                return _format_result(
                    {"error": "No test framework detected", "tests": []}
                )

            save_enumeration(enum, project_path)

            if files_only:
                return _format_result(
                    {
                        "framework": enum.framework,
                        "total_files": enum.total_files,
                        "files": enum.test_files,
                    }
                )
            else:
                return _format_result(enum.to_dict())

        elif name == "idlergear_test_coverage":
            from pathlib import Path

            from idlergear.testing import build_coverage_map, get_tests_for_file

            path = arguments.get("path")
            project_path = Path(path) if path else None
            file = arguments.get("file")

            if file:
                tests = get_tests_for_file(file, project_path)
                return _format_result(
                    {
                        "source_file": file,
                        "test_files": tests,
                        "has_tests": len(tests) > 0,
                    }
                )

            coverage_map = build_coverage_map(project_path)
            if coverage_map is None:
                return _format_result({"error": "Could not build coverage map"})

            return _format_result(coverage_map.to_dict())

        elif name == "idlergear_test_uncovered":
            from pathlib import Path

            from idlergear.testing import get_uncovered_files

            path = arguments.get("path")
            project_path = Path(path) if path else None

            uncovered = get_uncovered_files(project_path)

            return _format_result(
                {
                    "uncovered": uncovered,
                    "count": len(uncovered),
                }
            )

        elif name == "idlergear_test_changed":
            from pathlib import Path

            from idlergear.testing import (
                get_changed_files,
                get_tests_for_changes,
                run_changed_tests,
            )

            path = arguments.get("path")
            project_path = Path(path) if path else None
            since = arguments.get("since")
            run = arguments.get("run", False)

            if run:
                result, output = run_changed_tests(project_path, since=since)
                return _format_result(
                    {
                        "success": result.exit_code == 0,
                        **result.to_dict(),
                        "output_lines": len(output.splitlines()),
                    }
                )
            else:
                changed = get_changed_files(project_path, since=since)
                tests = get_tests_for_changes(project_path, since=since)
                return _format_result(
                    {
                        "changed_files": changed,
                        "tests_to_run": tests,
                        "changed_count": len(changed),
                        "test_count": len(tests),
                    }
                )

        elif name == "idlergear_test_sync":
            from pathlib import Path

            from idlergear.testing import (
                check_external_test_runs,
                sync_external_runs,
            )

            path = arguments.get("path")
            project_path = Path(path) if path else None

            external_runs = check_external_test_runs(project_path)
            if not external_runs:
                return _format_result(
                    {
                        "external_detected": False,
                        "imported": 0,
                        "message": "No external test runs detected",
                    }
                )

            imported = sync_external_runs(project_path)
            return _format_result(
                {
                    "external_detected": True,
                    "external_runs": [r.to_dict() for r in external_runs],
                    "imported": len(imported),
                    "results": [r.to_dict() for r in imported],
                }
            )

        elif name == "idlergear_test_staleness":
            from pathlib import Path

            from idlergear.testing import get_test_staleness

            path = arguments.get("path")
            project_path = Path(path) if path else None

            staleness = get_test_staleness(project_path)
            return _format_result(staleness)

        # Documentation generation tools (Python + Rust + .NET)
        elif name == "idlergear_docs_check":
            from idlergear.docs import check_pdoc_available
            from idlergear.docs_rust import check_cargo_available
            from idlergear.docs_dotnet import check_dotnet_available

            lang = arguments.get("lang", "all")
            if lang == "python":
                return _format_result({"python": {"available": check_pdoc_available()}})
            elif lang == "rust":
                return _format_result({"rust": {"available": check_cargo_available()}})
            elif lang == "dotnet":
                return _format_result(
                    {"dotnet": {"available": check_dotnet_available()}}
                )
            else:
                return _format_result(
                    {
                        "python": {"available": check_pdoc_available()},
                        "rust": {"available": check_cargo_available()},
                        "dotnet": {"available": check_dotnet_available()},
                    }
                )

        elif name == "idlergear_docs_module":
            from idlergear.docs import check_pdoc_available, generate_module_docs

            if not check_pdoc_available():
                return _format_result(
                    {
                        "error": "pdoc not installed",
                        "install": "pip install 'idlergear[docs]'",
                    }
                )

            module_name = arguments["module"]
            doc = generate_module_docs(module_name)
            return _format_result(doc.to_dict())

        elif name == "idlergear_docs_generate":
            from idlergear.docs import (
                check_pdoc_available,
                generate_docs_json,
                generate_docs_markdown,
            )

            if not check_pdoc_available():
                return _format_result(
                    {
                        "error": "pdoc not installed",
                        "install": "pip install 'idlergear[docs]'",
                    }
                )

            package = arguments["package"]
            fmt = arguments.get("format", "json")
            include_private = arguments.get("include_private", False)
            max_depth = arguments.get("max_depth")

            if fmt == "markdown":
                result = generate_docs_markdown(
                    package,
                    include_private=include_private,
                    max_depth=max_depth,
                )
                return [TextContent(type="text", text=result)]
            else:
                result = generate_docs_json(
                    package,
                    include_private=include_private,
                    max_depth=max_depth,
                )
                return [TextContent(type="text", text=result)]

        elif name == "idlergear_docs_summary":
            import json
            from pathlib import Path
            from idlergear.docs import (
                check_pdoc_available,
                generate_summary_json,
                detect_python_project,
            )
            from idlergear.docs_rust import (
                detect_rust_project,
                generate_rust_summary_json,
            )
            from idlergear.docs_dotnet import (
                detect_dotnet_project,
                find_xml_docs,
                parse_xml_docs,
                generate_dotnet_summary,
            )

            package = arguments["package"]
            mode = arguments.get("mode", "standard")
            lang = arguments.get("lang", "auto")
            include_private = arguments.get("include_private", False)
            max_depth = arguments.get("max_depth")

            # Auto-detect language if needed
            if lang == "auto":
                # Check if package is a path
                path = Path(package)
                if path.exists():
                    rust_project = detect_rust_project(path)
                    if rust_project["detected"]:
                        lang = "rust"
                    else:
                        dotnet_project = detect_dotnet_project(path)
                        if dotnet_project["detected"]:
                            lang = "dotnet"
                        else:
                            python_project = detect_python_project(path)
                            if python_project["detected"]:
                                lang = "python"
                            else:
                                lang = "python"  # Default to python
                else:
                    # Assume it's a Python module name
                    lang = "python"

            if lang == "rust":
                result = generate_rust_summary_json(package, mode=mode)  # type: ignore
                return [TextContent(type="text", text=result)]
            elif lang == "dotnet":
                path = Path(package)
                xml_docs = find_xml_docs(path)
                if not xml_docs:
                    return _format_result(
                        {
                            "error": "No XML documentation files found",
                            "hint": "Build with <GenerateDocumentationFile>true</GenerateDocumentationFile>",
                        }
                    )
                assembly = parse_xml_docs(xml_docs[0])
                summary = generate_dotnet_summary(assembly, mode=mode)
                return [TextContent(type="text", text=json.dumps(summary, indent=2))]
            else:
                if not check_pdoc_available():
                    return _format_result(
                        {
                            "error": "pdoc not installed",
                            "install": "pip install 'idlergear[docs]'",
                        }
                    )
                result = generate_summary_json(
                    package,
                    mode=mode,  # type: ignore
                    include_private=include_private,
                    max_depth=max_depth,
                )
                return [TextContent(type="text", text=result)]

        elif name == "idlergear_docs_build":
            from pathlib import Path
            from idlergear.docs import (
                build_html_docs,
                check_pdoc_available,
                detect_python_project,
            )
            from idlergear.docs_rust import (
                build_rust_docs,
                check_cargo_available,
                detect_rust_project,
            )
            from idlergear.docs_dotnet import (
                build_dotnet_docs,
                check_dotnet_available,
                detect_dotnet_project,
            )

            package = arguments.get("package", ".")
            lang = arguments.get("lang", "auto")
            open_browser = arguments.get("open_browser", False)

            # Auto-detect language if needed
            if lang == "auto":
                path = Path(package) if package else Path(".")
                rust_project = detect_rust_project(path)
                if rust_project["detected"]:
                    lang = "rust"
                else:
                    dotnet_project = detect_dotnet_project(path)
                    if dotnet_project["detected"]:
                        lang = "dotnet"
                    else:
                        lang = "python"

            if lang == "rust":
                if not check_cargo_available():
                    return _format_result({"error": "cargo not found"})

                path = Path(package) if package else Path(".")
                result = build_rust_docs(path, open_browser=open_browser)
                return _format_result(result)
            elif lang == "dotnet":
                if not check_dotnet_available():
                    return _format_result({"error": "dotnet not found"})

                path = Path(package) if package else Path(".")
                configuration = arguments.get("configuration", "Debug")
                result = build_dotnet_docs(path, configuration=configuration)
                return _format_result(result)
            else:
                if not check_pdoc_available():
                    return _format_result(
                        {
                            "error": "pdoc not installed",
                            "install": "pip install 'idlergear[docs]'",
                        }
                    )

                if not package or package == ".":
                    project = detect_python_project()
                    if project.get("packages"):
                        package = project["packages"][0]
                    else:
                        return _format_result(
                            {"error": "Could not detect Python package"}
                        )

                output_dir = arguments.get("output_dir", "docs/api")
                logo = arguments.get("logo")
                favicon = arguments.get("favicon")

                result = build_html_docs(
                    package, output_dir=output_dir, logo=logo, favicon=favicon
                )
                return _format_result(result)

        elif name == "idlergear_docs_detect":
            from idlergear.docs import detect_python_project
            from idlergear.docs_rust import detect_rust_project
            from idlergear.docs_dotnet import detect_dotnet_project

            path = arguments.get("path", ".")

            # Check Rust first, then .NET, then Python
            rust_result = detect_rust_project(path)
            if rust_result["detected"]:
                return _format_result(rust_result)

            dotnet_result = detect_dotnet_project(path)
            if dotnet_result["detected"]:
                dotnet_result["language"] = "dotnet"
                return _format_result(dotnet_result)

            python_result = detect_python_project(path)
            if python_result["detected"]:
                python_result["language"] = "python"
                return _format_result(python_result)

            # None detected
            return _format_result(
                {
                    "path": path,
                    "detected": False,
                    "message": "No Python, Rust, or .NET project detected",
                }
            )

        elif name == "idlergear_watch_versions":
            from idlergear.watch import check_stale_data_references
            from pathlib import Path

            project_root = Path.cwd()
            warnings = check_stale_data_references(project_root)

            return _format_result(
                {
                    "warnings_count": len(warnings),
                    "warnings": warnings,
                }
            )

        # File Registry handlers
        elif name == "idlergear_file_register":
            from idlergear.file_registry import FileRegistry, FileStatus

            registry = _get_cached_registry()
            status = FileStatus(arguments["status"])
            registry.register_file(
                arguments["path"],
                status,
                reason=arguments.get("reason"),
            )

            # Broadcast change to daemon for multi-agent coordination
            await _broadcast_registry_change(
                action="registered",
                file_path=arguments["path"],
                data={
                    "status": arguments["status"],
                    "reason": arguments.get("reason"),
                },
            )

            return _format_result(
                {
                    "success": True,
                    "path": arguments["path"],
                    "status": arguments["status"],
                    "reason": arguments.get("reason"),
                }
            )

        elif name == "idlergear_file_deprecate":
            from idlergear.file_registry import FileRegistry

            registry = _get_cached_registry()
            registry.deprecate_file(
                arguments["path"],
                successor=arguments.get("successor"),
                reason=arguments.get("reason"),
            )

            # Broadcast change to daemon for multi-agent coordination
            await _broadcast_registry_change(
                action="deprecated",
                file_path=arguments["path"],
                data={
                    "successor": arguments.get("successor"),
                    "reason": arguments.get("reason"),
                },
            )

            return _format_result(
                {
                    "success": True,
                    "path": arguments["path"],
                    "deprecated": True,
                    "successor": arguments.get("successor"),
                    "reason": arguments.get("reason"),
                }
            )

        elif name == "idlergear_file_status":
            from idlergear.file_registry import FileRegistry

            registry = _get_cached_registry()
            path = arguments["path"]

            status = registry.get_status(path)
            entry = registry.get_entry(path)

            if status is None:
                return _format_result(
                    {
                        "path": path,
                        "registered": False,
                        "status": None,
                    }
                )

            result = {
                "path": path,
                "registered": True,
                "status": status.value,
            }

            if entry:
                result["reason"] = entry.reason
                result["current_version"] = entry.current_version
                result["deprecated_at"] = entry.deprecated_at
                result["replaces"] = entry.replaces
                result["deprecated_versions"] = entry.deprecated_versions

            return _format_result(result)

        elif name == "idlergear_file_list":
            from idlergear.file_registry import FileRegistry, FileStatus

            registry = _get_cached_registry()

            # Filter by status if provided
            status_filter = None
            if "status" in arguments:
                status_filter = FileStatus(arguments["status"])

            entries = registry.list_files(status_filter)

            # Convert to dict format
            files = []
            for entry in entries:
                files.append(
                    {
                        "path": entry.path,
                        "status": entry.status.value,
                        "reason": entry.reason,
                        "current_version": entry.current_version,
                        "deprecated_at": entry.deprecated_at,
                        "replaces": entry.replaces,
                        "deprecated_versions": entry.deprecated_versions,
                    }
                )

            return _format_result(
                {
                    "count": len(files),
                    "files": files,
                }
            )

        # File annotation handlers (NEW v0.6.0)
        elif name == "idlergear_file_annotate":
            from idlergear.file_registry import FileRegistry

            registry = _get_cached_registry()
            entry = registry.annotate_file(
                arguments["path"],
                description=arguments.get("description"),
                tags=arguments.get("tags"),
                components=arguments.get("components"),
                related_files=arguments.get("related_files"),
            )

            return _format_result(
                {
                    "success": True,
                    "path": entry.path,
                    "status": entry.status.value,
                    "description": entry.description,
                    "tags": entry.tags,
                    "components": entry.components,
                    "related_files": entry.related_files,
                }
            )

        elif name == "idlergear_file_search":
            from idlergear.file_registry import FileRegistry, FileStatus

            registry = _get_cached_registry()

            # Convert status string to enum if provided
            status_filter = None
            if "status" in arguments:
                status_filter = FileStatus(arguments["status"])

            results = registry.search_files(
                query=arguments.get("query"),
                tags=arguments.get("tags"),
                components=arguments.get("components"),
                status=status_filter,
            )

            # Convert to dict format
            files = []
            for entry in results:
                files.append(
                    {
                        "path": entry.path,
                        "status": entry.status.value,
                        "description": entry.description,
                        "tags": entry.tags,
                        "components": entry.components,
                        "related_files": entry.related_files,
                        "reason": entry.reason,
                        "current_version": entry.current_version,
                    }
                )

            return _format_result(
                {
                    "count": len(files),
                    "files": files,
                }
            )

        elif name == "idlergear_file_get_annotation":
            from idlergear.file_registry import FileRegistry

            registry = _get_cached_registry()
            entry = registry.get_annotation(arguments["path"])

            if not entry:
                return _format_result(
                    {
                        "found": False,
                        "path": arguments["path"],
                    }
                )

            return _format_result(
                {
                    "found": True,
                    "path": entry.path,
                    "status": entry.status.value,
                    "description": entry.description,
                    "tags": entry.tags,
                    "components": entry.components,
                    "related_files": entry.related_files,
                    "reason": entry.reason,
                    "current_version": entry.current_version,
                    "deprecated_at": entry.deprecated_at,
                    "replaces": entry.replaces,
                    "deprecated_versions": entry.deprecated_versions,
                }
            )

        elif name == "idlergear_file_list_tags":
            from idlergear.file_registry import FileRegistry

            registry = _get_cached_registry()
            tag_map = registry.list_tags()

            # Convert to list format for better display
            tags = []
            for tag, info in tag_map.items():
                tags.append(
                    {
                        "tag": tag,
                        "count": info["count"],
                        "files": info["files"],
                    }
                )

            # Sort by count (descending)
            tags.sort(key=lambda x: x["count"], reverse=True)

            return _format_result(
                {
                    "count": len(tags),
                    "tags": tags,
                }
            )

        elif name == "idlergear_file_audit":
            from idlergear.file_registry import FileRegistry

            registry = _get_cached_registry()
            since_hours = arguments.get("since_hours", 24)
            include_code_scan = arguments.get("include_code_scan", False)

            report = registry.audit_project(
                since_hours=since_hours,
                include_code_scan=include_code_scan,
            )

            return _format_result(report)

        elif name == "idlergear_file_scan":
            from idlergear.file_registry_scanner import FileRegistryScanner

            scanner = FileRegistryScanner()
            min_confidence = arguments.get("min_confidence", "low")
            include_git_renames = arguments.get("include_git_renames", True)
            include_patterns = arguments.get("include_patterns", True)
            include_directories = arguments.get("include_directories", True)

            suggestions = scanner.scan(
                min_confidence=min_confidence,
                include_git_renames=include_git_renames,
                include_patterns=include_patterns,
                include_directories=include_directories,
            )

            # Convert suggestions to serializable format
            result = {
                "suggestions": [
                    {
                        "file_path": s.file_path,
                        "suggested_status": s.suggested_status.value,
                        "confidence": s.confidence,
                        "reason": s.reason,
                        "current_version": s.current_version,
                        "evidence": s.evidence,
                    }
                    for s in suggestions
                ],
                "total": len(suggestions),
            }

            # Group by confidence
            grouped = scanner.group_suggestions_by_confidence(suggestions)
            result["by_confidence"] = {
                level: len(sug_list) for level, sug_list in grouped.items()
            }

            return _format_result(result)

        # Plugin handlers (NEW v0.8.0)
        elif name == "idlergear_plugin_list":
            from idlergear.plugins import (
                LangfusePlugin,
                LlamaIndexPlugin,
                PluginRegistry,
            )

            registry = _get_plugin_registry()

            # Register available plugins
            registry.register_plugin_class(LangfusePlugin)
            registry.register_plugin_class(LlamaIndexPlugin)

            loaded_only = arguments.get("loaded_only", False)

            if loaded_only:
                plugins = registry.list_loaded_plugins()
            else:
                plugins = registry.list_available_plugins()

            return _format_result(
                {
                    "plugins": plugins,
                    "loaded": registry.list_loaded_plugins(),
                    "count": len(plugins),
                }
            )

        elif name == "idlergear_plugin_status":
            from idlergear.plugins import LangfusePlugin, LlamaIndexPlugin

            registry = _get_plugin_registry()

            # Register available plugins
            registry.register_plugin_class(LangfusePlugin)
            registry.register_plugin_class(LlamaIndexPlugin)

            plugin_name = arguments.get("plugin_name")

            if plugin_name:
                # Get status for specific plugin
                plugin = registry.get_plugin(plugin_name)
                if not plugin:
                    # Try to load it
                    plugin = registry.load_plugin(plugin_name)

                if plugin:
                    return _format_result(
                        {
                            "plugin": plugin_name,
                            "loaded": True,
                            "initialized": plugin.is_initialized(),
                            "healthy": plugin.health_check(),
                            "capabilities": [
                                cap.value for cap in plugin.capabilities()
                            ],
                        }
                    )
                else:
                    # Check if enabled in config
                    enabled = registry.config.is_plugin_enabled(plugin_name)
                    return _format_result(
                        {
                            "plugin": plugin_name,
                            "loaded": False,
                            "enabled": enabled,
                            "available": plugin_name
                            in registry.list_available_plugins(),
                        }
                    )
            else:
                # Get status for all plugins
                statuses = []
                for name in registry.list_available_plugins():
                    plugin = registry.get_plugin(name)
                    if plugin:
                        statuses.append(
                            {
                                "plugin": name,
                                "loaded": True,
                                "initialized": plugin.is_initialized(),
                                "healthy": plugin.health_check(),
                                "capabilities": [
                                    cap.value for cap in plugin.capabilities()
                                ],
                            }
                        )
                    else:
                        enabled = registry.config.is_plugin_enabled(name)
                        statuses.append(
                            {
                                "plugin": name,
                                "loaded": False,
                                "enabled": enabled,
                            }
                        )

                return _format_result({"plugins": statuses, "count": len(statuses)})

        elif name == "idlergear_plugin_enable":
            import toml

            plugin_name = arguments["plugin_name"]
            enabled = arguments.get("enabled", True)

            # Load config.toml
            config_path = Path.cwd() / ".idlergear" / "config.toml"
            if config_path.exists():
                config = toml.load(config_path)
            else:
                config = {}

            # Update plugin config
            if "plugins" not in config:
                config["plugins"] = {}
            if plugin_name not in config["plugins"]:
                config["plugins"][plugin_name] = {}

            config["plugins"][plugin_name]["enabled"] = enabled

            # Write back
            with open(config_path, "w") as f:
                toml.dump(config, f)

            return _format_result(
                {
                    "plugin": plugin_name,
                    "enabled": enabled,
                    "config_path": str(config_path),
                }
            )

        elif name == "idlergear_plugin_search":
            from idlergear.plugins import LlamaIndexPlugin

            registry = _get_plugin_registry()

            # Register and load LlamaIndex plugin
            registry.register_plugin_class(LlamaIndexPlugin)
            plugin = registry.load_plugin("llamaindex")

            if not plugin:
                return _format_result(
                    {
                        "error": "LlamaIndex plugin not enabled. Enable it first with: idlergear plugin enable llamaindex"
                    }
                )

            # Perform search
            query = arguments["query"]
            top_k = arguments.get("top_k", 5)
            knowledge_type = arguments.get("knowledge_type")

            results = plugin.search(query, top_k=top_k, knowledge_type=knowledge_type)

            return _format_result(
                {
                    "query": query,
                    "results": results,
                    "count": len(results),
                }
            )

        elif name == "idlergear_plugin_index_reference":
            from idlergear.plugins import LlamaIndexPlugin

            registry = _get_plugin_registry()

            # Register and load LlamaIndex plugin
            registry.register_plugin_class(LlamaIndexPlugin)
            plugin = registry.load_plugin("llamaindex")

            if not plugin:
                return _format_result(
                    {
                        "error": "LlamaIndex plugin not enabled. Enable it first with: idlergear plugin enable llamaindex"
                    }
                )

            # Index reference
            reference = {
                "title": arguments["title"],
                "body": arguments.get("body", ""),
            }
            plugin.index_reference(reference)

            return _format_result(
                {
                    "success": True,
                    "indexed": "reference",
                    "title": arguments["title"],
                }
            )

        elif name == "idlergear_plugin_index_note":
            from idlergear.plugins import LlamaIndexPlugin

            registry = _get_plugin_registry()

            # Register and load LlamaIndex plugin
            registry.register_plugin_class(LlamaIndexPlugin)
            plugin = registry.load_plugin("llamaindex")

            if not plugin:
                return _format_result(
                    {
                        "error": "LlamaIndex plugin not enabled. Enable it first with: idlergear plugin enable llamaindex"
                    }
                )

            # Index note
            note = {
                "id": arguments["note_id"],
                "content": arguments["content"],
                "tags": arguments.get("tags", []),
            }
            plugin.index_note(note)

            return _format_result(
                {
                    "success": True,
                    "indexed": "note",
                    "note_id": arguments["note_id"],
                }
            )

        # Knowledge gap detection tools
        elif name == "idlergear_knowledge_detect_gaps":
            from idlergear.gap_detector import GapDetector, GapType
            from idlergear.config import find_idlergear_root

            root = find_idlergear_root()
            if root is None:
                raise ValueError("Not in an IdlerGear project")

            detector = GapDetector(project_root=root)

            # Parse gap type filter
            gap_types = None
            if arguments.get("gap_type"):
                try:
                    gap_types = [GapType(arguments["gap_type"])]
                except ValueError:
                    raise ValueError(f"Unknown gap type: {arguments['gap_type']}")

            # Detect gaps
            gaps = detector.detect_gaps(gap_types=gap_types)

            # Convert to dict format
            result = {
                "total_gaps": len(gaps),
                "gaps": [g.to_dict() for g in gaps],
            }

            return _format_result(result)

        elif name == "idlergear_knowledge_gap_summary":
            from idlergear.gap_detector import GapDetector, GapSeverity
            from idlergear.config import find_idlergear_root

            root = find_idlergear_root()
            if root is None:
                raise ValueError("Not in an IdlerGear project")

            detector = GapDetector(project_root=root)
            gaps = detector.detect_gaps()

            # Group by severity
            by_severity = {
                "critical": len(
                    [g for g in gaps if g.severity == GapSeverity.CRITICAL]
                ),
                "high": len([g for g in gaps if g.severity == GapSeverity.HIGH]),
                "medium": len([g for g in gaps if g.severity == GapSeverity.MEDIUM]),
                "low": len([g for g in gaps if g.severity == GapSeverity.LOW]),
                "info": len([g for g in gaps if g.severity == GapSeverity.INFO]),
            }

            result = {
                "total_gaps": len(gaps),
                "by_severity": by_severity,
                "has_critical": by_severity["critical"] > 0,
                "has_high": by_severity["high"] > 0,
                "health_status": "critical"
                if by_severity["critical"] > 0
                else "needs_attention"
                if by_severity["high"] > 0
                else "good"
                if by_severity["medium"] > 0
                else "healthy",
            }

            return _format_result(result)

        elif name == "idlergear_get_suggestions":
            from idlergear.proactive import get_session_start_suggestions
            from idlergear.config import find_idlergear_root

            root = find_idlergear_root()
            if root is None:
                raise ValueError("Not in an IdlerGear project")

            suggestions = get_session_start_suggestions(project_root=root)

            result = {
                "total_suggestions": len(suggestions),
                "suggestions": [s.to_dict() for s in suggestions],
            }

            return _format_result(result)

        # AI State Reporting Handlers (#374 - AI Observability)
        elif name == "idlergear_ai_report_activity":
            from datetime import datetime
            from idlergear.daemon.client import get_daemon_client, DaemonNotRunning

            # Extract parameters
            phase = arguments.get("phase")
            task_id = arguments.get("task_id")
            action = arguments.get("action")
            target = arguments.get("target")
            reason = arguments.get("reason")

            # Create activity report
            activity = {
                "phase": phase,
                "task_id": task_id,
                "action": action,
                "target": target,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            }

            # Try to send to daemon
            try:
                root = find_idlergear_root()
                if root and _registered_agent_id:
                    client = get_daemon_client(root)
                    # Update agent state in daemon
                    await client.call(
                        "agent.update_state",
                        {
                            "agent_id": _registered_agent_id,
                            "ai_state": {"current_activity": activity},
                        },
                    )
                    # Broadcast to subscribers (TUI)
                    await client.call(
                        "broadcast",
                        {
                            "type": "ai.activity_changed",
                            "agent_id": _registered_agent_id,
                            "activity": activity,
                        },
                    )
            except (DaemonNotRunning, Exception):
                # Gracefully degrade if daemon not available
                pass

            return _format_result(
                {
                    "status": "reported",
                    "phase": phase,
                    "action": action,
                    "target": target,
                }
            )

        elif name == "idlergear_ai_report_plan":
            from datetime import datetime
            from idlergear.daemon.client import get_daemon_client, DaemonNotRunning

            # Extract parameters
            steps = arguments.get("steps", [])
            confidence = arguments.get("confidence")

            # Create plan report
            plan = {
                "steps": steps,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat(),
            }

            # Try to send to daemon
            try:
                root = find_idlergear_root()
                if root and _registered_agent_id:
                    client = get_daemon_client(root)
                    # Update agent state
                    await client.call(
                        "agent.update_state",
                        {
                            "agent_id": _registered_agent_id,
                            "ai_state": {"planned_steps": plan},
                        },
                    )
                    # Broadcast
                    await client.call(
                        "broadcast",
                        {
                            "type": "ai.plan_updated",
                            "agent_id": _registered_agent_id,
                            "plan": plan,
                        },
                    )
            except (DaemonNotRunning, Exception):
                pass

            return _format_result(
                {
                    "status": "reported",
                    "num_steps": len(steps),
                    "confidence": confidence,
                    "low_confidence_warning": confidence < 0.7,
                }
            )

        elif name == "idlergear_ai_report_uncertainty":
            from datetime import datetime
            from idlergear.daemon.client import get_daemon_client, DaemonNotRunning

            # Extract parameters
            question = arguments.get("question")
            confidence = arguments.get("confidence")
            context = arguments.get("context", {})

            # Create uncertainty report
            uncertainty = {
                "question": question,
                "confidence": confidence,
                "context": context,
                "timestamp": datetime.now().isoformat(),
            }

            # Try to send to daemon
            try:
                root = find_idlergear_root()
                if root and _registered_agent_id:
                    client = get_daemon_client(root)
                    # Update agent state (append to uncertainties list)
                    await client.call(
                        "agent.append_uncertainty",
                        {
                            "agent_id": _registered_agent_id,
                            "uncertainty": uncertainty,
                        },
                    )
                    # Broadcast
                    await client.call(
                        "broadcast",
                        {
                            "type": "ai.uncertainty_detected",
                            "agent_id": _registered_agent_id,
                            "uncertainty": uncertainty,
                        },
                    )
            except (DaemonNotRunning, Exception):
                pass

            return _format_result(
                {
                    "status": "reported",
                    "question": question,
                    "confidence": confidence,
                    "intervention_recommended": confidence < 0.5,
                }
            )

        elif name == "idlergear_ai_report_search":
            from datetime import datetime
            from idlergear.daemon.client import get_daemon_client, DaemonNotRunning

            # Extract parameters
            query = arguments.get("query")
            search_type = arguments.get("search_type")
            results_found = arguments.get("results_found")
            files_searched = arguments.get("files_searched", [])

            # Create search report
            search = {
                "query": query,
                "search_type": search_type,
                "results_found": results_found,
                "files_searched": files_searched,
                "timestamp": datetime.now().isoformat(),
            }

            # Detect repeated searches (simple heuristic: check last 5 searches)
            # This would ideally be more sophisticated in daemon
            try:
                root = find_idlergear_root()
                if root and _registered_agent_id:
                    client = get_daemon_client(root)
                    # Append to search history
                    await client.call(
                        "agent.append_search",
                        {
                            "agent_id": _registered_agent_id,
                            "search": search,
                        },
                    )
                    # Broadcast (daemon will detect repetition)
                    await client.call(
                        "broadcast",
                        {
                            "type": "ai.search_performed",
                            "agent_id": _registered_agent_id,
                            "search": search,
                        },
                    )
            except (DaemonNotRunning, Exception):
                pass

            return _format_result(
                {
                    "status": "reported",
                    "query": query,
                    "results_found": results_found,
                    "search_inefficiency_warning": results_found == 0,
                }
            )

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _subscribe_to_registry_events():
    """Subscribe to file registry events from daemon.

    This allows the MCP server to be notified when other agents
    make changes to the file registry (e.g., deprecating files).

    When registry change events are received, the cache is invalidated
    to ensure all agents see the latest registry state.
    """
    import asyncio
    import sys

    from idlergear.daemon.client import DaemonNotRunning, get_daemon_client
    from idlergear.daemon.protocol import Notification

    # Try to find idlergear root
    try:
        idlergear_root = find_idlergear_root()
        if not idlergear_root:
            return  # No idlergear root, can't subscribe
    except Exception:
        return  # Failed to find root

    # Try to connect to daemon (non-blocking, fail gracefully)
    try:
        client = get_daemon_client(idlergear_root)
        await client.connect()

        # Define event handler
        async def handle_registry_event(notification: Notification) -> None:
            """Handle file registry change events from daemon."""
            try:
                # Check if this is a registry event
                method = notification.method
                params = notification.params or {}

                if method == "event":
                    event = params.get("event", "")
                    data = params.get("data", {})

                    if event.startswith("file."):
                        # Registry changed - invalidate cache
                        _invalidate_registry_cache()

                        # Log the change
                        action = data.get("action", "unknown")
                        file_path = data.get("file_path", "unknown")
                        print(
                            f"[IdlerGear MCP] Registry changed: {action} {file_path} (cache invalidated)",
                            file=sys.stderr,
                        )
            except Exception as e:
                # Don't let handler failures break the subscription
                print(
                    f"[IdlerGear MCP] Warning: Error handling registry event: {e}",
                    file=sys.stderr,
                )

        # Override the client's notification handler
        # This is safe because we control the client lifecycle
        client._handle_notification = handle_registry_event  # type: ignore

        # Subscribe to file registry events
        await client.subscribe("file.*")

        print(
            "[IdlerGear MCP] Subscribed to file registry events from daemon",
            file=sys.stderr,
        )

        # Keep connection alive in background
        # The _receive_loop is already running and will call our handler
        while True:
            await asyncio.sleep(60)  # Keep alive

    except DaemonNotRunning:
        # Daemon not running - this is OK, subscription is optional
        pass
    except Exception as e:
        # Log but don't crash the server
        print(
            f"[IdlerGear MCP] Warning: Failed to subscribe to daemon events: {e}",
            file=sys.stderr,
        )


async def run_server():
    """Run the MCP server with reload support."""
    # Set up signal handler for reload (SIGUSR1)
    _setup_reload_signal()

    # Write PID file so CLI can find and signal us
    _write_pid_file()

    # Auto-detect and activate project virtual environment
    _activate_project_environment()

    # Ensure daemon is running for real-time monitoring and coordination
    _ensure_daemon_running()

    # Auto-register this MCP server as an agent
    await _auto_register_agent()

    # Start daemon subscription in background (non-blocking)
    daemon_task = asyncio.create_task(_subscribe_to_registry_events())

    try:
        async with stdio_server() as (read_stream, write_stream):
            init_options = server.create_initialization_options()
            await server.run(read_stream, write_stream, init_options)
    finally:
        # Cancel daemon subscription
        daemon_task.cancel()
        try:
            await daemon_task
        except asyncio.CancelledError:
            pass

        _cleanup_pid_file()


def main():
    """Entry point for the MCP server."""
    import asyncio
    import atexit

    # Register cleanup
    atexit.register(_cleanup_pid_file)

    asyncio.run(run_server())


if __name__ == "__main__":
    main()
