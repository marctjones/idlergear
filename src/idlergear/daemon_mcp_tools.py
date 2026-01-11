"""MCP tool definitions for daemon-based multi-agent coordination."""

from mcp.types import Tool


def get_daemon_tools() -> list[Tool]:
    """Get list of daemon coordination MCP tools."""
    return [
        # Agent registration tools
        Tool(
            name="idlergear_agent_register",
            description="Register this AI agent session with the daemon for multi-agent coordination. Call this at session start to enable queue polling, lock coordination, and event notifications.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Unique agent identifier (e.g., 'claude-code-1')",
                    },
                    "agent_type": {
                        "type": "string",
                        "description": "Agent type (e.g., 'claude-code', 'goose', 'aider')",
                    },
                    "capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Agent capabilities (e.g., ['code-generation', 'testing'])",
                    },
                },
                "required": ["agent_id", "agent_type"],
            },
        ),
        Tool(
            name="idlergear_agent_heartbeat",
            description="Send heartbeat to daemon to maintain agent session. Call periodically (every 60s recommended).",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent identifier",
                    },
                },
                "required": ["agent_id"],
            },
        ),
        Tool(
            name="idlergear_agent_update_status",
            description="Update agent status (active/idle/busy) and current task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["active", "idle", "busy"],
                    },
                    "current_task": {
                        "type": "string",
                        "description": "Current task/command ID being worked on",
                    },
                },
                "required": ["agent_id", "status"],
            },
        ),
        Tool(
            name="idlergear_agent_list",
            description="List all active AI agent sessions. Useful for checking what other agents are working on.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_type": {
                        "type": "string",
                        "description": "Filter by agent type",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "idle", "busy"],
                        "description": "Filter by status",
                    },
                },
            },
        ),
        # Queue tools
        Tool(
            name="idlergear_queue_add",
            description="Add a command/prompt to the execution queue for async processing. Other agents can pick this up.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt/command to execute",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority (0=normal, higher=more urgent)",
                        "default": 0,
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorizing the command",
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="idlergear_queue_poll",
            description="Poll for next pending command. Use this to pick up queued work.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent requesting work",
                    },
                },
                "required": ["agent_id"],
            },
        ),
        Tool(
            name="idlergear_queue_list",
            description="List queued commands by status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "pending",
                            "assigned",
                            "running",
                            "completed",
                            "failed",
                        ],
                        "description": "Filter by status",
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Filter by assigned agent",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_queue_get",
            description="Get details of a queued command by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Command ID"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="idlergear_queue_complete",
            description="Mark a command as completed with results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Command ID"},
                    "result": {
                        "type": "object",
                        "description": "Result data (JSON object)",
                    },
                    "error": {
                        "type": "string",
                        "description": "Error message if failed",
                    },
                },
                "required": ["id"],
            },
        ),
        # Lock tools
        Tool(
            name="idlergear_lock_acquire",
            description="Acquire a write lock on a resource (e.g., 'task:42', 'vision') to prevent conflicts with other agents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource": {
                        "type": "string",
                        "description": "Resource identifier (e.g., 'task:42', 'vision')",
                    },
                    "agent_id": {"type": "string"},
                    "timeout": {
                        "type": "number",
                        "description": "Lock timeout in seconds (default: 30)",
                    },
                },
                "required": ["resource", "agent_id"],
            },
        ),
        Tool(
            name="idlergear_lock_release",
            description="Release a write lock on a resource.",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource": {"type": "string"},
                    "agent_id": {"type": "string"},
                },
                "required": ["resource", "agent_id"],
            },
        ),
        Tool(
            name="idlergear_lock_check",
            description="Check if a resource is locked and by whom.",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource": {"type": "string"},
                },
                "required": ["resource"],
            },
        ),
    ]
