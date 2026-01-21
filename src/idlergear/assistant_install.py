"""Multi-assistant installation support for IdlerGear."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class Assistant(str, Enum):
    """Supported AI assistants."""

    CLAUDE = "claude"
    GEMINI = "gemini"
    COPILOT = "copilot"
    CODEX = "codex"
    AIDER = "aider"
    GOOSE = "goose"


@dataclass
class AssistantConfig:
    """Configuration for an AI assistant."""

    assistant: Assistant
    display_name: str
    instruction_file: str  # e.g., CLAUDE.md, GEMINI.md
    mcp_config_path: Path  # Path to MCP config file
    project_files: list[str]  # Files created in project directory
    global_files: list[str]  # Files created in home/config directory


ASSISTANT_CONFIGS = {
    Assistant.CLAUDE: AssistantConfig(
        assistant=Assistant.CLAUDE,
        display_name="Claude Code",
        instruction_file="CLAUDE.md",
        mcp_config_path=Path(".mcp.json"),
        project_files=["CLAUDE.md", "AGENTS.md", ".mcp.json", ".claude/"],
        global_files=[],
    ),
    Assistant.GEMINI: AssistantConfig(
        assistant=Assistant.GEMINI,
        display_name="Gemini CLI",
        instruction_file="GEMINI.md",
        mcp_config_path=Path.home() / ".gemini" / "settings.json",
        project_files=["GEMINI.md"],
        global_files=["~/.gemini/settings.json"],
    ),
    Assistant.COPILOT: AssistantConfig(
        assistant=Assistant.COPILOT,
        display_name="GitHub Copilot CLI",
        instruction_file="COPILOT.md",
        mcp_config_path=Path.home() / ".copilot" / "mcp.json",
        project_files=["COPILOT.md"],
        global_files=["~/.copilot/agents/idlergear.md", "~/.copilot/mcp.json"],
    ),
    Assistant.CODEX: AssistantConfig(
        assistant=Assistant.CODEX,
        display_name="Codex CLI",
        instruction_file="AGENTS.md",  # Codex uses AGENTS.md
        mcp_config_path=Path.home() / ".codex" / "config.toml",
        project_files=["AGENTS.md"],
        global_files=["~/.codex/config.toml"],
    ),
    Assistant.AIDER: AssistantConfig(
        assistant=Assistant.AIDER,
        display_name="Aider",
        instruction_file=".aider.conventions.md",
        mcp_config_path=Path(".aider.conf.yml"),  # No MCP support
        project_files=[".aider.conventions.md"],
        global_files=[],
    ),
    Assistant.GOOSE: AssistantConfig(
        assistant=Assistant.GOOSE,
        display_name="Goose",
        instruction_file=".goosehints",
        mcp_config_path=Path.home() / ".config" / "goose" / "config.yaml",
        project_files=[".goosehints"],
        global_files=["~/.config/goose/config.yaml"],
    ),
}


def detect_installed_assistants() -> list[Assistant]:
    """Detect which AI assistants are installed on the system.

    Returns:
        List of detected assistants
    """
    import shutil

    detected = []

    # Claude Code - check for claude binary
    if shutil.which("claude"):
        detected.append(Assistant.CLAUDE)

    # Gemini CLI
    if shutil.which("gemini"):
        detected.append(Assistant.GEMINI)

    # GitHub Copilot CLI
    if shutil.which("gh") and (Path.home() / ".copilot").exists():
        detected.append(Assistant.COPILOT)

    # Codex CLI
    if shutil.which("codex"):
        detected.append(Assistant.CODEX)

    # Aider
    if shutil.which("aider"):
        detected.append(Assistant.AIDER)

    # Goose
    if shutil.which("goose"):
        detected.append(Assistant.GOOSE)

    return detected


def get_idlergear_md_section() -> str:
    """Get the IdlerGear section to add to instruction files."""
    return """
## IdlerGear

This project uses IdlerGear for knowledge management.

### Session Start
Run this at the start of every session:
```bash
idlergear context
```

### During Development
- `idlergear task create "description"` - Create tasks
- `idlergear note create "content"` - Capture notes
- `idlergear task list` - View open tasks

### Rules
- NEVER create TODO.md, NOTES.md, or SESSION_*.md files
- NEVER write inline TODO comments
- ALWAYS use IdlerGear commands for knowledge capture
"""


def generate_gemini_md(project_path: Path) -> str:
    """Generate GEMINI.md content."""
    project_name = project_path.name
    return f"""# Gemini CLI - {project_name}

Instructions for Gemini CLI when working on this project.

## IdlerGear Integration

This project uses **IdlerGear** for knowledge management - a structured system that replaces ad-hoc files like TODO.md and NOTES.md with a command-based API.

### CRITICAL: Session Start

**Run this command at the start of EVERY session:**
```bash
idlergear context
```

This provides:
- Project vision and goals
- Current plan (if any)
- Open tasks and priorities
- Recent notes and explorations
- Reference documentation

### Core Commands

**Task Management:**
```bash
idlergear task create "description"  # Create a new task
idlergear task list                  # View all open tasks
idlergear task close <id>            # Close completed task
idlergear task show <id>             # View task details
```

**Notes & Insights:**
```bash
idlergear note create "content"      # Capture quick thought
idlergear note list                  # View all notes
idlergear note promote <id> --to task  # Convert note to task
```

**Project Context:**
```bash
idlergear vision show                # View project vision
idlergear plan show                  # View current plan
idlergear reference list             # List documentation
idlergear search "query"             # Search all knowledge
```

**File Registry (Token-Efficient):**
```bash
idlergear file deprecate old.py --successor new.py  # Mark file as deprecated
idlergear file annotate file.py --description "..." # Annotate for search
idlergear file search --query "authentication"      # Search files (93% savings!)
idlergear file status file.py                       # Check file status
```

### FORBIDDEN Patterns

**NEVER create these files:**
- TODO.md, TASKS.md
- NOTES.md, SESSION_*.md, SCRATCH.md
- BACKLOG.md, FEATURE_IDEAS.md

**NEVER write these comments:**
- `# TODO: ...`
- `# FIXME: ...`
- `// HACK: ...`
- `/* NOTE: ... */`

**ALWAYS use IdlerGear commands instead:**
```bash
# Instead of: # TODO: Add validation
idlergear task create "Add validation" --label tech-debt

# Instead of: # NOTE: API requires auth
idlergear note create "API requires auth header"

# Instead of: # FIXME: Memory leak
idlergear task create "Fix memory leak in processor" --label bug
```

### MCP Server (146 Tools)

IdlerGear provides 146 MCP tools for direct integration with Gemini CLI:
```bash
# MCP server automatically registered via ~/.gemini/settings.json

# Use MCP tools directly:
# - idlergear_task_create
# - idlergear_context
# - idlergear_file_search
# - idlergear_session_start
# ... and 142 more
```

See [MCP Tools Reference](docs/mcp-tools.md) for complete list.

### Development Workflow

1. **Start session**: `idlergear context`
2. **Check open tasks**: `idlergear task list`
3. **Work on task**: Make changes, commit
4. **Capture insights**: `idlergear note create "..."`
5. **Create new tasks**: `idlergear task create "..."`
6. **Save session**: `idlergear session-save` (optional)

### Token Efficiency

IdlerGear provides massive token savings:
- **Context**: 97% savings (15K → 570 tokens via `idlergear context --mode minimal`)
- **File Search**: 93% savings (15K → 200 tokens via file annotations)
- **Task List**: 90% savings with `--preview` flag

### Multi-Agent Coordination

If multiple AI agents work on the project:
```bash
# Start daemon for coordination
idlergear daemon start

# All agents automatically receive:
# - Registry updates (deprecated files)
# - Task changes
# - Broadcast messages
```

### Best Practices

1. ✅ **Run `idlergear context` at session start** - Always get current state
2. ✅ **Search file annotations before grep** - Save 93% tokens
3. ✅ **Create tasks immediately** - Don't defer with TODO comments
4. ✅ **Link deprecated files to successors** - Help future AI agents
5. ✅ **Annotate files proactively** - Describe purpose, tags, components

### Troubleshooting

**"Command not found: idlergear"**
- Install: `pipx install idlergear`
- Or: `pip install idlergear`

**"IdlerGear not initialized"**
- Run: `idlergear init`
- Then: `idlergear install`

**"MCP server not connected"**
- Check: `~/.gemini/settings.json`
- MCP server should be auto-registered during `idlergear install --gemini`

### Documentation

- [Full Documentation](https://github.com/marctjones/idlergear)
- [File Registry Guide](docs/guides/file-registry.md)
- [MCP Tools Reference](docs/mcp-tools.md)
- [Roadmap](ROADMAP.md)

---

**Remember**: Use IdlerGear commands, not files. It's the command-based API for AI-assisted development.
"""


def generate_copilot_md(project_path: Path) -> str:
    """Generate COPILOT.md content."""
    project_name = project_path.name
    return f"""# GitHub Copilot CLI - {project_name}

Instructions for GitHub Copilot CLI when working on this project.

## IdlerGear Integration

This project uses **IdlerGear** for knowledge management - a structured system that replaces ad-hoc files like TODO.md and NOTES.md with a command-based API.

### CRITICAL: Session Start

**Run this command at the start of EVERY session:**
```bash
idlergear context
```

This provides:
- Project vision and goals
- Current plan (if any)
- Open tasks and priorities
- Recent notes and explorations
- Reference documentation

### Core Commands

**Task Management:**
```bash
idlergear task create "description"  # Create a new task
idlergear task list                  # View all open tasks
idlergear task close <id>            # Close completed task
idlergear task show <id>             # View task details
```

**Notes & Insights:**
```bash
idlergear note create "content"      # Capture quick thought
idlergear note list                  # View all notes
idlergear note promote <id> --to task  # Convert note to task
```

**Project Context:**
```bash
idlergear vision show                # View project vision
idlergear plan show                  # View current plan
idlergear reference list             # List documentation
idlergear search "query"             # Search all knowledge
```

**File Registry (Token-Efficient):**
```bash
idlergear file deprecate old.py --successor new.py  # Mark file as deprecated
idlergear file annotate file.py --description "..." # Annotate for search
idlergear file search --query "authentication"      # Search files (93% savings!)
idlergear file status file.py                       # Check file status
```

### FORBIDDEN Patterns

**NEVER create these files:**
- TODO.md, TASKS.md
- NOTES.md, SESSION_*.md, SCRATCH.md
- BACKLOG.md, FEATURE_IDEAS.md

**NEVER write these comments:**
- `# TODO: ...`
- `# FIXME: ...`
- `// HACK: ...`
- `/* NOTE: ... */`

**ALWAYS use IdlerGear commands instead:**
```bash
# Instead of: # TODO: Add validation
idlergear task create "Add validation" --label tech-debt

# Instead of: # NOTE: API requires auth
idlergear note create "API requires auth header"

# Instead of: # FIXME: Memory leak
idlergear task create "Fix memory leak in processor" --label bug
```

### MCP Server (146 Tools)

IdlerGear provides 146 MCP tools for direct integration:
```bash
# Connect to IdlerGear MCP server
gh copilot /mcp add idlergear ~/.mcp.json

# Use MCP tools directly:
# - idlergear_task_create
# - idlergear_context
# - idlergear_file_search
# - idlergear_session_start
# ... and 142 more
```

See [MCP Tools Reference](docs/mcp-tools.md) for complete list.

### Development Workflow

1. **Start session**: `idlergear context`
2. **Check open tasks**: `idlergear task list`
3. **Work on task**: Make changes, commit
4. **Capture insights**: `idlergear note create "..."`
5. **Create new tasks**: `idlergear task create "..."`
6. **Save session**: `idlergear session-save` (optional)

### Token Efficiency

IdlerGear provides massive token savings:
- **Context**: 97% savings (15K → 570 tokens via `idlergear context --mode minimal`)
- **File Search**: 93% savings (15K → 200 tokens via file annotations)
- **Task List**: 90% savings with `--preview` flag

### Multi-Agent Coordination

If multiple AI agents work on the project:
```bash
# Start daemon for coordination
idlergear daemon start

# All agents automatically receive:
# - Registry updates (deprecated files)
# - Task changes
# - Broadcast messages
```

### Best Practices

1. ✅ **Run `idlergear context` at session start** - Always get current state
2. ✅ **Search file annotations before grep** - Save 93% tokens
3. ✅ **Create tasks immediately** - Don't defer with TODO comments
4. ✅ **Link deprecated files to successors** - Help future AI agents
5. ✅ **Annotate files proactively** - Describe purpose, tags, components

### Troubleshooting

**"Command not found: idlergear"**
- Install: `pipx install idlergear`
- Or: `pip install idlergear`

**"IdlerGear not initialized"**
- Run: `idlergear init`
- Then: `idlergear install`

**"MCP server not connected"**
- Check: `gh copilot /mcp list`
- Add: `gh copilot /mcp add idlergear ~/.mcp.json`

### Documentation

- [Full Documentation](https://github.com/marctjones/idlergear)
- [File Registry Guide](docs/guides/file-registry.md)
- [MCP Tools Reference](docs/mcp-tools.md)
- [Roadmap](ROADMAP.md)

---

**Remember**: Use IdlerGear commands, not files. It's the command-based API for AI-assisted development.
"""


def generate_goosehints(project_path: Path) -> str:
    """Generate .goosehints content for Goose."""
    project_name = project_path.name
    return f"""# Goose Hints for {project_name}

This project uses IdlerGear for knowledge management.

## Session Start
Run `idlergear context` at the start of every session.

## Commands
- Task management: `idlergear task create/list/close`
- Notes: `idlergear note create`
- Vision: `idlergear vision show`

## Rules
- Never create TODO.md or NOTES.md files
- Never write inline TODO comments
- Always use IdlerGear commands
"""


def generate_aider_conventions(project_path: Path) -> str:
    """Generate .aider.conventions.md content."""
    project_name = project_path.name
    return f"""# Aider Conventions for {project_name}

## IdlerGear Integration

This project uses IdlerGear for knowledge management.

At the start of each session, run:
```bash
idlergear context
```

### Task Management
- Create tasks: `idlergear task create "description"`
- List tasks: `idlergear task list`
- Close tasks: `idlergear task close <id>`

### Notes
- Create notes: `idlergear note create "content"`

### Rules
- Never create TODO.md, NOTES.md, or SESSION_*.md files
- Never write inline TODO/FIXME comments
- Always use IdlerGear commands for knowledge capture
"""


def add_mcp_to_gemini_settings() -> bool:
    """Add IdlerGear MCP server to Gemini CLI settings.

    Returns:
        True if added/updated, False if already configured
    """
    config_path = Path.home() / ".gemini" / "settings.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        try:
            settings = json.loads(config_path.read_text())
        except json.JSONDecodeError:
            settings = {}
    else:
        settings = {}

    # Ensure mcpServers exists
    if "mcpServers" not in settings:
        settings["mcpServers"] = {}

    if "idlergear" in settings["mcpServers"]:
        return False

    settings["mcpServers"]["idlergear"] = {
        "command": "idlergear-mcp",
        "type": "stdio",
    }

    config_path.write_text(json.dumps(settings, indent=2) + "\n")
    os.chmod(config_path, 0o600)
    return True


def add_mcp_to_goose_config() -> bool:
    """Add IdlerGear MCP server to Goose config.

    Returns:
        True if added/updated, False if already configured
    """
    import yaml

    config_path = Path.home() / ".config" / "goose" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
        except Exception:
            config = {}
    else:
        config = {}

    # Ensure extensions.mcp exists
    if "extensions" not in config:
        config["extensions"] = {}
    if "mcp" not in config["extensions"]:
        config["extensions"]["mcp"] = []

    # Check if already configured
    mcp_list = config["extensions"]["mcp"]
    for server in mcp_list:
        if isinstance(server, dict) and server.get("name") == "idlergear":
            return False

    # Add IdlerGear
    mcp_list.append(
        {
            "name": "idlergear",
            "type": "stdio",
            "command": "idlergear-mcp",
        }
    )

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    os.chmod(config_path, 0o600)
    return True


def install_for_assistant(
    assistant: Assistant,
    project_path: Optional[Path] = None,
) -> dict[str, str]:
    """Install IdlerGear integration for a specific assistant.

    Args:
        assistant: The assistant to install for
        project_path: Project directory (defaults to cwd)

    Returns:
        Dict of file -> status (created/updated/unchanged)
    """
    if project_path is None:
        project_path = Path.cwd()

    results = {}

    if assistant == Assistant.CLAUDE:
        # Use existing Claude Code installation
        from idlergear.install import (
            add_agents_md_section,
            add_claude_md_section,
            install_mcp_server,
        )

        if install_mcp_server():
            results[".mcp.json"] = "created"
        else:
            results[".mcp.json"] = "unchanged"

        if add_claude_md_section():
            results["CLAUDE.md"] = "created"
        else:
            results["CLAUDE.md"] = "unchanged"

        if add_agents_md_section():
            results["AGENTS.md"] = "created"
        else:
            results["AGENTS.md"] = "unchanged"

    elif assistant == Assistant.GEMINI:
        # Create GEMINI.md
        gemini_md = project_path / "GEMINI.md"
        if not gemini_md.exists():
            gemini_md.write_text(generate_gemini_md(project_path))
            results["GEMINI.md"] = "created"
        else:
            results["GEMINI.md"] = "unchanged"

        # Add MCP to settings
        if add_mcp_to_gemini_settings():
            results["~/.gemini/settings.json"] = "updated"
        else:
            results["~/.gemini/settings.json"] = "unchanged"

    elif assistant == Assistant.COPILOT:
        # Create COPILOT.md
        copilot_md = project_path / "COPILOT.md"
        if not copilot_md.exists():
            copilot_md.write_text(generate_copilot_md(project_path))
            results["COPILOT.md"] = "created"
        else:
            results["COPILOT.md"] = "unchanged"

        # Create agent profile
        agent_dir = Path.home() / ".copilot" / "agents"
        agent_dir.mkdir(parents=True, exist_ok=True)
        agent_file = agent_dir / "idlergear.md"
        if not agent_file.exists():
            agent_file.write_text(get_idlergear_md_section())
            results["~/.copilot/agents/idlergear.md"] = "created"
        else:
            results["~/.copilot/agents/idlergear.md"] = "unchanged"

    elif assistant == Assistant.CODEX:
        # Codex uses AGENTS.md
        from idlergear.install import add_agents_md_section

        if add_agents_md_section():
            results["AGENTS.md"] = "created"
        else:
            results["AGENTS.md"] = "unchanged"

    elif assistant == Assistant.AIDER:
        # Create .aider.conventions.md
        conventions = project_path / ".aider.conventions.md"
        if not conventions.exists():
            conventions.write_text(generate_aider_conventions(project_path))
            results[".aider.conventions.md"] = "created"
        else:
            results[".aider.conventions.md"] = "unchanged"

    elif assistant == Assistant.GOOSE:
        # Create .goosehints
        hints = project_path / ".goosehints"
        if not hints.exists():
            hints.write_text(generate_goosehints(project_path))
            results[".goosehints"] = "created"
        else:
            results[".goosehints"] = "unchanged"

        # Add MCP to config
        try:
            if add_mcp_to_goose_config():
                results["~/.config/goose/config.yaml"] = "updated"
            else:
                results["~/.config/goose/config.yaml"] = "unchanged"
        except ImportError:
            results["~/.config/goose/config.yaml"] = "skipped (pyyaml not installed)"

    return results


def install_for_all(project_path: Optional[Path] = None) -> dict[str, dict[str, str]]:
    """Install IdlerGear integration for all detected assistants.

    Args:
        project_path: Project directory (defaults to cwd)

    Returns:
        Dict of assistant -> file results
    """
    detected = detect_installed_assistants()
    results = {}

    for assistant in detected:
        results[assistant.value] = install_for_assistant(assistant, project_path)

    return results
