"""Documentation coverage tracking for IdlerGear.

Ensures documentation stays up-to-date by:
1. Extracting MCP tools from mcp_server.py
2. Extracting CLI commands from cli.py
3. Checking documentation in SKILLS.md, README.md, etc.
4. Reporting coverage gaps
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from idlergear.config import find_idlergear_root


@dataclass
class MCPTool:
    """MCP tool metadata."""

    name: str
    function_name: str
    description: Optional[str] = None
    file_path: Optional[Path] = None
    line_number: Optional[int] = None


@dataclass
class CLICommand:
    """CLI command metadata."""

    name: str
    parent: Optional[str] = None  # For subcommands (e.g., "task" parent of "task list")
    function_name: str = ""
    description: Optional[str] = None
    file_path: Optional[Path] = None
    line_number: Optional[int] = None

    @property
    def full_name(self) -> str:
        """Get full command name (e.g., 'task list')."""
        if self.parent:
            return f"{self.parent} {self.name}"
        return self.name


@dataclass
class DocumentationCoverage:
    """Documentation coverage report."""

    mcp_tools: list[MCPTool]
    cli_commands: list[CLICommand]
    documented_in_skills: set[str]
    documented_in_readme: set[str]
    documented_in_agents: set[str]

    @property
    def mcp_coverage_skills(self) -> float:
        """Get MCP tool coverage in SKILLS.md (0.0 - 1.0)."""
        if not self.mcp_tools:
            return 1.0
        documented = sum(1 for tool in self.mcp_tools if tool.name in self.documented_in_skills)
        return documented / len(self.mcp_tools)

    @property
    def cli_coverage_readme(self) -> float:
        """Get CLI command coverage in README.md (0.0 - 1.0)."""
        if not self.cli_commands:
            return 1.0
        documented = sum(
            1 for cmd in self.cli_commands if cmd.full_name in self.documented_in_readme
        )
        return documented / len(self.cli_commands)

    @property
    def undocumented_mcp_tools(self) -> list[MCPTool]:
        """Get list of MCP tools not documented in SKILLS.md."""
        return [tool for tool in self.mcp_tools if tool.name not in self.documented_in_skills]

    @property
    def undocumented_cli_commands(self) -> list[CLICommand]:
        """Get list of CLI commands not documented in README.md."""
        return [
            cmd for cmd in self.cli_commands if cmd.full_name not in self.documented_in_readme
        ]


def extract_mcp_tools(mcp_server_file: Path) -> list[MCPTool]:
    """Extract MCP tools from mcp_server.py.

    Args:
        mcp_server_file: Path to mcp_server.py

    Returns:
        List of MCPTool objects
    """
    if not mcp_server_file.exists():
        return []

    tools = []
    content = mcp_server_file.read_text()
    tree = ast.parse(content)

    # Look for tool definitions in call_tool function
    # Pattern: if tool.name == "idlergear_task_create":
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            # Check if it's comparing tool.name
            if (
                isinstance(node.left, ast.Attribute)
                and isinstance(node.left.value, ast.Name)
                and node.left.value.id == "tool"
                and node.left.attr == "name"
            ):
                # Get the tool name from the comparison
                if node.ops and isinstance(node.ops[0], ast.Eq):
                    if node.comparators and isinstance(node.comparators[0], ast.Constant):
                        tool_name = node.comparators[0].value
                        if isinstance(tool_name, str) and tool_name.startswith("idlergear_"):
                            tools.append(
                                MCPTool(
                                    name=tool_name,
                                    function_name=tool_name,
                                    file_path=mcp_server_file,
                                    line_number=node.lineno,
                                )
                            )

    # Also look for tools in list_tools function
    # Pattern: Tool(name="idlergear_...", description="...")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "Tool":
                tool_name = None
                tool_desc = None

                for keyword in node.keywords:
                    if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                        tool_name = keyword.value.value
                    elif keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
                        tool_desc = keyword.value.value

                if tool_name and tool_name.startswith("idlergear_"):
                    # Avoid duplicates
                    if not any(t.name == tool_name for t in tools):
                        tools.append(
                            MCPTool(
                                name=tool_name,
                                function_name=tool_name,
                                description=tool_desc,
                                file_path=mcp_server_file,
                                line_number=node.lineno,
                            )
                        )

    return sorted(tools, key=lambda t: t.name)


def extract_cli_commands(cli_file: Path) -> list[CLICommand]:
    """Extract CLI commands from cli.py.

    Args:
        cli_file: Path to cli.py

    Returns:
        List of CLICommand objects
    """
    if not cli_file.exists():
        return []

    commands = []
    content = cli_file.read_text()
    tree = ast.parse(content)

    # Track Typer apps (for subcommands)
    typer_apps = {}  # app_name -> parent_command

    # Find Typer app definitions
    # Pattern: task_app = typer.Typer(...)
    # Pattern: app.add_typer(task_app, name="task")
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            # Check for typer.Typer() assignments
            if (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and isinstance(node.value.func.value, ast.Name)
                and node.value.func.value.id == "typer"
                and node.value.func.attr == "Typer"
            ):
                if node.targets and isinstance(node.targets[0], ast.Name):
                    app_name = node.targets[0].id
                    typer_apps[app_name] = None  # Will be filled in by add_typer

        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            # Check for app.add_typer(task_app, name="task")
            if (
                isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "add_typer"
            ):
                if node.value.args and isinstance(node.value.args[0], ast.Name):
                    app_var = node.value.args[0].id
                    # Find the name keyword
                    for keyword in node.value.keywords:
                        if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                            parent_name = keyword.value.value
                            typer_apps[app_var] = parent_name

    # Find command decorators
    # Pattern: @app.command() or @task_app.command("list")
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    # Get the app name and method
                    if isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr == "command":
                            app_var = (
                                decorator.func.value.id
                                if isinstance(decorator.func.value, ast.Name)
                                else None
                            )
                            parent = typer_apps.get(app_var) if app_var else None

                            # Get command name (from decorator arg or function name)
                            cmd_name = node.name
                            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                cmd_name = decorator.args[0].value

                            # Get docstring
                            docstring = ast.get_docstring(node)

                            commands.append(
                                CLICommand(
                                    name=cmd_name,
                                    parent=parent,
                                    function_name=node.name,
                                    description=docstring,
                                    file_path=cli_file,
                                    line_number=node.lineno,
                                )
                            )

    return sorted(commands, key=lambda c: c.full_name)


def check_documentation_in_file(
    file_path: Path, tool_names: list[str], command_names: list[str]
) -> tuple[set[str], set[str]]:
    """Check which tools/commands are documented in a file.

    Args:
        file_path: Path to documentation file
        tool_names: List of MCP tool names to check
        command_names: List of CLI command names to check

    Returns:
        Tuple of (documented_tools, documented_commands)
    """
    if not file_path.exists():
        return set(), set()

    content = file_path.read_text()

    # Check for MCP tools (look for tool name mentions)
    documented_tools = set()
    for tool_name in tool_names:
        # Look for the tool name in the file
        # Could be in code blocks, headings, or inline code
        if tool_name in content or tool_name.replace("idlergear_", "") in content:
            documented_tools.add(tool_name)

    # Check for CLI commands
    documented_commands = set()
    for cmd_name in command_names:
        # Look for "idlergear {command}" pattern
        pattern = rf"\bidlergear\s+{re.escape(cmd_name)}\b"
        if re.search(pattern, content):
            documented_commands.add(cmd_name)

    return documented_tools, documented_commands


def get_documentation_coverage(root: Optional[Path] = None) -> DocumentationCoverage:
    """Get documentation coverage report.

    Args:
        root: Project root. If None, auto-detect.

    Returns:
        DocumentationCoverage object
    """
    if root is None:
        root = find_idlergear_root()
        if not root:
            raise ValueError("Not in an IdlerGear project")

    # Extract tools and commands
    mcp_server_file = root / "src" / "idlergear" / "mcp_server.py"
    cli_file = root / "src" / "idlergear" / "cli.py"

    mcp_tools = extract_mcp_tools(mcp_server_file)
    cli_commands = extract_cli_commands(cli_file)

    # Documentation files to check
    skills_md = root / "SKILLS.md"
    readme_md = root / "README.md"
    agents_md = root / "AGENTS.md"

    # Check coverage
    tool_names = [t.name for t in mcp_tools]
    cmd_names = [c.full_name for c in cli_commands]

    skills_tools, skills_cmds = check_documentation_in_file(skills_md, tool_names, cmd_names)
    readme_tools, readme_cmds = check_documentation_in_file(readme_md, tool_names, cmd_names)
    agents_tools, agents_cmds = check_documentation_in_file(agents_md, tool_names, cmd_names)

    return DocumentationCoverage(
        mcp_tools=mcp_tools,
        cli_commands=cli_commands,
        documented_in_skills=skills_tools,
        documented_in_readme=readme_cmds,  # README for commands
        documented_in_agents=agents_tools.union(agents_cmds),
    )


def format_coverage_report(coverage: DocumentationCoverage, verbose: bool = False) -> str:
    """Format documentation coverage report for terminal display.

    Args:
        coverage: DocumentationCoverage object
        verbose: If True, list all undocumented items

    Returns:
        Formatted string
    """
    lines = []

    lines.append("=== Documentation Coverage Report ===\n")

    # MCP Tools
    mcp_pct = coverage.mcp_coverage_skills * 100
    lines.append(f"MCP Tools ({len(coverage.mcp_tools)} total):")
    lines.append(f"  Documented in SKILLS.md: {len(coverage.documented_in_skills)}/{len(coverage.mcp_tools)} ({mcp_pct:.0f}%)")

    if coverage.undocumented_mcp_tools and verbose:
        lines.append("\n  Undocumented MCP tools:")
        for tool in coverage.undocumented_mcp_tools:
            lines.append(f"    - {tool.name}")

    # CLI Commands
    cli_pct = coverage.cli_coverage_readme * 100
    lines.append(f"\nCLI Commands ({len(coverage.cli_commands)} total):")
    lines.append(
        f"  Documented in README.md: {len(coverage.documented_in_readme)}/{len(coverage.cli_commands)} ({cli_pct:.0f}%)"
    )

    if coverage.undocumented_cli_commands and verbose:
        lines.append("\n  Undocumented CLI commands:")
        for cmd in coverage.undocumented_cli_commands:
            lines.append(f"    - idlergear {cmd.full_name}")

    # Overall status
    lines.append("\nOverall Status:")
    if mcp_pct >= 95 and cli_pct >= 95:
        lines.append("  ✅ Excellent coverage (>95%)")
    elif mcp_pct >= 85 and cli_pct >= 85:
        lines.append("  ✓ Good coverage (>85%)")
    elif mcp_pct >= 70 and cli_pct >= 70:
        lines.append("  ⚠️  Fair coverage (>70%)")
    else:
        lines.append("  ❌ Poor coverage (<70%)")

    return "\n".join(lines)
