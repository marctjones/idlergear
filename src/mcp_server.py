"""
MCP (Model Context Protocol) Server for IdlerGear.

Exposes IdlerGear commands as tools that LLM clients can discover and invoke.
Runs on localhost only for security.
"""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.status import ProjectStatus
from src.context import ProjectContext
from src.check import ProjectChecker
from src.sync import ProjectSync
from src.logs import LogCoordinator
from src.messages import MessageManager
from src.coord import CoordRepo
from src.teleport import TeleportTracker
from src.eddi import EddiManager


# Create the MCP server instance
app = Server("idlergear")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available IdlerGear tools."""
    return [
        Tool(
            name="project_status",
            description="Get comprehensive project status including git state, charter documents, and LLM-managed branches",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path (default: current directory)",
                        "default": ".",
                    }
                },
            },
        ),
        Tool(
            name="project_context",
            description="Generate comprehensive project context for LLM consumption including all charter documents, recent activity, and project structure",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "plain"],
                        "description": "Output format",
                        "default": "markdown",
                    },
                    "include_docs": {
                        "type": "boolean",
                        "description": "Include charter documents",
                        "default": True,
                    },
                    "include_activity": {
                        "type": "boolean",
                        "description": "Include recent git activity",
                        "default": True,
                    },
                    "include_structure": {
                        "type": "boolean",
                        "description": "Include project structure",
                        "default": True,
                    },
                },
            },
        ),
        Tool(
            name="project_check",
            description="Analyze project for best practice adherence. Returns issues, warnings, and suggestions about testing, documentation, git hygiene, and more",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    }
                },
            },
        ),
        Tool(
            name="sync_status",
            description="Check web sync status - shows if there are sync branches and ahead/behind status",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    }
                },
            },
        ),
        Tool(
            name="sync_push",
            description="Push current project state to web sync branch for use in web-based LLM tools (Claude Web, Copilot Web, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    },
                    "include_untracked": {
                        "type": "boolean",
                        "description": "Include untracked files",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="sync_pull",
            description="Pull changes from web sync branch back to local environment",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    },
                    "cleanup": {
                        "type": "boolean",
                        "description": "Delete sync branch after merge",
                        "default": True,
                    },
                },
            },
        ),
        # Logging tools
        Tool(
            name="logs_list",
            description="List all log capture sessions with their IDs, names, and status",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    }
                },
            },
        ),
        Tool(
            name="logs_show",
            description="Show log content for a specific session",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    },
                    "session_id": {
                        "type": "integer",
                        "description": "Session ID to show logs for",
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Show only last N lines",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="logs_cleanup",
            description="Delete old log files",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Delete logs older than N days",
                        "default": 7,
                    },
                },
            },
        ),
        Tool(
            name="logs_pull_loki",
            description="Pull logs from Grafana Loki and save as a session",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    },
                    "url": {
                        "type": "string",
                        "description": "Loki server URL (e.g., http://loki:3100)",
                    },
                    "query": {
                        "type": "string",
                        "description": "LogQL query (e.g., {app=\"myapp\"})",
                    },
                    "since": {
                        "type": "string",
                        "description": "Time range (e.g., 1h, 30m, 2d)",
                        "default": "1h",
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional session name",
                    },
                },
                "required": ["url", "query"],
            },
        ),
        # Message tools
        Tool(
            name="message_send",
            description="Send a message to another LLM environment via git sync",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    },
                    "to": {
                        "type": "string",
                        "description": "Target environment (e.g., 'web', 'local')",
                    },
                    "body": {
                        "type": "string",
                        "description": "Message content",
                    },
                    "from_env": {
                        "type": "string",
                        "description": "Source environment identifier",
                        "default": "local",
                    },
                },
                "required": ["to", "body"],
            },
        ),
        Tool(
            name="message_list",
            description="List messages for the current project",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    },
                    "filter_to": {
                        "type": "string",
                        "description": "Filter by destination",
                    },
                    "filter_from": {
                        "type": "string",
                        "description": "Filter by source",
                    },
                    "unread_only": {
                        "type": "boolean",
                        "description": "Show only unread messages",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="message_read",
            description="Read a specific message and mark as read",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message ID to read",
                    },
                },
                "required": ["message_id"],
            },
        ),
        Tool(
            name="message_respond",
            description="Respond to a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message ID to respond to",
                    },
                    "body": {
                        "type": "string",
                        "description": "Response content",
                    },
                    "from_env": {
                        "type": "string",
                        "description": "Source environment identifier",
                        "default": "local",
                    },
                },
                "required": ["message_id", "body"],
            },
        ),
        # Coordination repo tools
        Tool(
            name="coord_init",
            description="Initialize private coordination repository for cross-environment messaging",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="coord_send",
            description="Send message via coordination repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project name",
                    },
                    "message": {
                        "type": "string",
                        "description": "Message content",
                    },
                    "to": {
                        "type": "string",
                        "description": "Target environment",
                        "default": "web",
                    },
                    "via": {
                        "type": "string",
                        "description": "Method: file or issue",
                        "default": "file",
                    },
                },
                "required": ["project", "message"],
            },
        ),
        Tool(
            name="coord_read",
            description="Read messages from coordination repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project name",
                    },
                    "via": {
                        "type": "string",
                        "description": "Method: file or issue",
                        "default": "file",
                    },
                },
                "required": ["project"],
            },
        ),
        # Teleport tools
        Tool(
            name="teleport_prepare",
            description="Prepare for Claude Code web teleport (stash changes, checkout branch)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Target branch",
                        "default": "main",
                    },
                },
            },
        ),
        Tool(
            name="teleport_finish",
            description="Finish teleport session (merge to main, cleanup branches, push)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Target branch to merge to",
                        "default": "main",
                    },
                },
            },
        ),
        Tool(
            name="teleport_list",
            description="List past teleport sessions",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max sessions to return",
                        "default": 10,
                    },
                    "branch": {
                        "type": "string",
                        "description": "Filter by branch",
                    },
                },
            },
        ),
        Tool(
            name="teleport_restore_stash",
            description="Restore stashed changes from teleport prepare",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project directory path",
                        "default": ".",
                    },
                },
            },
        ),
        # Eddi tools
        Tool(
            name="eddi_status",
            description="Get eddi-msgsrv installation status",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="eddi_install",
            description="Install eddi-msgsrv for Tor-based secure messaging",
            inputSchema={
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "Force reinstall even if already installed",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="eddi_uninstall",
            description="Uninstall eddi-msgsrv",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool invocations."""

    try:
        path = arguments.get("path", ".")

        if name == "project_status":
            status = ProjectStatus(path)
            output = status.format_status()
            return [TextContent(type="text", text=output)]

        elif name == "project_context":
            context = ProjectContext(path)
            output = context.format_context(
                include_docs=arguments.get("include_docs", True),
                include_activity=arguments.get("include_activity", True),
                include_structure=arguments.get("include_structure", True),
                format_type=arguments.get("format", "markdown"),
            )
            return [TextContent(type="text", text=output)]

        elif name == "project_check":
            checker = ProjectChecker(path)
            checker.run_all_checks()
            output = checker.format_report()
            return [TextContent(type="text", text=output)]

        elif name == "sync_status":
            syncer = ProjectSync(path)
            result = syncer.sync_status()

            # Format status as readable text
            lines = [
                "📊 Sync Status",
                f"Current branch: {result['current_branch']}",
                f"Sync branch: {result['sync_branch']}",
                f"Local exists: {'Yes' if result['local_exists'] else 'No'}",
                f"Remote exists: {'Yes' if result['remote_exists'] else 'No'}",
                f"Uncommitted changes: {result['uncommitted_changes']}",
            ]

            if result["ahead_behind"]:
                ahead = result["ahead_behind"]["ahead"]
                behind = result["ahead_behind"]["behind"]
                lines.append(f"Status: {ahead} ahead, {behind} behind")

                if behind > 0:
                    lines.append(
                        "⚠️ Web environment has changes - consider running sync_pull"
                    )
                elif ahead > 0:
                    lines.append("💡 Local has changes - consider running sync_push")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "sync_push":
            syncer = ProjectSync(path)
            result = syncer.sync_push(
                include_untracked=arguments.get("include_untracked", False)
            )

            lines = [
                f"✅ Pushed to sync branch: {result['sync_branch']}",
                f"From: {result['current_branch']}",
            ]

            if result["created_branch"]:
                lines.append("Created new sync branch")
            if result["committed_changes"]:
                lines.append("Committed changes")

            lines.append("")
            lines.append("📱 Next steps:")
            lines.append("1. Open web LLM tool")
            lines.append(f"2. Switch to branch: {result['sync_branch']}")
            lines.append("3. Work in web environment")
            lines.append("4. Run sync_pull when done")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "sync_pull":
            syncer = ProjectSync(path)
            result = syncer.sync_pull(cleanup=arguments.get("cleanup", True))

            lines = [
                f"✅ Pulled from sync branch: {result['sync_branch']}",
                f"To: {result['current_branch']}",
            ]

            if result["merged"]:
                lines.append("Merged changes successfully")
            if result["cleaned_up"]:
                lines.append("Cleaned up sync branch")

            return [TextContent(type="text", text="\n".join(lines))]

        # Logging tools
        elif name == "logs_list":
            coordinator = LogCoordinator(path)
            sessions = coordinator.list_sessions()

            if not sessions:
                return [TextContent(type="text", text="No log sessions found")]

            lines = [f"Log Sessions ({len(sessions)} total)", ""]
            for session in sessions:
                status_icon = {
                    "running": "🟢",
                    "completed": "✅",
                    "stopped": "⏹️",
                    "failed": "❌",
                }.get(session["status"], "❓")
                lines.append(f"{status_icon} Session {session['session_id']}: {session['name']}")
                lines.append(f"   Status: {session['status']}")
                lines.append(f"   Started: {session['started']}")
                lines.append("")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "logs_show":
            coordinator = LogCoordinator(path)
            session_id = arguments.get("session_id")
            tail = arguments.get("tail")

            session = coordinator.get_session(session_id)
            if not session:
                return [TextContent(type="text", text=f"Session {session_id} not found")]

            log_content = coordinator.read_log(session_id, tail=tail)

            lines = [
                f"Session {session_id}: {session['name']}",
                f"Status: {session['status']}",
                "─" * 40,
                log_content,
            ]

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "logs_cleanup":
            coordinator = LogCoordinator(path)
            days = arguments.get("days", 7)
            deleted = coordinator.cleanup_old_logs(days=days)
            return [TextContent(type="text", text=f"Deleted {deleted} old log file(s)")]

        elif name == "logs_pull_loki":
            coordinator = LogCoordinator(path)
            result = coordinator.pull_from_loki(
                url=arguments["url"],
                query=arguments["query"],
                since=arguments.get("since", "1h"),
                name=arguments.get("name"),
            )

            lines = [
                f"✅ Pulled {result.get('line_count', 0)} lines from Loki",
                f"Session ID: {result['session_id']}",
            ]

            return [TextContent(type="text", text="\n".join(lines))]

        # Message tools
        elif name == "message_send":
            manager = MessageManager(path)
            msg_id = manager.send_message(
                to=arguments["to"],
                body=arguments["body"],
                from_env=arguments.get("from_env", "local"),
            )
            return [TextContent(type="text", text=f"✅ Message {msg_id} sent\nNext: idlergear sync push --include-untracked")]

        elif name == "message_list":
            manager = MessageManager(path)
            messages = manager.list_messages(
                filter_to=arguments.get("filter_to"),
                filter_from=arguments.get("filter_from"),
                unread_only=arguments.get("unread_only", False),
            )
            output = manager.format_message_list(messages)
            return [TextContent(type="text", text=output)]

        elif name == "message_read":
            manager = MessageManager(path)
            message = manager.read_message(arguments["message_id"])
            if not message:
                return [TextContent(type="text", text=f"Message {arguments['message_id']} not found")]
            output = manager.format_message(message)
            return [TextContent(type="text", text=output)]

        elif name == "message_respond":
            manager = MessageManager(path)
            response_id = manager.respond_to_message(
                arguments["message_id"],
                arguments["body"],
                arguments.get("from_env", "local"),
            )
            return [TextContent(type="text", text=f"✅ Response {response_id} sent")]

        # Coordination repo tools
        elif name == "coord_init":
            coordinator = CoordRepo()
            result = coordinator.init()

            if result["status"] == "created":
                return [TextContent(type="text", text=f"✅ Created coordination repo\nRepo: {result['repo_url']}\nPath: {result['path']}")]
            elif result["status"] == "already_exists":
                return [TextContent(type="text", text=f"Coordination repo already exists\nPath: {result['path']}")]
            else:
                return [TextContent(type="text", text=f"❌ Error: {result.get('error', 'Unknown error')}")]

        elif name == "coord_send":
            coordinator = CoordRepo()
            result = coordinator.send_message(
                arguments["project"],
                arguments["message"],
                to=arguments.get("to", "web"),
                via=arguments.get("via", "file"),
            )

            if result["status"] == "sent":
                if arguments.get("via") == "issue":
                    return [TextContent(type="text", text=f"✅ Message sent\nIssue: {result['issue_url']}")]
                else:
                    return [TextContent(type="text", text=f"✅ Message sent\nMessage ID: {result['message_id']}")]
            else:
                return [TextContent(type="text", text=f"❌ Error: {result.get('error', 'Unknown error')}")]

        elif name == "coord_read":
            coordinator = CoordRepo()
            result = coordinator.read_messages(
                arguments["project"],
                via=arguments.get("via", "file"),
            )

            if result["status"] == "ok":
                messages = result["messages"]
                if not messages:
                    return [TextContent(type="text", text="No messages found")]

                lines = [f"Found {result['count']} message(s)", ""]
                for msg in messages:
                    if arguments.get("via") == "issue":
                        lines.append(f"Issue #{msg['number']}: {msg['title']}")
                        lines.append(f"   State: {msg['state']}")
                    else:
                        lines.append(f"Message {msg['id']}")
                        lines.append(f"   From: {msg['from']} → To: {msg['to']}")
                        lines.append(f"   {msg['message']}")
                    lines.append("")

                return [TextContent(type="text", text="\n".join(lines))]
            else:
                return [TextContent(type="text", text=f"❌ Error: {result.get('error', 'Unknown error')}")]

        # Teleport tools
        elif name == "teleport_prepare":
            tracker = TeleportTracker(path)
            branch = arguments.get("branch", "main")
            result = tracker.prepare_for_teleport(branch)

            messages = result.get("messages", [])
            if result["status"] == "ok":
                messages.append("")
                messages.append("✅ Ready for teleport!")
            else:
                messages.append(f"❌ Error: {result.get('error', 'Unknown error')}")

            return [TextContent(type="text", text="\n".join(messages))]

        elif name == "teleport_finish":
            tracker = TeleportTracker(path)
            branch = arguments.get("branch", "main")
            result = tracker.finish_teleport(branch)

            messages = result.get("messages", [])
            if result["status"] == "ok":
                messages.append("")
                messages.append("✅ Teleport complete!")
            else:
                messages.append(f"❌ Error: {result.get('error', 'Unknown error')}")

            return [TextContent(type="text", text="\n".join(messages))]

        elif name == "teleport_list":
            tracker = TeleportTracker(path)
            sessions = tracker.list_sessions(
                limit=arguments.get("limit", 10),
                branch=arguments.get("branch"),
            )
            output = tracker.format_session_list(sessions)
            return [TextContent(type="text", text=output)]

        elif name == "teleport_restore_stash":
            tracker = TeleportTracker(path)
            result = tracker.restore_stash()

            if result["status"] == "restored":
                return [TextContent(type="text", text=f"✅ {result['message']}")]
            elif result["status"] == "no_stash":
                return [TextContent(type="text", text=result['message'])]
            else:
                return [TextContent(type="text", text=f"❌ {result.get('message', result.get('error', 'Unknown error'))}")]

        # Eddi tools
        elif name == "eddi_status":
            manager = EddiManager()
            status = manager.status()

            lines = ["eddi-msgsrv Status", "=" * 40]
            if status["installed"]:
                lines.append("Installed: Yes ✅")
                lines.append(f"Version: {status['version']}")
                lines.append(f"Binary: {status['binary_path']}")
            else:
                lines.append("Installed: No")
                lines.append("")
                lines.append("Install with: idlergear eddi install")

            if status["src_dir"]:
                lines.append(f"Source: {status['src_dir']}")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "eddi_install":
            manager = EddiManager()
            result = manager.install(force=arguments.get("force", False))

            messages = result.get("messages", [])
            if result["status"] == "ok":
                messages.append("")
                messages.append("✅ eddi-msgsrv installed successfully")
            elif result["status"] == "already_installed":
                messages.append("")
                messages.append("Already installed")
            else:
                messages.append(f"❌ Error: {result.get('error', 'Unknown error')}")

            return [TextContent(type="text", text="\n".join(messages))]

        elif name == "eddi_uninstall":
            manager = EddiManager()
            result = manager.uninstall()

            messages = result.get("messages", [])
            messages.append("✅ Uninstalled")

            return [TextContent(type="text", text="\n".join(messages))]

        else:
            return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error executing {name}: {str(e)}")]


async def main():
    """Run the MCP server on stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
