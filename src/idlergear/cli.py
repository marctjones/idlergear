"""IdlerGear CLI - Command-line interface."""

from importlib.metadata import version as get_version

import typer

__version__ = get_version("idlergear")


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"idlergear {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="idlergear",
    help="Knowledge management API for AI-assisted development.",
    no_args_is_help=True,
)


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V", callback=version_callback, is_eager=True,
        help="Show version and exit."
    ),
) -> None:
    """IdlerGear - Knowledge management for AI-assisted development."""
    pass


# Sub-command groups
task_app = typer.Typer(help="Task management (→ GitHub Issues)")
note_app = typer.Typer(help="Quick notes capture")
explore_app = typer.Typer(help="Explorations (→ GitHub Discussions)")
vision_app = typer.Typer(help="Project vision management")
plan_app = typer.Typer(help="Plan management (→ GitHub Projects)")
reference_app = typer.Typer(help="Reference docs (→ GitHub Wiki)")
run_app = typer.Typer(help="Script execution and logs")
config_app = typer.Typer(help="Configuration management")
daemon_app = typer.Typer(help="Daemon control")
mcp_app = typer.Typer(help="MCP server management")
project_app = typer.Typer(help="Kanban project boards (→ GitHub Projects v2)")

app.add_typer(task_app, name="task")
app.add_typer(note_app, name="note")
app.add_typer(explore_app, name="explore")
app.add_typer(vision_app, name="vision")
app.add_typer(plan_app, name="plan")
app.add_typer(reference_app, name="reference")
app.add_typer(run_app, name="run")
app.add_typer(config_app, name="config")
app.add_typer(daemon_app, name="daemon")
app.add_typer(mcp_app, name="mcp")
app.add_typer(project_app, name="project")


@app.command()
def init(
    path: str = typer.Argument(".", help="Project directory to initialize"),
    skip_github: bool = typer.Option(False, "--skip-github", help="Skip GitHub detection"),
):
    """Initialize IdlerGear in an existing project directory.

    After initialization, automatically detects if you're in a GitHub
    repository and offers to configure GitHub backends.
    """
    from idlergear.init import init_project

    init_project(path)

    if skip_github:
        return

    # Auto-detect GitHub and offer to configure
    from idlergear.github_detect import detect_github_features, get_recommended_backends
    from idlergear.config import set_config_value
    from pathlib import Path

    project_path = Path(path).resolve()
    features = detect_github_features(project_path)

    if features.is_github_repo and not features.error:
        typer.echo("")
        typer.secho(f"Detected GitHub repository: {features.repo_name}", fg=typer.colors.CYAN)

        recommendations = get_recommended_backends(features)
        if recommendations:
            feature_list = []
            if features.has_issues:
                feature_list.append("Issues")
            if features.has_discussions:
                feature_list.append("Discussions")

            typer.echo(f"Available: {', '.join(feature_list)}")
            typer.echo("")

            if typer.confirm("Use GitHub for tasks and explorations?", default=True):
                for backend_type, backend_name in recommendations.items():
                    set_config_value(f"backends.{backend_type}", backend_name, project_path=project_path)
                    typer.secho(f"  ✓ {backend_type} → {backend_name}", fg=typer.colors.GREEN)
            else:
                typer.echo("Using local backends. Run 'idlergear setup-github' anytime to reconfigure.")


@app.command()
def search(
    query: str,
    types: list[str] = typer.Option(
        [],
        "--type",
        "-t",
        help="Types to search: task, note, reference, plan",
    ),
):
    """Search across all knowledge types."""
    from idlergear.config import find_idlergear_root
    from idlergear.search import search_all

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    results = search_all(query, types=types if types else None)

    if not results:
        typer.echo(f"No results found for '{query}'.")
        return

    typer.echo(f"Found {len(results)} result(s) for '{query}':\n")

    # Group by type
    by_type: dict[str, list] = {}
    for result in results:
        t = result["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(result)

    type_colors = {
        "task": typer.colors.GREEN,
        "note": typer.colors.YELLOW,
        "reference": typer.colors.MAGENTA,
        "plan": typer.colors.BLUE,
    }

    for type_name, items in by_type.items():
        typer.secho(f"{type_name.upper()}S ({len(items)})", fg=type_colors.get(type_name, typer.colors.WHITE), bold=True)
        for item in items:
            id_str = f"#{item.get('id', item.get('name', '?'))}"
            title = item.get("title", "")
            preview = item.get("preview", "")[:60]
            typer.echo(f"  {id_str:8}  {title}")
            if preview and preview != title:
                typer.echo(f"            {preview}")
        typer.echo("")


@app.command()
def context(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Include more detail"),
    include_refs: bool = typer.Option(False, "--refs", "-r", help="Include reference documents"),
):
    """Show project context for AI session start.

    Gathers and displays all relevant project knowledge in one command:
    - Vision (project purpose and direction)
    - Current plan (what we're working on)
    - Open tasks (prioritized)
    - Open explorations (research in progress)
    - Recent notes (quick captures)

    Run this at the start of each AI session to understand the project.

    Examples:
        idlergear context           # Quick overview
        idlergear context --json    # For programmatic consumption
        idlergear context --refs    # Include reference documents
    """
    import json

    from idlergear.config import find_idlergear_root
    from idlergear.context import format_context, format_context_json, gather_context

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    ctx = gather_context(include_references=include_refs)

    if json_output:
        typer.echo(json.dumps(format_context_json(ctx), indent=2))
    else:
        typer.echo(format_context(ctx, verbose=verbose))


@app.command()
def status(
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed dashboard"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Show unified project status dashboard.

    Quick one-line summary of tasks, notes, runs, and git status.

    Examples:
        idlergear status              # One-line summary
        idlergear status --detailed   # Full dashboard
        idlergear status --json       # JSON output for tools
    """
    from idlergear.config import find_idlergear_root
    from idlergear.status import show_status

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    show_status(detailed=detailed, json_output=json_output)


@app.command()
def check(
    file: str = typer.Option(None, "--file", "-f", help="File to check for violations"),
    no_todos: bool = typer.Option(False, "--no-todos", help="Check for TODO comments"),
    no_forbidden: bool = typer.Option(False, "--no-forbidden", help="Check for forbidden files"),
    context_reminder: bool = typer.Option(False, "--context-reminder", help="Remind to run context at session start"),
    structure: bool = typer.Option(False, "--structure", help="Check .idlergear/ directory structure"),
    files: bool = typer.Option(False, "--files", help="Check for misplaced files in project root"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only output on violations"),
):
    """Check for IdlerGear policy violations and structure issues.

    Used by hooks to enforce IdlerGear usage:
    - Block TODO comments in code
    - Block forbidden files (TODO.md, NOTES.md, etc.)
    - Remind to run context at session start
    - Validate .idlergear/ directory structure
    - Find misplaced files that should be organized

    Examples:
        idlergear check --file src/main.py --quiet
        idlergear check --no-todos
        idlergear check --context-reminder
        idlergear check --structure       # Validate directory structure
        idlergear check --files           # Find misplaced files
    """
    from pathlib import Path
    import re

    violations = []

    # Check .idlergear/ structure (v0.3)
    if structure:
        from idlergear.config import find_idlergear_root
        from idlergear.schema import IdlerGearSchema

        root = find_idlergear_root()
        if root is None:
            violations.append("Not in an IdlerGear project")
        else:
            schema = IdlerGearSchema(root)
            result = schema.validate()

            if result["missing"]:
                violations.append("Missing directories (run 'idlergear migrate' to fix):")
                for d in result["missing"]:
                    violations.append(f"  {d}")

            if result["legacy"]:
                if not quiet:
                    typer.secho("Legacy directories found (run 'idlergear migrate'):", fg=typer.colors.YELLOW)
                    for d in result["legacy"]:
                        typer.echo(f"  {d}")

    # Check for misplaced files
    if files:
        from idlergear.config import find_idlergear_root
        from idlergear.schema import detect_misplaced_files

        root = find_idlergear_root()
        if root is None:
            violations.append("Not in an IdlerGear project")
        else:
            misplaced = detect_misplaced_files(root)
            if misplaced:
                violations.append("Misplaced files found:")
                for item in misplaced:
                    violations.append(f"  {item['name']}: {item['action']}")

    # Check file for TODO comments
    if file:
        file_path = Path(file)
        if file_path.exists() and file_path.is_file():
            try:
                content = file_path.read_text()
                # Check for TODO patterns
                todo_patterns = [
                    r'//\s*TODO:',
                    r'#\s*TODO:',
                    r'/\*\s*TODO:',
                    r'//\s*FIXME:',
                    r'#\s*FIXME:',
                    r'/\*\s*FIXME:',
                    r'//\s*HACK:',
                    r'#\s*HACK:',
                    r'/\*\s*HACK:',
                    r'<!--\s*TODO:',
                ]
                for pattern in todo_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        violations.append(f"TODO/FIXME/HACK comment found in {file}")
                        violations.append("Use: idlergear task create \"...\" --label tech-debt")
                        break
            except Exception:
                pass  # Can't read file, skip

        # Check for forbidden file names
        forbidden_files = [
            "TODO.md", "TODO.txt", "TASKS.md",
            "NOTES.md", "SCRATCH.md", "BACKLOG.md",
            "FEATURE_IDEAS.md", "RESEARCH.md",
        ]
        if file_path.name in forbidden_files:
            violations.append(f"Forbidden file: {file_path.name}")
            violations.append("Use IdlerGear commands instead:")
            violations.append("  idlergear task create \"...\"")
            violations.append("  idlergear note create \"...\"")

        if file_path.name.startswith("SESSION_") and file_path.suffix == ".md":
            violations.append(f"Forbidden file pattern: {file_path.name}")
            violations.append("Use: idlergear note create \"...\"")

    # Check for forbidden files in project
    if no_forbidden:
        from idlergear.config import find_idlergear_root
        root = find_idlergear_root()
        if root:
            forbidden = [
                "TODO.md", "TODO.txt", "TASKS.md",
                "NOTES.md", "SCRATCH.md", "BACKLOG.md",
            ]
            for f in forbidden:
                if (root / f).exists():
                    violations.append(f"Forbidden file exists: {f}")

    # Grep for TODO comments in project
    if no_todos:
        from idlergear.config import find_idlergear_root
        root = find_idlergear_root()
        if root:
            import subprocess
            result = subprocess.run(
                ["grep", "-rn", "-E", r"(//|#|/\*)\s*(TODO|FIXME|HACK):", str(root),
                 "--include=*.py", "--include=*.js", "--include=*.ts", "--include=*.go",
                 "--include=*.rs", "--include=*.java", "--include=*.c", "--include=*.cpp"],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                violations.append("TODO/FIXME/HACK comments found:")
                for line in result.stdout.strip().split("\n")[:5]:
                    violations.append(f"  {line}")
                violations.append("Use: idlergear task create \"...\" --label tech-debt")

    # Context reminder
    if context_reminder:
        if not quiet:
            typer.secho("REMINDER: Run 'idlergear context' at session start", fg=typer.colors.CYAN)

    # Report violations
    if violations:
        for v in violations:
            typer.secho(v, fg=typer.colors.RED)
        raise typer.Exit(1)
    elif not quiet and not context_reminder:
        typer.secho("No violations found.", fg=typer.colors.GREEN)


@app.command()
def migrate(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be done without making changes"),
):
    """Migrate .idlergear/ to v0.3 schema.

    Performs the following migrations:
    - tasks/ → issues/
    - reference/ → wiki/
    - vision.md → vision/VISION.md
    - Removes empty explorations/ (notes use tags now)
    - Creates missing directories (sync/, projects/)

    Examples:
        idlergear migrate --dry-run   # Preview changes
        idlergear migrate             # Perform migration
    """
    from pathlib import Path
    import shutil

    from idlergear.config import find_idlergear_root
    from idlergear.schema import IdlerGearSchema, SCHEMA_VERSION

    root = find_idlergear_root()
    if root is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    schema = IdlerGearSchema(root)

    if not schema.needs_migration():
        typer.secho(f"Already on v{SCHEMA_VERSION} schema. Nothing to migrate.", fg=typer.colors.GREEN)
        return

    actions = []

    # Check tasks/ → issues/
    if schema.legacy_tasks_dir.exists() and not schema.issues_dir.exists():
        actions.append(("rename", schema.legacy_tasks_dir, schema.issues_dir, "tasks/ → issues/"))

    # Check reference/ → wiki/
    if schema.legacy_reference_dir.exists() and not schema.wiki_dir.exists():
        actions.append(("rename", schema.legacy_reference_dir, schema.wiki_dir, "reference/ → wiki/"))

    # Check vision.md → vision/VISION.md
    if schema.legacy_vision_file.exists() and not schema.vision_file.exists():
        actions.append(("move", schema.legacy_vision_file, schema.vision_file, "vision.md → vision/VISION.md"))

    # Check explorations/ (if empty, remove; otherwise prompt)
    if schema.legacy_explorations_dir.exists():
        exploration_files = list(schema.legacy_explorations_dir.glob("*.md"))
        if not exploration_files:
            actions.append(("remove", schema.legacy_explorations_dir, None, "Remove empty explorations/"))
        else:
            actions.append(("warn", schema.legacy_explorations_dir, None,
                           f"explorations/ has {len(exploration_files)} files - convert to notes with 'explore' tag"))

    # Create missing v0.3 directories
    for dir_path in schema.get_all_directories():
        if not dir_path.exists():
            actions.append(("create", dir_path, None, f"Create {dir_path.name}/"))

    if not actions:
        typer.secho(f"Already on v{SCHEMA_VERSION} schema. Nothing to migrate.", fg=typer.colors.GREEN)
        return

    # Show planned actions
    typer.echo(f"Migration to v{SCHEMA_VERSION}:")
    typer.echo("")

    for action_type, source, target, description in actions:
        if action_type == "warn":
            typer.secho(f"  WARNING: {description}", fg=typer.colors.YELLOW)
        else:
            typer.echo(f"  {description}")

    if dry_run:
        typer.echo("")
        typer.secho("Dry run - no changes made.", fg=typer.colors.CYAN)
        return

    typer.echo("")

    # Execute actions
    for action_type, source, target, description in actions:
        if action_type == "rename":
            source.rename(target)
            typer.secho(f"  ✓ {description}", fg=typer.colors.GREEN)
        elif action_type == "move":
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            typer.secho(f"  ✓ {description}", fg=typer.colors.GREEN)
        elif action_type == "remove":
            source.rmdir()
            typer.secho(f"  ✓ {description}", fg=typer.colors.GREEN)
        elif action_type == "create":
            source.mkdir(parents=True, exist_ok=True)
            typer.secho(f"  ✓ {description}", fg=typer.colors.GREEN)
        elif action_type == "warn":
            typer.secho(f"  ! {description}", fg=typer.colors.YELLOW)

    typer.echo("")
    typer.secho(f"Migration to v{SCHEMA_VERSION} complete!", fg=typer.colors.GREEN)


@app.command()
def new(
    name: str = typer.Argument(..., help="Project name"),
    path: str = typer.Option(None, "--path", "-p", help="Parent directory (default: current)"),
    template: str = typer.Option("base", "--template", "-t", help="Template: base, python"),
    python: bool = typer.Option(False, "--python", help="Shortcut for --template python"),
    vision: str = typer.Option("", "--vision", "-v", help="Initial project vision"),
    description: str = typer.Option("", "--description", "-d", help="Short description"),
    no_git: bool = typer.Option(False, "--no-git", help="Skip git initialization"),
    no_venv: bool = typer.Option(False, "--no-venv", help="Skip venv creation (Python only)"),
):
    """Create a new project with full IdlerGear + Claude Code integration.

    Creates a new directory with:
    - Git repository
    - .idlergear/ for knowledge management
    - .claude/ with settings protecting idlergear files
    - .mcp.json for MCP server registration
    - AGENTS.md for AI tool compatibility
    - Template-specific files (e.g., pyproject.toml for Python)

    Examples:
        idlergear new myproject --python
        idlergear new myapi --template python --vision "Build a REST API"
    """
    from idlergear.newproject import create_project

    # Handle --python shortcut
    if python:
        template = "python"

    try:
        project_path = create_project(
            name=name,
            path=path,
            template=template,
            vision=vision,
            description=description,
            init_git=not no_git,
            init_venv=not no_venv,
        )
        typer.secho(f"Created project: {project_path}", fg=typer.colors.GREEN)
        typer.echo("")
        typer.echo("Next steps:")
        typer.echo(f"  cd {name}")
        typer.echo("  claude                    # Start Claude Code")
        typer.echo("  idlergear vision edit     # Set your project vision")
        typer.echo("  idlergear task create ... # Create your first task")
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command("setup-github")
def setup_github(
    auto_yes: bool = typer.Option(False, "--yes", "-y", help="Auto-accept all recommendations"),
    check_only: bool = typer.Option(False, "--check", help="Only check, don't configure"),
):
    """Detect GitHub features and configure backends.

    Automatically detects if you're in a GitHub repository and what
    features are available (Issues, Discussions, Wiki, Projects).
    Then offers to configure IdlerGear to use those features.

    Examples:
        idlergear setup-github           # Interactive setup
        idlergear setup-github --yes     # Accept all recommendations
        idlergear setup-github --check   # Just show what's available
    """
    from idlergear.config import find_idlergear_root, set_config_value
    from idlergear.github_detect import (
        detect_github_features,
        format_features_summary,
        get_recommended_backends,
    )

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo("Detecting GitHub features...")
    features = detect_github_features()

    typer.echo("")
    typer.echo(format_features_summary(features))
    typer.echo("")

    if features.error or not features.is_github_repo:
        if not check_only:
            typer.echo("Using local backends (default).")
        raise typer.Exit(0)

    recommendations = get_recommended_backends(features)

    if not recommendations:
        typer.echo("No GitHub backends recommended for current features.")
        raise typer.Exit(0)

    if check_only:
        typer.echo("Recommended backend configuration:")
        for backend_type, backend_name in recommendations.items():
            typer.echo(f"  {backend_type}: {backend_name}")
        raise typer.Exit(0)

    # Apply recommendations
    typer.echo("Recommended backends:")
    for backend_type, backend_name in recommendations.items():
        typer.echo(f"  {backend_type} → {backend_name}")

    typer.echo("")

    if auto_yes:
        apply = True
    else:
        apply = typer.confirm("Apply these settings?", default=True)

    if apply:
        for backend_type, backend_name in recommendations.items():
            set_config_value(f"backends.{backend_type}", backend_name)
            typer.secho(f"  ✓ Set {backend_type} backend to {backend_name}", fg=typer.colors.GREEN)
        typer.echo("")
        typer.secho("GitHub backends configured!", fg=typer.colors.GREEN)
        typer.echo("Your tasks and explorations will now sync with GitHub Issues.")
    else:
        typer.echo("No changes made. You can run 'idlergear config backend' to configure manually.")


@app.command()
def serve():
    """Start the MCP server for AI tool integration."""
    from idlergear.mcp_server import main

    main()


@app.command()
def uninstall(
    remove_data: bool = typer.Option(
        False,
        "--remove-data",
        help="Also remove .idlergear directory with all tasks, notes, etc.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be removed without doing it",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
):
    """Remove IdlerGear from the current project.

    Removes:
    - MCP server registration from .mcp.json
    - IdlerGear section from AGENTS.md
    - Protected paths from .claude/settings.json

    By default, keeps the .idlergear directory with your data.
    Use --remove-data to also delete all tasks, notes, etc.

    Examples:
        idlergear uninstall              # Remove config, keep data
        idlergear uninstall --remove-data  # Remove everything
        idlergear uninstall --dry-run    # See what would be removed
    """
    from pathlib import Path

    from idlergear.uninstall import uninstall_idlergear

    project_path = Path.cwd()
    idlergear_dir = project_path / ".idlergear"

    if not idlergear_dir.exists():
        typer.secho("No IdlerGear installation found in this directory.", fg=typer.colors.YELLOW)
        raise typer.Exit(0)

    # Check what would be removed
    results = uninstall_idlergear(project_path, remove_data=remove_data, dry_run=True)

    if not any(results.values()):
        typer.echo("Nothing to remove.")
        raise typer.Exit(0)

    # Show what will be removed
    typer.echo("The following will be removed:" if not dry_run else "Would remove:")
    if results["mcp_config"]:
        typer.echo("  • IdlerGear from .mcp.json")
    if results["claude_md"]:
        typer.echo("  • IdlerGear section from CLAUDE.md")
    if results["agents_md"]:
        typer.echo("  • IdlerGear section from AGENTS.md")
    if results["rules_file"]:
        typer.echo("  • .claude/rules/idlergear.md")
    if results["claude_settings"]:
        typer.echo("  • Protected paths from .claude/settings.json")
    if results["idlergear_data"]:
        typer.secho("  • .idlergear/ directory (ALL DATA)", fg=typer.colors.RED, bold=True)

    if dry_run:
        raise typer.Exit(0)

    typer.echo("")

    # Confirm
    if not force:
        if remove_data:
            typer.secho(
                "WARNING: This will permanently delete all your tasks, notes, explorations, and references!",
                fg=typer.colors.RED,
            )
        if not typer.confirm("Proceed with uninstall?", default=False):
            typer.echo("Cancelled.")
            raise typer.Exit(0)

    # Do it
    results = uninstall_idlergear(project_path, remove_data=remove_data, dry_run=False)

    typer.echo("")
    typer.echo("Removed:")
    if results["mcp_config"]:
        typer.secho("  ✓ IdlerGear from .mcp.json", fg=typer.colors.GREEN)
    if results["claude_md"]:
        typer.secho("  ✓ IdlerGear section from CLAUDE.md", fg=typer.colors.GREEN)
    if results["agents_md"]:
        typer.secho("  ✓ IdlerGear section from AGENTS.md", fg=typer.colors.GREEN)
    if results["rules_file"]:
        typer.secho("  ✓ .claude/rules/idlergear.md", fg=typer.colors.GREEN)
    if results["claude_settings"]:
        typer.secho("  ✓ Protected paths from .claude/settings.json", fg=typer.colors.GREEN)
    if results["idlergear_data"]:
        typer.secho("  ✓ .idlergear/ directory", fg=typer.colors.GREEN)

    typer.echo("")
    if not remove_data and idlergear_dir.exists():
        typer.echo("Note: .idlergear/ directory preserved. Use --remove-data to delete it.")
    typer.secho("IdlerGear uninstalled.", fg=typer.colors.GREEN)


@app.command()
def install(
    skip_agents: bool = typer.Option(False, "--skip-agents", help="Skip AGENTS.md update"),
    skip_claude: bool = typer.Option(False, "--skip-claude", help="Skip CLAUDE.md update"),
    skip_rules: bool = typer.Option(False, "--skip-rules", help="Skip .claude/rules/ creation"),
    skip_hooks: bool = typer.Option(False, "--skip-hooks", help="Skip .claude/hooks.json creation"),
    skip_commands: bool = typer.Option(False, "--skip-commands", help="Skip /start command creation"),
):
    """Install IdlerGear integration for Claude Code.

    Creates:
    - .mcp.json - MCP server registration
    - CLAUDE.md - Usage instructions
    - AGENTS.md - AI agent instructions
    - .claude/rules/idlergear.md - Enforcement rules
    - .claude/hooks.json - Enforcement hooks
    - .claude/commands/start.md - /start slash command
    """
    from idlergear.config import find_idlergear_root
    from idlergear.install import (
        add_agents_md_section,
        add_claude_md_section,
        add_hooks_config,
        add_rules_file,
        add_start_command,
        install_mcp_server,
    )

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Install MCP server
    if install_mcp_server():
        typer.secho("Added idlergear to .mcp.json", fg=typer.colors.GREEN)
    else:
        typer.echo(".mcp.json already has idlergear configured")

    # Add CLAUDE.md section
    if not skip_claude:
        if add_claude_md_section():
            typer.secho("Added IdlerGear section to CLAUDE.md", fg=typer.colors.GREEN)
        else:
            typer.echo("CLAUDE.md already has IdlerGear section")

    # Add AGENTS.md section
    if not skip_agents:
        if add_agents_md_section():
            typer.secho("Added IdlerGear section to AGENTS.md", fg=typer.colors.GREEN)
        else:
            typer.echo("AGENTS.md already has IdlerGear section")

    # Create rules file
    if not skip_rules:
        if add_rules_file():
            typer.secho("Created .claude/rules/idlergear.md", fg=typer.colors.GREEN)
        else:
            typer.echo(".claude/rules/idlergear.md already exists")

    # Create hooks config
    if not skip_hooks:
        if add_hooks_config():
            typer.secho("Added hooks to .claude/hooks.json", fg=typer.colors.GREEN)
        else:
            typer.echo(".claude/hooks.json already has IdlerGear hooks")

    # Create /start command
    if not skip_commands:
        if add_start_command():
            typer.secho("Created .claude/commands/start.md", fg=typer.colors.GREEN)
        else:
            typer.echo(".claude/commands/start.md already exists")

    typer.echo("")
    typer.echo("Claude Code will now have access to IdlerGear tools.")
    typer.echo("Use /start at session beginning to load project context.")
    typer.echo("Restart Claude Code or run /mcp to verify.")


# Daemon commands
@daemon_app.command("start")
def daemon_start(
    foreground: bool = typer.Option(False, "--foreground", "-f", help="Run in foreground"),
):
    """Start the IdlerGear daemon."""
    from idlergear.config import find_idlergear_root
    from idlergear.daemon.lifecycle import DaemonLifecycle

    root = find_idlergear_root()
    if root is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    lifecycle = DaemonLifecycle(root)

    if lifecycle.is_running():
        typer.echo(f"Daemon already running (PID {lifecycle.get_pid()})")
        return

    if foreground:
        typer.echo("Starting daemon in foreground...")
        from idlergear.daemon.server import run_daemon
        run_daemon(root)
    else:
        typer.echo("Starting daemon...")
        try:
            pid = lifecycle.start(wait=True)
            typer.secho(f"Daemon started (PID {pid})", fg=typer.colors.GREEN)
        except RuntimeError as e:
            typer.secho(f"Failed to start daemon: {e}", fg=typer.colors.RED)
            raise typer.Exit(1)


@daemon_app.command("stop")
def daemon_stop():
    """Stop the IdlerGear daemon."""
    from idlergear.config import find_idlergear_root
    from idlergear.daemon.lifecycle import DaemonLifecycle

    root = find_idlergear_root()
    if root is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    lifecycle = DaemonLifecycle(root)

    if not lifecycle.is_running():
        typer.echo("Daemon is not running.")
        return

    typer.echo("Stopping daemon...")
    if lifecycle.stop():
        typer.secho("Daemon stopped.", fg=typer.colors.GREEN)
    else:
        typer.secho("Failed to stop daemon.", fg=typer.colors.RED)
        raise typer.Exit(1)


@daemon_app.command("status")
def daemon_status():
    """Check daemon status."""
    import asyncio

    from idlergear.config import find_idlergear_root
    from idlergear.daemon.lifecycle import DaemonLifecycle

    root = find_idlergear_root()
    if root is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    lifecycle = DaemonLifecycle(root)
    status = asyncio.run(lifecycle.get_status())

    if status.get("running"):
        typer.secho("Daemon: running", fg=typer.colors.GREEN)
        typer.echo(f"  PID: {status.get('pid')}")
        typer.echo(f"  Socket: {status.get('socket')}")
        if status.get("connections") is not None:
            typer.echo(f"  Connections: {status.get('connections')}")
        if not status.get("healthy", True):
            typer.secho(f"  Warning: {status.get('error', 'Not healthy')}", fg=typer.colors.YELLOW)
    else:
        typer.secho("Daemon: not running", fg=typer.colors.YELLOW)
        typer.echo(f"  Socket: {status.get('socket')}")


# MCP server commands
@mcp_app.command("reload")
def mcp_reload():
    """Reload the MCP server to pick up code changes.

    Sends SIGUSR1 to the running MCP server process, causing it to
    re-execute itself with the latest code. This is useful after
    updating IdlerGear (e.g., git pull, pip install) without needing
    to restart Claude Code.

    The reload is transparent to Claude Code - the stdin/stdout
    connection is preserved across the reload.
    """
    import glob
    import os
    import signal

    # Find running MCP server by PID file
    pid_files = glob.glob("/tmp/idlergear-mcp-*.pid")

    if not pid_files:
        typer.secho("No running MCP server found.", fg=typer.colors.YELLOW)
        typer.echo("The MCP server may not be running, or was started without PID tracking.")
        raise typer.Exit(1)

    reloaded = 0
    for pid_file in pid_files:
        try:
            pid = int(open(pid_file).read().strip())

            # Check if process exists
            os.kill(pid, 0)  # Signal 0 just checks existence

            # Send reload signal
            os.kill(pid, signal.SIGUSR1)
            typer.secho(f"Sent reload signal to MCP server (PID {pid})", fg=typer.colors.GREEN)
            reloaded += 1

        except (ValueError, FileNotFoundError):
            # Invalid or missing PID file
            try:
                os.unlink(pid_file)
            except Exception:
                pass
        except ProcessLookupError:
            # Process doesn't exist, clean up stale PID file
            try:
                os.unlink(pid_file)
            except Exception:
                pass
            typer.secho(f"Cleaned up stale PID file: {pid_file}", fg=typer.colors.YELLOW)
        except PermissionError:
            typer.secho(f"Permission denied sending signal to PID from {pid_file}", fg=typer.colors.RED)

    if reloaded == 0:
        typer.secho("No active MCP servers found to reload.", fg=typer.colors.YELLOW)
        raise typer.Exit(1)
    else:
        typer.echo(f"\nReloaded {reloaded} MCP server(s). New code will be active for next tool call.")


@mcp_app.command("status")
def mcp_status():
    """Show status of running MCP servers."""
    import glob
    import os

    from idlergear.mcp_server import __version__

    pid_files = glob.glob("/tmp/idlergear-mcp-*.pid")

    if not pid_files:
        typer.secho("No running MCP servers found.", fg=typer.colors.YELLOW)
        typer.echo("The MCP server may not be running, or was started without PID tracking.")
        return

    typer.echo(f"IdlerGear MCP Server version: {__version__}")
    typer.echo("")

    active = 0
    for pid_file in pid_files:
        try:
            pid = int(open(pid_file).read().strip())

            # Check if process exists
            os.kill(pid, 0)

            typer.secho(f"  PID {pid}: running", fg=typer.colors.GREEN)
            active += 1

        except (ValueError, FileNotFoundError):
            pass
        except ProcessLookupError:
            # Stale PID file
            try:
                os.unlink(pid_file)
            except Exception:
                pass

    if active == 0:
        typer.secho("No active MCP servers.", fg=typer.colors.YELLOW)
    else:
        typer.echo(f"\n{active} active MCP server(s)")


# Config commands
@config_app.command("get")
def config_get(key: str):
    """Get a configuration value."""
    from idlergear.config import find_idlergear_root, get_config_value

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    value = get_config_value(key)
    if value is None:
        typer.echo(f"{key}: (not set)")
    else:
        typer.echo(f"{key}: {value}")


@config_app.command("set")
def config_set(key: str, value: str):
    """Set a configuration value."""
    from idlergear.config import find_idlergear_root, set_config_value

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    set_config_value(key, value)
    typer.secho(f"Set {key} = {value}", fg=typer.colors.GREEN)


@config_app.command("backend")
def config_backend(
    backend_type: str = typer.Argument(
        None,
        help="Backend type: task, note, reference, plan, vision",
    ),
    backend_name: str = typer.Argument(
        None,
        help="Backend name to use (e.g., local, github)",
    ),
):
    """Configure or show backend settings.

    Without arguments, shows all backend configurations.
    With one argument, shows the backend for that type.
    With two arguments, sets the backend for that type.

    Examples:
        idlergear config backend              # Show all backends
        idlergear config backend task         # Show task backend
        idlergear config backend task github  # Set task backend to github
    """
    from idlergear.backends import get_configured_backend_name, list_available_backends
    from idlergear.config import find_idlergear_root, set_config_value

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    all_types = ["task", "note", "reference", "plan", "vision"]

    if backend_type is None:
        # Show all backend configurations
        typer.echo("Backend configurations:")
        for t in all_types:
            name = get_configured_backend_name(t)
            available = list_available_backends(t)
            typer.echo(f"  {t:12} = {name}  (available: {', '.join(available)})")
        return

    if backend_type not in all_types:
        typer.secho(f"Unknown backend type: {backend_type}", fg=typer.colors.RED)
        typer.echo(f"Valid types: {', '.join(all_types)}")
        raise typer.Exit(1)

    if backend_name is None:
        # Show backend for this type
        name = get_configured_backend_name(backend_type)
        available = list_available_backends(backend_type)
        typer.echo(f"{backend_type} backend: {name}")
        typer.echo(f"Available backends: {', '.join(available)}")
        return

    # Set backend
    available = list_available_backends(backend_type)
    if backend_name not in available:
        typer.secho(f"Unknown backend: {backend_name}", fg=typer.colors.RED)
        typer.echo(f"Available backends for {backend_type}: {', '.join(available)}")
        raise typer.Exit(1)

    set_config_value(f"backends.{backend_type}", backend_name)
    typer.secho(f"Set {backend_type} backend to {backend_name}", fg=typer.colors.GREEN)


@app.command()
def migrate(
    backend_type: str = typer.Argument(
        ...,
        help="Backend type to migrate: task, reference, note",
    ),
    source: str = typer.Argument(
        ...,
        help="Source backend name (e.g., local)",
    ),
    target: str = typer.Argument(
        ...,
        help="Target backend name (e.g., github)",
    ),
    state: str = typer.Option(
        "all",
        "--state",
        "-s",
        help="State filter for tasks/explorations: open, closed, all",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be migrated without doing it",
    ),
):
    """Migrate data from one backend to another.

    Examples:
        idlergear migrate task local github        # Migrate all tasks local -> GitHub
        idlergear migrate task local github --state open  # Only open tasks
        idlergear migrate task local github --dry-run     # Show what would be migrated
    """
    from idlergear.config import find_idlergear_root
    from idlergear.migration import migrate_backend

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    valid_types = ["task", "reference", "note"]
    if backend_type not in valid_types:
        typer.secho(f"Invalid backend type: {backend_type}", fg=typer.colors.RED)
        typer.echo(f"Valid types: {', '.join(valid_types)}")
        raise typer.Exit(1)

    if source == target:
        typer.secho("Source and target backends must be different.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo(f"Migrating {backend_type}s from {source} to {target}...")

    def on_item(info: dict) -> None:
        src = info["source"]
        tgt = info["target"]
        title = src.get("title", src.get("content", "")[:40])
        typer.echo(f"  ✓ #{src.get('id', '?')} → #{tgt.get('id', '?')}: {title}")

    def on_error(item: dict, error: Exception) -> None:
        title = item.get("title", item.get("content", "")[:40])
        typer.secho(f"  ✗ #{item.get('id', '?')}: {title} - {error}", fg=typer.colors.RED)

    try:
        stats = migrate_backend(
            backend_type,
            source,
            target,
            state=state,
            dry_run=dry_run,
            on_item=on_item if not dry_run else None,
            on_error=on_error if not dry_run else None,
        )

        if dry_run:
            typer.echo(f"\nDry run: {stats['total']} {backend_type}(s) would be migrated.")
        else:
            typer.echo(f"\nMigration complete:")
            typer.echo(f"  Total: {stats['total']}")
            typer.secho(f"  Migrated: {stats['migrated']}", fg=typer.colors.GREEN)
            if stats["errors"]:
                typer.secho(f"  Errors: {stats['errors']}", fg=typer.colors.RED)

    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Migration failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


# Task commands
@task_app.command("create")
def task_create(
    title: str,
    body: str = typer.Option(None, "--body", "-b", help="Task body/description"),
    labels: list[str] = typer.Option([], "--label", "-l", help="Labels"),
    priority: str = typer.Option(None, "--priority", "-p", help="Priority: high, medium, low"),
    due: str = typer.Option(None, "--due", "-d", help="Due date (YYYY-MM-DD)"),
):
    """Create a new task."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    backend = get_backend("task")
    task = backend.create(
        title,
        body=body,
        labels=labels if labels else None,
        priority=priority,
        due=due,
    )
    typer.secho(f"Created task #{task['id']}: {task['title']}", fg=typer.colors.GREEN)


@task_app.command("list")
def task_list(
    state: str = typer.Option("open", "--state", "-s", help="Filter by state: open, closed, all"),
    priority: str = typer.Option(None, "--priority", "-p", help="Filter by priority: high, medium, low"),
):
    """List tasks."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    backend = get_backend("task")
    tasks = backend.list(state=state)

    # Filter by priority if specified
    if priority:
        tasks = [t for t in tasks if t.get("priority") == priority]

    if not tasks:
        typer.echo(f"No {state} tasks found.")
        return

    for task in tasks:
        state_icon = "o" if task["state"] == "open" else "x"
        labels_str = f" [{', '.join(task['labels'])}]" if task.get("labels") else ""
        priority_str = f" !{task['priority']}" if task.get("priority") else ""
        due_str = f" @{task['due']}" if task.get("due") else ""
        typer.echo(f"  [{state_icon}] #{task['id']:3d}  {task['title']}{priority_str}{due_str}{labels_str}")


@task_app.command("show")
def task_show(task_id: int):
    """Show a task."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    backend = get_backend("task")
    task = backend.get(task_id)
    if task is None:
        typer.secho(f"Task #{task_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    state_color = typer.colors.GREEN if task["state"] == "open" else typer.colors.RED
    typer.echo(f"Task #{task['id']}: {task['title']}")
    typer.secho(f"State: {task['state']}", fg=state_color)
    if task.get("priority"):
        priority_colors = {"high": typer.colors.RED, "medium": typer.colors.YELLOW, "low": typer.colors.BLUE}
        typer.secho(f"Priority: {task['priority']}", fg=priority_colors.get(task["priority"], typer.colors.WHITE))
    if task.get("due"):
        typer.echo(f"Due: {task['due']}")
    if task.get("labels"):
        typer.echo(f"Labels: {', '.join(task['labels'])}")
    if task.get("assignees"):
        typer.echo(f"Assignees: {', '.join(task['assignees'])}")
    created = task.get("created") or task.get("created_at")
    if created:
        typer.echo(f"Created: {created}")
    if task.get("github_issue"):
        typer.echo(f"GitHub: #{task['github_issue']}")
    typer.echo("")
    if task.get("body"):
        typer.echo(task["body"])


@task_app.command("close")
def task_close(task_id: int):
    """Close a task."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    backend = get_backend("task")
    task = backend.close(task_id)
    if task is None:
        typer.secho(f"Task #{task_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Closed task #{task_id}: {task['title']}", fg=typer.colors.GREEN)


@task_app.command("edit")
def task_edit(
    task_id: int,
    title: str = typer.Option(None, "--title", "-t", help="New title"),
    body: str = typer.Option(None, "--body", "-b", help="New body"),
    add_label: list[str] = typer.Option([], "--add-label", help="Add label"),
    priority: str = typer.Option(None, "--priority", "-p", help="Priority: high, medium, low (empty to clear)"),
    due: str = typer.Option(None, "--due", "-d", help="Due date (YYYY-MM-DD, empty to clear)"),
):
    """Edit a task."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    backend = get_backend("task")

    # Get current task to merge labels
    current = backend.get(task_id)
    if current is None:
        typer.secho(f"Task #{task_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    labels = None
    if add_label:
        labels = list(set(current.get("labels", []) + list(add_label)))

    task = backend.update(task_id, title=title, body=body, labels=labels, priority=priority, due=due)
    typer.secho(f"Updated task #{task_id}", fg=typer.colors.GREEN)


@task_app.command("sync")
def task_sync(target: str = typer.Argument("github")):
    """Sync tasks with remote."""
    typer.echo(f"Syncing tasks to {target}...")
    # TODO: Implement GitHub sync


# Note commands
@note_app.command("create")
def note_create(
    content: str,
    tag: list[str] = typer.Option([], "--tag", "-t", help="Tags (e.g., explore, idea)"),
):
    """Create a quick note."""
    from idlergear.config import find_idlergear_root
    from idlergear.notes import create_note

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    note = create_note(content, tags=list(tag) if tag else None)
    tag_str = f" [{', '.join(note['tags'])}]" if note.get("tags") else ""
    typer.secho(f"Created note #{note['id']}{tag_str}", fg=typer.colors.GREEN)


@note_app.command("list")
def note_list(
    tag: str = typer.Option(None, "--tag", "-t", help="Filter by tag (e.g., explore, idea)"),
):
    """List notes."""
    from idlergear.config import find_idlergear_root
    from idlergear.notes import list_notes

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    notes = list_notes(tag=tag)
    if not notes:
        if tag:
            typer.echo(f"No notes with tag '{tag}' found.")
        else:
            typer.echo("No notes found.")
        return

    for note in notes:
        preview = note["content"][:50].replace("\n", " ")
        if len(note["content"]) > 50:
            preview += "..."
        tag_str = f" [{', '.join(note['tags'])}]" if note.get("tags") else ""
        typer.echo(f"  #{note['id']:3d}{tag_str}  {preview}")


@note_app.command("show")
def note_show(note_id: int):
    """Show a note."""
    from idlergear.config import find_idlergear_root
    from idlergear.notes import get_note

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    note = get_note(note_id)
    if note is None:
        typer.secho(f"Note #{note_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo(f"Note #{note['id']}")
    if note.get("tags"):
        typer.echo(f"Tags: {', '.join(note['tags'])}")
    typer.echo(f"Created: {note['created']}")
    typer.echo("")
    typer.echo(note["content"])


@note_app.command("delete")
def note_delete(note_id: int):
    """Delete a note."""
    from idlergear.config import find_idlergear_root
    from idlergear.notes import delete_note

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if delete_note(note_id):
        typer.secho(f"Deleted note #{note_id}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Note #{note_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)


@note_app.command("promote")
def note_promote(
    note_id: int,
    to: str = typer.Option("task", "--to", "-t", help="Promote to: task, reference"),
):
    """Promote a note to another type."""
    from idlergear.config import find_idlergear_root
    from idlergear.notes import promote_note

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        result = promote_note(note_id, to)
        if result is None:
            typer.secho(f"Note #{note_id} not found.", fg=typer.colors.RED)
            raise typer.Exit(1)
        typer.secho(f"Promoted note #{note_id} to {to} #{result['id']}", fg=typer.colors.GREEN)
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


@note_app.command("sync")
def note_sync(target: str = typer.Argument("github")):
    """Sync notes with remote."""
    typer.echo(f"Syncing notes to {target}...")
    # TODO: Implement GitHub sync


# Explore commands (deprecated - now aliases for notes with --tag explore)
@explore_app.command("create")
def explore_create(
    title: str,
    body: str = typer.Option(None, "--body", "-b", help="Exploration body"),
):
    """Create an exploration (alias for 'note create --tag explore')."""
    from idlergear.config import find_idlergear_root
    from idlergear.notes import create_note

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Combine title and body into note content
    content = title
    if body:
        content = f"{title}\n\n{body}"

    note = create_note(content, tags=["explore"])
    typer.secho(f"Created exploration note #{note['id']}", fg=typer.colors.GREEN)
    typer.echo("  (Tip: Use 'note create --tag explore' directly)")


@explore_app.command("list")
def explore_list():
    """List explorations (alias for 'note list --tag explore')."""
    from idlergear.config import find_idlergear_root
    from idlergear.notes import list_notes

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    notes = list_notes(tag="explore")
    if not notes:
        typer.echo("No exploration notes found.")
        return

    for note in notes:
        preview = note["content"][:50].replace("\n", " ")
        if len(note["content"]) > 50:
            preview += "..."
        typer.echo(f"  #{note['id']:3d}  {preview}")


@explore_app.command("show")
def explore_show(note_id: int):
    """Show an exploration (alias for 'note show')."""
    from idlergear.config import find_idlergear_root
    from idlergear.notes import get_note

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    note = get_note(note_id)
    if note is None:
        typer.secho(f"Note #{note_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo(f"Note #{note['id']}")
    if note.get("tags"):
        typer.echo(f"Tags: {', '.join(note['tags'])}")
    typer.echo(f"Created: {note['created']}")
    typer.echo("")
    typer.echo(note["content"])


@explore_app.command("delete")
def explore_delete(note_id: int):
    """Delete an exploration (alias for 'note delete')."""
    from idlergear.config import find_idlergear_root
    from idlergear.notes import delete_note

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if delete_note(note_id):
        typer.secho(f"Deleted note #{note_id}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Note #{note_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)


# Vision commands
@vision_app.command("show")
def vision_show():
    """Show the project vision."""
    from idlergear.config import find_idlergear_root
    from idlergear.vision import get_vision

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    vision = get_vision()
    if vision is None or not vision.strip():
        typer.echo("No vision set. Use 'idlergear vision edit' to set one.")
        return

    typer.echo(vision)


@vision_app.command("edit")
def vision_edit(
    content: str = typer.Option(None, "--content", "-c", help="New vision content"),
):
    """Edit the project vision."""
    import os
    import subprocess
    import tempfile

    from idlergear.config import find_idlergear_root
    from idlergear.vision import get_vision, set_vision

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if content is not None:
        # Direct content update
        set_vision(content)
        typer.secho("Vision updated.", fg=typer.colors.GREEN)
        return

    # Open in editor
    editor = os.environ.get("EDITOR", "nano")
    current_vision = get_vision() or "# Project Vision\n\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(current_vision)
        temp_path = f.name

    try:
        subprocess.run([editor, temp_path], check=True)
        with open(temp_path) as f:
            new_content = f.read()
        set_vision(new_content)
        typer.secho("Vision updated.", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError:
        typer.secho("Editor exited with error.", fg=typer.colors.RED)
        raise typer.Exit(1)
    finally:
        os.unlink(temp_path)


@vision_app.command("sync")
def vision_sync(target: str = typer.Argument("github")):
    """Sync vision with remote."""
    typer.echo(f"Syncing vision to {target}...")
    # TODO: Implement GitHub sync (copy to VISION.md in repo root)


# Plan commands
@plan_app.command("create")
def plan_create(
    name: str,
    title: str = typer.Option(None, "--title", "-t", help="Plan title"),
    body: str = typer.Option(None, "--body", "-b", help="Plan description"),
):
    """Create a plan."""
    from idlergear.config import find_idlergear_root
    from idlergear.plans import create_plan

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        plan = create_plan(name, title=title, body=body)
        typer.secho(f"Created plan: {plan['name']}", fg=typer.colors.GREEN)
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


@plan_app.command("list")
def plan_list():
    """List plans."""
    from idlergear.config import find_idlergear_root
    from idlergear.plans import get_current_plan, list_plans

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    plans = list_plans()
    if not plans:
        typer.echo("No plans found.")
        return

    current = get_current_plan()
    current_name = current["name"] if current else None

    for plan in plans:
        marker = "*" if plan["name"] == current_name else " "
        typer.echo(f"  {marker} {plan['name']}: {plan['title']}")


@plan_app.command("show")
def plan_show(name: str = typer.Argument(None, help="Plan name (default: current)")):
    """Show a plan."""
    from idlergear.config import find_idlergear_root
    from idlergear.plans import get_current_plan, get_plan

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if name is None:
        plan = get_current_plan()
        if plan is None:
            typer.echo("No current plan set. Use 'idlergear plan switch <name>' to set one.")
            return
    else:
        plan = get_plan(name)
        if plan is None:
            typer.secho(f"Plan '{name}' not found.", fg=typer.colors.RED)
            raise typer.Exit(1)

    typer.echo(f"Plan: {plan['name']}")
    typer.echo(f"Title: {plan['title']}")
    typer.echo(f"State: {plan['state']}")
    typer.echo(f"Created: {plan['created']}")
    if plan.get("github_project"):
        typer.echo(f"GitHub: Project #{plan['github_project']}")
    typer.echo("")
    if plan.get("body"):
        typer.echo(plan["body"])


@plan_app.command("switch")
def plan_switch(name: str):
    """Switch to a plan."""
    from idlergear.config import find_idlergear_root
    from idlergear.plans import switch_plan

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    plan = switch_plan(name)
    if plan is None:
        typer.secho(f"Plan '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Switched to plan: {plan['name']}", fg=typer.colors.GREEN)


@plan_app.command("sync")
def plan_sync(target: str = typer.Argument("github")):
    """Sync plans with remote."""
    typer.echo(f"Syncing plans to {target}...")
    # TODO: Implement GitHub Projects sync


# Reference commands
@reference_app.command("add")
def reference_add(
    title: str,
    body: str = typer.Option(None, "--body", "-b", help="Reference body"),
):
    """Add a reference document."""
    from idlergear.config import find_idlergear_root
    from idlergear.reference import add_reference

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    ref = add_reference(title, body=body)
    typer.secho(f"Added reference: {ref['title']}", fg=typer.colors.GREEN)


@reference_app.command("list")
def reference_list():
    """List reference documents."""
    from idlergear.config import find_idlergear_root
    from idlergear.reference import list_references

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    refs = list_references()
    if not refs:
        typer.echo("No reference documents found.")
        return

    for ref in refs:
        typer.echo(f"  {ref['title']}")


@reference_app.command("show")
def reference_show(title: str):
    """Show a reference document."""
    from idlergear.config import find_idlergear_root
    from idlergear.reference import get_reference

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    ref = get_reference(title)
    if ref is None:
        typer.secho(f"Reference '{title}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo(f"Reference: {ref['title']}")
    typer.echo(f"Created: {ref['created']}")
    typer.echo(f"Updated: {ref['updated']}")
    typer.echo("")
    if ref.get("body"):
        typer.echo(ref["body"])


@reference_app.command("edit")
def reference_edit(
    title: str,
    new_title: str = typer.Option(None, "--title", "-t", help="New title"),
    body: str = typer.Option(None, "--body", "-b", help="New body"),
):
    """Edit a reference document."""
    from idlergear.config import find_idlergear_root
    from idlergear.reference import update_reference

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    ref = update_reference(title, new_title=new_title, body=body)
    if ref is None:
        typer.secho(f"Reference '{title}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Updated reference: {ref['title']}", fg=typer.colors.GREEN)


@reference_app.command("search")
def reference_search(query: str):
    """Search reference documents."""
    from idlergear.config import find_idlergear_root
    from idlergear.reference import search_references

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    results = search_references(query)
    if not results:
        typer.echo(f"No references found matching '{query}'.")
        return

    typer.echo(f"Found {len(results)} matching reference(s):")
    for ref in results:
        typer.echo(f"  {ref['title']}")


@reference_app.command("sync")
def reference_sync(target: str = typer.Argument("github")):
    """Sync references with remote."""
    typer.echo(f"Syncing references to {target}...")
    # TODO: Implement GitHub Wiki sync


# Run commands
@run_app.command("start")
def run_start(
    command: str,
    name: str = typer.Option(None, "--name", "-n", help="Run name"),
):
    """Start a script/command."""
    from idlergear.config import find_idlergear_root
    from idlergear.runs import start_run

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        run = start_run(command, name=name)
        typer.secho(f"Started run '{run['name']}' (PID {run['pid']})", fg=typer.colors.GREEN)
        typer.echo(f"  Command: {run['command']}")
        typer.echo(f"  Logs: idlergear run logs {run['name']}")
    except RuntimeError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


@run_app.command("list")
def run_list():
    """List runs."""
    from idlergear.config import find_idlergear_root
    from idlergear.runs import list_runs

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    runs = list_runs()
    if not runs:
        typer.echo("No runs found.")
        return

    for run in runs:
        status_color = typer.colors.GREEN if run["status"] == "running" else typer.colors.WHITE
        typer.echo(f"  {run['name']}", nl=False)
        typer.secho(f"  [{run['status']}]", fg=status_color, nl=False)
        if run.get("pid") and run["status"] == "running":
            typer.echo(f"  PID {run['pid']}", nl=False)
        typer.echo("")


@run_app.command("status")
def run_status(name: str):
    """Check run status."""
    from idlergear.config import find_idlergear_root
    from idlergear.runs import get_run_status

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    status = get_run_status(name)
    if status is None:
        typer.secho(f"Run '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    status_color = typer.colors.GREEN if status["status"] == "running" else typer.colors.WHITE
    typer.echo(f"Run: {status['name']}")
    typer.secho(f"Status: {status['status']}", fg=status_color)
    if status.get("command"):
        typer.echo(f"Command: {status['command']}")
    if status.get("pid") and status["status"] == "running":
        typer.echo(f"PID: {status['pid']}")
    typer.echo(f"Stdout: {status.get('stdout_size', 0)} bytes")
    typer.echo(f"Stderr: {status.get('stderr_size', 0)} bytes")


@run_app.command("logs")
def run_logs(
    name: str,
    tail: int = typer.Option(None, "--tail", "-t", help="Show last N lines"),
    stderr: bool = typer.Option(False, "--stderr", "-e", help="Show stderr instead of stdout"),
):
    """Show run logs."""
    from idlergear.config import find_idlergear_root
    from idlergear.runs import get_run_logs

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    stream = "stderr" if stderr else "stdout"
    logs = get_run_logs(name, tail=tail, stream=stream)

    if logs is None:
        typer.secho(f"Run '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not logs:
        typer.echo(f"No {stream} output yet.")
        return

    typer.echo(logs)


@run_app.command("stop")
def run_stop(name: str):
    """Stop a running process."""
    from idlergear.config import find_idlergear_root
    from idlergear.runs import stop_run

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if stop_run(name):
        typer.secho(f"Stopped run '{name}'", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Run '{name}' is not running or not found.", fg=typer.colors.RED)
        raise typer.Exit(1)


# Project commands
@project_app.command("create")
def project_create(
    title: str,
    columns: list[str] = typer.Option(
        [],
        "--column",
        "-c",
        help="Custom columns (default: Backlog, In Progress, Review, Done)",
    ),
    github: bool = typer.Option(False, "--github", "-g", help="Also create on GitHub Projects v2"),
):
    """Create a new project board."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import create_project

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        project = create_project(
            title,
            columns=list(columns) if columns else None,
            create_on_github=github,
        )
        typer.secho(f"Created project: {project['title']}", fg=typer.colors.GREEN)
        typer.echo(f"  ID: {project['id']}")
        typer.echo(f"  Columns: {', '.join(project['columns'])}")
        if project.get("github_project_number"):
            typer.echo(f"  GitHub Project: #{project['github_project_number']}")
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


@project_app.command("list")
def project_list(
    github: bool = typer.Option(False, "--github", "-g", help="Also list GitHub Projects"),
):
    """List project boards."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import list_github_projects, list_projects

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    projects = list_projects()

    if not projects and not github:
        typer.echo("No projects found. Create one with 'idlergear project create <title>'")
        return

    if projects:
        typer.echo("Local Projects:")
        for proj in projects:
            gh_link = f" (GitHub #{proj['github_project_number']})" if proj.get("github_project_number") else ""
            typer.echo(f"  {proj['title']}{gh_link}")
            task_count = sum(len(tasks) for tasks in proj["tasks"].values())
            typer.echo(f"    {task_count} tasks across {len(proj['columns'])} columns")

    if github:
        typer.echo("")
        typer.echo("GitHub Projects:")
        gh_projects = list_github_projects()
        if not gh_projects:
            typer.echo("  No GitHub Projects found (or gh CLI not authenticated)")
        else:
            for proj in gh_projects:
                typer.echo(f"  #{proj.get('number', '?')}: {proj.get('title', 'Untitled')}")


@project_app.command("show")
def project_show(name: str):
    """Show a project board with tasks in each column."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root
    from idlergear.projects import get_project

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    project = get_project(name)
    if project is None:
        typer.secho(f"Project '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo(f"Project: {project['title']}")
    if project.get("github_project_number"):
        typer.echo(f"GitHub Project: #{project['github_project_number']}")
    typer.echo(f"Created: {project['created_at']}")
    typer.echo("")

    # Show Kanban columns
    task_backend = get_backend("task")

    for column in project["columns"]:
        task_ids = project["tasks"].get(column, [])
        typer.secho(f"═══ {column} ({len(task_ids)}) ═══", bold=True)

        if not task_ids:
            typer.echo("  (empty)")
        else:
            for task_id in task_ids:
                task = task_backend.get(task_id)
                if task:
                    title = task.get("title", "(no title)")[:50]
                    typer.echo(f"  #{task_id}: {title}")
                else:
                    typer.secho(f"  #{task_id}: (task not found)", fg=typer.colors.YELLOW)
        typer.echo("")


@project_app.command("delete")
def project_delete(
    name: str,
    github: bool = typer.Option(False, "--github", "-g", help="Also delete from GitHub"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a project board."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import delete_project, get_project

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    project = get_project(name)
    if project is None:
        typer.secho(f"Project '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not force:
        confirm_msg = f"Delete project '{project['title']}'?"
        if github and project.get("github_project_number"):
            confirm_msg = f"Delete project '{project['title']}' locally AND from GitHub?"
        if not typer.confirm(confirm_msg):
            typer.echo("Cancelled.")
            raise typer.Exit(0)

    if delete_project(name, delete_on_github=github):
        typer.secho(f"Deleted project: {project['title']}", fg=typer.colors.GREEN)
    else:
        typer.secho("Failed to delete project.", fg=typer.colors.RED)
        raise typer.Exit(1)


@project_app.command("add-task")
def project_add_task(
    project_name: str,
    task_id: int,
    column: str = typer.Option(None, "--column", "-c", help="Target column (default: first column)"),
):
    """Add a task to a project board."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import add_task_to_project

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        project = add_task_to_project(project_name, str(task_id), column)
        if project is None:
            typer.secho(f"Project '{project_name}' not found.", fg=typer.colors.RED)
            raise typer.Exit(1)

        target_col = column or project["columns"][0]
        typer.secho(f"Added task #{task_id} to '{project['title']}' → {target_col}", fg=typer.colors.GREEN)
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


@project_app.command("remove-task")
def project_remove_task(project_name: str, task_id: int):
    """Remove a task from a project board."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import remove_task_from_project

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    project = remove_task_from_project(project_name, str(task_id))
    if project is None:
        typer.secho(f"Project '{project_name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Removed task #{task_id} from '{project['title']}'", fg=typer.colors.GREEN)


@project_app.command("move")
def project_move_task(project_name: str, task_id: int, column: str):
    """Move a task to a different column."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import move_task

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        project = move_task(project_name, str(task_id), column)
        if project is None:
            typer.secho(f"Project '{project_name}' not found.", fg=typer.colors.RED)
            raise typer.Exit(1)

        typer.secho(f"Moved task #{task_id} to '{column}'", fg=typer.colors.GREEN)
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


@project_app.command("sync")
def project_sync(name: str):
    """Sync a project to GitHub Projects v2."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import sync_project_to_github

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo(f"Syncing project '{name}' to GitHub...")

    try:
        project = sync_project_to_github(name)
        if project is None:
            typer.secho(f"Project '{name}' not found.", fg=typer.colors.RED)
            raise typer.Exit(1)

        typer.secho(f"Synced project to GitHub Projects #{project['github_project_number']}", fg=typer.colors.GREEN)
    except RuntimeError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


@project_app.command("link")
def project_link(name: str, github_project_number: int):
    """Link a local project to an existing GitHub Project."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import link_to_github_project

    if find_idlergear_root() is None:
        typer.secho("Not in an IdlerGear project. Run 'idlergear init' first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        project = link_to_github_project(name, github_project_number)
        if project is None:
            typer.secho(f"Local project '{name}' not found.", fg=typer.colors.RED)
            raise typer.Exit(1)

        typer.secho(f"Linked '{project['title']}' to GitHub Project #{github_project_number}", fg=typer.colors.GREEN)
    except RuntimeError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
