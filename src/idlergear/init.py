"""Initialize IdlerGear in a project directory."""

import os
from pathlib import Path

import typer

DEFAULT_CONFIG = """\
# IdlerGear configuration

[project]
name = ""

[github]
# repo = "owner/repo"
# token = ""  # Or use GITHUB_TOKEN env var

[daemon]
auto_start = true
"""


def init_project(path: str = ".") -> None:
    """Initialize .idlergear directory structure."""
    project_path = Path(path).resolve()
    idlergear_path = project_path / ".idlergear"

    if idlergear_path.exists():
        typer.secho(
            f"IdlerGear already initialized in {project_path}",
            fg=typer.colors.YELLOW,
        )
        return

    # Create directory structure
    directories = [
        idlergear_path,
        idlergear_path / "tasks",
        idlergear_path / "notes",
        idlergear_path / "explorations",
        idlergear_path / "plans",
        idlergear_path / "reference",
        idlergear_path / "runs",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    # Create config file
    config_path = idlergear_path / "config.toml"
    config_path.write_text(DEFAULT_CONFIG)

    # Create empty vision file
    vision_path = idlergear_path / "vision.md"
    vision_path.write_text("# Project Vision\n\n")

    # Add .idlergear to .gitignore exceptions if .gitignore exists
    gitignore_path = project_path / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        # Check if we need to add daemon files to gitignore
        if ".idlergear/daemon.sock" not in content:
            with open(gitignore_path, "a") as f:
                f.write("\n# IdlerGear daemon files (don't commit)\n")
                f.write(".idlergear/daemon.sock\n")
                f.write(".idlergear/daemon.pid\n")

    typer.secho(
        f"✓ Initialized IdlerGear in {project_path}",
        fg=typer.colors.GREEN,
    )
    typer.echo(f"  Created: {idlergear_path}")
    typer.echo("")
    typer.echo("Next steps:")
    typer.echo("  idlergear vision edit     # Set your project vision")
    typer.echo("  idlergear task create     # Create your first task")
