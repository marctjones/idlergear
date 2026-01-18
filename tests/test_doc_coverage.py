"""Tests for documentation coverage tracking."""

from pathlib import Path

import pytest

from idlergear.doc_coverage import (
    DocumentationCoverage,
    MCPTool,
    CLICommand,
    extract_mcp_tools,
    extract_cli_commands,
    check_documentation_in_file,
    format_coverage_report,
)


@pytest.fixture
def mock_mcp_server(tmp_path):
    """Create a mock mcp_server.py file."""
    mcp_file = tmp_path / "mcp_server.py"
    mcp_file.write_text('''
"""Mock MCP server."""
from mcp import Tool

def list_tools():
    return [
        Tool(
            name="idlergear_task_create",
            description="Create a new task",
        ),
        Tool(
            name="idlergear_task_list",
            description="List tasks",
        ),
        Tool(
            name="idlergear_note_create",
            description="Create a note",
        ),
    ]

def call_tool(tool):
    if tool.name == "idlergear_task_create":
        return "created"
    elif tool.name == "idlergear_task_list":
        return "listed"
    elif tool.name == "idlergear_note_create":
        return "noted"
''')
    return mcp_file


@pytest.fixture
def mock_cli_file(tmp_path):
    """Create a mock cli.py file."""
    cli_file = tmp_path / "cli.py"
    cli_file.write_text('''
"""Mock CLI."""
import typer

app = typer.Typer()
task_app = typer.Typer()
app.add_typer(task_app, name="task")

@app.command()
def init():
    """Initialize project."""
    pass

@app.command("status")
def show_status():
    """Show status."""
    pass

@task_app.command()
def create():
    """Create task."""
    pass

@task_app.command("list")
def list_tasks():
    """List tasks."""
    pass
''')
    return cli_file


@pytest.fixture
def mock_skills_md(tmp_path):
    """Create a mock SKILLS.md file."""
    skills = tmp_path / "SKILLS.md"
    skills.write_text('''
# Skills

## Task Management

- `idlergear_task_create` - Create a new task
- `idlergear_task_list` - List all tasks

## Note Management

Notes are managed with `idlergear_note_create`.
''')
    return skills


@pytest.fixture
def mock_readme_md(tmp_path):
    """Create a mock README.md file."""
    readme = tmp_path / "README.md"
    readme.write_text('''
# README

## Commands

Initialize your project:
```bash
idlergear init
```

Check status:
```bash
idlergear status
```

Create a task:
```bash
idlergear task create "My task"
```

List tasks:
```bash
idlergear task list
```
''')
    return readme


def test_extract_mcp_tools(mock_mcp_server):
    """Test extracting MCP tools from mcp_server.py."""
    tools = extract_mcp_tools(mock_mcp_server)

    # Should extract all 3 tools from the mock file
    assert len(tools) >= 3
    tool_names = [t.name for t in tools]
    assert "idlergear_note_create" in tool_names
    assert "idlergear_task_create" in tool_names
    assert "idlergear_task_list" in tool_names


def test_extract_mcp_tools_nonexistent():
    """Test extracting from nonexistent file."""
    tools = extract_mcp_tools(Path("/nonexistent/mcp_server.py"))
    assert tools == []


def test_extract_cli_commands(mock_cli_file):
    """Test extracting CLI commands from cli.py."""
    commands = extract_cli_commands(mock_cli_file)

    assert len(commands) == 4

    # Find specific commands
    init_cmd = next(c for c in commands if c.name == "init")
    assert init_cmd.parent is None
    assert init_cmd.full_name == "init"
    assert init_cmd.description == "Initialize project."

    status_cmd = next(c for c in commands if c.name == "status")
    assert status_cmd.full_name == "status"

    create_cmd = next(c for c in commands if c.name == "create")
    assert create_cmd.parent == "task"
    assert create_cmd.full_name == "task create"

    list_cmd = next(c for c in commands if c.name == "list")
    assert list_cmd.parent == "task"
    assert list_cmd.full_name == "task list"


def test_extract_cli_commands_nonexistent():
    """Test extracting from nonexistent file."""
    commands = extract_cli_commands(Path("/nonexistent/cli.py"))
    assert commands == []


def test_check_documentation_in_file(mock_skills_md, mock_readme_md):
    """Test checking documentation coverage in files."""
    tool_names = [
        "idlergear_task_create",
        "idlergear_task_list",
        "idlergear_note_create",
        "idlergear_vision_show",
    ]
    cmd_names = ["init", "status", "task create", "task list", "task close"]

    # Check SKILLS.md
    skills_tools, skills_cmds = check_documentation_in_file(
        mock_skills_md, tool_names, cmd_names
    )
    assert "idlergear_task_create" in skills_tools
    assert "idlergear_task_list" in skills_tools
    assert "idlergear_note_create" in skills_tools
    assert "idlergear_vision_show" not in skills_tools

    # Check README.md
    readme_tools, readme_cmds = check_documentation_in_file(
        mock_readme_md, tool_names, cmd_names
    )
    assert "init" in readme_cmds
    assert "status" in readme_cmds
    assert "task create" in readme_cmds
    assert "task list" in readme_cmds
    assert "task close" not in readme_cmds


def test_check_documentation_nonexistent():
    """Test checking nonexistent documentation file."""
    tools, cmds = check_documentation_in_file(
        Path("/nonexistent.md"),
        ["idlergear_task_create"],
        ["init"],
    )
    assert tools == set()
    assert cmds == set()


def test_documentation_coverage_properties():
    """Test DocumentationCoverage properties."""
    coverage = DocumentationCoverage(
        mcp_tools=[
            MCPTool(name="tool1", function_name="tool1"),
            MCPTool(name="tool2", function_name="tool2"),
            MCPTool(name="tool3", function_name="tool3"),
            MCPTool(name="tool4", function_name="tool4"),
        ],
        cli_commands=[
            CLICommand(name="cmd1", function_name="cmd1"),
            CLICommand(name="cmd2", function_name="cmd2"),
        ],
        documented_in_skills={"tool1", "tool2", "tool3"},  # 3/4 = 75%
        documented_in_readme={"cmd1"},  # 1/2 = 50%
        documented_in_agents=set(),
    )

    assert coverage.mcp_coverage_skills == 0.75
    assert coverage.cli_coverage_readme == 0.5

    assert len(coverage.undocumented_mcp_tools) == 1
    assert coverage.undocumented_mcp_tools[0].name == "tool4"

    assert len(coverage.undocumented_cli_commands) == 1
    assert coverage.undocumented_cli_commands[0].name == "cmd2"


def test_format_coverage_report():
    """Test formatting coverage report."""
    coverage = DocumentationCoverage(
        mcp_tools=[
            MCPTool(name="tool1", function_name="tool1"),
            MCPTool(name="tool2", function_name="tool2"),
        ],
        cli_commands=[
            CLICommand(name="cmd1", function_name="cmd1"),
            CLICommand(name="cmd2", function_name="cmd2"),
        ],
        documented_in_skills={"tool1", "tool2"},  # 100%
        documented_in_readme={"cmd1", "cmd2"},  # 100%
        documented_in_agents=set(),
    )

    report = format_coverage_report(coverage, verbose=False)

    assert "MCP Tools (2 total)" in report
    assert "100%" in report
    assert "Excellent coverage" in report


def test_format_coverage_report_verbose():
    """Test verbose coverage report."""
    coverage = DocumentationCoverage(
        mcp_tools=[
            MCPTool(name="tool1", function_name="tool1"),
            MCPTool(name="tool2", function_name="tool2"),
        ],
        cli_commands=[
            CLICommand(name="cmd1", function_name="cmd1"),
        ],
        documented_in_skills={"tool1"},  # 50%
        documented_in_readme=set(),  # 0%
        documented_in_agents=set(),
    )

    report = format_coverage_report(coverage, verbose=True)

    assert "Undocumented MCP tools:" in report
    assert "tool2" in report
    assert "Undocumented CLI commands:" in report
    assert "cmd1" in report


def test_cli_command_full_name():
    """Test CLICommand full_name property."""
    cmd1 = CLICommand(name="create", parent="task", function_name="create_task")
    assert cmd1.full_name == "task create"

    cmd2 = CLICommand(name="init", parent=None, function_name="init_project")
    assert cmd2.full_name == "init"
