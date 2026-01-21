"""Cursor AI IDE integration.

Generates .cursor/rules/*.mdc files for automatic context injection.
"""

from pathlib import Path
from typing import Dict, Optional

from idlergear.config import find_idlergear_root


def generate_vision_rule() -> str:
    """Generate vision.mdc rule file content."""
    return """---
description: IdlerGear project vision and goals
globs:
  - "**/*.py"
  - "**/*.md"
  - "**/src/**"
alwaysApply: true
---

# Project Vision and Goals

When working on this project, always keep the project vision in mind.

Use `@file docs/VISION.md` or run `idlergear vision show` to see the current project vision.

Key guidelines:
- Stay aligned with project goals
- Consider long-term implications of changes
- Validate decisions against vision
"""


def generate_tasks_rule() -> str:
    """Generate tasks.mdc rule file content."""
    return """---
description: Active IdlerGear tasks and priorities
globs:
  - "**/*.py"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/src/**"
alwaysApply: false
---

# Active Tasks

Before starting work, check active tasks for context.

Run `idlergear task list` to see all open tasks.

When you complete work:
- Update task status
- Close completed tasks with `idlergear task close <id>`
- Create new tasks for discovered issues

**IMPORTANT**: Never write TODO comments. Always create tasks:
```bash
idlergear task create "Description" --label tech-debt
```
"""


def generate_context_rule() -> str:
    """Generate context.mdc rule file content."""
    return """---
description: IdlerGear project context for AI assistants
globs:
  - "**/*"
alwaysApply: true
---

# IdlerGear Project Context

This project uses IdlerGear for knowledge management.

## Quick Reference

Get full context efficiently:
```bash
idlergear context --mode minimal  # ~570 tokens
idlergear context --mode standard # ~7K tokens
```

## Core Commands

- `idlergear task create TEXT` - Create a task
- `idlergear note create TEXT` - Capture insight/learning
- `idlergear vision show` - View project goals
- `idlergear search QUERY` - Search all knowledge

## Forbidden

**Never create these files:**
- TODO.md, NOTES.md, SESSION_*.md
- Use `idlergear` commands instead

**Never write these comments:**
- `// TODO:`, `# FIXME:`, `/* HACK: */`
- Create tasks with `idlergear task create` instead

## Plugin System

This project may have plugins enabled. Check with:
```bash
idlergear plugin list
idlergear plugin status
```

Available integrations:
- Langfuse: Observability and token tracking
- LlamaIndex: Semantic search (use `idlergear plugin search`)
- Mem0: Experiential memory with pattern learning
"""


def install_cursor_rules(project_path: Optional[Path] = None) -> Dict[str, str]:
    """Install Cursor AI IDE rules (.cursor/rules/*.mdc files).

    Args:
        project_path: Project directory (defaults to IdlerGear root)

    Returns:
        Dict of {filename: action} where action is 'created', 'updated', or 'unchanged'
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    # Create .cursor/rules/ directory
    cursor_rules_dir = project_path / ".cursor" / "rules"
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    # Generate and write each rule file
    rules = {
        "idlergear-vision.mdc": generate_vision_rule(),
        "idlergear-tasks.mdc": generate_tasks_rule(),
        "idlergear-context.mdc": generate_context_rule(),
    }

    for filename, content in rules.items():
        file_path = cursor_rules_dir / filename
        action = "unchanged"

        if not file_path.exists():
            file_path.write_text(content)
            action = "created"
        else:
            # Check if content differs
            existing_content = file_path.read_text()
            if existing_content != content:
                file_path.write_text(content)
                action = "updated"

        results[str(file_path)] = action

    return results


def generate_cursorignore(project_path: Optional[Path] = None) -> str:
    """Generate .cursorignore file content.

    Args:
        project_path: Project directory (defaults to IdlerGear root)

    Returns:
        Action taken ('created', 'updated', or 'unchanged')
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    cursorignore_path = project_path / ".cursorignore"

    content = """# IdlerGear internal directories
.idlergear/
.claude/hooks/
.claude/scripts/

# Build artifacts
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Dependencies
node_modules/
"""

    action = "unchanged"

    if not cursorignore_path.exists():
        cursorignore_path.write_text(content)
        action = "created"
    else:
        existing_content = cursorignore_path.read_text()
        if existing_content != content:
            # Append IdlerGear section if not present
            if ".idlergear/" not in existing_content:
                with open(cursorignore_path, "a") as f:
                    f.write("\n# IdlerGear internal directories\n")
                    f.write(".idlergear/\n")
                    f.write(".claude/hooks/\n")
                    f.write(".claude/scripts/\n")
                action = "updated"

    return action
