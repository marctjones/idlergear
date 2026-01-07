"""Goose integration for IdlerGear."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


GOOSEHINTS_TEMPLATE = """# Goose Agent Instructions

## IdlerGear Knowledge Management

This project uses [IdlerGear](https://github.com/marctjones/idlergear) for knowledge management.

### CRITICAL: Session Start

**ALWAYS call this MCP tool FIRST in EVERY session:**

```python
# Via MCP (RECOMMENDED - fastest, ~570 tokens in minimal mode!)
idlergear_session_start(context_mode="minimal")
```

This provides:
- Project vision, plan, tasks, notes
- Previous session state (task ID, working files, notes)
- Smart recommendations for what to work on

**Result:** Perfect session continuity - eliminates "where did we leave off?" questions!

**CLI Alternative** (if MCP not available):
```bash
idlergear session-start
```

**DO NOT skip this step** - it's the foundation of effective AI-assisted development.

### FORBIDDEN: File-Based Knowledge

**DO NOT create any of these files:**
- `TODO.md`, `TODO.txt`, `TASKS.md`
- `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
- `FEATURE_IDEAS.md`, `RESEARCH.md`, `BACKLOG.md`
- Any markdown file for tracking work or capturing thoughts

**ALWAYS use IdlerGear commands instead.**

### FORBIDDEN: Inline TODOs

**DO NOT write inline TODO comments:**
- `// TODO: ...`
- `# FIXME: ...`
- `/* HACK: ... */`

**INSTEAD:** Create a task with `idlergear task create "..." --label technical-debt`

### REQUIRED: Use IdlerGear Commands

| Instead of... | Use this command |
|---------------|------------------|
| Creating TODO.md | `idlergear task create "description"` |
| Writing notes to files | `idlergear note create "content"` |
| Adding TODO comments | `idlergear task create "..." --label technical-debt` |
| Creating VISION.md | `idlergear vision edit` |
| Documenting findings | `idlergear reference add "title" --body "..."` |

### During Development

| Action | Command |
|--------|---------|
| Found a bug | `idlergear task create "..." --label bug` |
| Had an idea | `idlergear note create "..."` |
| Research question | `idlergear note create "..." --tag explore` |
| Completed work | `idlergear task close <id>` |
| Check project goals | `idlergear vision show` |
| View open tasks | `idlergear task list` |

### Knowledge Flow

```
note → task or reference
```
- Quick thoughts go to notes (capture now, review later)
- Use `--tag explore` for research questions, `--tag idea` for ideas
- Actionable work goes to tasks (clear completion criteria)
- Use `idlergear note promote <id> --to task` to convert notes to tasks

### Reference Documentation

- `idlergear reference list` - View reference documents
- `idlergear reference show "title"` - Read a specific reference
- `idlergear reference add "title" --body "..."` - Add documentation
- `idlergear search "query"` - Search across all knowledge types

## Recommended MCP Servers

For optimal Goose integration, configure these MCP servers in your Goose settings:

### 1. IdlerGear MCP Server (REQUIRED)

```json
{
  "mcpServers": {
    "idlergear": {
      "command": "idlergear-mcp",
      "args": [],
      "cwd": "."
    }
  }
}
```

Provides **51 MCP tools** including:
- Task management (create, update, close, list)
- Note & reference storage
- Project context (vision, plan, tasks, notes)
- **Session management** (start, save, end, status)
- **Filesystem operations** (11 tools) - ✅ Built-in!
- **Git + task integration** (18 tools) - ✅ Built-in!
- **Process management** (11 tools) - ✅ Built-in!
- **Environment detection** (4 tools) - ✅ Built-in!
- **OpenTelemetry logs** (3 tools) - ✅ Built-in!

**UNIQUE FEATURES:**
- `idlergear_git_commit_task` - Auto-link commits to tasks
- `idlergear_git_status_for_task` - Show only task-related files
- `idlergear_git_sync_tasks` - Update tasks from commit messages
- `idlergear_session_start` - Perfect session continuity
- `idlergear_env_info` - Consolidated environment snapshot

**That's it!** IdlerGear includes all the filesystem, git, and process management tools you need - **no Node.js required!**

## Goose MCP Configuration

### Simple Setup (Goose CLI & GUI)

Add IdlerGear to your Goose config (`~/.config/goose/config.yaml` or via GUI settings):

**Goose CLI:**
```yaml
mcp_servers:
  idlergear:
    command: idlergear-mcp
    args: []
    env: {}
```

**Goose GUI:**
1. Open Settings → Extensions/MCP Servers
2. Click "Add Custom Extension"
3. Enter:
   - **Name**: `idlergear`
   - **Command**: `idlergear-mcp`
   - **Args**: (leave empty)
4. Save and restart Goose

**That's it!** IdlerGear provides all 51 tools in one server - no Node.js dependencies!

## Session Best Practices for Goose

### ⚡ Session Start (CRITICAL!)

**First action every session:**
```python
idlergear_session_start(context_mode="minimal")
```

This ONE call provides:
- Vision, plan, tasks, notes (~570 tokens!)
- Previous session state (task ID, files, notes)
- Smart recommendations

**Benefits:**
- Perfect session continuity
- Zero "where did we leave off?" questions
- Minimal token usage (97% savings vs full context!)

### 💾 During Development

**Capture knowledge as you work:**
```python
# Quick thought or discovery
idlergear_note_create(content="Found auth bug in JWT validation", tags=["explore"])

# Identified work to do
idlergear_task_create(title="Fix JWT validation bug", labels=["bug"], priority="high")

# Save progress mid-session
idlergear_session_save(
    current_task_id=42,
    working_files=["auth.py", "tests.py"],
    notes="Completed authentication, starting authorization"
)

# Commit with task linking
idlergear_git_commit_task(
    task_id=42,
    message="Fix JWT validation bug",
    all=True  # Auto-stage changes
)
```

### 🏁 Session End

**Before ending session:**
```python
# End session with automatic suggestions for next time
idlergear_session_end(
    current_task_id=42,
    notes="Ready to implement role-based permissions"
)
```

**What this does:**
- Saves session state for next time
- Generates recommendations for continuation
- Perfect handoff to next session

**Alternative:** If not done with task, just save progress:
```python
idlergear_session_save(current_task_id=42, notes="Half-done with RBAC")
```

## Protected Files

**DO NOT modify directly:**
- `.idlergear/` - Data files (use CLI commands)
- `.mcp.json` - MCP configuration

## Token Savings (Measured!)

With IdlerGear MCP server configured:
- **Session context:** ~97% reduction (17K → 570 tokens with minimal mode!)
- **Filesystem operations:** ~70% reduction (tree view vs ls -R)
- **Git operations:** ~60% reduction (structured status/diff vs raw output)
- **Process management:** ~80% reduction (filtered list vs ps aux)
- **Environment detection:** ~60% reduction (consolidated vs multiple commands)

**Total:** **6,000-10,000 tokens saved per development session** + perfect session continuity!

## Goose-Specific Tips

### CLI vs GUI Differences

**Goose CLI:**
- Primarily text-based interaction
- Use `context_mode="minimal"` for speed
- JSON output is fine

**Goose GUI:**
- Visual interface benefits from rich formatting
- Can upgrade to `context_mode="standard"` if needed
- Markdown output may render nicer

### Best Practices

1. **Always start with** `idlergear_session_start()` - no exceptions!
2. **Use task-aware git** - `idlergear_git_commit_task(task_id=42)` links commits
3. **Save progress frequently** - `idlergear_session_save()` prevents lost work
4. **End sessions properly** - `idlergear_session_end()` ensures continuity
5. **Search before asking** - `idlergear_search("query")` finds existing knowledge

### Goose GUI Extension Marketplace

IdlerGear will soon be available in the Goose GUI Extension Marketplace for one-click installation!

## Help & Support

- Documentation: https://github.com/marctjones/idlergear
- Issues: https://github.com/marctjones/idlergear/issues
- MCP Servers: https://mcpservers.org
"""


def generate_goosehints(
    path: Optional[Path] = None,
    force: bool = False,
) -> None:
    """Generate .goosehints file with IdlerGear and MCP server recommendations.

    Args:
        path: Directory to generate .goosehints in (default: current directory)
        force: Overwrite existing .goosehints file
    """
    if path is None:
        path = Path.cwd()
    else:
        path = Path(path)

    goosehints_path = path / ".goosehints"

    if goosehints_path.exists() and not force:
        console.print(f"[red]Error:[/red] .goosehints already exists at {goosehints_path}")
        console.print("[yellow]Use --force to overwrite[/yellow]")
        raise typer.Exit(1)

    # Write the template
    goosehints_path.write_text(GOOSEHINTS_TEMPLATE)

    console.print(f"[green]✓[/green] Created .goosehints at {goosehints_path}")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Review the file and customize as needed")
    console.print("  2. Configure MCP servers in your Goose settings")
    console.print("  3. Goose will automatically load these instructions on session start")


def register_goose_extension() -> None:
    """Register IdlerGear as a Goose GUI extension.

    This will be implemented after researching Goose's extension API.
    Currently outputs instructions for manual registration.
    """
    console.print(Panel.fit(
        "[bold]Goose GUI Extension Registration[/bold]\n\n"
        "[yellow]Status:[/yellow] Manual configuration required (automatic registration coming soon)\n\n"
        "[bold]Steps:[/bold]\n"
        "  1. Open Goose GUI settings\n"
        "  2. Navigate to Extensions or MCP Servers section\n"
        "  3. Add IdlerGear MCP server with command: [cyan]idlergear-mcp[/cyan]\n"
        "  4. Optionally add recommended servers (filesystem, git, pm)\n"
        "  5. Restart Goose GUI to activate",
        title="🦆 Goose Integration"
    ))

    console.print("\n[bold]Goose CLI Configuration (config.yaml):[/bold]\n")
    console.print("```yaml")
    console.print("mcp_servers:")
    console.print("  idlergear:")
    console.print("    command: idlergear-mcp")
    console.print("    args: []")
    console.print("    env: {}")
    console.print("```")

    console.print("\n[bold]Goose GUI Configuration (JSON):[/bold]\n")
    console.print("```json")
    console.print('{')
    console.print('  "mcpServers": {')
    console.print('    "idlergear": {')
    console.print('      "command": "idlergear-mcp",')
    console.print('      "args": []')
    console.print('    }')
    console.print('  }')
    console.print('}')
    console.print("```")

    console.print("\n[green]✓[/green] IdlerGear provides 51 tools - filesystem, git, PM all built-in!")
    console.print("[green]✓[/green] Zero Node.js dependencies required!")
