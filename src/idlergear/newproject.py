"""Create new projects with IdlerGear integration."""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from idlergear.templates.base import (
    AGENTS_MD,
    CLAUDE_COMMAND_CONTEXT,
    CLAUDE_MD,
    CLAUDE_RULES_IDLERGEAR,
    CLAUDE_SETTINGS,
    GITIGNORE,
    MCP_CONFIG,
)


def slugify_package(name: str) -> str:
    """Convert project name to valid Python package name."""
    return name.lower().replace("-", "_").replace(" ", "_")


def create_project(
    name: str,
    path: str | None = None,
    template: str = "base",
    vision: str = "",
    description: str = "",
    init_git: bool = True,
    init_venv: bool = True,
) -> Path:
    """Create a new project with IdlerGear integration.

    Args:
        name: Project name
        path: Directory to create project in (default: current directory)
        template: Project template ("base", "python")
        vision: Initial project vision text
        description: Short project description
        init_git: Initialize git repository
        init_venv: Create Python virtual environment (for python template)

    Returns:
        Path to created project directory
    """
    # Determine project path
    if path is None:
        project_path = Path.cwd() / name
    else:
        project_path = Path(path) / name

    if project_path.exists():
        raise ValueError(f"Directory already exists: {project_path}")

    # Create base directory
    project_path.mkdir(parents=True)

    # Set defaults
    if not vision:
        vision = f"# {name}\n\nDescribe your project vision here."
    if not description:
        description = f"A new project: {name}"

    # Create base structure
    _create_base_structure(project_path, name, vision, description)

    # Apply template-specific files
    if template == "python":
        _create_python_structure(project_path, name, description, init_venv)
    elif template != "base":
        raise ValueError(f"Unknown template: {template}")

    # Initialize git
    if init_git:
        _init_git(project_path)

    return project_path


def _create_base_structure(
    project_path: Path, name: str, vision: str, description: str
) -> None:
    """Create base project structure common to all templates."""
    from idlergear.schema import IdlerGearSchema

    # Use schema to create correct v0.3 structure
    schema = IdlerGearSchema(project_path)

    # Create all directories from schema
    for dir_path in schema.get_all_directories():
        dir_path.mkdir(parents=True, exist_ok=True)

    # .idlergear/config.toml
    config_content = f"""\
# IdlerGear configuration

[project]
name = "{name}"

[github]
# repo = "owner/repo"
# token = ""  # Or use GITHUB_TOKEN env var
"""
    schema.config_file.write_text(config_content)

    # .idlergear/vision/VISION.md
    schema.vision_file.write_text(vision)

    # .claude/ directory
    claude_path = project_path / ".claude"
    claude_path.mkdir()
    (claude_path / "rules").mkdir()
    (claude_path / "commands").mkdir()

    # .claude/settings.json
    with open(claude_path / "settings.json", "w") as f:
        json.dump(CLAUDE_SETTINGS, f, indent=2)
        f.write("\n")

    # .claude/CLAUDE.md (symlink would be better but use copy for compatibility)
    claude_md_content = CLAUDE_MD.format(project_name=name, vision=vision)
    (claude_path / "CLAUDE.md").write_text(claude_md_content)

    # .claude/rules/idlergear.md
    (claude_path / "rules" / "idlergear.md").write_text(CLAUDE_RULES_IDLERGEAR)

    # .claude/commands/ig_context.md - /ig_context slash command
    (claude_path / "commands" / "ig_context.md").write_text(CLAUDE_COMMAND_CONTEXT)

    # Root CLAUDE.md (Claude Code also looks here)
    (project_path / "CLAUDE.md").write_text(claude_md_content)

    # .mcp.json
    with open(project_path / ".mcp.json", "w") as f:
        json.dump(MCP_CONFIG, f, indent=2)
        f.write("\n")

    # AGENTS.md (for compatibility with other AI tools)
    agents_content = AGENTS_MD.format(vision=vision)
    (project_path / "AGENTS.md").write_text(agents_content)

    # .gitignore
    (project_path / ".gitignore").write_text(GITIGNORE)


def _create_python_structure(
    project_path: Path, name: str, description: str, init_venv: bool
) -> None:
    """Create Python-specific project structure."""
    from idlergear.templates.python import (
        CLAUDE_RULES_PYTHON,
        CLAUDE_SETTINGS_PYTHON,
        GITIGNORE_PYTHON,
        PYPROJECT_TOML,
        README_MD,
        SRC_INIT,
        TEST_PLACEHOLDER,
        TESTS_INIT,
        VENV_ACTIVATE_HOOK,
    )

    package_name = slugify_package(name)

    # Append Python gitignore
    gitignore_path = project_path / ".gitignore"
    current = gitignore_path.read_text()
    gitignore_path.write_text(current + "\n" + GITIGNORE_PYTHON)

    # pyproject.toml
    pyproject_content = PYPROJECT_TOML.format(
        project_name=name,
        package_name=package_name,
        description=description,
    )
    (project_path / "pyproject.toml").write_text(pyproject_content)

    # README.md
    readme_content = README_MD.format(
        project_name=name,
        description=description,
    )
    (project_path / "README.md").write_text(readme_content)

    # src/<package>/
    src_path = project_path / "src" / package_name
    src_path.mkdir(parents=True)
    (src_path / "__init__.py").write_text(SRC_INIT.format(project_name=name))

    # tests/
    tests_path = project_path / "tests"
    tests_path.mkdir()
    (tests_path / "__init__.py").write_text(TESTS_INIT.format(project_name=name))
    (tests_path / "test_placeholder.py").write_text(TEST_PLACEHOLDER)

    # .claude/rules/ig_python.md
    (project_path / ".claude" / "rules" / "ig_python.md").write_text(CLAUDE_RULES_PYTHON)

    # Create venv
    if init_venv:
        try:
            subprocess.run(
                ["python3", "-m", "venv", "venv"],
                cwd=project_path,
                check=True,
                capture_output=True,
            )
            venv_created = True
        except subprocess.CalledProcessError:
            # Venv creation failed, continue without it
            venv_created = False
    else:
        venv_created = False

    # Update .claude/settings.json with Python-specific settings
    if venv_created:
        claude_settings_path = project_path / ".claude" / "settings.json"
        with open(claude_settings_path) as f:
            settings = json.load(f)

        # Merge Python settings
        settings["env"] = CLAUDE_SETTINGS_PYTHON["env"]

        # Add SessionStart hook for venv activation
        hooks_dir = project_path / ".claude" / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        activate_script = hooks_dir / "ig_activate-venv.sh"
        activate_script.write_text(VENV_ACTIVATE_HOOK)
        activate_script.chmod(0o755)

        settings["hooks"] = {
            "SessionStart": [
                {
                    "matcher": ".*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "./.claude/hooks/ig_activate-venv.sh",
                        }
                    ],
                }
            ]
        }

        with open(claude_settings_path, "w") as f:
            json.dump(settings, f, indent=2)
            f.write("\n")


def _init_git(project_path: Path) -> None:
    """Initialize git repository."""
    try:
        subprocess.run(
            ["git", "init"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "add", "."],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit with IdlerGear integration"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        # Git init failed, continue without it
        pass
    except FileNotFoundError:
        # Git not installed
        pass
