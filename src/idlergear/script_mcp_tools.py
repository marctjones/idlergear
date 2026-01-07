"""MCP tools for script generation and process management."""

from mcp.types import Tool

# Tool definitions for script generation
SCRIPT_TOOLS = [
    Tool(
        name="idlergear_script_generate",
        description=(
            "Generate a shell script that sets up dev environment and registers with IdlerGear daemon. "
            "The generated script will:\n"
            "1. Set up virtualenv and install dependencies\n"
            "2. Set environment variables\n"
            "3. Register as an agent with the IdlerGear daemon\n"
            "4. Optionally stream logs to the daemon\n"
            "5. Provide helper functions for coordination\n\n"
            "Use this when you need to create a script that runs in a separate terminal/process "
            "but stays coordinated with the IdlerGear system."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "script_name": {
                    "type": "string",
                    "description": "Name for the script (will be used for agent registration)",
                },
                "command": {
                    "type": "string",
                    "description": "The main command to execute",
                },
                "output_path": {
                    "type": "string",
                    "description": "Where to save the script (default: ./scripts/{name}.sh)",
                },
                "venv_path": {
                    "type": "string",
                    "description": "Path to virtualenv to activate (optional)",
                },
                "requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Python packages to install (e.g., ['pytest', 'django'])",
                },
                "env_vars": {
                    "type": "object",
                    "description": "Environment variables to set (key-value pairs)",
                    "additionalProperties": {"type": "string"},
                },
                "stream_logs": {
                    "type": "boolean",
                    "description": "Whether to stream logs to daemon (default: false)",
                    "default": False,
                },
            },
            "required": ["script_name", "command"],
        },
    ),
    Tool(
        name="idlergear_script_from_template",
        description=(
            "Generate a script from a predefined template. "
            "Templates include common setups like pytest, django-dev, flask-dev, jupyter, fastapi-dev. "
            "The generated script auto-registers with the daemon."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "template": {
                    "type": "string",
                    "description": "Template name",
                    "enum": ["pytest", "django-dev", "flask-dev", "jupyter", "fastapi-dev"],
                },
                "script_name": {
                    "type": "string",
                    "description": "Name for the script",
                },
                "output_path": {
                    "type": "string",
                    "description": "Where to save the script (default: ./scripts/{name}.sh)",
                },
                "venv_path": {
                    "type": "string",
                    "description": "Path to virtualenv (optional)",
                },
                "env_vars": {
                    "type": "object",
                    "description": "Additional environment variables",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["template", "script_name"],
        },
    ),
    Tool(
        name="idlergear_run_with_daemon",
        description=(
            "Start a background process that registers with the daemon and optionally streams logs. "
            "Use this when you want a long-running process to be coordinated with other AI agents."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Command to execute",
                },
                "name": {
                    "type": "string",
                    "description": "Name for the run (generated from command if not provided)",
                },
                "register": {
                    "type": "boolean",
                    "description": "Register with daemon as an agent (default: true)",
                    "default": True,
                },
                "stream_logs": {
                    "type": "boolean",
                    "description": "Stream logs to daemon in real-time (default: false)",
                    "default": False,
                },
            },
            "required": ["command"],
        },
    ),
]
