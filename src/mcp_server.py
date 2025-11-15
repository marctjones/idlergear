"""
MCP (Model Context Protocol) Server for IdlerGear.

Exposes IdlerGear commands as tools that LLM clients can discover and invoke.
Runs on localhost only for security.
"""
import asyncio
import json
from typing import Any, Optional
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.status import ProjectStatus
from src.context import ProjectContext
from src.check import ProjectChecker
from src.sync import ProjectSync


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
                        "default": "."
                    }
                }
            }
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
                        "default": "."
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "plain"],
                        "description": "Output format",
                        "default": "markdown"
                    },
                    "include_docs": {
                        "type": "boolean",
                        "description": "Include charter documents",
                        "default": True
                    },
                    "include_activity": {
                        "type": "boolean",
                        "description": "Include recent git activity",
                        "default": True
                    },
                    "include_structure": {
                        "type": "boolean",
                        "description": "Include project structure",
                        "default": True
                    }
                }
            }
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
                        "default": "."
                    }
                }
            }
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
                        "default": "."
                    }
                }
            }
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
                        "default": "."
                    },
                    "include_untracked": {
                        "type": "boolean",
                        "description": "Include untracked files",
                        "default": False
                    }
                }
            }
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
                        "default": "."
                    },
                    "cleanup": {
                        "type": "boolean",
                        "description": "Delete sync branch after merge",
                        "default": True
                    }
                }
            }
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
                format_type=arguments.get("format", "markdown")
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
                f"📊 Sync Status",
                f"Current branch: {result['current_branch']}",
                f"Sync branch: {result['sync_branch']}",
                f"Local exists: {'Yes' if result['local_exists'] else 'No'}",
                f"Remote exists: {'Yes' if result['remote_exists'] else 'No'}",
                f"Uncommitted changes: {result['uncommitted_changes']}"
            ]
            
            if result['ahead_behind']:
                ahead = result['ahead_behind']['ahead']
                behind = result['ahead_behind']['behind']
                lines.append(f"Status: {ahead} ahead, {behind} behind")
                
                if behind > 0:
                    lines.append("⚠️ Web environment has changes - consider running sync_pull")
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
                f"From: {result['current_branch']}"
            ]
            
            if result['created_branch']:
                lines.append("Created new sync branch")
            if result['committed_changes']:
                lines.append("Committed changes")
            
            lines.append("")
            lines.append("📱 Next steps:")
            lines.append(f"1. Open web LLM tool")
            lines.append(f"2. Switch to branch: {result['sync_branch']}")
            lines.append(f"3. Work in web environment")
            lines.append(f"4. Run sync_pull when done")
            
            return [TextContent(type="text", text="\n".join(lines))]
        
        elif name == "sync_pull":
            syncer = ProjectSync(path)
            result = syncer.sync_pull(
                cleanup=arguments.get("cleanup", True)
            )
            
            lines = [
                f"✅ Pulled from sync branch: {result['sync_branch']}",
                f"To: {result['current_branch']}"
            ]
            
            if result['merged']:
                lines.append("Merged changes successfully")
            if result['cleaned_up']:
                lines.append("Cleaned up sync branch")
            
            return [TextContent(type="text", text="\n".join(lines))]
        
        else:
            return [TextContent(
                type="text",
                text=f"❌ Unknown tool: {name}"
            )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Error executing {name}: {str(e)}"
        )]


async def main():
    """Run the MCP server on stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
