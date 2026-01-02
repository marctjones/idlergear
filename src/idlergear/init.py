"""Initialize IdlerGear in a project directory."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from idlergear.schema import SCHEMA_VERSION, IdlerGearSchema, create_empty_index

DEFAULT_CONFIG = f"""\
# IdlerGear configuration
# Schema version: {SCHEMA_VERSION}

[project]
name = ""

[github]
# repo = "owner/repo"
# token = ""  # Or use GITHUB_TOKEN env var

[daemon]
auto_start = true
"""

DEFAULT_VISION = """\
# Project Vision

<!--
Define your project's purpose and direction here.
This is the north star for AI assistants and team members.

Questions to answer:
- What problem does this project solve?
- Who is it for?
- What are the key principles?
- What does success look like?
-->

## Purpose

[Your project purpose here]

## Principles

1. [First principle]
2. [Second principle]

## Goals

- [ ] [First goal]
- [ ] [Second goal]
"""


def init_project(path: str = ".") -> None:
    """Initialize .idlergear directory structure (v0.3 schema)."""
    project_path = Path(path).resolve()
    schema = IdlerGearSchema(project_path)

    if schema.exists():
        typer.secho(
            f"IdlerGear already initialized in {project_path}",
            fg=typer.colors.YELLOW,
        )
        # Check if migration is needed
        if schema.needs_migration():
            typer.echo("")
            typer.secho(
                "Note: Your project uses an older schema. Run 'idlergear migrate' to update.",
                fg=typer.colors.CYAN,
            )
        return

    # Create v0.3 directory structure
    for directory in schema.get_all_directories():
        directory.mkdir(parents=True, exist_ok=True)

    # Create config file
    schema.config_file.write_text(DEFAULT_CONFIG)

    # Create vision file in vision/ directory
    schema.vision_file.write_text(DEFAULT_VISION)

    # Create empty index files
    for index_path in [schema.issues_index, schema.wiki_index, schema.plans_index]:
        index_path.write_text(json.dumps(create_empty_index(), indent=2))

    # Add .idlergear to .gitignore exceptions if .gitignore exists
    gitignore_path = project_path / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        additions = []
        # Check if we need to add daemon files to gitignore
        if ".idlergear/daemon.sock" not in content:
            additions.append("\n# IdlerGear daemon files (don't commit)")
            additions.append(".idlergear/daemon.sock")
            additions.append(".idlergear/daemon.pid")
        # Add sync state to gitignore (ephemeral)
        if ".idlergear/sync/" not in content:
            additions.append(".idlergear/sync/")

        if additions:
            with open(gitignore_path, "a") as f:
                f.write("\n".join(additions) + "\n")

    typer.secho(
        f"Initialized IdlerGear v{SCHEMA_VERSION} in {project_path}",
        fg=typer.colors.GREEN,
    )
    typer.echo(f"  Created: {schema.idlergear_dir}")
    typer.echo("")
    typer.echo("Directory structure:")
    typer.echo("  .idlergear/")
    typer.echo("  ├── config.toml       # Configuration")
    typer.echo("  ├── issues/           # Local issue tracking")
    typer.echo("  ├── wiki/             # Knowledge base")
    typer.echo("  ├── notes/            # Quick notes")
    typer.echo("  ├── plans/            # Implementation plans")
    typer.echo("  ├── runs/             # Script execution logs")
    typer.echo("  ├── vision/           # Project vision")
    typer.echo("  ├── projects/         # Kanban boards")
    typer.echo("  └── sync/             # External sync state")
    typer.echo("")
    typer.echo("Next steps:")
    typer.echo("  idlergear vision edit     # Set your project vision")
    typer.echo("  idlergear task create     # Create your first task")
    typer.echo("  idlergear install         # Install Claude Code integration")
