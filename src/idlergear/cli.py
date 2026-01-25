"""IdlerGear CLI - Command-line interface."""

import json
from enum import Enum
from pathlib import Path
from typing import List, Optional

from importlib.metadata import version as get_version

import typer

from .display import display, is_interactive

__version__ = get_version("idlergear")


class OutputFormat(str, Enum):
    HUMAN = "human"
    JSON = "json"


class State:
    def __init__(self, output_format: OutputFormat):
        self.output_format = output_format


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
    ctx: typer.Context,
    output: OutputFormat = typer.Option(
        None, "--output", help="Output format (json or human). Auto-detects if not set."
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    no_upgrade: bool = typer.Option(
        False, "--no-upgrade", help="Skip automatic upgrade check."
    ),
) -> None:
    """IdlerGear - Knowledge management for AI-assisted development."""
    output_format = OutputFormat.HUMAN
    if output == OutputFormat.JSON:
        output_format = OutputFormat.JSON
    elif not is_interactive() and output is None:
        # Default to JSON for non-interactive sessions (pipes)
        output_format = OutputFormat.JSON

    ctx.obj = State(output_format=output_format)

    # Check for upgrade (skip for init/install/doctor commands and when --no-upgrade)
    if not no_upgrade and ctx.invoked_subcommand not in (
        "init",
        "install",
        "doctor",
        None,
    ):
        from idlergear.upgrade import check_and_prompt_upgrade

        try:
            check_and_prompt_upgrade()
        except Exception:
            pass  # Don't let upgrade check break normal operation


# Sub-command groups
task_app = typer.Typer(help="Task management (→ GitHub Issues)")
note_app = typer.Typer(help="Quick notes capture")
vision_app = typer.Typer(help="Project vision management")
plan_app = typer.Typer(help="Plan management (→ GitHub Projects)")
milestone_app = typer.Typer(help="Milestone management (→ GitHub Milestones)")
reference_app = typer.Typer(help="Reference docs (→ GitHub Wiki)")
run_app = typer.Typer(help="Script execution and logs")
label_app = typer.Typer(help="Label management (→ GitHub Labels)")
config_app = typer.Typer(help="Configuration management")
daemon_app = typer.Typer(help="Daemon control")
mcp_app = typer.Typer(help="MCP server management")
project_app = typer.Typer(help="Kanban project boards (→ GitHub Projects v2)")
session_app = typer.Typer(help="Session state persistence")
goose_app = typer.Typer(help="Goose integration and configuration")
otel_app = typer.Typer(help="OpenTelemetry log collection")
test_app = typer.Typer(help="Test framework detection and status")
docs_app = typer.Typer(help="Python API documentation generation")
agents_app = typer.Typer(help="AGENTS.md generation and management")
secrets_app = typer.Typer(help="Secure local secrets management")
release_app = typer.Typer(help="Release management (GitHub Releases)")
file_app = typer.Typer(help="File registry and annotations (track file status)")
plugin_app = typer.Typer(help="Plugin management and integration (Langfuse, LlamaIndex, Mem0)")
graph_app = typer.Typer(help="Knowledge graph queries and population")

app.add_typer(task_app, name="task")
app.add_typer(note_app, name="note")
app.add_typer(vision_app, name="vision")
app.add_typer(plan_app, name="plan")
app.add_typer(milestone_app, name="milestone")
app.add_typer(reference_app, name="reference")
app.add_typer(run_app, name="run")
app.add_typer(label_app, name="label")
app.add_typer(config_app, name="config")
app.add_typer(daemon_app, name="daemon")
app.add_typer(mcp_app, name="mcp")
app.add_typer(project_app, name="project")
app.add_typer(session_app, name="session")
app.add_typer(goose_app, name="goose")
app.add_typer(otel_app, name="otel")
app.add_typer(test_app, name="test")
app.add_typer(docs_app, name="docs")
app.add_typer(agents_app, name="agents")
app.add_typer(secrets_app, name="secrets")
app.add_typer(release_app, name="release")
app.add_typer(file_app, name="file")
app.add_typer(plugin_app, name="plugin")
app.add_typer(graph_app, name="graph")


# Helper functions
def validate_labels(labels: list[str]) -> tuple[list[str], list[str]]:
    """Validate that labels exist in the GitHub repository.

    Args:
        labels: List of label names to validate

    Returns:
        Tuple of (valid_labels, invalid_labels)
    """
    import subprocess
    import json

    if not labels:
        return [], []

    try:
        # Get all existing labels
        result = subprocess.run(
            ["gh", "label", "list", "--json", "name"],
            capture_output=True,
            text=True,
            check=True,
        )
        existing_labels = {label["name"] for label in json.loads(result.stdout)}

        # Check which labels are invalid
        valid = []
        invalid = []
        for label in labels:
            if label in existing_labels:
                valid.append(label)
            else:
                invalid.append(label)

        return valid, invalid

    except (subprocess.CalledProcessError, FileNotFoundError):
        # If gh command fails, skip validation (might not be in a git repo)
        return labels, []


@app.command()
def init(
    path: str = typer.Argument(".", help="Project directory to initialize"),
    skip_github: bool = typer.Option(
        False, "--skip-github", help="Skip GitHub detection"
    ),
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
        typer.secho(
            f"Detected GitHub repository: {features.repo_name}", fg=typer.colors.CYAN
        )

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
                    set_config_value(
                        f"backends.{backend_type}",
                        backend_name,
                        project_path=project_path,
                    )
                    typer.secho(
                        f"  ✓ {backend_type} → {backend_name}", fg=typer.colors.GREEN
                    )
            else:
                typer.echo(
                    "Using local backends. Run 'idlergear setup-github' anytime to reconfigure."
                )


@app.command()
def search(
    ctx: typer.Context,
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
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    results = search_all(query, types=types if types else None)

    # For human-readable output, pass the query along for a better title.
    # For JSON, group into a dictionary.
    if ctx.obj.output_format == "human":
        if results:
            results[0]["_query"] = query  # Hack to pass query to formatter
        display(results, ctx.obj.output_format, "search")
    else:
        by_type: dict[str, list] = {}
        for result in results:
            t = result["type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(result)
        display(by_type, ctx.obj.output_format, "search")


@app.command()
def context(
    ctx: typer.Context,
    mode: str = typer.Option(
        "minimal",
        "--mode",
        "-m",
        help="Verbosity mode: minimal (~750 tokens), standard (~2500), detailed (~7000), full (no limits)",
    ),
    include_refs: bool = typer.Option(
        False, "--refs", "-r", help="Include reference documents"
    ),
    include_session: bool = typer.Option(
        False, "--session", "-s", help="Include session state"
    ),
):
    """Show project context for AI session start.

    Gathers and displays all relevant project knowledge in one command:
    - Vision (project purpose and direction)
    - Current plan (what we're working on)
    - Open tasks (prioritized)
    - Open explorations (research in progress)
    - Recent notes (quick captures)
    - Session state (optional, with --session flag)

    Run this at the start of each AI session to understand the project.

    Token-Efficient Modes:
        minimal  (~750 tokens):  Top 5 tasks (titles only), no notes/explorations
        standard (~2500 tokens): Top 10 tasks (1-line preview), 5 notes, 3 explorations
        detailed (~7000 tokens): Top 15 tasks (5-line preview), 8 notes, 5 explorations
        full (no limit):         All tasks/notes with full bodies

    Examples:
        idlergear context                     # Minimal mode (default, ~750 tokens)
        idlergear context --mode standard     # Balanced mode (~2500 tokens)
        idlergear context --mode full --refs  # Everything including references
        idlergear context --output json       # JSON output for tools
        idlergear context --session           # Include last saved session
    """
    from idlergear.config import find_idlergear_root
    from idlergear.context import format_context_json, gather_context

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    # Validate mode
    valid_modes = ["minimal", "standard", "detailed", "full"]
    if mode not in valid_modes:
        typer.secho(
            f"Invalid mode '{mode}'. Choose from: {', '.join(valid_modes)}",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    context_data = gather_context(include_references=include_refs, mode=mode)

    # Add session state if requested
    if include_session:
        from idlergear.sessions import load_session

        session = load_session()
        if session:
            # Add to the dataclass for consistent handling
            context_data.session = session.to_dict()

    if ctx.obj.output_format == "json":
        json_data = format_context_json(context_data)
        if include_session and hasattr(context_data, "session"):
            json_data["session"] = context_data.session
        display(json_data, "json", "context")
    else:
        # The session data needs special handling for the text format,
        # as it's appended after the main block.
        display(context_data, "human", "context")
        if include_session and hasattr(context_data, "session"):
            from idlergear.sessions import format_session_state, load_session

            session = load_session()
            if session:
                typer.echo("\n\n" + format_session_state(session))


@app.command()
def status(
    ctx: typer.Context,
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Show detailed dashboard"
    ),
):
    """Show unified project status dashboard.

    Quick one-line summary of tasks, notes, runs, and git status.

    Examples:
        idlergear status              # One-line summary
        idlergear status --detailed   # Full dashboard
        idlergear status --output json # JSON output for tools
    """
    from idlergear.config import find_idlergear_root
    from idlergear.status import get_project_status

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    status_data = get_project_status()

    if ctx.obj.output_format == "json":
        display(status_data.to_dict(), "json", "status")
    else:
        data_type = "status" if detailed else "status_summary"
        display(status_data, "human", data_type)


@app.command()
def check(
    file: str = typer.Option(None, "--file", "-f", help="File to check for violations"),
    no_todos: bool = typer.Option(False, "--no-todos", help="Check for TODO comments"),
    no_forbidden: bool = typer.Option(
        False, "--no-forbidden", help="Check for forbidden files"
    ),
    context_reminder: bool = typer.Option(
        False, "--context-reminder", help="Remind to run context at session start"
    ),
    structure: bool = typer.Option(
        False, "--structure", help="Check .idlergear/ directory structure"
    ),
    files: bool = typer.Option(
        False, "--files", help="Check for misplaced files in project root"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Only output on violations"
    ),
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
                violations.append(
                    "Missing directories (run 'idlergear upgrade-schema' to fix):"
                )
                for d in result["missing"]:
                    violations.append(f"  {d}")

            if result["legacy"]:
                if not quiet:
                    typer.secho(
                        "Legacy directories found (run 'idlergear upgrade-schema'):",
                        fg=typer.colors.YELLOW,
                    )
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
                    r"//\s*TODO:",
                    r"#\s*TODO:",
                    r"/\*\s*TODO:",
                    r"//\s*FIXME:",
                    r"#\s*FIXME:",
                    r"/\*\s*FIXME:",
                    r"//\s*HACK:",
                    r"#\s*HACK:",
                    r"/\*\s*HACK:",
                    r"<!--\s*TODO:",
                ]
                for pattern in todo_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        violations.append(f"TODO/FIXME/HACK comment found in {file}")
                        violations.append(
                            'Use: idlergear task create "..." --label tech-debt'
                        )
                        break
            except Exception:
                pass  # Can't read file, skip

        # Check for forbidden file names
        forbidden_files = [
            "TODO.md",
            "TODO.txt",
            "TASKS.md",
            "NOTES.md",
            "SCRATCH.md",
            "BACKLOG.md",
            "FEATURE_IDEAS.md",
            "RESEARCH.md",
        ]
        if file_path.name in forbidden_files:
            violations.append(f"Forbidden file: {file_path.name}")
            violations.append("Use IdlerGear commands instead:")
            violations.append('  idlergear task create "..."')
            violations.append('  idlergear note create "..."')

        if file_path.name.startswith("SESSION_") and file_path.suffix == ".md":
            violations.append(f"Forbidden file pattern: {file_path.name}")
            violations.append('Use: idlergear note create "..."')

    # Check for forbidden files in project
    if no_forbidden:
        from idlergear.config import find_idlergear_root

        root = find_idlergear_root()
        if root:
            forbidden = [
                "TODO.md",
                "TODO.txt",
                "TASKS.md",
                "NOTES.md",
                "SCRATCH.md",
                "BACKLOG.md",
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
                [
                    "grep",
                    "-rn",
                    "-E",
                    r"(//|#|/\*)\s*(TODO|FIXME|HACK):",
                    str(root),
                    "--include=*.py",
                    "--include=*.js",
                    "--include=*.ts",
                    "--include=*.go",
                    "--include=*.rs",
                    "--include=*.java",
                    "--include=*.c",
                    "--include=*.cpp",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                violations.append("TODO/FIXME/HACK comments found:")
                for line in result.stdout.strip().split("\n")[:5]:
                    violations.append(f"  {line}")
                violations.append('Use: idlergear task create "..." --label tech-debt')

    # Context reminder
    if context_reminder:
        if not quiet:
            typer.secho(
                "REMINDER: Run 'idlergear context' at session start",
                fg=typer.colors.CYAN,
            )

    # Report violations
    if violations:
        for v in violations:
            typer.secho(v, fg=typer.colors.RED)
        raise typer.Exit(1)
    elif not quiet and not context_reminder:
        typer.secho("No violations found.", fg=typer.colors.GREEN)


@app.command()
def doctor(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show all checks including passed ones"
    ),
    fix: bool = typer.Option(
        False, "--fix", help="Automatically fix issues by running install --upgrade"
    ),
):
    """Check IdlerGear installation health and suggest fixes.

    Checks for:
    - Configuration health (initialized, version current)
    - File installation status (MCP, hooks, rules, skills)
    - Legacy files from older versions
    - Unmanaged knowledge files (TODO.md, NOTES.md, etc.)

    Examples:
        idlergear doctor              # Run health checks
        idlergear doctor -v           # Show all checks including passed
        idlergear doctor --fix        # Auto-fix by running install --upgrade
    """
    from idlergear.doctor import run_doctor, format_report

    report = run_doctor()

    if ctx.obj.output_format == "json":
        display(report.to_dict(), "json", "doctor")
    else:
        typer.echo(format_report(report, verbose=verbose))

    # Auto-fix if requested
    if fix and not report.is_healthy:
        typer.echo("")
        typer.secho(
            "Running auto-fix (idlergear install --upgrade)...", fg=typer.colors.YELLOW
        )
        from idlergear.upgrade import do_upgrade

        result = do_upgrade()
        if "error" in result:
            typer.secho(f"Error: {result['error']}", fg=typer.colors.RED)
            raise typer.Exit(1)
        else:
            typer.secho(
                "Upgrade complete. Run 'idlergear doctor' again to verify.",
                fg=typer.colors.GREEN,
            )

    # Exit with error code if unhealthy (for CI/scripts)
    if report.has_errors:
        raise typer.Exit(1)


@app.command("upgrade-schema")
def upgrade_schema(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be done without making changes"
    ),
):
    """Upgrade .idlergear/ to v0.3 schema.

    Performs the following migrations:
    - tasks/ → issues/
    - reference/ → wiki/
    - .idlergear/vision.md → VISION.md (repo root)
    - Removes empty explorations/ (notes use tags now)
    - Creates missing directories (sync/, projects/)

    Examples:
        idlergear upgrade-schema --dry-run   # Preview changes
        idlergear upgrade-schema             # Perform migration
    """
    import shutil

    from idlergear.config import find_idlergear_root
    from idlergear.schema import IdlerGearSchema, SCHEMA_VERSION

    root = find_idlergear_root()
    if root is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    schema = IdlerGearSchema(root)

    if not schema.needs_migration():
        typer.secho(
            f"Already on v{SCHEMA_VERSION} schema. Nothing to migrate.",
            fg=typer.colors.GREEN,
        )
        return

    actions = []

    # Check tasks/ → issues/
    if schema.legacy_tasks_dir.exists() and not schema.issues_dir.exists():
        actions.append(
            ("rename", schema.legacy_tasks_dir, schema.issues_dir, "tasks/ → issues/")
        )

    # Check reference/ → wiki/
    if schema.legacy_reference_dir.exists() and not schema.wiki_dir.exists():
        actions.append(
            (
                "rename",
                schema.legacy_reference_dir,
                schema.wiki_dir,
                "reference/ → wiki/",
            )
        )

    # Check .idlergear/vision.md → VISION.md (repo root)
    if schema.legacy_vision_file.exists() and not schema.vision_file.exists():
        actions.append(
            (
                "move",
                schema.legacy_vision_file,
                schema.vision_file,
                ".idlergear/vision.md → VISION.md",
            )
        )

    # Check explorations/ (if empty, remove; otherwise prompt)
    if schema.legacy_explorations_dir.exists():
        exploration_files = list(schema.legacy_explorations_dir.glob("*.md"))
        if not exploration_files:
            actions.append(
                (
                    "remove",
                    schema.legacy_explorations_dir,
                    None,
                    "Remove empty explorations/",
                )
            )
        else:
            actions.append(
                (
                    "warn",
                    schema.legacy_explorations_dir,
                    None,
                    f"explorations/ has {len(exploration_files)} files - convert to notes with 'explore' tag",
                )
            )

    # Create missing v0.3 directories
    for dir_path in schema.get_all_directories():
        if not dir_path.exists():
            actions.append(("create", dir_path, None, f"Create {dir_path.name}/"))

    if not actions:
        typer.secho(
            f"Already on v{SCHEMA_VERSION} schema. Nothing to migrate.",
            fg=typer.colors.GREEN,
        )
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
def organize(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be done without making changes"
    ),
    auto: bool = typer.Option(
        False, "--auto", "-y", help="Automatically organize without prompting"
    ),
):
    """Organize misplaced files into IdlerGear structure.

    Finds files like TODO.md, NOTES.md, SESSION_*.md in the project root
    and offers to convert them into IdlerGear tasks/notes.

    Examples:
        idlergear organize --dry-run   # Preview what would be organized
        idlergear organize             # Interactive organization
        idlergear organize --auto      # Auto-organize without prompts
    """
    from idlergear.config import find_idlergear_root
    from idlergear.schema import detect_misplaced_files

    root = find_idlergear_root()
    if root is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    misplaced = detect_misplaced_files(root)

    if not misplaced:
        typer.secho(
            "No misplaced files found. Project is organized!", fg=typer.colors.GREEN
        )
        return

    typer.echo(f"Found {len(misplaced)} misplaced file(s):\n")

    for item in misplaced:
        typer.echo(f"  {item['name']}")
        typer.secho(f"    → {item['action']}", fg=typer.colors.CYAN)

    if dry_run:
        typer.echo("")
        typer.secho("Dry run - no changes made.", fg=typer.colors.CYAN)
        return

    typer.echo("")

    if not auto:
        proceed = typer.confirm("Organize these files?")
        if not proceed:
            typer.secho("Cancelled.", fg=typer.colors.YELLOW)
            return

    # Process each misplaced file
    from idlergear.task import create_task
    from idlergear.notes import create_note

    organized_count = 0
    for item in misplaced:
        file_path = item["path"]
        file_type = item["type"]

        try:
            content = file_path.read_text()

            if file_type == "issue":
                # Parse content for task-like items
                lines = [l.strip() for l in content.split("\n") if l.strip()]
                tasks_created = 0

                for line in lines:
                    # Skip headers and empty lines
                    if line.startswith("#") or not line:
                        continue
                    # Skip common markdown patterns
                    if line.startswith("---") or line.startswith("==="):
                        continue

                    # Clean up list markers
                    task_text = line.lstrip("-*•[] ").strip()
                    if not task_text or len(task_text) < 3:
                        continue

                    # Determine labels based on file name
                    labels = []
                    if "bug" in item["name"].lower():
                        labels.append("bug")
                    elif "idea" in item["name"].lower():
                        labels.append("idea")
                    elif "feature" in item["name"].lower():
                        labels.append("enhancement")

                    create_task(task_text[:200], labels=labels if labels else None)
                    tasks_created += 1

                if tasks_created > 0:
                    typer.secho(
                        f"  ✓ {item['name']}: Created {tasks_created} task(s)",
                        fg=typer.colors.GREEN,
                    )
                    # Archive the file
                    archive_path = root / ".idlergear" / "archive" / item["name"]
                    archive_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.rename(archive_path)
                    organized_count += 1
                else:
                    typer.secho(
                        f"  ! {item['name']}: No tasks found in file",
                        fg=typer.colors.YELLOW,
                    )

            elif file_type == "note":
                # Determine tags based on file name
                tags = []
                if "research" in item["name"].lower():
                    tags.append("research")
                elif "session" in item["name"].lower():
                    tags.append("session")

                # Create as single note with full content
                create_note(content[:2000], tags=tags if tags else None)
                typer.secho(f"  ✓ {item['name']}: Created note", fg=typer.colors.GREEN)

                # Archive the file
                archive_path = root / ".idlergear" / "archive" / item["name"]
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.rename(archive_path)
                organized_count += 1

        except Exception as e:
            typer.secho(f"  ✗ {item['name']}: {e}", fg=typer.colors.RED)

    typer.echo("")
    typer.secho(
        f"Organized {organized_count} file(s). Originals archived to .idlergear/archive/",
        fg=typer.colors.GREEN,
    )


@app.command()
def new(
    name: str = typer.Argument(..., help="Project name"),
    path: str = typer.Option(
        None, "--path", "-p", help="Parent directory (default: current)"
    ),
    template: str = typer.Option(
        "base", "--template", "-t", help="Template: base, python"
    ),
    python: bool = typer.Option(
        False, "--python", help="Shortcut for --template python"
    ),
    vision: str = typer.Option("", "--vision", "-v", help="Initial project vision"),
    description: str = typer.Option(
        "", "--description", "-d", help="Short description"
    ),
    no_git: bool = typer.Option(False, "--no-git", help="Skip git initialization"),
    no_venv: bool = typer.Option(
        False, "--no-venv", help="Skip venv creation (Python only)"
    ),
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
    auto_yes: bool = typer.Option(
        False, "--yes", "-y", help="Auto-accept all recommendations"
    ),
    check_only: bool = typer.Option(
        False, "--check", help="Only check, don't configure"
    ),
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
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
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
            typer.secho(
                f"  ✓ Set {backend_type} backend to {backend_name}",
                fg=typer.colors.GREEN,
            )
        typer.echo("")
        typer.secho("GitHub backends configured!", fg=typer.colors.GREEN)
        typer.echo("Your tasks and explorations will now sync with GitHub Issues.")
    else:
        typer.echo(
            "No changes made. You can run 'idlergear config backend' to configure manually."
        )


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
        typer.secho(
            "No IdlerGear installation found in this directory.", fg=typer.colors.YELLOW
        )
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
    if results.get("hook_scripts"):
        typer.echo("  • Hook scripts from .claude/hooks/")
    if results["claude_settings"]:
        typer.echo("  • Protected paths from .claude/settings.json")
    if results["idlergear_data"]:
        typer.secho(
            "  • .idlergear/ directory (ALL DATA)", fg=typer.colors.RED, bold=True
        )

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
    if results.get("hook_scripts"):
        typer.secho("  ✓ Hook scripts from .claude/hooks/", fg=typer.colors.GREEN)
    if results["claude_settings"]:
        typer.secho(
            "  ✓ Protected paths from .claude/settings.json", fg=typer.colors.GREEN
        )
    if results["idlergear_data"]:
        typer.secho("  ✓ .idlergear/ directory", fg=typer.colors.GREEN)

    typer.echo("")
    if not remove_data and idlergear_dir.exists():
        typer.echo(
            "Note: .idlergear/ directory preserved. Use --remove-data to delete it."
        )
    typer.secho("IdlerGear uninstalled.", fg=typer.colors.GREEN)


@app.command()
def install(
    skip_agents: bool = typer.Option(
        False, "--skip-agents", help="Skip AGENTS.md update"
    ),
    skip_claude: bool = typer.Option(
        False, "--skip-claude", help="Skip CLAUDE.md update"
    ),
    skip_rules: bool = typer.Option(
        False, "--skip-rules", help="Skip .claude/rules/ creation"
    ),
    skip_hooks: bool = typer.Option(
        False, "--skip-hooks", help="Skip .claude/hooks.json creation"
    ),
    skip_skill: bool = typer.Option(
        False, "--skip-skill", help="Skip .claude/skills/idlergear/ creation"
    ),
    skip_graph_hooks: bool = typer.Option(
        False, "--skip-graph-hooks", help="Skip knowledge graph auto-update hooks"
    ),
    auto_version: bool = typer.Option(
        False,
        "--auto-version",
        help="Install git hook to auto-bump patch version on commit",
    ),
    # Multi-assistant options
    all_assistants: bool = typer.Option(
        False, "--all", help="Install for all detected AI assistants"
    ),
    gemini: bool = typer.Option(False, "--gemini", help="Install for Gemini CLI"),
    copilot: bool = typer.Option(
        False, "--copilot", help="Install for GitHub Copilot CLI"
    ),
    codex: bool = typer.Option(False, "--codex", help="Install for Codex CLI"),
    aider: bool = typer.Option(False, "--aider", help="Install for Aider"),
    goose: bool = typer.Option(False, "--goose", help="Install for Goose"),
    cursor: bool = typer.Option(False, "--cursor", help="Install Cursor AI IDE rules"),
):
    """Install IdlerGear integration for Claude Code (and other assistants).

    Creates by default:
    - .mcp.json - MCP server registration
    - .claude/skills/idlergear/ - Skill with auto-triggering (RECOMMENDED)
    - CLAUDE.md - Usage instructions
    - AGENTS.md - AI agent instructions
    - .claude/rules/idlergear.md - Enforcement rules
    - .claude/hooks.json - Enforcement hooks
    - .git/hooks/post-commit, post-merge - Auto-update knowledge graph

    Optional:
    - .git/hooks/pre-commit - Auto-increment patch version (--auto-version)
    - .cursor/rules/*.mdc - Cursor AI IDE integration (--cursor)
    - .aider.conf.yml - Aider configuration (--aider)

    Note: Graph auto-update is enabled by default. Disable with:
          idlergear config set graph.auto_update false
    """
    from idlergear.config import find_idlergear_root
    from idlergear.install import (
        add_agents_md_section,
        add_auto_version_hook,
        add_claude_md_section,
        add_commands,
        add_graph_update_hooks,
        add_hooks_config,
        add_rules_file,
        add_skill,
        install_hook_scripts,
        install_mcp_server,
        install_scripts,
    )

    if find_idlergear_root() is None:
        # Auto-initialize if not already initialized
        from idlergear.init import init_project

        typer.secho("No .idlergear/ found, initializing...", fg=typer.colors.YELLOW)
        init_project(".")
        typer.echo("")

    # Install MCP server
    if install_mcp_server():
        typer.secho("Added idlergear to .mcp.json", fg=typer.colors.GREEN)
    else:
        typer.echo(".mcp.json already has idlergear configured")

    # Create skill (RECOMMENDED - auto-triggering)
    def report_results(results: dict[str, str], component: str):
        """Report created/updated/unchanged files."""
        created = [k for k, v in results.items() if v == "created"]
        updated = [k for k, v in results.items() if v == "updated"]
        backed_up = [k for k, v in results.items() if v == "backed_up"]
        unchanged = [k for k, v in results.items() if v == "unchanged"]
        if created:
            typer.secho(
                f"Created {component}: {', '.join(created)}", fg=typer.colors.GREEN
            )
        if updated:
            typer.secho(
                f"Updated {component}: {', '.join(updated)}", fg=typer.colors.YELLOW
            )
        if backed_up:
            typer.secho(
                f"Updated {component} (backed up user modifications): {', '.join(backed_up)}",
                fg=typer.colors.CYAN,
            )
        if unchanged and not created and not updated and not backed_up:
            typer.echo(f"{component} unchanged")

    # Create/update skill
    if not skip_skill:
        skill_results = add_skill()
        report_results(skill_results, "skill files")

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
        rules_result = add_rules_file()
        if rules_result == "created":
            typer.secho("Created .claude/rules/idlergear.md", fg=typer.colors.GREEN)
        elif rules_result == "updated":
            typer.secho("Updated .claude/rules/idlergear.md", fg=typer.colors.YELLOW)
        else:
            typer.echo(".claude/rules/idlergear.md unchanged")

    # Create hooks config and install hook scripts
    if not skip_hooks:
        if add_hooks_config():
            typer.secho("Added hooks to .claude/hooks.json", fg=typer.colors.GREEN)
        else:
            typer.echo(".claude/hooks.json already has IdlerGear hooks")
        hook_results = install_hook_scripts()
        report_results(hook_results, "hook scripts")

    # Install utility scripts (ig-askpass, ig-sudo, etc.)
    script_results = install_scripts()
    report_results(script_results, "utility scripts")

    # Install slash commands
    cmd_results = add_commands()
    report_results(cmd_results, "slash commands")

    # Install graph auto-update git hooks (by default)
    if not skip_graph_hooks:
        if add_graph_update_hooks():
            typer.secho(
                "Installed .git/hooks/post-commit and post-merge (graph auto-update)",
                fg=typer.colors.GREEN,
            )
        else:
            typer.echo(
                ".git/hooks already have graph update hooks (or not a git repo)"
            )

    # Install auto-version git hook (optional)
    if auto_version:
        if add_auto_version_hook():
            typer.secho(
                "Installed .git/hooks/pre-commit (auto-version)", fg=typer.colors.GREEN
            )
        else:
            typer.echo(
                ".git/hooks/pre-commit already has auto-version hook (or not a git repo)"
            )

    # Install Cursor AI IDE rules
    if cursor:
        from idlergear.cursor import install_cursor_rules, generate_cursorignore

        cursor_results = install_cursor_rules()
        report_results(cursor_results, ".cursor/rules/")

        cursorignore_action = generate_cursorignore()
        if cursorignore_action == "created":
            typer.secho("Created .cursorignore", fg=typer.colors.GREEN)
        elif cursorignore_action == "updated":
            typer.secho("Updated .cursorignore", fg=typer.colors.YELLOW)

    # Install Aider configuration
    if aider:
        from idlergear.aider import install_aider_config, generate_aiderignore

        config_action = install_aider_config()
        if config_action == "created":
            typer.secho("Created .aider.conf.yml", fg=typer.colors.GREEN)
        elif config_action == "updated":
            typer.secho("Updated .aider.conf.yml", fg=typer.colors.YELLOW)
        else:
            typer.secho(".aider.conf.yml unchanged", fg=typer.colors.BLUE)

        aiderignore_action = generate_aiderignore()
        if aiderignore_action == "created":
            typer.secho("Created .aiderignore", fg=typer.colors.GREEN)
        elif aiderignore_action == "updated":
            typer.secho("Updated .aiderignore", fg=typer.colors.YELLOW)

    # Store IdlerGear version for future upgrade detection
    from idlergear.upgrade import set_project_version
    from idlergear import __version__

    set_project_version(__version__)

    # Handle multi-assistant installation
    from idlergear.assistant_install import (
        Assistant,
        install_for_assistant,
        install_for_all,
    )

    other_assistants = []
    if gemini:
        other_assistants.append(Assistant.GEMINI)
    if copilot:
        other_assistants.append(Assistant.COPILOT)
    if codex:
        other_assistants.append(Assistant.CODEX)
    if aider:
        other_assistants.append(Assistant.AIDER)
    if goose:
        other_assistants.append(Assistant.GOOSE)

    if all_assistants:
        typer.echo("")
        typer.secho("Installing for all detected assistants...", fg=typer.colors.CYAN)
        all_results = install_for_all()
        for assistant_name, results in all_results.items():
            if results:
                typer.secho(f"\n{assistant_name}:", bold=True)
                report_results(results, "files")
        if not all_results:
            typer.echo("No additional AI assistants detected.")

    elif other_assistants:
        typer.echo("")
        for assistant in other_assistants:
            typer.secho(f"\nInstalling for {assistant.value}...", fg=typer.colors.CYAN)
            results = install_for_assistant(assistant)
            report_results(results, f"{assistant.value} files")

    typer.echo("")
    typer.echo("Claude Code will now have access to IdlerGear tools.")
    typer.echo("IdlerGear auto-starts at session beginning via hooks and skill.")
    typer.echo(
        "Available commands: /ig_start (refresh context), /ig_status (diagnostics)"
    )
    typer.echo("Restart Claude Code or run /mcp to verify.")

    if other_assistants or all_assistants:
        typer.echo("")
        typer.echo("Other assistants configured - restart them to activate IdlerGear.")


# Daemon commands
@daemon_app.command("start")
def daemon_start(
    foreground: bool = typer.Option(
        False, "--foreground", "-f", help="Run in foreground"
    ),
):
    """Start the IdlerGear daemon."""
    from idlergear.config import find_idlergear_root
    from idlergear.daemon.lifecycle import DaemonLifecycle

    root = find_idlergear_root()
    if root is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
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
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
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
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
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
            typer.secho(
                f"  Warning: {status.get('error', 'Not healthy')}",
                fg=typer.colors.YELLOW,
            )
    else:
        typer.secho("Daemon: not running", fg=typer.colors.YELLOW)
        typer.echo(f"  Socket: {status.get('socket')}")


@daemon_app.command("queue")
def daemon_queue_command(
    command: str = typer.Argument(..., help="Command to queue for execution"),
    priority: int = typer.Option(
        5, "--priority", "-p", help="Priority (1-10, higher = more urgent)"
    ),
    wait: bool = typer.Option(
        False, "--wait", "-w", help="Wait for command to complete"
    ),
):
    """Queue a command for execution by any available AI agent."""
    import asyncio
    from idlergear.config import find_idlergear_root
    from idlergear.daemon.client import DaemonClient

    root = find_idlergear_root()
    if root is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    async def queue_cmd():
        async with DaemonClient(root) as client:
            cmd_id = await client.queue_command(command, priority=priority)
            typer.secho(f"Command queued: {cmd_id}", fg=typer.colors.GREEN)

            if wait:
                typer.echo("Waiting for command to complete...")
                # Poll for result
                while True:
                    result = await client.get_command_result(cmd_id)
                    if result:
                        typer.echo("\nResult:")
                        if result.get("success"):
                            typer.secho(result.get("output", ""), fg=typer.colors.GREEN)
                        else:
                            typer.secho(
                                f"Error: {result.get('error')}", fg=typer.colors.RED
                            )
                        break
                    await asyncio.sleep(1)

            return cmd_id

    try:
        asyncio.run(queue_cmd())
    except Exception as e:
        typer.secho(f"Failed to queue command: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@daemon_app.command("agents")
def daemon_agents():
    """List all active AI agents connected to the daemon."""
    import asyncio
    from idlergear.config import find_idlergear_root
    from idlergear.daemon.client import DaemonClient

    root = find_idlergear_root()
    if root is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    async def list_agents():
        async with DaemonClient(root) as client:
            agents = await client.list_agents()

            if not agents:
                typer.echo("No active agents.")
                return

            typer.echo(f"\nActive agents ({len(agents)}):\n")
            for agent in agents:
                status_color = {
                    "active": typer.colors.GREEN,
                    "idle": typer.colors.YELLOW,
                    "busy": typer.colors.CYAN,
                }.get(agent.get("status", "unknown"), typer.colors.WHITE)

                typer.secho(
                    f"  • {agent['name']}", fg=typer.colors.BRIGHT_WHITE, bold=True
                )
                typer.echo(f"    ID:     {agent['agent_id']}")
                typer.secho(f"    Status: {agent['status']}", fg=status_color)
                typer.echo(f"    Type:   {agent.get('agent_type', 'unknown')}")
                if agent.get("current_task"):
                    typer.echo(f"    Task:   {agent['current_task']}")
                typer.echo()

    try:
        asyncio.run(list_agents())
    except Exception as e:
        typer.secho(f"Failed to list agents: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@daemon_app.command("send")
def daemon_send_message(
    message: str = typer.Argument(..., help="Message to broadcast to all agents"),
):
    """Send a message to all active AI agents."""
    import asyncio
    from idlergear.config import find_idlergear_root
    from idlergear.daemon.client import DaemonClient

    root = find_idlergear_root()
    if root is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    async def send_msg():
        async with DaemonClient(root) as client:
            await client.broadcast_event(
                {
                    "type": "user_message",
                    "message": message,
                    "timestamp": asyncio.get_event_loop().time(),
                }
            )
            typer.secho("Message sent to all agents.", fg=typer.colors.GREEN)

    try:
        asyncio.run(send_msg())
    except Exception as e:
        typer.secho(f"Failed to send message: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@daemon_app.command("queue-list")
def daemon_queue_list():
    """List all queued commands."""
    import asyncio
    from idlergear.config import find_idlergear_root
    from idlergear.daemon.client import DaemonClient

    root = find_idlergear_root()
    if root is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    async def list_queue():
        async with DaemonClient(root) as client:
            commands = await client.list_queued_commands()

            if not commands:
                typer.echo("No queued commands.")
                return

            typer.echo(f"\nQueued commands ({len(commands)}):\n")
            for cmd in commands:
                status_color = {
                    "pending": typer.colors.YELLOW,
                    "assigned": typer.colors.CYAN,
                    "running": typer.colors.BLUE,
                    "completed": typer.colors.GREEN,
                    "failed": typer.colors.RED,
                }.get(cmd.get("status", "unknown"), typer.colors.WHITE)

                typer.secho(
                    f"  [{cmd['id'][:8]}]", fg=typer.colors.BRIGHT_WHITE, bold=True
                )
                typer.secho(f"    Status:   {cmd['status']}", fg=status_color)
                typer.echo(f"    Command:  {cmd['command'][:60]}...")
                typer.echo(f"    Priority: {cmd.get('priority', 5)}")
                if cmd.get("assigned_to"):
                    typer.echo(f"    Agent:    {cmd['assigned_to']}")
                typer.echo()

    try:
        asyncio.run(list_queue())
    except Exception as e:
        typer.secho(f"Failed to list queue: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


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
        typer.echo(
            "The MCP server may not be running, or was started without PID tracking."
        )
        raise typer.Exit(1)

    reloaded = 0
    for pid_file in pid_files:
        try:
            pid = int(open(pid_file).read().strip())

            # Check if process exists
            os.kill(pid, 0)  # Signal 0 just checks existence

            # Send reload signal
            os.kill(pid, signal.SIGUSR1)
            typer.secho(
                f"Sent reload signal to MCP server (PID {pid})", fg=typer.colors.GREEN
            )
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
            typer.secho(
                f"Cleaned up stale PID file: {pid_file}", fg=typer.colors.YELLOW
            )
        except PermissionError:
            typer.secho(
                f"Permission denied sending signal to PID from {pid_file}",
                fg=typer.colors.RED,
            )

    if reloaded == 0:
        typer.secho("No active MCP servers found to reload.", fg=typer.colors.YELLOW)
        raise typer.Exit(1)
    else:
        typer.echo(
            f"\nReloaded {reloaded} MCP server(s). New code will be active for next tool call."
        )


@mcp_app.command("status")
def mcp_status():
    """Show status of running MCP servers."""
    import glob
    import os

    from idlergear.mcp_server import __version__

    pid_files = glob.glob("/tmp/idlergear-mcp-*.pid")

    if not pid_files:
        typer.secho("No running MCP servers found.", fg=typer.colors.YELLOW)
        typer.echo(
            "The MCP server may not be running, or was started without PID tracking."
        )
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


@mcp_app.command("generate")
def mcp_generate(
    ctx: typer.Context,
    global_config: bool = typer.Option(
        False,
        "--global",
        "-g",
        help="Generate global Claude Code config instead of project-level",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be generated without writing"
    ),
    include_idlergear: bool = typer.Option(
        True, "--idlergear/--no-idlergear", help="Include IdlerGear MCP server"
    ),
):
    """Generate MCP configuration file.

    Creates .mcp.json for project-level config, or updates Claude Code's
    global config for --global.
    """

    from idlergear.mcp_config import (
        generate_project_mcp_config,
        get_claude_code_config_path,
        get_project_mcp_path,
    )

    if global_config:
        config_path = get_claude_code_config_path()
    else:
        config_path = get_project_mcp_path()

    config = generate_project_mcp_config(include_idlergear=include_idlergear)
    content = json.dumps(config.to_dict(), indent=2)

    if dry_run:
        typer.echo(f"Would write to {config_path}:")
        typer.echo(content)
        return

    if config_path.exists():
        typer.secho(f"Config already exists: {config_path}", fg=typer.colors.YELLOW)
        if not typer.confirm("Overwrite?"):
            raise typer.Exit(0)

    config.save(config_path)
    typer.secho(f"Generated {config_path}", fg=typer.colors.GREEN)


@mcp_app.command("show")
def mcp_show(
    ctx: typer.Context,
    global_config: bool = typer.Option(
        False, "--global", "-g", help="Show global Claude Code config"
    ),
):
    """Show current MCP configuration."""
    from idlergear.mcp_config import (
        get_claude_code_config_path,
        get_project_mcp_path,
        load_claude_code_config,
        load_project_mcp_config,
    )

    if global_config:
        config_path = get_claude_code_config_path()
        config = load_claude_code_config()
    else:
        config_path = get_project_mcp_path()
        config = load_project_mcp_config()

    if config is None:
        typer.secho(f"No config found at {config_path}", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    typer.echo(f"Config: {config_path}")
    typer.echo("")

    if not config.servers:
        typer.echo("No MCP servers configured.")
        return

    for name, server in config.servers.items():
        typer.secho(f"  {name}:", fg=typer.colors.CYAN, bold=True)
        typer.echo(f"    command: {server.command}")
        if server.args:
            typer.echo(f"    args: {' '.join(server.args)}")
        if server.env:
            typer.echo(f"    env: {server.env}")
        typer.echo(f"    type: {server.type}")


@mcp_app.command("check")
def mcp_check(
    ctx: typer.Context,
    global_config: bool = typer.Option(
        False, "--global", "-g", help="Check global Claude Code config"
    ),
):
    """Validate MCP configuration."""
    from idlergear.mcp_config import (
        get_claude_code_config_path,
        get_project_mcp_path,
        load_claude_code_config,
        load_project_mcp_config,
        validate_mcp_config,
    )

    if global_config:
        config_path = get_claude_code_config_path()
        config = load_claude_code_config()
    else:
        config_path = get_project_mcp_path()
        config = load_project_mcp_config()

    if config is None:
        typer.secho(f"No config found at {config_path}", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    result = validate_mcp_config(config)

    if result.valid and not result.warnings:
        typer.secho("✓ Configuration is valid", fg=typer.colors.GREEN)
        return

    if result.issues:
        typer.secho("Errors:", fg=typer.colors.RED, bold=True)
        for issue in result.issues:
            typer.echo(f"  ✗ {issue}")

    if result.warnings:
        typer.secho("Warnings:", fg=typer.colors.YELLOW, bold=True)
        for warning in result.warnings:
            typer.echo(f"  ⚠ {warning}")

    if not result.valid:
        raise typer.Exit(1)


@mcp_app.command("add")
def mcp_add(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Server name"),
    command: str = typer.Argument(..., help="Command to run the server"),
    args: Optional[list[str]] = typer.Option(
        None, "--arg", "-a", help="Command arguments (can be repeated)"
    ),
    server_type: str = typer.Option(
        "stdio", "--type", "-t", help="Server type (stdio, sse, http)"
    ),
    global_config: bool = typer.Option(
        False, "--global", "-g", help="Add to global Claude Code config"
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite if server already exists"
    ),
):
    """Add an MCP server to configuration."""
    from idlergear.mcp_config import (
        McpServerConfig,
        add_server_to_config,
        get_claude_code_config_path,
        get_project_mcp_path,
    )

    if global_config:
        config_path = get_claude_code_config_path()
    else:
        config_path = get_project_mcp_path()

    server = McpServerConfig(
        name=name,
        command=command,
        args=args or [],
        type=server_type,
    )

    success, message = add_server_to_config(config_path, server, overwrite=overwrite)

    if success:
        typer.secho(message, fg=typer.colors.GREEN)
    else:
        typer.secho(message, fg=typer.colors.RED)
        raise typer.Exit(1)


@mcp_app.command("remove")
def mcp_remove(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Server name to remove"),
    global_config: bool = typer.Option(
        False, "--global", "-g", help="Remove from global Claude Code config"
    ),
):
    """Remove an MCP server from configuration."""
    from idlergear.mcp_config import (
        get_claude_code_config_path,
        get_project_mcp_path,
        remove_server_from_config,
    )

    if global_config:
        config_path = get_claude_code_config_path()
    else:
        config_path = get_project_mcp_path()

    success, message = remove_server_from_config(config_path, name)

    if success:
        typer.secho(message, fg=typer.colors.GREEN)
    else:
        typer.secho(message, fg=typer.colors.RED)
        raise typer.Exit(1)


@mcp_app.command("test")
def mcp_test_cmd(
    ctx: typer.Context,
    server_name: Optional[str] = typer.Argument(
        None, help="Server name to test (tests all if not specified)"
    ),
    global_config: bool = typer.Option(
        False, "--global", "-g", help="Test servers from global config"
    ),
    timeout: float = typer.Option(5.0, "--timeout", help="Timeout in seconds"),
):
    """Test MCP server connectivity."""
    import asyncio

    from idlergear.mcp_config import (
        get_claude_code_config_path,
        get_project_mcp_path,
        load_claude_code_config,
        load_project_mcp_config,
        test_mcp_server,
    )

    if global_config:
        config_path = get_claude_code_config_path()
        config = load_claude_code_config()
    else:
        config_path = get_project_mcp_path()
        config = load_project_mcp_config()

    if config is None:
        typer.secho(f"No config found at {config_path}", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    servers_to_test = []
    if server_name:
        if server_name not in config.servers:
            typer.secho(
                f"Server '{server_name}' not found in config", fg=typer.colors.RED
            )
            raise typer.Exit(1)
        servers_to_test.append(config.servers[server_name])
    else:
        servers_to_test = list(config.servers.values())

    if not servers_to_test:
        typer.echo("No servers to test.")
        return

    async def run_tests():
        results = []
        for server in servers_to_test:
            typer.echo(f"Testing {server.name}...", nl=False)
            result = await test_mcp_server(server, timeout=timeout)
            results.append(result)

            if result.success:
                typer.secho(
                    f" OK ({result.response_time_ms:.0f}ms)",
                    fg=typer.colors.GREEN,
                )
                if result.server_info:
                    info = result.server_info
                    typer.echo(
                        f"  Server: {info.get('name', 'unknown')} {info.get('version', '')}"
                    )
            else:
                typer.secho(f" FAILED: {result.error}", fg=typer.colors.RED)

        return results

    results = asyncio.run(run_tests())
    failed = sum(1 for r in results if not r.success)

    typer.echo("")
    if failed:
        typer.secho(f"{failed}/{len(results)} servers failed", fg=typer.colors.RED)
        raise typer.Exit(1)
    else:
        typer.secho(f"All {len(results)} servers OK", fg=typer.colors.GREEN)


@daemon_app.command("cleanup")
def daemon_cleanup(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be removed without removing"),
    all_agents: bool = typer.Option(False, "--all", help="Remove all presence files (nuclear option)"),
):
    """Clean up stale agent presence files.

    An agent is considered stale if:
    - Presence file exists but daemon is not running OR
    - Agent is not in daemon's active registry OR
    - last_heartbeat is older than 5 minutes

    Examples:
        idlergear daemon cleanup --dry-run    # Preview stale agents
        idlergear daemon cleanup               # Remove stale agents
        idlergear daemon cleanup --all         # Remove all presence files
    """
    import json
    from datetime import datetime, timezone, timedelta
    from idlergear.config import find_idlergear_root
    from idlergear.daemon.lifecycle import DaemonLifecycle

    root = find_idlergear_root()
    if root is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    idlergear_dir = root / ".idlergear"
    agents_dir = idlergear_dir / "agents"

    if not agents_dir.exists():
        typer.echo("No agents directory found.")
        return

    # Get all presence files
    presence_files = [f for f in agents_dir.glob("*.json") if f.name != "agents.json"]

    if not presence_files:
        typer.echo("No agent presence files found.")
        return

    # Check if daemon is running
    lifecycle = DaemonLifecycle(idlergear_dir)
    daemon_running = lifecycle.is_running()

    # Get active agents from daemon registry
    active_agent_ids = set()
    if daemon_running:
        try:
            import asyncio
            from idlergear.daemon.client import DaemonClient

            async def get_active():
                async with DaemonClient(root) as client:
                    agents = await client.list_agents()
                    return {a["agent_id"] for a in agents}

            active_agent_ids = asyncio.run(get_active())
        except Exception:
            # If we can't get active agents, assume none are active
            pass

    # Identify stale presence files
    stale_files = []
    kept_files = []
    staleness_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)

    for presence_file in presence_files:
        try:
            data = json.loads(presence_file.read_text())
            agent_id = data.get("agent_id", presence_file.stem)
            last_heartbeat_str = data.get("last_heartbeat")

            # Determine if stale
            is_stale = False

            if all_agents:
                # --all flag: consider all files stale
                is_stale = True
            elif not daemon_running:
                # Daemon not running: all are considered stale
                is_stale = True
            elif agent_id not in active_agent_ids:
                # Not in daemon registry: stale
                is_stale = True
            elif last_heartbeat_str:
                # Check heartbeat age
                try:
                    last_heartbeat = datetime.fromisoformat(last_heartbeat_str.replace("Z", "+00:00"))
                    if last_heartbeat < staleness_cutoff:
                        is_stale = True
                except (ValueError, AttributeError):
                    # Can't parse heartbeat, consider stale
                    is_stale = True

            if is_stale:
                stale_files.append((presence_file, data))
            else:
                kept_files.append((presence_file, data))

        except (json.JSONDecodeError, OSError):
            # Malformed file, consider it stale
            stale_files.append((presence_file, {}))

    # Display results
    if not stale_files:
        typer.secho("✓ No stale agent presence files found.", fg=typer.colors.GREEN)
        if kept_files:
            typer.echo(f"  {len(kept_files)} active agent(s) present")
        return

    # Show what will be removed
    typer.echo(f"\nFound {len(stale_files)} stale agent presence file(s):\n")

    for presence_file, data in stale_files:
        agent_id = data.get("agent_id", presence_file.stem)
        agent_type = data.get("agent_type", "unknown")
        connected_at = data.get("connected_at", "unknown")
        last_hb = data.get("last_heartbeat", "unknown")

        # Calculate age
        try:
            if last_hb and last_hb != "unknown":
                hb_time = datetime.fromisoformat(last_hb.replace("Z", "+00:00"))
                age = datetime.now(timezone.utc) - hb_time
                age_str = f"{age.days}d {age.seconds // 3600}h ago" if age.days > 0 else f"{age.seconds // 3600}h {(age.seconds % 3600) // 60}m ago"
            else:
                age_str = "unknown"
        except (ValueError, AttributeError):
            age_str = "unknown"

        typer.echo(f"  • {agent_id}")
        typer.echo(f"    Type: {agent_type}")
        typer.echo(f"    Last seen: {age_str}")
        typer.echo()

    if kept_files:
        typer.echo(f"Keeping {len(kept_files)} active agent(s)\n")

    # Dry run or actual cleanup
    if dry_run:
        typer.echo(f"Dry run: Would remove {len(stale_files)} presence file(s)")
        typer.echo("Run without --dry-run to actually remove them")
        return

    # Actual cleanup
    removed = 0
    for presence_file, data in stale_files:
        try:
            presence_file.unlink()
            removed += 1
        except OSError as e:
            agent_id = data.get("agent_id", presence_file.stem)
            typer.secho(f"  ✗ Failed to remove {agent_id}: {e}", fg=typer.colors.RED)

    typer.secho(f"\n✓ Removed {removed}/{len(stale_files)} stale presence file(s)", fg=typer.colors.GREEN)


# Config commands
@config_app.command("get")
def config_get(key: str):
    """Get a configuration value."""
    from idlergear.config import find_idlergear_root, get_config_value

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    value = get_config_value(key)
    if value is None:
        typer.echo(f"{key}: (not set)")
    else:
        typer.echo(f"{key}: {value}")


@config_app.command("set")
def config_set(key: str, value: str):
    """Set a configuration value.

    Values are automatically converted to the correct type based on schema:
    - Booleans: "true", "false", "yes", "no", "1", "0"
    - Integers: "123", "456"
    - Strings: anything else
    """
    from idlergear.config import CONFIG_SCHEMAS, find_idlergear_root, set_config_value

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    # Parse value based on schema type
    parsed_value: str | bool | int | float = value
    parts = key.split(".")
    if len(parts) >= 2 and parts[0] in CONFIG_SCHEMAS:
        schema = CONFIG_SCHEMAS[parts[0]]
        field_path = parts[1:]
        current = schema
        for part in field_path:
            if isinstance(current, dict) and part in current:
                current = current[part]

        if isinstance(current, dict) and "type" in current:
            expected_type = current["type"]

            # Convert value to expected type
            if expected_type == "boolean":
                if value.lower() in ("true", "yes", "1"):
                    parsed_value = True
                elif value.lower() in ("false", "no", "0"):
                    parsed_value = False
                else:
                    typer.secho(
                        f"Invalid boolean value: {value}. Use: true, false, yes, no, 1, or 0",
                        fg=typer.colors.RED,
                    )
                    raise typer.Exit(1)
            elif expected_type == "integer":
                try:
                    parsed_value = int(value)
                except ValueError:
                    typer.secho(
                        f"Invalid integer value: {value}",
                        fg=typer.colors.RED,
                    )
                    raise typer.Exit(1)
            elif expected_type == "float":
                try:
                    parsed_value = float(value)
                except ValueError:
                    typer.secho(
                        f"Invalid float value: {value}",
                        fg=typer.colors.RED,
                    )
                    raise typer.Exit(1)

    try:
        set_config_value(key, parsed_value)
        typer.secho(f"Set {key} = {parsed_value}", fg=typer.colors.GREEN)
    except ValueError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


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
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
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
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    valid_types = ["task", "reference", "note"]
    if backend_type not in valid_types:
        typer.secho(f"Invalid backend type: {backend_type}", fg=typer.colors.RED)
        typer.echo(f"Valid types: {', '.join(valid_types)}")
        raise typer.Exit(1)

    if source == target:
        typer.secho(
            "Source and target backends must be different.", fg=typer.colors.RED
        )
        raise typer.Exit(1)

    typer.echo(f"Migrating {backend_type}s from {source} to {target}...")

    def on_item(info: dict) -> None:
        src = info["source"]
        tgt = info["target"]
        title = src.get("title", src.get("content", "")[:40])
        typer.echo(f"  ✓ #{src.get('id', '?')} → #{tgt.get('id', '?')}: {title}")

    def on_error(item: dict, error: Exception) -> None:
        title = item.get("title", item.get("content", "")[:40])
        typer.secho(
            f"  ✗ #{item.get('id', '?')}: {title} - {error}", fg=typer.colors.RED
        )

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
            typer.echo(
                f"\nDry run: {stats['total']} {backend_type}(s) would be migrated."
            )
        else:
            typer.echo("\nMigration complete:")
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
    priority: str = typer.Option(
        None, "--priority", "-p", help="Priority: high, medium, low"
    ),
    due: str = typer.Option(None, "--due", "-d", help="Due date (YYYY-MM-DD)"),
    milestone: str = typer.Option(None, "--milestone", "-m", help="Milestone number or title"),
    needs_tests: bool = typer.Option(
        False, "--needs-tests", help="Mark task as requiring test coverage"
    ),
    no_validate: bool = typer.Option(False, "--no-validate", help="Skip label validation"),
):
    """Create a new task."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root
    import subprocess

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("task")

    # Add needs-tests label if flag is set
    labels_list = list(labels) if labels else []
    if needs_tests and "needs-tests" not in labels_list:
        labels_list.append("needs-tests")

    # Validate and potentially create labels if any were provided
    if labels_list and not no_validate:
        valid_labels, invalid_labels = validate_labels(labels_list)

        if invalid_labels:
            # Ask user if they want to create the missing labels
            create = typer.confirm(
                f"Create missing labels: {', '.join(invalid_labels)}?",
                default=True,
            )

            if create:
                for label in invalid_labels:
                    try:
                        subprocess.run(
                            ["gh", "label", "create", label],
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                        typer.secho(f"  ✓ Created label: {label}", fg=typer.colors.GREEN)
                    except subprocess.CalledProcessError:
                        typer.secho(f"  ✗ Failed to create label: {label}", fg=typer.colors.RED)
                        raise typer.Exit(1)
            else:
                typer.secho("Cancelled - cannot create task without valid labels.", fg=typer.colors.YELLOW)
                raise typer.Exit(1)

    task = backend.create(
        title,
        body=body,
        labels=labels_list if labels_list else None,
        priority=priority,
        due=due,
        milestone=milestone,
    )
    typer.secho(f"Created task #{task['id']}: {task['title']}", fg=typer.colors.GREEN)

    # Auto-add to project if configured
    from idlergear.projects import auto_add_task_if_configured
    from idlergear.config import get_config_value

    if auto_add_task_if_configured(task['id']):
        default_project = get_config_value("projects.default_project")
        typer.secho(
            f"  ✓ Added to project '{default_project}'",
            fg=typer.colors.GREEN
        )


@task_app.command("list")
def task_list(
    ctx: typer.Context,
    state: str = typer.Option(
        "open", "--state", "-s", help="Filter by state: open, closed, all"
    ),
    priority: str = typer.Option(
        None, "--priority", "-p", help="Filter by priority: high, medium, low"
    ),
    labels: list[str] = typer.Option(
        [], "--label", "-l", help="Filter by labels (can specify multiple)"
    ),
    limit: int = typer.Option(None, "--limit", "-n", help="Limit number of results"),
    preview: bool = typer.Option(
        False,
        "--preview",
        help="Show brief preview instead of full body (token-efficient)",
    ),
):
    """List tasks.

    Examples:
        idlergear task list                  # List all open tasks
        idlergear task list --limit 5        # Top 5 tasks only
        idlergear task list --preview        # Titles only (minimal tokens)
        idlergear task list --state all      # Include closed tasks
        idlergear task list --label bug      # Only bug tasks
    """
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("task")
    tasks = backend.list(state=state)

    # Filter by priority if specified
    if priority:
        tasks = [t for t in tasks if t.get("priority") == priority]

    # Filter by labels if specified
    if labels:
        tasks = [
            t
            for t in tasks
            if any(label in t.get("labels", []) for label in labels)
        ]

    # Apply limit if specified
    if limit:
        tasks = tasks[:limit]

    # Strip task bodies if preview mode (token-efficient)
    if preview:
        for task in tasks:
            task["body"] = None

    display(tasks, ctx.obj.output_format, "tasks")


@task_app.command("show")
def task_show(ctx: typer.Context, task_id: int):
    """Show a task."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root
    from idlergear.git import GitServer

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("task")
    task = backend.get(task_id)

    if task is None and ctx.obj.output_format == "human":
        typer.secho(f"Task #{task_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Add test coverage info if in a git repo
    try:
        git = GitServer()
        coverage = git.get_task_test_coverage(task_id)
        task["test_coverage"] = coverage
    except Exception:
        # Not in a git repo or other error - continue without coverage info
        pass

    display(task, ctx.obj.output_format, "task")


@task_app.command("close")
def task_close(
    task_id: int,
    comment: str = typer.Option(None, "--comment", "-c", help="Closing comment"),
):
    """Close a task.

    Optionally provide a closing comment. When using GitHub backend,
    the comment will be added to the issue.
    """
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root
    from idlergear.git import GitServer

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("task")

    # Get task first to check labels before closing
    task = backend.get(task_id)
    if task is None:
        typer.secho(f"Task #{task_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Check if task needs tests but none were added
    if task.get("labels") and "needs-tests" in task["labels"]:
        try:
            git = GitServer()
            coverage = git.get_task_test_coverage(task_id)
            if not coverage["has_tests"]:
                typer.secho(
                    "⚠️  Warning: Task marked 'needs-tests' but no test files in commits",
                    fg=typer.colors.YELLOW,
                )
                typer.secho(
                    "   Consider adding tests before closing.",
                    fg=typer.colors.YELLOW,
                )
                if not typer.confirm("Close anyway?", default=False):
                    typer.secho("Task close aborted.", fg=typer.colors.CYAN)
                    raise typer.Abort()
        except typer.Abort:
            # Re-raise Abort to allow it to propagate
            raise
        except Exception:
            # Not in a git repo or other error - continue without check
            pass

    # Proceed with close
    task = backend.close(task_id, comment=comment)
    if task is None:
        typer.secho(f"Task #{task_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Closed task #{task_id}: {task['title']}", fg=typer.colors.GREEN)
    if comment:
        typer.secho(f"  Comment: {comment}", fg=typer.colors.CYAN)


@task_app.command("edit")
def task_edit(
    task_id: int,
    title: str = typer.Option(None, "--title", "-t", help="New title"),
    body: str = typer.Option(None, "--body", "-b", help="New body"),
    add_label: list[str] = typer.Option([], "--add-label", help="Add label"),
    priority: str = typer.Option(
        None, "--priority", "-p", help="Priority: high, medium, low (empty to clear)"
    ),
    due: str = typer.Option(
        None, "--due", "-d", help="Due date (YYYY-MM-DD, empty to clear)"
    ),
):
    """Edit a task."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
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

    task = backend.update(
        task_id, title=title, body=body, labels=labels, priority=priority, due=due
    )
    typer.secho(f"Updated task #{task_id}", fg=typer.colors.GREEN)


@task_app.command("reopen")
def task_reopen(task_id: int):
    """Reopen a closed task."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("task")
    task = backend.reopen(task_id)
    if task is None:
        typer.secho(f"Task #{task_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Reopened task #{task_id}: {task['title']}", fg=typer.colors.GREEN)


@task_app.command("sync")
def task_sync(target: str = typer.Argument("github")):
    """Sync tasks with remote."""
    typer.echo(f"Syncing tasks to {target}...")
    # See task #317


# Label commands
@label_app.command("list")
def label_list(
    ctx: typer.Context,
):
    """List all labels in the repository.

    Examples:
        idlergear label list
        idlergear label list --json
    """
    import subprocess

    try:
        # Use gh label list to get all labels
        result = subprocess.run(
            ["gh", "label", "list", "--json", "name,description,color"],
            capture_output=True,
            text=True,
            check=True,
        )

        import json
        labels = json.loads(result.stdout)

        if ctx.obj.output_format == "json":
            typer.echo(json.dumps(labels, indent=2))
        else:
            if not labels:
                typer.echo("No labels found.")
                return

            typer.echo(f"\nFound {len(labels)} labels:\n")
            for label in labels:
                name = label.get("name", "")
                desc = label.get("description", "")
                color = label.get("color", "")

                # Display with color if available
                desc_str = f" - {desc}" if desc else ""
                color_str = f" (#{color})" if color else ""
                typer.echo(f"  • {name}{desc_str}{color_str}")
            typer.echo()

    except FileNotFoundError:
        typer.secho(
            "GitHub CLI (gh) not found. Install from: https://cli.github.com",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    except subprocess.CalledProcessError as e:
        typer.secho(f"Error listing labels: {e.stderr}", fg=typer.colors.RED)
        raise typer.Exit(1)


@label_app.command("create")
def label_create(
    name: str,
    description: str = typer.Option(None, "--description", "-d", help="Label description"),
    color: str = typer.Option(None, "--color", "-c", help="Label color (hex without #)"),
    force: bool = typer.Option(False, "--force", "-f", help="Update if exists"),
):
    """Create a new label.

    Examples:
        idlergear label create bug --description "Bug report" --color D73A4A
        idlergear label create enhancement --force
    """
    import subprocess

    try:
        args = ["gh", "label", "create", name]

        if description:
            args.extend(["--description", description])
        if color:
            args.extend(["--color", color])
        if force:
            args.append("--force")

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=True,
        )

        typer.secho(f"✓ Created label: {name}", fg=typer.colors.GREEN)

    except FileNotFoundError:
        typer.secho(
            "GitHub CLI (gh) not found. Install from: https://cli.github.com",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    except subprocess.CalledProcessError as e:
        if "already exists" in e.stderr:
            typer.secho(
                f"Label '{name}' already exists. Use --force to update.",
                fg=typer.colors.YELLOW,
            )
        else:
            typer.secho(f"Error creating label: {e.stderr}", fg=typer.colors.RED)
        raise typer.Exit(1)


@label_app.command("delete")
def label_delete(
    name: str,
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a label.

    Examples:
        idlergear label delete old-label
        idlergear label delete old-label --yes
    """
    import subprocess

    if not confirm:
        confirmed = typer.confirm(f"Delete label '{name}'?")
        if not confirmed:
            typer.echo("Cancelled.")
            raise typer.Exit(0)

    try:
        result = subprocess.run(
            ["gh", "label", "delete", name, "--yes"],
            capture_output=True,
            text=True,
            check=True,
        )

        typer.secho(f"✓ Deleted label: {name}", fg=typer.colors.GREEN)

    except FileNotFoundError:
        typer.secho(
            "GitHub CLI (gh) not found. Install from: https://cli.github.com",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    except subprocess.CalledProcessError as e:
        typer.secho(f"Error deleting label: {e.stderr}", fg=typer.colors.RED)
        raise typer.Exit(1)


@label_app.command("edit")
def label_edit(
    name: str,
    new_name: str = typer.Option(None, "--name", "-n", help="New label name"),
    description: str = typer.Option(None, "--description", "-d", help="New description"),
    color: str = typer.Option(None, "--color", "-c", help="New color (hex without #)"),
):
    """Edit an existing label.

    Examples:
        idlergear label edit bug --description "Critical bug"
        idlergear label edit old-name --name new-name
        idlergear label edit enhancement --color 00FF00
    """
    import subprocess

    if not any([new_name, description, color]):
        typer.secho(
            "At least one of --name, --description, or --color must be specified.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(1)

    try:
        args = ["gh", "label", "edit", name]

        if new_name:
            args.extend(["--name", new_name])
        if description:
            args.extend(["--description", description])
        if color:
            args.extend(["--color", color])

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=True,
        )

        display_name = new_name if new_name else name
        typer.secho(f"✓ Updated label: {display_name}", fg=typer.colors.GREEN)

    except FileNotFoundError:
        typer.secho(
            "GitHub CLI (gh) not found. Install from: https://cli.github.com",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    except subprocess.CalledProcessError as e:
        typer.secho(f"Error editing label: {e.stderr}", fg=typer.colors.RED)
        raise typer.Exit(1)


@label_app.command("ensure-standards")
def label_ensure_standards(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be created"),
):
    """Ensure GitHub best practice labels exist.

    Creates standard labels recommended for project management:
    - bug (D73A4A) - Something isn't working
    - enhancement (A2EEEF) - New feature or request
    - documentation (0075CA) - Improvements or additions to documentation
    - good first issue (7057FF) - Good for newcomers
    - help wanted (008672) - Extra attention is needed
    - question (D876E3) - Further information is requested
    - wontfix (FFFFFF) - This will not be worked on
    - duplicate (CFD3D7) - This issue or pull request already exists
    - invalid (E4E669) - This doesn't seem right
    - tech-debt (FBCA04) - Technical debt
    - decision (C5DEF5) - Design decision
    - exploration (0E8A16) - Research or exploration

    Examples:
        idlergear label ensure-standards
        idlergear label ensure-standards --dry-run
    """
    import subprocess
    import json

    # Standard GitHub labels with colors and descriptions
    standard_labels = {
        "bug": {"color": "D73A4A", "description": "Something isn't working"},
        "enhancement": {"color": "A2EEEF", "description": "New feature or request"},
        "documentation": {"color": "0075CA", "description": "Improvements or additions to documentation"},
        "good first issue": {"color": "7057FF", "description": "Good for newcomers"},
        "help wanted": {"color": "008672", "description": "Extra attention is needed"},
        "question": {"color": "D876E3", "description": "Further information is requested"},
        "wontfix": {"color": "FFFFFF", "description": "This will not be worked on"},
        "duplicate": {"color": "CFD3D7", "description": "This issue or pull request already exists"},
        "invalid": {"color": "E4E669", "description": "This doesn't seem right"},
        "tech-debt": {"color": "FBCA04", "description": "Technical debt"},
        "decision": {"color": "C5DEF5", "description": "Design decision"},
        "exploration": {"color": "0E8A16", "description": "Research or exploration"},
    }

    try:
        # Get existing labels
        result = subprocess.run(
            ["gh", "label", "list", "--json", "name"],
            capture_output=True,
            text=True,
            check=True,
        )
        existing = {label["name"] for label in json.loads(result.stdout)}

        # Determine which labels need to be created
        to_create = {
            name: details
            for name, details in standard_labels.items()
            if name not in existing
        }

        if not to_create:
            typer.secho("✓ All standard labels already exist.", fg=typer.colors.GREEN)
            return

        if dry_run:
            typer.echo(f"\nWould create {len(to_create)} labels:\n")
            for name, details in to_create.items():
                typer.echo(f"  • {name} (#{details['color']}) - {details['description']}")
            typer.echo()
            return

        # Create missing labels
        typer.echo(f"\nCreating {len(to_create)} standard labels:\n")
        created = 0
        for name, details in to_create.items():
            try:
                subprocess.run(
                    [
                        "gh", "label", "create", name,
                        "--description", details["description"],
                        "--color", details["color"],
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                typer.secho(f"  ✓ {name}", fg=typer.colors.GREEN)
                created += 1
            except subprocess.CalledProcessError as e:
                typer.secho(f"  ✗ {name}: {e.stderr.strip()}", fg=typer.colors.RED)

        typer.echo()
        typer.secho(f"Created {created}/{len(to_create)} labels.", fg=typer.colors.GREEN)

    except FileNotFoundError:
        typer.secho(
            "GitHub CLI (gh) not found. Install from: https://cli.github.com",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    except subprocess.CalledProcessError as e:
        typer.secho(f"Error: {e.stderr}", fg=typer.colors.RED)
        raise typer.Exit(1)


# Note commands
@note_app.command("create")
def note_create(
    content: str,
    tag: list[str] = typer.Option([], "--tag", "-t", help="Tags (e.g., explore, idea)"),
    no_validate: bool = typer.Option(False, "--no-validate", help="Skip tag label validation"),
):
    """Create a quick note."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root
    import subprocess

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("note")

    # Validate and potentially create tag labels if any were provided
    # Tags are stored as "tag:tagname" labels
    if tag and not no_validate:
        tag_labels = [f"tag:{t}" for t in tag]
        valid_labels, invalid_labels = validate_labels(tag_labels)

        if invalid_labels:
            # Extract tag names from "tag:name" format for display
            missing_tags = [label.replace("tag:", "") for label in invalid_labels]

            # Ask user if they want to create the missing tag labels
            create = typer.confirm(
                f"Create missing tag labels: {', '.join(missing_tags)}?",
                default=True,
            )

            if create:
                for label in invalid_labels:
                    try:
                        subprocess.run(
                            ["gh", "label", "create", label, "--color", "C2E0C6"],
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                        typer.secho(f"  ✓ Created label: {label}", fg=typer.colors.GREEN)
                    except subprocess.CalledProcessError:
                        typer.secho(f"  ✗ Failed to create label: {label}", fg=typer.colors.RED)
                        raise typer.Exit(1)
            else:
                typer.secho("Cancelled - cannot create note without valid tag labels.", fg=typer.colors.YELLOW)
                raise typer.Exit(1)

    note = backend.create(content, tags=list(tag) if tag else None)
    tag_str = f" [{', '.join(note['tags'])}]" if note.get("tags") else ""
    typer.secho(f"Created note #{note['id']}{tag_str}", fg=typer.colors.GREEN)


@note_app.command("list")
def note_list(
    ctx: typer.Context,
    tag: str = typer.Option(
        None, "--tag", "-t", help="Filter by tag (e.g., explore, idea)"
    ),
):
    """List notes."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("note")
    notes = backend.list(tag=tag)
    display(notes, ctx.obj.output_format, "notes")


@note_app.command("show")
def note_show(ctx: typer.Context, note_id: int):
    """Show a note."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("note")
    note = backend.get(note_id)
    if note is None:
        # For JSON output, we want the display function to handle this.
        if ctx.obj.output_format == "human":
            typer.secho(f"Note #{note_id} not found.", fg=typer.colors.RED)
            raise typer.Exit(1)

    display(note, ctx.obj.output_format, "note")


@note_app.command("edit")
def note_edit(
    note_id: int,
    content: str = typer.Option(None, "--content", "-c", help="New content"),
    tag: list[str] = typer.Option([], "--tag", "-t", help="Replace tags"),
    add_tag: list[str] = typer.Option([], "--add-tag", help="Add tags"),
):
    """Edit a note."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("note")

    # Determine new tags
    tags = None
    if tag:
        tags = list(tag)
    elif add_tag:
        current = backend.get(note_id)
        if current:
            tags = list(set(current.get("tags", []) + list(add_tag)))

    # GitHub backend doesn't support partial updates easily, so we merge locally if needed
    # But get_backend handles the appropriate backend implementation
    note = backend.update(note_id, content=content, tags=tags)
    if note is None:
        typer.secho(f"Note #{note_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Updated note #{note_id}", fg=typer.colors.GREEN)


@note_app.command("delete")
def note_delete(note_id: int):
    """Delete a note."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("note")
    if backend.delete(note_id):
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
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("note")
    try:
        result = backend.promote(note_id, to)
        if result is None:
            typer.secho(f"Note #{note_id} not found.", fg=typer.colors.RED)
            raise typer.Exit(1)
        typer.secho(
            f"Promoted note #{note_id} to {to} #{result['id']}", fg=typer.colors.GREEN
        )
    except Exception as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


@note_app.command("sync")
def note_sync(target: str = typer.Argument("github")):
    """Sync notes with remote."""
    typer.echo(f"Syncing notes to {target}...")
    # See task #318


# Vision commands
@vision_app.command("show")
def vision_show(ctx: typer.Context):
    """Show the project vision."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("vision")
    vision = backend.get()
    display(vision, ctx.obj.output_format, "vision")


@vision_app.command("edit")
def vision_edit(
    content: str = typer.Option(None, "--content", "-c", help="New vision content"),
):
    """Edit the project vision."""
    import os
    import subprocess
    import tempfile

    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("vision")

    if content is not None:
        # Direct content update
        backend.set(content)
        typer.secho("Vision updated.", fg=typer.colors.GREEN)
        return

    # Open in editor
    editor = os.environ.get("EDITOR", "nano")
    current_vision = backend.get() or "# Project Vision\n\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(current_vision)
        temp_path = f.name

    try:
        subprocess.run([editor, temp_path], check=True)
        with open(temp_path) as f:
            new_content = f.read()
        backend.set(new_content)
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
    # See task #319


# Plan commands
@plan_app.command("create")
def plan_create(
    name: str,
    title: str = typer.Option(None, "--title", "-t", help="Plan title"),
    body: str = typer.Option(None, "--body", "-b", help="Plan description"),
):
    """Create a plan."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("plan")
    try:
        plan = backend.create(name, title=title, body=body)
        typer.secho(f"Created plan: {plan['name']}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


@plan_app.command("list")
def plan_list(ctx: typer.Context):
    """List plans."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("plan")
    plans = backend.list()
    
    current = None
    if hasattr(backend, "get_current"):
        current = backend.get_current()
    
    current_name = current["name"] if current else None

    # Augment data for the display function
    for plan in plans:
        plan["is_current"] = (plan.get("current") or plan["name"] == current_name)

    display(plans, ctx.obj.output_format, "plans")


@plan_app.command("show")
def plan_show(
    ctx: typer.Context,
    name: str = typer.Argument(None, help="Plan name (default: current)"),
):
    """Show a plan."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("plan")
    plan = None
    if name is None:
        if hasattr(backend, "get_current"):
            plan = backend.get_current()
        if plan is None and ctx.obj.output_format == "human":
            typer.echo(
                "No current plan set. Use 'idlergear plan switch <name>' to set one."
            )
            raise typer.Exit(0)
    else:
        plan = backend.get(name)
        if plan is None and ctx.obj.output_format == "human":
            typer.secho(f"Plan '{name}' not found.", fg=typer.colors.RED)
            raise typer.Exit(1)

    display(plan, ctx.obj.output_format, "plan")


@plan_app.command("switch")
def plan_switch(name: str):
    """Switch to a plan."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("plan")
    plan = backend.switch(name)
    if plan is None:
        typer.secho(f"Plan '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Switched to plan: {plan['name']}", fg=typer.colors.GREEN)


@plan_app.command("edit")
def plan_edit(
    name: str,
    title: str = typer.Option(None, "--title", "-t", help="New title"),
    body: str = typer.Option(None, "--body", "-b", help="New body"),
    state: str = typer.Option(None, "--state", "-s", help="New state: active, completed"),
):
    """Edit a plan."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("plan")
    plan = backend.update(name, title=title, body=body, state=state)
    if plan is None:
        typer.secho(f"Plan '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Updated plan: {plan['name']}", fg=typer.colors.GREEN)


@plan_app.command("delete")
def plan_delete(name: str):
    """Delete a plan."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("plan")
    if backend.delete(name):
        typer.secho(f"Deleted plan: {name}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Plan '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)


@plan_app.command("complete")
def plan_complete(name: str):
    """Mark a plan as completed."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("plan")
    plan = backend.update(name, state="completed")
    if plan is None:
        typer.secho(f"Plan '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Completed plan: {plan['name']}", fg=typer.colors.GREEN)


@plan_app.command("sync")
def plan_sync(target: str = typer.Argument("github")):
    """Sync plans with remote."""
    typer.echo(f"Syncing plans to {target}...")
    # See task #320


# Milestone commands
@milestone_app.command("create")
def milestone_create(
    title: str,
    description: str = typer.Option(None, "--description", "-d", help="Milestone description"),
    due_on: str = typer.Option(None, "--due", help="Due date (YYYY-MM-DD)"),
):
    """Create a GitHub milestone."""
    import subprocess

    try:
        # Build API request
        data = {"title": title, "state": "open"}
        if description:
            data["description"] = description
        if due_on:
            data["due_on"] = f"{due_on}T00:00:00Z"

        # Get repo info
        repo_info = subprocess.run(
            ["gh", "repo", "view", "--json", "owner,name"],
            capture_output=True,
            text=True,
            check=True,
        )
        import json
        repo = json.loads(repo_info.stdout)
        owner = repo["owner"]["login"] if isinstance(repo["owner"], dict) else repo["owner"]
        name = repo["name"]

        # Create milestone
        result = subprocess.run(
            [
                "gh", "api",
                f"repos/{owner}/{name}/milestones",
                "-f", f"title={title}",
                "-f", "state=open",
            ] + (["-f", f"description={description}"] if description else [])
              + (["-f", f"due_on={due_on}T00:00:00Z"] if due_on else []),
            capture_output=True,
            text=True,
            check=True,
        )

        milestone = json.loads(result.stdout)
        typer.secho(
            f"Created milestone: {milestone['title']} (#{milestone['number']})",
            fg=typer.colors.GREEN,
        )

    except subprocess.CalledProcessError as e:
        typer.secho(f"Failed to create milestone: {e.stderr}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@milestone_app.command("list")
def milestone_list(
    ctx: typer.Context,
    state: str = typer.Option("open", "--state", "-s", help="Filter by state: open, closed, all"),
):
    """List GitHub milestones."""
    import subprocess
    import json

    try:
        # Get repo info
        repo_info = subprocess.run(
            ["gh", "repo", "view", "--json", "owner,name"],
            capture_output=True,
            text=True,
            check=True,
        )
        repo = json.loads(repo_info.stdout)
        owner = repo["owner"]["login"] if isinstance(repo["owner"], dict) else repo["owner"]
        name = repo["name"]

        # Fetch milestones
        url = f"repos/{owner}/{name}/milestones"
        if state in ("open", "closed"):
            url += f"?state={state}"

        result = subprocess.run(
            ["gh", "api", url],
            capture_output=True,
            text=True,
            check=True,
        )

        milestones = json.loads(result.stdout)

        # Format for display
        formatted = []
        for m in milestones:
            total = m["open_issues"] + m["closed_issues"]
            progress = (m["closed_issues"] / total * 100) if total > 0 else 0

            formatted.append({
                "number": m["number"],
                "title": m["title"],
                "state": m["state"],
                "open_issues": m["open_issues"],
                "closed_issues": m["closed_issues"],
                "progress": f"{progress:.0f}%",
                "due_on": m.get("due_on", ""),
                "description": m.get("description", ""),
            })

        display(formatted, ctx.obj.output_format, "milestones")

    except subprocess.CalledProcessError as e:
        typer.secho(f"Failed to list milestones: {e.stderr}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@milestone_app.command("show")
def milestone_show(
    ctx: typer.Context,
    milestone: str = typer.Argument(..., help="Milestone number or title"),
):
    """Show milestone details."""
    import subprocess
    import json

    try:
        # Get repo info
        repo_info = subprocess.run(
            ["gh", "repo", "view", "--json", "owner,name"],
            capture_output=True,
            text=True,
            check=True,
        )
        repo = json.loads(repo_info.stdout)
        owner = repo["owner"]["login"] if isinstance(repo["owner"], dict) else repo["owner"]
        name = repo["name"]

        # Fetch all milestones to find by title if needed
        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{name}/milestones"],
            capture_output=True,
            text=True,
            check=True,
        )

        milestones = json.loads(result.stdout)

        # Find milestone by number or title
        found = None
        for m in milestones:
            if str(m["number"]) == milestone or m["title"].lower() == milestone.lower():
                found = m
                break

        if not found:
            typer.secho(f"Milestone '{milestone}' not found.", fg=typer.colors.RED)
            raise typer.Exit(1)

        # Get issues for this milestone
        issues_result = subprocess.run(
            ["gh", "issue", "list", "--milestone", found["title"], "--json", "number,title,state", "--limit", "1000"],
            capture_output=True,
            text=True,
            check=True,
        )

        issues = json.loads(issues_result.stdout)

        total = found["open_issues"] + found["closed_issues"]
        progress = (found["closed_issues"] / total * 100) if total > 0 else 0

        # Format for display
        display_data = {
            "number": found["number"],
            "title": found["title"],
            "state": found["state"],
            "description": found.get("description", ""),
            "open_issues": found["open_issues"],
            "closed_issues": found["closed_issues"],
            "progress": f"{progress:.0f}%",
            "due_on": found.get("due_on", ""),
            "created_at": found.get("created_at", ""),
            "updated_at": found.get("updated_at", ""),
            "issues": issues,
        }

        display(display_data, ctx.obj.output_format, "milestone")

    except subprocess.CalledProcessError as e:
        typer.secho(f"Failed to show milestone: {e.stderr}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@milestone_app.command("close")
def milestone_close(
    milestone: str = typer.Argument(..., help="Milestone number or title"),
):
    """Close a milestone."""
    import subprocess
    import json

    try:
        # Get repo info
        repo_info = subprocess.run(
            ["gh", "repo", "view", "--json", "owner,name"],
            capture_output=True,
            text=True,
            check=True,
        )
        repo = json.loads(repo_info.stdout)
        owner = repo["owner"]["login"] if isinstance(repo["owner"], dict) else repo["owner"]
        name = repo["name"]

        # Find milestone
        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{name}/milestones"],
            capture_output=True,
            text=True,
            check=True,
        )

        milestones = json.loads(result.stdout)
        found = None
        for m in milestones:
            if str(m["number"]) == milestone or m["title"].lower() == milestone.lower():
                found = m
                break

        if not found:
            typer.secho(f"Milestone '{milestone}' not found.", fg=typer.colors.RED)
            raise typer.Exit(1)

        # Close milestone
        subprocess.run(
            [
                "gh", "api",
                f"repos/{owner}/{name}/milestones/{found['number']}",
                "-X", "PATCH",
                "-f", "state=closed",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        typer.secho(f"Closed milestone: {found['title']}", fg=typer.colors.GREEN)

    except subprocess.CalledProcessError as e:
        typer.secho(f"Failed to close milestone: {e.stderr}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


# Reference commands
@reference_app.command("add")
def reference_add(
    title: str,
    body: str = typer.Option(None, "--body", "-b", help="Reference body"),
):
    """Add a reference document."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("reference")
    ref = backend.add(title, body=body)
    typer.secho(f"Added reference: {ref['title']}", fg=typer.colors.GREEN)


@reference_app.command("list")
def reference_list(ctx: typer.Context):
    """List reference documents."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("reference")
    refs = backend.list()
    display(refs, ctx.obj.output_format, "references")


@reference_app.command("show")
def reference_show(ctx: typer.Context, title: str):
    """Show a reference document."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("reference")
    ref = backend.get(title)
    if ref is None and ctx.obj.output_format == "human":
        typer.secho(f"Reference '{title}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    display(ref, ctx.obj.output_format, "reference")


@reference_app.command("edit")
def reference_edit(
    title: str,
    new_title: str = typer.Option(None, "--title", "-t", help="New title"),
    body: str = typer.Option(None, "--body", "-b", help="New body"),
):
    """Edit a reference document."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("reference")
    ref = backend.update(title, new_title=new_title, body=body)
    if ref is None:
        typer.secho(f"Reference '{title}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Updated reference: {ref['title']}", fg=typer.colors.GREEN)


@reference_app.command("delete")
def reference_delete(title: str):
    """Delete a reference document."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("reference")
    if backend.delete(title):
        typer.secho(f"Deleted reference: {title}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Reference '{title}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)


@reference_app.command("search")
def reference_search(query: str):
    """Search reference documents."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    backend = get_backend("reference")
    results = backend.search(query)
    if not results:
        typer.echo(f"No references found matching '{query}'.")
        return

    typer.echo(f"Found {len(results)} matching reference(s):")
    for ref in results:
        typer.echo(f"  {ref['title']}")


@reference_app.command("sync")
def reference_sync(
    ctx: typer.Context,
    push: bool = typer.Option(
        False, "--push", help="Push local references to GitHub Wiki"
    ),
    pull: bool = typer.Option(
        False, "--pull", help="Pull GitHub Wiki pages to local references"
    ),
    status: bool = typer.Option(
        False, "--status", "-s", help="Show sync status without making changes"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force overwrite on conflicts (with --pull: use remote, with --push: use local)",
    ),
    ours: bool = typer.Option(False, "--ours", help="On conflict, keep local version"),
    theirs: bool = typer.Option(
        False, "--theirs", help="On conflict, keep remote version"
    ),
):
    """Sync references with GitHub Wiki.

    By default, performs bidirectional sync - pushing local changes and pulling remote changes.
    Conflicts are reported and must be resolved manually unless --ours or --theirs is specified.

    Examples:
        idlergear reference sync                # Bidirectional sync
        idlergear reference sync --push         # Push local to wiki
        idlergear reference sync --pull         # Pull wiki to local
        idlergear reference sync --status       # Check what needs syncing
        idlergear reference sync --ours         # On conflict, keep local
        idlergear reference sync --theirs       # On conflict, keep remote
    """
    from idlergear.wiki import WikiSync

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN

    sync = WikiSync()

    # Status only
    if status:
        # Check what would be synced
        if output_format == OutputFormat.JSON:
            # Get counts
            from idlergear.reference import list_references

            refs = list_references()

            if sync.wiki_dir.exists():
                sync.pull_wiki()
                wiki_pages = sync.list_wiki_pages()
            else:
                wiki_pages = []

            ref_titles = {r["title"] for r in refs}
            wiki_titles = {p.title for p in wiki_pages}

            typer.echo(
                json.dumps(
                    {
                        "local_only": list(ref_titles - wiki_titles),
                        "remote_only": list(wiki_titles - ref_titles),
                        "both": list(ref_titles & wiki_titles),
                        "local_count": len(refs),
                        "remote_count": len(wiki_pages),
                    }
                )
            )
        else:
            from idlergear.reference import list_references

            refs = list_references()

            typer.echo("Sync Status:")
            typer.echo(f"  Local references: {len(refs)}")

            if sync.wiki_dir.exists() or sync.wiki_exists():
                sync.pull_wiki()
                wiki_pages = sync.list_wiki_pages()
                typer.echo(f"  Wiki pages: {len(wiki_pages)}")

                ref_titles = {r["title"] for r in refs}
                wiki_titles = {p.title for p in wiki_pages}

                local_only = ref_titles - wiki_titles
                remote_only = wiki_titles - ref_titles

                if local_only:
                    typer.echo()
                    typer.echo("  Local only (will be pushed):")
                    for title in local_only:
                        typer.echo(f"    + {title}")

                if remote_only:
                    typer.echo()
                    typer.echo("  Remote only (will be pulled):")
                    for title in remote_only:
                        typer.echo(f"    + {title}")

                if not local_only and not remote_only:
                    typer.secho("\n  ✓ Already in sync", fg=typer.colors.GREEN)
            else:
                typer.echo("  Wiki: Not initialized")
                typer.echo()
                typer.echo(
                    "  Run 'idlergear reference sync --push' to initialize and push references."
                )
        return

    # Determine conflict resolution
    conflict_resolution = "manual"
    if ours or (push and force):
        conflict_resolution = "local"
    elif theirs or (pull and force):
        conflict_resolution = "remote"

    # Push only
    if push and not pull:
        if output_format != OutputFormat.JSON:
            typer.echo("Pushing references to GitHub Wiki...")

        result = sync.push_references_to_wiki()

        if output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps(
                    {
                        "pushed": result.pushed,
                        "conflicts": result.conflicts,
                        "errors": result.errors,
                    }
                )
            )
        else:
            typer.echo(str(result))
        return

    # Pull only
    if pull and not push:
        if output_format != OutputFormat.JSON:
            typer.echo("Pulling GitHub Wiki to references...")

        result = sync.pull_wiki_to_references(overwrite=force)

        if output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps(
                    {
                        "pulled": result.pulled,
                        "conflicts": result.conflicts,
                        "errors": result.errors,
                    }
                )
            )
        else:
            typer.echo(str(result))
        return

    # Bidirectional sync (default)
    if output_format != OutputFormat.JSON:
        typer.echo("Syncing references with GitHub Wiki...")

    result = sync.sync_bidirectional(conflict_resolution=conflict_resolution)

    if output_format == OutputFormat.JSON:
        typer.echo(
            json.dumps(
                {
                    "pushed": result.pushed,
                    "pulled": result.pulled,
                    "conflicts": result.conflicts,
                    "errors": result.errors,
                }
            )
        )
    else:
        typer.echo(str(result))

        if result.conflicts:
            typer.echo()
            typer.echo("To resolve conflicts, use:")
            typer.echo("  --ours   : Keep local version")
            typer.echo("  --theirs : Keep remote version")


# Run commands
@run_app.command("start")
def run_start(
    command: str,
    name: str = typer.Option(None, "--name", "-n", help="Run name"),
    tmux: bool = typer.Option(False, "--tmux", help="Run in a tmux session (allows attaching later)"),
    container: bool = typer.Option(False, "--container", help="Run in a container (podman/docker)"),
    image: str = typer.Option(None, "--image", help="Container image (required with --container)"),
    memory: str = typer.Option(None, "--memory", help="Container memory limit (e.g., '512m', '2g')"),
    cpus: str = typer.Option(None, "--cpus", help="Container CPU limit (e.g., '1.5')"),
):
    """Start a script/command.

    Examples:
        idlergear run start "python server.py" --name backend
        idlergear run start "pytest" --tmux --name tests
        idlergear run start "npm start" --container --image node:18 --name frontend
    """
    from idlergear.config import find_idlergear_root
    from idlergear.runs import start_run

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    # Validate container options
    if container and not image:
        typer.secho(
            "Error: --image is required when using --container",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    try:
        run = start_run(
            command,
            name=name,
            use_tmux=tmux,
            use_container=container,
            container_image=image,
            container_memory=memory,
            container_cpus=cpus,
        )
        typer.secho(
            f"Started run '{run['name']}' (PID {run['pid']})", fg=typer.colors.GREEN
        )
        typer.echo(f"  Command: {run['command']}")

        if container and run.get("container_id"):
            typer.echo(f"  Container ID: {run['container_id']}")
            typer.echo(f"  Image: {image}")
            if memory:
                typer.echo(f"  Memory limit: {memory}")
            if cpus:
                typer.echo(f"  CPU limit: {cpus}")
        elif tmux and run.get("tmux_session"):
            typer.echo(f"  Tmux session: {run['tmux_session']}")
            typer.echo(f"  Attach: tmux attach-session -t {run['tmux_session']}")
            typer.echo(f"  Or use: idlergear run attach {run['name']}")

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
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    runs = list_runs()
    if not runs:
        typer.echo("No runs found.")
        return

    for run in runs:
        status_color = (
            typer.colors.GREEN if run["status"] == "running" else typer.colors.WHITE
        )
        typer.echo(f"  {run['name']}", nl=False)
        typer.secho(f"  [{run['status']}]", fg=status_color, nl=False)
        if run.get("pid") and run["status"] == "running":
            typer.echo(f"  PID {run['pid']}", nl=False)
        typer.echo("")


@run_app.command("history")
def run_history(
    failed: bool = typer.Option(
        False, "--failed", "-f", help="Show only failed runs"
    ),
    status: str = typer.Option(
        None, "--status", "-s", help="Filter by status (running, stopped, completed, failed)"
    ),
    limit: int = typer.Option(
        None, "--limit", "-l", help="Limit number of results"
    ),
):
    """Show run history.

    Examples:
        idlergear run history              # Recent runs with status
        idlergear run history --failed     # Only failed runs
        idlergear run history --limit 20   # Limit results
        idlergear run history --status completed  # Only completed runs
    """
    from idlergear.config import find_idlergear_root
    from idlergear.runs import list_runs

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    runs = list_runs()
    if not runs:
        typer.echo("No runs found.")
        return

    # Filter by status
    if failed:
        runs = [r for r in runs if r["status"] == "failed"]
    elif status:
        runs = [r for r in runs if r["status"] == status]

    # Apply limit
    if limit:
        runs = runs[:limit]

    if not runs:
        typer.echo("No matching runs found.")
        return

    # Display runs with more detailed information
    for run in runs:
        status_color = {
            "running": typer.colors.GREEN,
            "completed": typer.colors.BLUE,
            "failed": typer.colors.RED,
            "stopped": typer.colors.YELLOW,
        }.get(run["status"], typer.colors.WHITE)

        typer.echo(f"  {run['name']}", nl=False)
        typer.secho(f"  [{run['status']}]", fg=status_color, nl=False)
        if run.get("command"):
            typer.echo(f"  {run['command']}", nl=False)
        if run.get("pid") and run["status"] == "running":
            typer.echo(f"  (PID {run['pid']})", nl=False)
        typer.echo("")


@run_app.command("status")
def run_status(name: str):
    """Check run status."""
    from idlergear.config import find_idlergear_root
    from idlergear.runs import get_run_status

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    status = get_run_status(name)
    if status is None:
        typer.secho(f"Run '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    status_color = (
        typer.colors.GREEN if status["status"] == "running" else typer.colors.WHITE
    )
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
    stderr: bool = typer.Option(
        False, "--stderr", "-e", help="Show stderr instead of stdout"
    ),
):
    """Show run logs."""
    from idlergear.config import find_idlergear_root
    from idlergear.runs import get_run_logs

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
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
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    if stop_run(name):
        typer.secho(f"Stopped run '{name}'", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Run '{name}' is not running or not found.", fg=typer.colors.RED)
        raise typer.Exit(1)


@run_app.command("attach")
def run_attach(name: str):
    """Attach to a tmux session for a run.

    Only works for runs started with --tmux flag.
    """
    from idlergear.config import find_idlergear_root
    from idlergear.runs import attach_to_run

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    try:
        result = attach_to_run(name)
        typer.secho(
            f"Tmux session: {result['tmux_session']}", fg=typer.colors.GREEN
        )
        typer.echo(f"  {result['message']}")
        typer.echo("")
        typer.echo("To attach to the session, run:")
        typer.secho(f"  {result['attach_command']}", fg=typer.colors.BRIGHT_CYAN)
    except RuntimeError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


@run_app.command("delete")
def run_delete(name: str):
    """Delete a run and its logs."""
    from idlergear.config import find_idlergear_root
    from idlergear.runs import delete_run

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    if delete_run(name):
        typer.secho(f"Deleted run '{name}'", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Run '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)


@run_app.command("cleanup")
def run_cleanup(
    older_than: int = typer.Option(
        7, "--older-than", "-d", help="Delete runs older than N days (default: 7)"
    ),
    status: str = typer.Option(
        None, "--status", "-s", help="Only delete runs with this status (e.g., stopped, failed)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be deleted without deleting"
    ),
):
    """Clean up old runs.

    Examples:
        idlergear run cleanup                    # Delete runs older than 7 days
        idlergear run cleanup --older-than 30   # Delete runs older than 30 days
        idlergear run cleanup --status failed    # Only delete failed runs
        idlergear run cleanup --dry-run          # Preview what would be deleted
    """
    from idlergear.config import find_idlergear_root
    from idlergear.runs import cleanup_runs

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    deleted = cleanup_runs(older_than_days=older_than, status=status, dry_run=dry_run)

    if not deleted:
        typer.echo("No runs to clean up.")
        return

    action = "Would delete" if dry_run else "Deleted"
    for name in deleted:
        typer.echo(f"  {action}: {name}")

    typer.secho(
        f"{action} {len(deleted)} run(s)",
        fg=typer.colors.YELLOW if dry_run else typer.colors.GREEN,
    )


@run_app.command("clean")
def run_clean(
    older_than: int = typer.Option(
        7, "--older-than", "-d", help="Delete runs older than N days (default: 7)"
    ),
    status: str = typer.Option(
        None, "--status", "-s", help="Only delete runs with this status (e.g., stopped, failed)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be deleted without deleting"
    ),
):
    """Clean up old runs (alias for cleanup).

    Examples:
        idlergear run clean                    # Delete runs older than 7 days
        idlergear run clean --older-than 30   # Delete runs older than 30 days
        idlergear run clean --status failed    # Only delete failed runs
        idlergear run clean --dry-run          # Preview what would be deleted
    """
    # Just call the cleanup function
    run_cleanup(older_than=older_than, status=status, dry_run=dry_run)


@run_app.command("exec")
def run_exec(
    command: str = typer.Argument(..., help="Command to execute"),
    name: str = typer.Option(None, "--name", "-n", help="Run name"),
    no_header: bool = typer.Option(
        False, "--no-header", help="Suppress header/footer output"
    ),
    no_register: bool = typer.Option(
        False, "--no-register", help="Don't register with daemon"
    ),
    stream: bool = typer.Option(
        False, "--stream", "-s", help="Stream logs to daemon for other agents to see"
    ),
):
    """Execute a command with PTY passthrough and tracking.

    This wraps any command while preserving terminal colors and interactivity,
    and provides AI-visible metadata (run ID, script hash, timestamps).

    Examples:
        ig run exec "./run_tests.sh"
        ig run exec "python manage.py migrate" --name django-migrate
        ig run exec "npm run build" --no-header
        ig run exec "./long_job.sh" --stream  # Stream logs to daemon

    The output includes header/footer blocks that AI assistants can parse
    to understand what ran and whether it succeeded.
    """
    from idlergear.runs import run_with_pty

    try:
        result = run_with_pty(
            command,
            name=name,
            show_header=not no_header,
            register_with_daemon=not no_register,
            stream_logs=stream,
        )
        # Exit with the same code as the wrapped command
        raise typer.Exit(result["exit_code"])
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@run_app.command("generate-script")
def run_generate_script(
    script_name: str,
    command: str,
    output: str = typer.Option(
        None, "--output", "-o", help="Output file path (default: ./scripts/{name}.sh)"
    ),
    venv: str = typer.Option(None, "--venv", help="Virtualenv path"),
    requirement: list[str] = typer.Option(
        [], "--requirement", "-r", help="Python packages to install"
    ),
    env: list[str] = typer.Option(
        [], "--env", "-e", help="Environment variables (KEY=VALUE)"
    ),
    agent_name: str = typer.Option(
        None, "--agent-name", help="Agent name for daemon (default: script name)"
    ),
    agent_type: str = typer.Option("dev-script", "--agent-type", help="Agent type"),
    no_register: bool = typer.Option(
        False, "--no-register", help="Don't register with daemon"
    ),
    stream_logs: bool = typer.Option(
        False, "--stream-logs", help="Stream logs to daemon"
    ),
    template: str = typer.Option(
        None,
        "--template",
        "-t",
        help="Use template (pytest, django-dev, flask-dev, etc)",
    ),
):
    """Generate a dev environment setup script that registers with IdlerGear daemon.

    Examples:
        # Generate a pytest runner
        idlergear run generate-script test "pytest -v" --template pytest

        # Custom Django dev server
        idlergear run generate-script django-dev "python manage.py runserver" \\
            --venv ./venv --requirement django --env DJANGO_SETTINGS_MODULE=settings

        # With log streaming
        idlergear run generate-script worker "celery worker" --stream-logs
    """
    from pathlib import Path

    from idlergear.config import find_idlergear_root
    from idlergear.script_generator import (
        generate_dev_script,
        generate_script_from_template,
        save_script,
    )

    project_root = find_idlergear_root()
    if project_root is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    # Parse environment variables
    env_vars = {}
    for env_var in env:
        if "=" not in env_var:
            typer.secho(
                f"Invalid environment variable: {env_var} (use KEY=VALUE)",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)
        key, value = env_var.split("=", 1)
        env_vars[key] = value

    try:
        # Generate from template or custom
        if template:
            script_content = generate_script_from_template(
                template,
                script_name,
                venv_path=venv,
                env_vars=env_vars if env_vars else None,
                agent_name=agent_name,
                agent_type=agent_type,
                register_with_daemon=not no_register,
                stream_logs=stream_logs,
                project_path=project_root,
            )
        else:
            script_content = generate_dev_script(
                script_name,
                command,
                venv_path=venv,
                requirements=list(requirement) if requirement else None,
                env_vars=env_vars if env_vars else None,
                agent_name=agent_name,
                agent_type=agent_type,
                register_with_daemon=not no_register,
                stream_logs=stream_logs,
                project_path=project_root,
            )

        # Determine output path
        if output is None:
            scripts_dir = project_root / "scripts"
            scripts_dir.mkdir(exist_ok=True)
            output = str(scripts_dir / f"{script_name}.sh")

        output_path = Path(output)
        save_script(script_content, output_path, make_executable=True)

        typer.secho(f"✓ Generated script: {output_path}", fg=typer.colors.GREEN)
        typer.echo(f"\nRun with: ./{output_path.relative_to(project_root)}")
        typer.echo("\nFeatures:")
        if not no_register:
            typer.echo("  ✓ Auto-registers with IdlerGear daemon")
        if stream_logs:
            typer.echo("  ✓ Streams logs to daemon")
        if venv:
            typer.echo(f"  ✓ Activates virtualenv: {venv}")
        if requirement:
            typer.echo(f"  ✓ Installs packages: {', '.join(requirement)}")
        if env_vars:
            typer.echo(f"  ✓ Sets environment variables: {', '.join(env_vars.keys())}")

    except Exception as e:
        typer.secho(f"Error generating script: {e}", fg=typer.colors.RED)
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
    github: bool = typer.Option(
        False, "--github", "-g", help="Also create on GitHub Projects v2"
    ),
):
    """Create a new project board."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import create_project

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
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
    github: bool = typer.Option(
        False, "--github", "-g", help="Also list GitHub Projects"
    ),
):
    """List project boards."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import list_github_projects, list_projects

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    projects = list_projects()

    if not projects and not github:
        typer.echo(
            "No projects found. Create one with 'idlergear project create <title>'"
        )
        return

    if projects:
        typer.echo("Local Projects:")
        for proj in projects:
            gh_link = (
                f" (GitHub #{proj['github_project_number']})"
                if proj.get("github_project_number")
                else ""
            )
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
                typer.echo(
                    f"  #{proj.get('number', '?')}: {proj.get('title', 'Untitled')}"
                )


@project_app.command("show")
def project_show(name: str):
    """Show a project board with tasks in each column."""
    from idlergear.backends.registry import get_backend
    from idlergear.config import find_idlergear_root
    from idlergear.projects import get_project

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
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
                    typer.secho(
                        f"  #{task_id}: (task not found)", fg=typer.colors.YELLOW
                    )
        typer.echo("")


@project_app.command("delete")
def project_delete(
    name: str,
    github: bool = typer.Option(
        False, "--github", "-g", help="Also delete from GitHub"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a project board."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import delete_project, get_project

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    project = get_project(name)
    if project is None:
        typer.secho(f"Project '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not force:
        confirm_msg = f"Delete project '{project['title']}'?"
        if github and project.get("github_project_number"):
            confirm_msg = (
                f"Delete project '{project['title']}' locally AND from GitHub?"
            )
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
    column: str = typer.Option(
        None, "--column", "-c", help="Target column (default: first column)"
    ),
):
    """Add a task to a project board."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import add_task_to_project

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    try:
        project = add_task_to_project(project_name, str(task_id), column)
        if project is None:
            typer.secho(f"Project '{project_name}' not found.", fg=typer.colors.RED)
            raise typer.Exit(1)

        target_col = column or project["columns"][0]
        typer.secho(
            f"Added task #{task_id} to '{project['title']}' → {target_col}",
            fg=typer.colors.GREEN,
        )
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


@project_app.command("remove-task")
def project_remove_task(project_name: str, task_id: int):
    """Remove a task from a project board."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import remove_task_from_project

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    project = remove_task_from_project(project_name, str(task_id))
    if project is None:
        typer.secho(f"Project '{project_name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(
        f"Removed task #{task_id} from '{project['title']}'", fg=typer.colors.GREEN
    )


@project_app.command("move")
def project_move_task(project_name: str, task_id: int, column: str):
    """Move a task to a different column."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import move_task

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
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
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    typer.echo(f"Syncing project '{name}' to GitHub...")

    try:
        project = sync_project_to_github(name)
        if project is None:
            typer.secho(f"Project '{name}' not found.", fg=typer.colors.RED)
            raise typer.Exit(1)

        typer.secho(
            f"Synced project to GitHub Projects #{project['github_project_number']}",
            fg=typer.colors.GREEN,
        )
    except RuntimeError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


@project_app.command("link")
def project_link(name: str, github_project_number: int):
    """Link a local project to an existing GitHub Project."""
    from idlergear.config import find_idlergear_root
    from idlergear.projects import link_to_github_project

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    try:
        project = link_to_github_project(name, github_project_number)
        if project is None:
            typer.secho(f"Local project '{name}' not found.", fg=typer.colors.RED)
            raise typer.Exit(1)

        typer.secho(
            f"Linked '{project['title']}' to GitHub Project #{github_project_number}",
            fg=typer.colors.GREEN,
        )
    except RuntimeError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)


# ============================================================================
# Session Commands
# ============================================================================


@session_app.command("save")
def session_save(
    name: str = typer.Argument(None, help="Optional name for the session"),
    next_steps: str = typer.Option(None, "--next", "-n", help="What to do next"),
    blockers: str = typer.Option(
        None, "--blockers", "-b", help="What's blocking progress"
    ),
):
    """Save current session state.

    Examples:
        idlergear session save                    # Auto-name with timestamp
        idlergear session save fixing-parser      # Named session
        idlergear session save --next "Run tests" # With next steps
    """
    from idlergear.config import find_idlergear_root
    from idlergear.sessions import save_session

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    session_file = save_session(name=name, next_steps=next_steps, blockers=blockers)
    typer.secho(f"Session saved to: {session_file.name}", fg=typer.colors.GREEN)


@session_app.command("restore")
def session_restore(
    name: str = typer.Argument(None, help="Session name or timestamp to restore"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Restore/view a saved session state.

    Examples:
        idlergear session restore                 # Most recent session
        idlergear session restore fixing-parser   # By name
        idlergear session restore 2026-01-01      # By timestamp
    """
    import json

    from idlergear.config import find_idlergear_root
    from idlergear.sessions import format_session_state, load_session

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    state = load_session(name=name)
    if state is None:
        if name:
            typer.secho(f"Session '{name}' not found.", fg=typer.colors.RED)
        else:
            typer.secho("No saved sessions found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if json_output:
        typer.echo(json.dumps(state.to_dict(), indent=2))
    else:
        typer.echo(format_session_state(state))


@session_app.command("list")
def session_list(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """List all saved sessions.

    Examples:
        idlergear session list        # List all sessions
        idlergear session list --json # JSON output
    """
    import json

    from idlergear.config import find_idlergear_root
    from idlergear.sessions import list_sessions

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    sessions = list_sessions()

    if not sessions:
        typer.secho("No saved sessions.", fg=typer.colors.YELLOW)
        return

    if json_output:
        typer.echo(json.dumps(sessions, indent=2))
    else:
        typer.secho(
            f"Saved sessions ({len(sessions)}):", fg=typer.colors.CYAN, bold=True
        )
        for session in sessions:
            name = session["name"]
            saved_at = session.get("saved_at", "unknown")
            task = session.get("current_task")

            # Parse saved_at to show relative time
            try:
                from datetime import datetime

                dt = datetime.fromisoformat(saved_at.replace("Z", "+00:00"))
                elapsed = datetime.now() - dt.replace(tzinfo=None)
                hours = int(elapsed.total_seconds() / 3600)
                if hours < 1:
                    time_str = f"{int(elapsed.total_seconds() / 60)}m ago"
                elif hours < 24:
                    time_str = f"{hours}h ago"
                else:
                    time_str = f"{hours // 24}d ago"
            except (ValueError, TypeError):
                time_str = saved_at

            task_str = f" - {task}" if task else ""
            typer.echo(f"  {name:30s} {time_str:12s}{task_str}")


@session_app.command("show")
def session_show(
    session_id: str = typer.Argument(..., help="Session ID to show (e.g., s001)"),
    branch: str = typer.Option("main", "--branch", "-b", help="Branch name"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Show detailed session snapshot.

    Examples:
        idlergear session show s001       # Show session details
        idlergear session show s003 --json  # JSON output
    """
    import json

    from idlergear.config import find_idlergear_root
    from idlergear.session_history import SessionHistory

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    try:
        history = SessionHistory()
        snapshot = history.load_snapshot(session_id, branch)

        if snapshot is None:
            typer.secho(f"Session '{session_id}' not found in branch '{branch}'.", fg=typer.colors.RED)
            raise typer.Exit(1)

        if json_output:
            typer.echo(json.dumps(snapshot.to_dict(), indent=2))
        else:
            # Format human-readable output
            typer.secho(f"\nSession: {snapshot.session_id}", fg=typer.colors.CYAN, bold=True)
            typer.echo(f"Branch: {snapshot.branch}")
            typer.echo(f"Timestamp: {snapshot.timestamp}")
            typer.echo(f"Duration: {snapshot.duration_seconds}s")

            if snapshot.parent:
                typer.echo(f"Parent: {snapshot.parent}")

            # State
            state = snapshot.state
            if state:
                typer.echo("\nState:")
                if state.get("current_task_id"):
                    typer.echo(f"  Task: #{state['current_task_id']}")
                if state.get("working_files"):
                    typer.echo(f"  Files: {', '.join(state['working_files'][:3])}")
                if state.get("notes"):
                    typer.echo(f"  Notes: {state['notes']}")

            # Outcome
            outcome = snapshot.outcome
            if outcome:
                typer.echo("\nOutcome:")
                if outcome.get("status"):
                    typer.echo(f"  Status: {outcome['status']}")
                if outcome.get("goals_achieved"):
                    typer.echo(f"  Goals: {', '.join(outcome['goals_achieved'])}")
                if outcome.get("next_steps"):
                    typer.echo(f"  Next: {', '.join(outcome['next_steps'])}")

    except ValueError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@session_app.command("diff")
def session_diff(
    session1: str = typer.Argument(..., help="First session ID (e.g., s001)"),
    session2: str = typer.Argument(..., help="Second session ID (e.g., s002)"),
    branch: str = typer.Option("main", "--branch", "-b", help="Branch name"),
):
    """Compare two session snapshots.

    Examples:
        idlergear session diff s001 s002  # Compare two sessions
    """
    from idlergear.config import find_idlergear_root
    from idlergear.session_history import SessionHistory

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    try:
        history = SessionHistory()
        snap1 = history.load_snapshot(session1, branch)
        snap2 = history.load_snapshot(session2, branch)

        if snap1 is None:
            typer.secho(f"Session '{session1}' not found.", fg=typer.colors.RED)
            raise typer.Exit(1)

        if snap2 is None:
            typer.secho(f"Session '{session2}' not found.", fg=typer.colors.RED)
            raise typer.Exit(1)

        typer.secho(f"\nComparing {session1} vs {session2}:", fg=typer.colors.CYAN, bold=True)

        # Compare timestamps
        typer.echo(f"\nTime:")
        typer.echo(f"  {session1}: {snap1.timestamp}")
        typer.echo(f"  {session2}: {snap2.timestamp}")

        # Compare durations
        typer.echo(f"\nDuration:")
        typer.echo(f"  {session1}: {snap1.duration_seconds}s")
        typer.echo(f"  {session2}: {snap2.duration_seconds}s")

        # Compare tasks
        task1 = snap1.state.get("current_task_id")
        task2 = snap2.state.get("current_task_id")
        if task1 != task2:
            typer.echo(f"\nTask changed:")
            typer.echo(f"  {session1}: #{task1}" if task1 else f"  {session1}: None")
            typer.echo(f"  {session2}: #{task2}" if task2 else f"  {session2}: None")

        # Compare files
        files1 = set(snap1.state.get("working_files", []))
        files2 = set(snap2.state.get("working_files", []))

        added_files = files2 - files1
        removed_files = files1 - files2

        if added_files or removed_files:
            typer.echo(f"\nFiles changed:")
            if added_files:
                typer.secho(f"  Added: {', '.join(added_files)}", fg=typer.colors.GREEN)
            if removed_files:
                typer.secho(f"  Removed: {', '.join(removed_files)}", fg=typer.colors.RED)

        # Compare outcomes
        outcome1 = snap1.outcome.get("status")
        outcome2 = snap2.outcome.get("status")
        if outcome1 != outcome2:
            typer.echo(f"\nOutcome:")
            typer.echo(f"  {session1}: {outcome1}")
            typer.echo(f"  {session2}: {outcome2}")

    except ValueError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@session_app.command("checkpoints")
def session_checkpoints(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of checkpoints to show"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """List auto-saved checkpoints.

    Checkpoints are lightweight auto-saves created every 15 minutes
    for crash recovery.

    Examples:
        idlergear session checkpoints         # List recent checkpoints
        idlergear session checkpoints --limit 20  # Show more
    """
    from idlergear.config import find_idlergear_root
    from idlergear.session_history import SessionHistory

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    try:
        history = SessionHistory()
        checkpoints = history.list_checkpoints()

        if not checkpoints:
            typer.secho("No checkpoints found.", fg=typer.colors.YELLOW)
            typer.echo("Checkpoints are auto-saved every 15 minutes during active sessions.")
            return

        # Limit results
        if limit:
            checkpoints = checkpoints[-limit:]

        if json_output:
            import json

            print(json.dumps(checkpoints, indent=2))
            return

        typer.secho(f"\n📌 Session Checkpoints (showing {len(checkpoints)}):\n", bold=True)

        for cp in reversed(checkpoints):  # Show newest first
            checkpoint_id = cp["checkpoint_id"]
            timestamp = cp["timestamp"]

            # Format timestamp
            try:
                from datetime import datetime

                dt = datetime.fromisoformat(timestamp)
                elapsed = datetime.now() - dt
                hours = int(elapsed.total_seconds() / 3600)
                if hours < 1:
                    minutes = int(elapsed.total_seconds() / 60)
                    time_ago = f"{minutes}m ago"
                elif hours < 24:
                    time_ago = f"{hours}h ago"
                else:
                    days = hours // 24
                    time_ago = f"{days}d ago"
            except (ValueError, TypeError):
                time_ago = "unknown"

            typer.echo(f"  {checkpoint_id}  {time_ago}  ({timestamp})")

        typer.echo()
    except Exception as e:
        typer.secho(f"Error listing checkpoints: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@session_app.command("recover")
def session_recover(
    checkpoint_id: str = typer.Option(None, "--checkpoint", "-c", help="Specific checkpoint ID (default: latest)"),
):
    """Recover session state from a checkpoint.

    Loads the checkpoint state and displays it. Use this to recover from a crash
    or to see what state was auto-saved.

    Examples:
        idlergear session recover            # Recover from latest checkpoint
        idlergear session recover --checkpoint c005  # Recover from specific checkpoint
    """
    from idlergear.config import find_idlergear_root
    from idlergear.session_history import SessionHistory

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    try:
        history = SessionHistory()

        if checkpoint_id:
            checkpoint = history.load_checkpoint(checkpoint_id)
        else:
            checkpoint = history.load_checkpoint()

        if not checkpoint:
            typer.secho("No checkpoint found.", fg=typer.colors.YELLOW)
            if checkpoint_id:
                typer.echo(f"Checkpoint {checkpoint_id} does not exist.")
            else:
                typer.echo("No checkpoints available. They are created every 15 minutes during active sessions.")
            return

        # Display checkpoint info
        cp_id = checkpoint["checkpoint_id"]
        timestamp = checkpoint["timestamp"]
        state = checkpoint.get("state", {})

        typer.secho(f"\n💾 Recovered Checkpoint: {cp_id}\n", bold=True, fg=typer.colors.GREEN)
        typer.echo(f"Saved at: {timestamp}\n")

        # Show state
        typer.secho("State:", bold=True)
        if state.get("current_task_id"):
            typer.echo(f"  Current task: #{state['current_task_id']}")
        else:
            typer.echo("  Current task: None")

        if state.get("working_files"):
            typer.echo(f"  Working files ({len(state['working_files'])}):")
            for f in state["working_files"][:5]:
                typer.echo(f"    - {f}")
            if len(state["working_files"]) > 5:
                typer.echo(f"    ... and {len(state['working_files']) - 5} more")

        if state.get("notes"):
            typer.echo(f"  Notes: {state['notes']}")

        typer.echo()

    except Exception as e:
        typer.secho(f"Error recovering checkpoint: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@session_app.command("stats")
def session_stats(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze"),
    branch: str = typer.Option("main", "--branch", "-b", help="Branch to analyze"),
):
    """Show session statistics and analytics.

    Display productivity metrics, session overview, and tool usage
    statistics for recent sessions.

    Examples:
        idlergear session stats              # Last 7 days
        idlergear session stats --days 30    # Last 30 days
        idlergear session stats --branch experiment  # Specific branch
    """
    from idlergear.config import find_idlergear_root
    from idlergear.session_analytics import SessionStats, format_stats_output

    if find_idlergear_root() is None:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    try:
        stats = SessionStats()

        # Get and display overview stats
        overview = stats.get_overview_stats(days=days, branch=branch)
        typer.echo(format_stats_output(overview))

        # Get and display tool usage if we have sessions
        if overview["total_sessions"] > 0:
            tool_stats = stats.get_tool_usage_stats(days=days, branch=branch)
            if tool_stats["total_calls"] > 0:
                typer.echo("\n🔧 Tool Usage:")
                for tool_stat in tool_stats["tools"][:5]:  # Top 5 tools
                    typer.echo(
                        f"  {tool_stat['tool']}: {tool_stat['calls']} calls "
                        f"({tool_stat['percentage']})"
                    )

            # Get and display success rate
            success = stats.get_success_rate(days=days, branch=branch)
            if success["total_sessions"] > 0:
                typer.echo("\n✅ Success Rate:")
                typer.echo(
                    f"  {success['success_rate']} "
                    f"({success['successful']}/{success['total_sessions']} sessions)"
                )

    except RuntimeError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error calculating stats: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@session_app.command("monitor")
def session_monitor(
    session_file: str = typer.Option(None, "--file", "-f", help="Session file to monitor (auto-detect if not provided)"),
):
    """Monitor active session in real-time.

    Watch your Claude Code session as it happens. See tool calls,
    task operations, file changes, and more—all in a beautiful TUI.

    Also available as standalone command: idlerwatch

    Examples:
        idlergear session monitor           # Monitor current session
        idlergear session monitor --file /path/to/session.jsonl
        idlerwatch                            # Shortcut command
    """
    from pathlib import Path
    from idlergear.tui import run_monitor

    session_path = Path(session_file) if session_file else None

    try:
        run_monitor(session_path)
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        pass
    except Exception as e:
        typer.secho(f"Error running monitor: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


# Goose commands
@goose_app.command("init")
def goose_init(
    path: str = typer.Argument(".", help="Project directory"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing .goosehints"),
):
    """Generate .goosehints file with IdlerGear and MCP server recommendations."""
    from pathlib import Path
    from .goose import generate_goosehints

    generate_goosehints(Path(path), force=force)


@goose_app.command("register")
def goose_register():
    """Register IdlerGear as a Goose GUI extension.

    Currently provides manual registration instructions.
    Automatic registration will be implemented after researching Goose's extension API.
    """
    from .goose import register_goose_extension

    register_goose_extension()


# OTel commands
@otel_app.command("start")
def otel_start_cmd(
    grpc_port: int = typer.Option(4317, help="gRPC port for OTLP receiver"),
    http_port: int = typer.Option(4318, help="HTTP port for OTLP receiver"),
    daemon: bool = typer.Option(False, help="Run in background as daemon"),
):
    """Start OpenTelemetry collector."""
    from .otel import otel_start

    otel_start(grpc_port=grpc_port, http_port=http_port, daemon=daemon)


@otel_app.command("stop")
def otel_stop_cmd():
    """Stop OpenTelemetry collector."""
    from .otel import otel_stop

    otel_stop()


@otel_app.command("status")
def otel_status_cmd():
    """Show OpenTelemetry collector status."""
    from .otel import otel_status

    otel_status()


@otel_app.command("logs")
def otel_logs_cmd(
    tail: int = typer.Option(20, help="Show last N logs"),
    service: str = typer.Option(None, help="Filter by service name"),
    severity: str = typer.Option(None, help="Filter by severity"),
    search: str = typer.Option(None, help="Full-text search"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Query and display collected logs."""
    from .otel import otel_logs

    otel_logs(
        tail=tail,
        service=service,
        severity=severity,
        search=search,
        json_output=json_output,
    )


@otel_app.command("config")
def otel_config_cmd():
    """Show OpenTelemetry configuration."""
    from .otel import otel_config_show

    otel_config_show()


# ===== Session Management Commands =====
@app.command()
def session_start(
    context_mode: str = "minimal",
    no_state: bool = False,
):
    """Start a new session and load context + previous state.

    This is the recommended first command in any AI assistant session.
    """
    from .session import start_session

    result = start_session(
        context_mode=context_mode,
        load_state=not no_state,
    )

    # Display context
    print("# Project Context")
    print(json.dumps(result["context"], indent=2))
    print()

    # Display session state
    if result.get("session_state"):
        print("# Previous Session")
        print(json.dumps(result["session_state"], indent=2))
        print()

    # Display recommendations
    if result.get("recommendations"):
        print("# Recommendations")
        for rec in result["recommendations"]:
            print(f"- {rec}")


@app.command()
def session_save(
    task: Optional[int] = None,
    files: Optional[str] = None,
    notes: Optional[str] = None,
):
    """Save current session state."""
    from .session import SessionState

    working_files = files.split(",") if files else None

    session = SessionState()
    state = session.save(
        current_task_id=task,
        working_files=working_files,
        notes=notes,
    )

    print("Session state saved:")
    print(json.dumps(state, indent=2))


@app.command()
def session_end(
    task: Optional[int] = None,
    files: Optional[str] = None,
    notes: Optional[str] = None,
):
    """End session and save state with suggestions."""
    from .session import end_session

    working_files = files.split(",") if files else None

    result = end_session(
        current_task_id=task,
        working_files=working_files,
        notes=notes,
    )

    print("Session ended:")
    print(json.dumps(result, indent=2))


@app.command()
def session_status():
    """Show current session state."""
    from .session import SessionState

    session = SessionState()
    summary = session.get_summary()
    print(summary)


@app.command()
def session_clear():
    """Clear session state."""
    from .session import SessionState

    session = SessionState()
    if session.clear():
        print("Session state cleared")
    else:
        print("No session state to clear")


@app.command()
def session_snapshot(
    notes: str = typer.Option("", "--notes", "-n", help="Session notes"),
    task_id: Optional[int] = typer.Option(None, "--task", "-t", help="Current task ID"),
    duration: int = typer.Option(0, "--duration", "-d", help="Session duration in minutes"),
):
    """Create a session snapshot (full history record).

    Saves current session state as a snapshot in the session history.
    Unlike session-save (which overwrites), this creates a permanent record.

    Examples:
        idlergear session-snapshot --notes "Completed indexer design"
        idlergear session-snapshot --task 270 --duration 45
    """
    from .session import SessionState
    from .session_history import SessionHistory
    import subprocess

    # Get current session state
    session_state = SessionState()
    state_data = session_state.load() or {}

    # Get git context
    try:
        git_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        git_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()[:7]

        git_dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
        ).stdout.strip() != ""
    except Exception:
        git_branch = "unknown"
        git_commit = "unknown"
        git_dirty = False

    # Build snapshot state
    snapshot_state = {
        "current_task_id": task_id or state_data.get("current_task_id"),
        "working_files": state_data.get("working_files", []),
        "git_branch": git_branch,
        "git_commit": git_commit,
        "uncommitted_changes": git_dirty,
        "notes": notes or state_data.get("notes"),
    }

    # Create snapshot
    history = SessionHistory()
    snapshot = history.create_snapshot(
        state=snapshot_state,
        duration_seconds=duration * 60,
        outcome={
            "status": "saved",
            "goals_achieved": [],
        },
    )

    print(f"✓ Created session snapshot: {snapshot.session_id}")
    print(f"  Branch: {snapshot.branch}")
    print(f"  Timestamp: {snapshot.timestamp}")
    if task_id:
        print(f"  Task: #{task_id}")


@app.command()
def session_history(
    branch: str = typer.Option("main", "--branch", "-b", help="Branch name"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max sessions to show"),
):
    """List session history (snapshots).

    Shows all session snapshots in chronological order.

    Examples:
        idlergear session-history              # Show last 10 sessions
        idlergear session-history --limit 20   # Show last 20
        idlergear session-history --branch experiment
    """
    from .session_history import SessionHistory

    history = SessionHistory()
    snapshots = history.list_sessions(branch)

    if not snapshots:
        print(f"No session history for branch '{branch}'")
        return

    # Show most recent first
    snapshots = list(reversed(snapshots))[:limit]

    print(f"Session History (branch: {branch})")
    print("=" * 70)

    for snapshot in snapshots:
        state = snapshot.state
        duration_min = snapshot.duration_seconds // 60

        status = snapshot.outcome.get("status", "unknown")
        status_icon = {
            "success": "✅",
            "incomplete": "⚠️",
            "abandoned": "❌",
            "saved": "💾",
            "migrated": "🔄",
        }.get(status, "·")

        print(f"\n{status_icon} {snapshot.session_id} ({snapshot.timestamp})")
        if duration_min > 0:
            print(f"   Duration: {duration_min} minutes")
        if state.get("current_task_id"):
            print(f"   Task: #{state['current_task_id']}")
        if state.get("git_commit"):
            print(f"   Git: {state.get('git_branch')} @ {state['git_commit']}")
        if state.get("notes"):
            notes_preview = state["notes"][:60]
            print(f"   Notes: {notes_preview}{'...' if len(state['notes']) > 60 else ''}")


@app.command()
def session_show(
    session_id: str = typer.Argument(..., help="Session ID (e.g., s001)"),
    branch: str = typer.Option("main", "--branch", "-b", help="Branch name"),
):
    """Show details of a specific session snapshot.

    Examples:
        idlergear session-show s003
        idlergear session-show s001 --branch experiment
    """
    from .session_history import SessionHistory

    history = SessionHistory()
    snapshot = history.load_snapshot(session_id, branch)

    if not snapshot:
        print(f"Session {session_id} not found in branch '{branch}'")
        return

    # Pretty print the full snapshot
    import json
    print(json.dumps(snapshot.to_dict(), indent=2))


# Hooks commands
hooks_app = typer.Typer(help="Manage Claude Code hooks for IdlerGear enforcement")
app.add_typer(hooks_app, name="hooks")


@hooks_app.command("install")
def hooks_install(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing hooks"),
):
    """Install Claude Code hooks for automatic IdlerGear enforcement.

    Installs three hooks:
    - SessionStart: Auto-load project context (100% compliance)
    - PreToolUse: Block forbidden files like TODO.md (0% violations)
    - Stop: Prompt for knowledge capture before ending

    Examples:
        idlergear hooks install           # Install hooks (skip existing)
        idlergear hooks install --force  # Overwrite existing hooks
    """
    from idlergear.hooks import install_hooks

    results = install_hooks(force=force)

    typer.echo("Installing Claude Code hooks...")
    typer.echo()

    for filename, installed in results.items():
        if installed:
            typer.secho(f"✓ Installed {filename}", fg=typer.colors.GREEN)
        else:
            typer.secho(
                f"- Skipped {filename} (already exists)", fg=typer.colors.YELLOW
            )

    typer.echo()
    typer.echo("Hooks installed in .claude/hooks/")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("  1. Test hooks: idlergear hooks test")
    typer.echo("  2. Restart Claude Code to activate")
    typer.echo()
    typer.echo("See docs/CLAUDE_CODE_HOOKS.md for details")


@hooks_app.command("test")
def hooks_test():
    """Test installed hooks."""
    from idlergear.hooks import test_hooks

    typer.echo("Testing Claude Code hooks...")
    typer.echo()

    results = test_hooks()

    all_passed = True

    for hook_name, result in results.items():
        if not result.get("exists"):
            typer.secho(f"✗ {hook_name}: NOT INSTALLED", fg=typer.colors.RED)
            all_passed = False
            continue

        if not result.get("executable"):
            typer.secho(f"✗ {hook_name}: Not executable", fg=typer.colors.RED)
            all_passed = False
            continue

        # Hook-specific tests
        if hook_name == "session-start":
            if result.get("exit_code") == 0 and result.get("output_length", 0) > 0:
                typer.secho(f"✓ {hook_name}: PASSED", fg=typer.colors.GREEN)
            else:
                typer.secho(f"✗ {hook_name}: No output", fg=typer.colors.RED)
                all_passed = False

        elif hook_name == "pre-tool-use":
            if result.get("blocks_forbidden"):
                typer.secho(
                    f"✓ {hook_name}: PASSED (blocks TODO.md)", fg=typer.colors.GREEN
                )
            else:
                typer.secho(
                    f"✗ {hook_name}: Does not block forbidden files",
                    fg=typer.colors.RED,
                )
                all_passed = False

        elif hook_name == "stop":
            if result.get("valid_json"):
                typer.secho(f"✓ {hook_name}: PASSED", fg=typer.colors.GREEN)
            else:
                typer.secho(f"✗ {hook_name}: Invalid output", fg=typer.colors.RED)
                all_passed = False

    typer.echo()
    if all_passed:
        typer.secho("All hooks passed!", fg=typer.colors.GREEN, bold=True)
    else:
        typer.secho(
            "Some hooks failed. See docs/CLAUDE_CODE_HOOKS.md for troubleshooting.",
            fg=typer.colors.YELLOW,
        )


@hooks_app.command("list")
def hooks_list():
    """List installed hooks."""
    from idlergear.hooks import list_hooks
    from datetime import datetime

    hooks = list_hooks()

    if not hooks:
        typer.echo("No hooks installed.")
        typer.echo()
        typer.echo("Install hooks: idlergear hooks install")
        return

    typer.echo("Installed hooks:")
    typer.echo()

    for hook in hooks:
        executable = "✓" if hook["executable"] else "✗"
        modified = datetime.fromtimestamp(hook["modified"]).strftime("%Y-%m-%d %H:%M")
        typer.echo(f"{executable} {hook['name']:<20} {hook['size']:>6}B  {modified}")

    typer.echo()
    typer.echo("Location: .claude/hooks/")


# ===== Wiki Commands =====

wiki_app = typer.Typer(help="GitHub Wiki synchronization commands")
app.add_typer(wiki_app, name="wiki")


@wiki_app.command("push")
def wiki_push():
    """Push IdlerGear references to GitHub Wiki."""
    from idlergear.wiki import WikiSync

    typer.echo("Pushing references to GitHub Wiki...")
    typer.echo()

    sync = WikiSync()
    result = sync.push_references_to_wiki()

    typer.echo(str(result))


@wiki_app.command("pull")
def wiki_pull(
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing references"
    ),
):
    """Pull GitHub Wiki pages into IdlerGear references."""
    from idlergear.wiki import WikiSync

    typer.echo("Pulling Wiki pages to references...")
    typer.echo()

    sync = WikiSync()
    result = sync.pull_wiki_to_references(overwrite=overwrite)

    typer.echo(str(result))


@wiki_app.command("sync")
def wiki_sync(
    conflict_resolution: str = typer.Option(
        "manual",
        "--conflict",
        help="Conflict resolution strategy (manual, local, remote)",
    ),
):
    """Bidirectional sync between IdlerGear and GitHub Wiki."""
    from idlergear.wiki import WikiSync

    typer.echo("Syncing IdlerGear ↔ GitHub Wiki...")
    typer.echo()

    sync = WikiSync()
    result = sync.sync_bidirectional(conflict_resolution=conflict_resolution)

    typer.echo(str(result))

    if result.conflicts and conflict_resolution == "manual":
        typer.echo()
        typer.echo("To resolve conflicts:")
        typer.echo("  --conflict local   # Use local (IdlerGear) version")
        typer.echo("  --conflict remote  # Use remote (Wiki) version")


@wiki_app.command("status")
def wiki_status():
    """Show GitHub Wiki sync status."""
    from idlergear.wiki import WikiSync

    sync = WikiSync()

    if not sync.wiki_dir.exists():
        typer.echo("❌ Wiki not cloned")
        typer.echo()
        typer.echo("Clone wiki: idlergear wiki pull")
        return

    # Get git status
    returncode, stdout, stderr = sync._run_git("status", "--porcelain")

    if returncode != 0:
        typer.secho(f"Error: {stderr}", fg=typer.colors.RED)
        return

    # Check for changes
    if not stdout.strip():
        typer.secho("✓ Wiki is in sync", fg=typer.colors.GREEN)
    else:
        typer.secho("⚠️  Uncommitted changes in wiki:", fg=typer.colors.YELLOW)
        typer.echo()
        typer.echo(stdout)

    # Show last commit
    returncode, stdout, stderr = sync._run_git("log", "-1", "--oneline")
    if returncode == 0:
        typer.echo()
        typer.echo(f"Last commit: {stdout.strip()}")


@wiki_app.command("config")
def wiki_config(
    key: Optional[str] = typer.Argument(None, help="Config key"),
    value: Optional[str] = typer.Argument(None, help="Config value"),
):
    """Get or set wiki configuration."""
    from idlergear.wiki import get_wiki_config, set_wiki_config

    if not key:
        # Show all config
        config = get_wiki_config()
        typer.echo("Wiki configuration:")
        typer.echo()
        for k, v in config.items():
            typer.echo(f"  {k}: {v}")
        return

    if not value:
        # Get specific value
        config = get_wiki_config()
        if key in config:
            typer.echo(config[key])
        else:
            typer.secho(f"Unknown config key: {key}", fg=typer.colors.RED)
        return

    # Set value
    set_wiki_config(key, value)
    typer.secho(f"✓ Set wiki.{key} = {value}", fg=typer.colors.GREEN)


# ===== Watch Commands =====

watch_app = typer.Typer(help="Watch mode for proactive knowledge capture")
app.add_typer(watch_app, name="watch")


@watch_app.command("check")
def watch_check(
    ctx: typer.Context,
    act: bool = typer.Option(
        False, "--act", "-a", help="Automatically create tasks from TODO/FIXME comments"
    ),
):
    """One-shot analysis of project state with suggestions.

    Analyzes git status, scans for TODO/FIXME comments in diff,
    checks for stale references, and returns actionable suggestions.

    With --act, automatically creates tasks from detected TODO comments.

    Examples:
        idlergear watch check              # Analyze and show suggestions
        idlergear watch check --act        # Analyze AND auto-create tasks from TODOs
        idlergear --output json watch check  # JSON output for AI agents
    """
    from idlergear.watch import analyze, analyze_and_act

    if act:
        status, actions = analyze_and_act(auto_create_tasks=True)
    else:
        status = analyze()
        actions = []
    output_format = getattr(ctx.obj, "output_format", OutputFormat.HUMAN) if ctx.obj else OutputFormat.HUMAN

    if output_format == OutputFormat.JSON:
        result = status.to_dict()
        if actions:
            result["actions"] = [a.to_dict() for a in actions]
        typer.echo(json.dumps(result, indent=2))
        return

    # Human-readable output
    typer.echo("Watch Analysis")
    typer.echo("=" * 40)
    typer.echo()

    # Git status summary
    typer.secho("Git Status:", bold=True)
    typer.echo(f"  Files changed: {status.files_changed}")
    typer.echo(f"  Lines added: {status.lines_added}")
    typer.echo(f"  Lines deleted: {status.lines_deleted}")
    if status.minutes_since_commit is not None:
        typer.echo(f"  Time since commit: {status.minutes_since_commit} min")
    typer.echo()

    # Suggestions
    if status.suggestions:
        typer.secho(f"Suggestions ({len(status.suggestions)}):", bold=True)
        typer.echo()

        for suggestion in status.suggestions:
            # Color based on severity
            if suggestion.severity == "action":
                color = typer.colors.RED
                icon = "!"
            elif suggestion.severity == "warning":
                color = typer.colors.YELLOW
                icon = "?"
            else:
                color = typer.colors.CYAN
                icon = "i"

            typer.secho(f"  [{icon}] {suggestion.message}", fg=color)

            # Show context for certain categories
            if suggestion.category == "todo" and suggestion.context.get("file"):
                typer.echo(f"      File: {suggestion.context['file']}")
                typer.echo(f"      Text: {suggestion.context.get('text', '')}")
            elif suggestion.category == "reference" and suggestion.context.get(
                "related_file"
            ):
                typer.echo(f"      Related: {suggestion.context['related_file']}")

        typer.echo()
    else:
        typer.secho("No suggestions - project looks good!", fg=typer.colors.GREEN)

    # Show actions taken
    if actions:
        typer.echo()
        typer.secho("Actions Taken:", bold=True)
        for action in actions:
            if action.success:
                typer.secho(f"  ✓ {action.message}", fg=typer.colors.GREEN)
            else:
                typer.secho(f"  ✗ {action.message}", fg=typer.colors.RED)


@watch_app.command("versions")
def watch_versions(
    ctx: typer.Context,
):
    """Check for stale file version references in Python code.

    Detects when Python scripts reference old versions of data files
    (CSV, JSON, etc.) and suggests using the current version instead.

    Examples:
        idlergear watch versions              # Check for stale data file references
        idlergear --output json watch versions  # JSON output for AI agents
    """
    from idlergear.watch import check_stale_data_references
    from idlergear.config import find_idlergear_root

    project_root = find_idlergear_root()
    if project_root is None:
        if ctx.obj["output"] == "json":
            typer.echo('{"error": "Not in an IdlerGear project"}')
        else:
            typer.secho("Error: Not in an IdlerGear project", fg=typer.colors.RED)
        raise typer.Exit(1)

    warnings = check_stale_data_references(project_root)

    if ctx.obj["output"] == "json":
        import json
        typer.echo(json.dumps({"warnings": warnings}, indent=2))
    else:
        if not warnings:
            typer.secho("✓ No stale file version references found", fg=typer.colors.GREEN)
        else:
            typer.secho(
                f"\nFile Version Analysis ({len(warnings)} issues found)",
                fg=typer.colors.YELLOW,
                bold=True,
            )
            typer.echo()

            for warning in warnings:
                typer.secho(
                    f"⚠️  {warning['source_file']}:{warning['line']}",
                    fg=typer.colors.YELLOW,
                )
                typer.echo(f"    References stale: {warning['stale_file']}")
                if warning.get("current_file"):
                    typer.secho(
                        f"    → Use instead: {warning['current_file']}",
                        fg=typer.colors.GREEN,
                    )
                if warning.get("function"):
                    typer.echo(f"    Function: {warning['function']}")
                typer.echo()

            typer.echo()
            typer.secho(
                f"Summary: {len(warnings)} stale file references detected",
                fg=typer.colors.YELLOW,
            )


@watch_app.command("start")
def watch_start(
    interval: int = typer.Option(
        10, "--interval", "-i", help="Check interval in seconds"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Only show critical suggestions"
    ),
    polling: bool = typer.Option(
        False, "--polling", "-p", help="Use polling instead of file system events"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Start even if watch mode is disabled"
    ),
):
    """Start watching for changes and prompting for knowledge capture.

    This runs in the foreground and monitors file changes in real-time.
    Press Ctrl+C to stop.

    Examples:
        idlergear watch start                # Start with defaults
        idlergear watch start -q             # Only show critical suggestions
        idlergear watch start -i 5           # Check every 5 seconds
        idlergear watch start --polling      # Use polling mode (no watchdog)
    """
    from idlergear.watch import WatchConfig, run_interactive_watch

    config = WatchConfig.load()

    if not config.enabled and not force:
        typer.secho("Watch mode is disabled", fg=typer.colors.YELLOW)
        typer.echo()
        typer.echo("Enable it with:")
        typer.echo("  idlergear watch config enabled true")
        typer.echo()
        typer.echo("Or start anyway:")
        typer.echo("  idlergear watch start --force")
        return

    # Update config with interval if provided
    if interval != 10:
        config.poll_interval = interval

    run_interactive_watch(quiet=quiet, use_polling=polling)


@watch_app.command("status")
def watch_status():
    """Show current watch statistics."""
    from idlergear.watch import get_watch_stats

    stats = get_watch_stats()

    typer.echo("Watch Status:")
    typer.echo()

    if stats["changed_files"] > 0:
        typer.secho(
            f"  Changed files: {stats['changed_files']}", fg=typer.colors.YELLOW
        )
        typer.secho(
            f"  Changed lines: {stats['changed_lines']}", fg=typer.colors.YELLOW
        )
    else:
        typer.secho("  No uncommitted changes", fg=typer.colors.GREEN)

    typer.echo()

    if stats["todos"] > 0:
        typer.secho(f"  TODO comments: {stats['todos']}", fg=typer.colors.YELLOW)
    if stats["fixmes"] > 0:
        typer.secho(f"  FIXME comments: {stats['fixmes']}", fg=typer.colors.RED)
    if stats["hacks"] > 0:
        typer.secho(f"  HACK comments: {stats['hacks']}", fg=typer.colors.MAGENTA)

    if stats["todos"] == 0 and stats["fixmes"] == 0 and stats["hacks"] == 0:
        typer.secho("  No code markers detected", fg=typer.colors.GREEN)


@watch_app.command("config")
def watch_config(
    key: Optional[str] = typer.Argument(None, help="Config key"),
    value: Optional[str] = typer.Argument(None, help="Config value"),
):
    """Get or set watch configuration."""
    from idlergear.watch import WatchConfig

    config = WatchConfig.load()

    if not key:
        # Show all config
        typer.echo("Watch configuration:")
        typer.echo()
        typer.echo(f"  enabled: {config.enabled}")
        typer.echo(f"  debounce: {config.debounce}s")
        typer.echo(f"  files_changed_threshold: {config.files_changed_threshold}")
        typer.echo(
            f"  uncommitted_lines_threshold: {config.uncommitted_lines_threshold}"
        )
        typer.echo(f"  test_failures_threshold: {config.test_failures_threshold}")
        typer.echo(f"  detect_todos: {config.detect_todos}")
        typer.echo(f"  detect_fixmes: {config.detect_fixmes}")
        typer.echo(f"  detect_hacks: {config.detect_hacks}")
        return

    if not value:
        # Get specific value
        if hasattr(config, key):
            typer.echo(getattr(config, key))
        else:
            typer.secho(f"Unknown config key: {key}", fg=typer.colors.RED)
        return

    # Set value
    if key == "enabled":
        config.enabled = value.lower() == "true"
    elif key == "debounce":
        config.debounce = int(value)
    elif key == "files_changed_threshold":
        config.files_changed_threshold = int(value)
    elif key == "uncommitted_lines_threshold":
        config.uncommitted_lines_threshold = int(value)
    elif key == "test_failures_threshold":
        config.test_failures_threshold = int(value)
    elif key == "detect_todos":
        config.detect_todos = value.lower() == "true"
    elif key == "detect_fixmes":
        config.detect_fixmes = value.lower() == "true"
    elif key == "detect_hacks":
        config.detect_hacks = value.lower() == "true"
    else:
        typer.secho(f"Unknown config key: {key}", fg=typer.colors.RED)
        return

    config.save()
    typer.secho(f"✓ Set watch.{key} = {value}", fg=typer.colors.GREEN)


# ============================================================================
# Test commands - Test framework detection and status tracking
# ============================================================================


@test_app.command("detect")
def test_detect(
    ctx: typer.Context,
    path: str = typer.Argument(".", help="Project directory to analyze"),
):
    """Detect test framework in use.

    Supports: pytest, cargo test, dotnet test, jest, vitest, go test, rspec

    Examples:
        idlergear test detect        # Detect in current directory
        idlergear test detect ./api  # Detect in specific directory
    """
    from pathlib import Path

    from idlergear.testing import detect_framework

    project_path = Path(path).resolve()
    if not project_path.exists():
        typer.secho(f"Path does not exist: {path}", fg=typer.colors.RED)
        raise typer.Exit(1)

    config = detect_framework(project_path)

    if ctx.obj.output_format == OutputFormat.JSON:
        typer.echo(
            json.dumps(
                {
                    "framework": config.framework,
                    "command": config.command,
                    "test_dir": config.test_dir,
                    "test_pattern": config.test_pattern,
                }
            )
        )
    else:
        if config.framework == "unknown":
            typer.secho("No test framework detected.", fg=typer.colors.YELLOW)
            typer.echo("\nSupported frameworks:")
            typer.echo("  • pytest (Python)")
            typer.echo("  • cargo test (Rust)")
            typer.echo("  • dotnet test (.NET)")
            typer.echo("  • jest/vitest (JavaScript)")
            typer.echo("  • go test (Go)")
            typer.echo("  • rspec (Ruby)")
        else:
            typer.secho(f"Framework: {config.framework}", fg=typer.colors.GREEN)
            typer.echo(f"Command: {config.command}")
            if config.test_dir:
                typer.echo(f"Test directory: {config.test_dir}")
            if config.test_pattern:
                typer.echo(f"Test pattern: {config.test_pattern}")


@test_app.command("status")
def test_status(
    ctx: typer.Context,
    path: str = typer.Argument(".", help="Project directory"),
):
    """Show last test run status.

    Shows cached results from the most recent test run.

    Examples:
        idlergear test status        # Show last run status
        idlergear test status --json # JSON output
    """
    from pathlib import Path

    from idlergear.testing import format_status, get_last_result

    project_path = Path(path).resolve()
    result = get_last_result(project_path)

    if result is None:
        if ctx.obj.output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps({"status": "no_results", "message": "No test results found"})
            )
        else:
            typer.secho("No test results found.", fg=typer.colors.YELLOW)
            typer.echo("\nRun tests with: idlergear test run")
        return

    if ctx.obj.output_format == OutputFormat.JSON:
        typer.echo(
            json.dumps(
                {
                    "framework": result.framework,
                    "timestamp": result.timestamp,
                    "duration_seconds": result.duration_seconds,
                    "total": result.total,
                    "passed": result.passed,
                    "failed": result.failed,
                    "skipped": result.skipped,
                    "errors": result.errors,
                    "failed_tests": result.failed_tests,
                    "command": result.command,
                    "exit_code": result.exit_code,
                }
            )
        )
    else:
        typer.echo(format_status(result))


@test_app.command("run")
def test_run(
    ctx: typer.Context,
    path: str = typer.Argument(".", help="Project directory"),
    args: Optional[str] = typer.Option(
        None, "--args", "-a", help="Additional arguments to pass to test command"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show full test output"
    ),
):
    """Run tests and cache results.

    Detects the test framework and runs tests, parsing and caching the results.

    Examples:
        idlergear test run                    # Run all tests
        idlergear test run --args "-k auth"   # Run with extra args
        idlergear test run --verbose          # Show full output
    """
    from pathlib import Path

    from idlergear.testing import detect_framework, format_status, run_tests

    project_path = Path(path).resolve()
    if not project_path.exists():
        typer.secho(f"Path does not exist: {path}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Detect framework
    config = detect_framework(project_path)
    if config.framework == "unknown":
        typer.secho("No test framework detected.", fg=typer.colors.RED)
        typer.echo(
            "\nSupported frameworks: pytest, cargo, dotnet, jest, vitest, go, rspec"
        )
        raise typer.Exit(1)

    # Build command with extra args
    command = config.command
    if args:
        command = f"{command} {args}"

    typer.echo(f"Running: {command}")
    typer.echo()

    # Run tests
    result, output = run_tests(project_path, config, extra_args=args)

    if verbose:
        typer.echo(output)
        typer.echo()

    if ctx.obj.output_format == OutputFormat.JSON:
        typer.echo(
            json.dumps(
                {
                    "framework": result.framework,
                    "timestamp": result.timestamp,
                    "duration_seconds": result.duration_seconds,
                    "total": result.total,
                    "passed": result.passed,
                    "failed": result.failed,
                    "skipped": result.skipped,
                    "errors": result.errors,
                    "failed_tests": result.failed_tests,
                    "command": result.command,
                    "exit_code": result.exit_code,
                    "success": result.exit_code == 0,
                }
            )
        )
    else:
        typer.echo(format_status(result))

    # Exit with test exit code
    if result.exit_code != 0:
        raise typer.Exit(result.exit_code)


@test_app.command("history")
def test_history(
    ctx: typer.Context,
    path: str = typer.Argument(".", help="Project directory"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of results to show"),
):
    """Show test run history.

    Examples:
        idlergear test history           # Show last 10 runs
        idlergear test history -n 5      # Show last 5 runs
    """
    from pathlib import Path

    from idlergear.testing import get_history

    project_path = Path(path).resolve()
    history = get_history(project_path, limit=limit)

    if not history:
        if ctx.obj.output_format == OutputFormat.JSON:
            typer.echo(json.dumps([]))
        else:
            typer.secho("No test history found.", fg=typer.colors.YELLOW)
        return

    if ctx.obj.output_format == OutputFormat.JSON:
        typer.echo(
            json.dumps(
                [
                    {
                        "framework": r.framework,
                        "timestamp": r.timestamp,
                        "duration_seconds": r.duration_seconds,
                        "total": r.total,
                        "passed": r.passed,
                        "failed": r.failed,
                        "exit_code": r.exit_code,
                    }
                    for r in history
                ]
            )
        )
    else:
        typer.secho(
            f"Test history ({len(history)} runs):", fg=typer.colors.CYAN, bold=True
        )
        typer.echo()
        for r in history:
            # Format timestamp nicely
            try:
                from datetime import datetime

                dt = datetime.fromisoformat(r.timestamp.replace("Z", "+00:00"))
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                time_str = r.timestamp[:16]

            # Status indicator
            if r.failed > 0 or r.errors > 0:
                status = typer.style("✗", fg=typer.colors.RED)
            else:
                status = typer.style("✓", fg=typer.colors.GREEN)

            typer.echo(
                f"  {status} {time_str} | {r.passed}/{r.total} passed | {r.duration_seconds:.1f}s"
            )


@test_app.command("list")
def test_list(
    ctx: typer.Context,
    path: str = typer.Argument(".", help="Project directory"),
    files_only: bool = typer.Option(
        False, "--files", "-f", help="List test files only, not individual tests"
    ),
    refresh: bool = typer.Option(
        False, "--refresh", "-r", help="Re-enumerate tests (don't use cache)"
    ),
):
    """List all tests in the project.

    Enumerates tests using the framework's collection mechanism.

    Examples:
        idlergear test list           # List all tests
        idlergear test list --files   # List test files only
        idlergear test list --refresh # Force re-enumeration
    """
    from pathlib import Path

    from idlergear.testing import enumerate_tests, get_enumeration, save_enumeration

    project_path = Path(path).resolve()

    # Use cache unless refresh requested
    if not refresh:
        enum = get_enumeration(project_path)
        if enum is None:
            enum = enumerate_tests(project_path)
            if enum:
                save_enumeration(enum, project_path)
    else:
        enum = enumerate_tests(project_path)
        if enum:
            save_enumeration(enum, project_path)

    if enum is None:
        if ctx.obj.output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"error": "No test framework detected"}))
        else:
            typer.secho("No test framework detected.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if ctx.obj.output_format == OutputFormat.JSON:
        if files_only:
            typer.echo(
                json.dumps(
                    {
                        "framework": enum.framework,
                        "total_files": enum.total_files,
                        "files": enum.test_files,
                    }
                )
            )
        else:
            typer.echo(json.dumps(enum.to_dict()))
    else:
        typer.secho(
            f"Tests ({enum.framework}): {enum.total_tests} tests in {enum.total_files} files",
            fg=typer.colors.CYAN,
            bold=True,
        )
        typer.echo()

        if files_only:
            for f in enum.test_files:
                typer.echo(f"  {f}")
        else:
            # Group by file
            by_file: dict[str, list[str]] = {}
            for item in enum.test_items:
                if item.file not in by_file:
                    by_file[item.file] = []
                by_file[item.file].append(item.name)

            for file in sorted(by_file.keys()):
                typer.secho(f"  {file}", fg=typer.colors.GREEN)
                for test in by_file[file][:10]:  # Limit per file
                    typer.echo(f"    - {test}")
                if len(by_file[file]) > 10:
                    typer.echo(f"    ... and {len(by_file[file]) - 10} more")


@test_app.command("coverage")
def test_coverage(
    ctx: typer.Context,
    file: Optional[str] = typer.Argument(
        None, help="Source file to check coverage for"
    ),
    path: str = typer.Option(".", "--path", "-p", help="Project directory"),
    refresh: bool = typer.Option(False, "--refresh", "-r", help="Rebuild coverage map"),
):
    """Show test coverage mapping.

    Maps source files to their test files using naming conventions.

    Examples:
        idlergear test coverage                    # Show all mappings
        idlergear test coverage src/foo.py         # Show tests for specific file
        idlergear test coverage --refresh          # Rebuild coverage map
    """
    from pathlib import Path

    from idlergear.testing import (
        build_coverage_map,
        get_coverage_map,
        get_tests_for_file,
    )

    project_path = Path(path).resolve()

    if file:
        # Show tests for specific file
        tests = get_tests_for_file(file, project_path)

        if ctx.obj.output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"source_file": file, "test_files": tests}))
        else:
            if tests:
                typer.secho(f"Tests for {file}:", fg=typer.colors.CYAN)
                for t in tests:
                    typer.echo(f"  - {t}")
            else:
                typer.secho(f"No tests found for {file}", fg=typer.colors.YELLOW)
        return

    # Show full coverage map
    if refresh:
        coverage_map = build_coverage_map(project_path)
    else:
        coverage_map = get_coverage_map(project_path)
        if coverage_map is None:
            coverage_map = build_coverage_map(project_path)

    if coverage_map is None:
        if ctx.obj.output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"error": "Could not build coverage map"}))
        else:
            typer.secho("Could not build coverage map.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if ctx.obj.output_format == OutputFormat.JSON:
        typer.echo(json.dumps(coverage_map.to_dict()))
    else:
        covered = len(coverage_map.mappings)
        uncovered = len(coverage_map.uncovered)
        total = covered + uncovered
        pct = (covered / total * 100) if total > 0 else 0

        typer.secho(
            f"Coverage Map ({coverage_map.framework}): {covered}/{total} files have tests ({pct:.0f}%)",
            fg=typer.colors.CYAN,
            bold=True,
        )
        typer.echo()

        if coverage_map.uncovered:
            typer.secho("Uncovered files:", fg=typer.colors.YELLOW)
            for f in coverage_map.uncovered[:20]:
                typer.echo(f"  - {f}")
            if len(coverage_map.uncovered) > 20:
                typer.echo(f"  ... and {len(coverage_map.uncovered) - 20} more")


@test_app.command("uncovered")
def test_uncovered(
    ctx: typer.Context,
    path: str = typer.Argument(".", help="Project directory"),
):
    """List source files without tests.

    Examples:
        idlergear test uncovered       # List uncovered files
    """
    from pathlib import Path

    from idlergear.testing import get_uncovered_files

    project_path = Path(path).resolve()
    uncovered = get_uncovered_files(project_path)

    if ctx.obj.output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"uncovered": uncovered, "count": len(uncovered)}))
    else:
        if uncovered:
            typer.secho(
                f"Uncovered files ({len(uncovered)}):",
                fg=typer.colors.YELLOW,
                bold=True,
            )
            for f in uncovered:
                typer.echo(f"  - {f}")
        else:
            typer.secho("All source files have tests!", fg=typer.colors.GREEN)


@test_app.command("changed")
def test_changed(
    ctx: typer.Context,
    path: str = typer.Argument(".", help="Project directory"),
    since: Optional[str] = typer.Option(
        None, "--since", "-s", help="Commit hash or ref to compare against"
    ),
    run: bool = typer.Option(False, "--run", "-r", help="Actually run the tests"),
    args: Optional[str] = typer.Option(
        None, "--args", "-a", help="Additional arguments for test command"
    ),
):
    """Show or run tests for changed files.

    Identifies which tests should run based on files changed since last commit.

    Examples:
        idlergear test changed                 # Show tests for uncommitted changes
        idlergear test changed --run           # Run tests for changed files
        idlergear test changed --since HEAD~3  # Tests for last 3 commits
    """
    from pathlib import Path

    from idlergear.testing import (
        format_status,
        get_changed_files,
        get_tests_for_changes,
        run_changed_tests,
    )

    project_path = Path(path).resolve()

    if run:
        # Run the tests
        result, output = run_changed_tests(project_path, since=since, extra_args=args)

        if ctx.obj.output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps(
                    {
                        "success": result.exit_code == 0,
                        **result.to_dict(),
                    }
                )
            )
        else:
            if result.total == 0 and result.errors == 0:
                typer.secho(
                    "No tests to run - no changed files affect tests.",
                    fg=typer.colors.YELLOW,
                )
            else:
                typer.echo(format_status(result))

        if result.exit_code != 0:
            raise typer.Exit(result.exit_code)
    else:
        # Just show what would run
        changed = get_changed_files(project_path, since=since)
        tests = get_tests_for_changes(project_path, since=since)

        if ctx.obj.output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps(
                    {
                        "changed_files": changed,
                        "tests_to_run": tests,
                        "changed_count": len(changed),
                        "test_count": len(tests),
                    }
                )
            )
        else:
            typer.secho(
                f"Changed files: {len(changed)}", fg=typer.colors.CYAN, bold=True
            )
            for f in changed[:10]:
                typer.echo(f"  - {f}")
            if len(changed) > 10:
                typer.echo(f"  ... and {len(changed) - 10} more")

            typer.echo()
            typer.secho(f"Tests to run: {len(tests)}", fg=typer.colors.CYAN, bold=True)
            for t in tests[:10]:
                typer.echo(f"  - {t}")
            if len(tests) > 10:
                typer.echo(f"  ... and {len(tests) - 10} more")

            if tests:
                typer.echo()
                typer.echo("Run with: idlergear test changed --run")


@test_app.command("sync")
def test_sync(
    ctx: typer.Context,
    path: str = typer.Argument(".", help="Project directory"),
):
    """Detect and import test runs from outside IdlerGear.

    Checks for tests that ran via IDE, command line, or CI/CD and imports
    their results into IdlerGear's tracking.

    Examples:
        idlergear test sync        # Check for external test runs
    """
    from pathlib import Path

    from idlergear.testing import (
        check_external_test_runs,
        sync_external_runs,
    )

    project_path = Path(path).resolve()

    # Check for external runs
    external_runs = check_external_test_runs(project_path)

    if not external_runs:
        if ctx.obj.output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps(
                    {
                        "external_detected": False,
                        "imported": 0,
                        "message": "No external test runs detected",
                    }
                )
            )
        else:
            typer.echo("No external test runs detected.")
        return

    # Import them
    imported = sync_external_runs(project_path)

    if ctx.obj.output_format == OutputFormat.JSON:
        typer.echo(
            json.dumps(
                {
                    "external_detected": True,
                    "external_runs": [r.to_dict() for r in external_runs],
                    "imported": len(imported),
                    "results": [r.to_dict() for r in imported],
                }
            )
        )
    else:
        typer.secho(
            f"Detected {len(external_runs)} external test run(s)",
            fg=typer.colors.CYAN,
            bold=True,
        )
        for run in external_runs:
            status = "✅" if run.success else "❌" if run.success is False else "❓"
            typer.echo(f"  {status} {run.cache_path} @ {run.timestamp}")
            if run.estimated_tests:
                typer.echo(f"     ~{run.estimated_tests} tests")

        if imported:
            typer.echo()
            typer.secho(f"Imported {len(imported)} result(s)", fg=typer.colors.GREEN)
            for result in imported:
                typer.echo(f"  - {result.passed} passed, {result.failed} failed")
        else:
            typer.echo()
            typer.secho(
                "Could not import detailed results (cache may be incomplete)",
                fg=typer.colors.YELLOW,
            )


@test_app.command("staleness")
def test_staleness(
    ctx: typer.Context,
    path: str = typer.Argument(".", help="Project directory"),
):
    """Check how stale test results are.

    Reports when tests were last run and whether tests have run outside
    of IdlerGear since then.

    Examples:
        idlergear test staleness   # Check test result freshness
    """
    from pathlib import Path

    from idlergear.testing import get_test_staleness

    project_path = Path(path).resolve()
    staleness = get_test_staleness(project_path)

    if ctx.obj.output_format == OutputFormat.JSON:
        typer.echo(json.dumps(staleness))
    else:
        if staleness["last_run"]:
            seconds = staleness.get("seconds_ago", 0)
            if seconds is None:
                time_ago = "unknown"
            elif seconds < 60:
                time_ago = "just now"
            elif seconds < 3600:
                mins = int(seconds // 60)
                time_ago = f"{mins} minute{'s' if mins != 1 else ''} ago"
            elif seconds < 86400:
                hours = int(seconds // 3600)
                time_ago = f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                days = int(seconds // 86400)
                time_ago = f"{days} day{'s' if days != 1 else ''} ago"

            typer.secho("Last recorded test run:", bold=True)
            typer.echo(f"  {time_ago} ({staleness['last_run']})")
        else:
            typer.secho("No test runs recorded.", fg=typer.colors.YELLOW)

        if staleness["external_detected"]:
            typer.echo()
            typer.secho(
                "⚠️  External test runs detected!",
                fg=typer.colors.YELLOW,
                bold=True,
            )
            typer.echo("  Run 'idlergear test sync' to import them.")


# Documentation generation commands
@docs_app.command("generate")
def docs_generate(
    ctx: typer.Context,
    package: str = typer.Argument(..., help="Python package name to document"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file path (default: stdout)"
    ),
    format: str = typer.Option(
        "json", "--format", "-f", help="Output format: json, markdown"
    ),
    include_private: bool = typer.Option(
        False, "--private", "-p", help="Include private modules"
    ),
    max_depth: Optional[int] = typer.Option(
        None, "--depth", "-d", help="Maximum submodule depth"
    ),
):
    """Generate API documentation for a Python package.

    Requires pdoc: pip install 'idlergear[docs]'

    Examples:
        idlergear docs generate mypackage
        idlergear docs generate mypackage -f markdown -o docs/api.md
        idlergear docs generate mypackage --depth 2
    """
    from idlergear.docs import (
        check_pdoc_available,
        generate_docs_json,
        generate_docs_markdown,
    )

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN

    if not check_pdoc_available():
        if output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps(
                    {
                        "error": "pdoc not installed",
                        "install": "pip install 'idlergear[docs]'",
                    }
                )
            )
        else:
            typer.secho(
                "pdoc is not installed. Install with: pip install 'idlergear[docs]'",
                fg=typer.colors.RED,
            )
        raise typer.Exit(1)

    try:
        if format == "markdown":
            result = generate_docs_markdown(
                package, include_private=include_private, max_depth=max_depth
            )
        else:
            result = generate_docs_json(
                package, include_private=include_private, max_depth=max_depth
            )

        if output:
            Path(output).write_text(result)
            if output_format == OutputFormat.JSON:
                typer.echo(json.dumps({"status": "success", "output": output}))
            else:
                typer.secho(f"Documentation written to {output}", fg=typer.colors.GREEN)
        else:
            typer.echo(result)

    except ModuleNotFoundError as e:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"error": str(e)}))
        else:
            typer.secho(f"Module not found: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except Exception as e:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"error": str(e)}))
        else:
            typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@docs_app.command("module")
def docs_module(
    ctx: typer.Context,
    module: str = typer.Argument(..., help="Python module name to document"),
):
    """Generate documentation for a single Python module.

    Examples:
        idlergear docs module idlergear.tasks
        idlergear docs module json
    """
    from idlergear.docs import check_pdoc_available, generate_module_docs

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN

    if not check_pdoc_available():
        if output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps(
                    {
                        "error": "pdoc not installed",
                        "install": "pip install 'idlergear[docs]'",
                    }
                )
            )
        else:
            typer.secho(
                "pdoc is not installed. Install with: pip install 'idlergear[docs]'",
                fg=typer.colors.RED,
            )
        raise typer.Exit(1)

    try:
        doc = generate_module_docs(module)

        if output_format == OutputFormat.JSON:
            typer.echo(doc.to_json())
        else:
            typer.secho(f"Module: {doc.name}", bold=True)
            if doc.docstring:
                typer.echo()
                # First paragraph only
                first_para = doc.docstring.split("\n\n")[0]
                typer.echo(first_para)

            if doc.functions:
                typer.echo()
                typer.secho("Functions:", bold=True)
                for func in doc.functions:
                    typer.echo(f"  {func.name}{func.signature}")

            if doc.classes:
                typer.echo()
                typer.secho("Classes:", bold=True)
                for cls in doc.classes:
                    bases = f"({', '.join(cls.bases)})" if cls.bases else ""
                    typer.echo(f"  {cls.name}{bases}")

            if doc.submodules:
                typer.echo()
                typer.secho("Submodules:", bold=True)
                for sub in doc.submodules:
                    typer.echo(f"  {sub}")

    except ModuleNotFoundError as e:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"error": str(e)}))
        else:
            typer.secho(f"Module not found: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except Exception as e:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"error": str(e)}))
        else:
            typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@docs_app.command("check")
def docs_check(
    ctx: typer.Context,
    lang: str = typer.Option(
        "all", "--lang", "-l", help="Language to check: python, rust, dotnet, all"
    ),
):
    """Check if documentation generation is available.

    Checks if pdoc (Python), cargo (Rust), and dotnet (.NET) are installed.
    """
    from idlergear.docs import check_pdoc_available
    from idlergear.docs_rust import check_cargo_available
    from idlergear.docs_dotnet import check_dotnet_available

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN

    result: dict[str, dict[str, bool]] = {}
    if lang in ("python", "all"):
        result["python"] = {"available": check_pdoc_available()}
    if lang in ("rust", "all"):
        result["rust"] = {"available": check_cargo_available()}
    if lang in ("dotnet", "all"):
        result["dotnet"] = {"available": check_dotnet_available()}

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps(result))
    else:
        if "python" in result:
            if result["python"]["available"]:
                typer.secho("✓ Python (pdoc) is installed", fg=typer.colors.GREEN)
            else:
                typer.secho("✗ Python (pdoc) is not installed", fg=typer.colors.RED)
                typer.echo("  Install with: pip install 'idlergear[docs]'")
        if "rust" in result:
            if result["rust"]["available"]:
                typer.secho("✓ Rust (cargo) is installed", fg=typer.colors.GREEN)
            else:
                typer.secho("✗ Rust (cargo) is not installed", fg=typer.colors.RED)
                typer.echo("  Install from: https://rustup.rs/")
        if "dotnet" in result:
            if result["dotnet"]["available"]:
                typer.secho("✓ .NET (dotnet) is installed", fg=typer.colors.GREEN)
            else:
                typer.secho("✗ .NET (dotnet) is not installed", fg=typer.colors.RED)
                typer.echo("  Install from: https://dotnet.microsoft.com/")


@docs_app.command("summary")
def docs_summary(
    ctx: typer.Context,
    package: str = typer.Argument(..., help="Package name or path to summarize"),
    mode: str = typer.Option(
        "standard", "--mode", "-m", help="Summary mode: minimal, standard, detailed"
    ),
    lang: str = typer.Option(
        "auto", "--lang", "-l", help="Language: python, rust, dotnet, auto"
    ),
    include_private: bool = typer.Option(
        False, "--private", "-p", help="Include private modules"
    ),
    max_depth: Optional[int] = typer.Option(
        None, "--depth", "-d", help="Maximum submodule depth"
    ),
):
    """Generate token-efficient API summary for AI consumption.

    Supports Python, Rust, and .NET projects with auto-detection.

    Summary modes:
    - minimal: ~500 tokens - function/class names only
    - standard: ~2000 tokens - first-line docstrings
    - detailed: ~5000 tokens - full docstrings, parameters

    Examples:
        idlergear docs summary idlergear --mode minimal
        idlergear docs summary requests --mode standard --depth 1
        idlergear docs summary /path/to/rust/project --lang rust
        idlergear docs summary /path/to/dotnet/project --lang dotnet
        idlergear docs summary . --lang auto  # Auto-detect language
    """
    from pathlib import Path
    from idlergear.docs import (
        check_pdoc_available,
        generate_summary_json,
        detect_python_project,
    )
    from idlergear.docs_rust import (
        detect_rust_project,
        generate_rust_summary_json,
    )
    from idlergear.docs_dotnet import (
        detect_dotnet_project,
        find_xml_docs,
        parse_xml_docs,
        generate_dotnet_summary,
    )

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN

    if mode not in ("minimal", "standard", "detailed"):
        typer.secho(f"Invalid mode: {mode}. Use minimal, standard, or detailed.")
        raise typer.Exit(1)

    # Auto-detect language if needed
    detected_lang = lang
    if lang == "auto":
        path = Path(package)
        if path.exists():
            rust_project = detect_rust_project(path)
            if rust_project["detected"]:
                detected_lang = "rust"
            else:
                dotnet_project = detect_dotnet_project(path)
                if dotnet_project["detected"]:
                    detected_lang = "dotnet"
                else:
                    python_project = detect_python_project(path)
                    if python_project["detected"]:
                        detected_lang = "python"
                    else:
                        detected_lang = "python"  # Default
        else:
            # Assume it's a Python module name
            detected_lang = "python"

    try:
        if detected_lang == "rust":
            result = generate_rust_summary_json(package, mode=mode)  # type: ignore
            typer.echo(result)
        elif detected_lang == "dotnet":
            path = Path(package)
            xml_docs = find_xml_docs(path)
            if not xml_docs:
                if output_format == OutputFormat.JSON:
                    typer.echo(
                        json.dumps(
                            {
                                "error": "No XML documentation files found",
                                "hint": "Build with <GenerateDocumentationFile>true</GenerateDocumentationFile>",
                            }
                        )
                    )
                else:
                    typer.secho(
                        "No XML documentation files found.",
                        fg=typer.colors.RED,
                    )
                    typer.echo("  Build with: dotnet build -p:GenerateDocumentationFile=true")
                raise typer.Exit(1)

            # Parse first XML docs file
            assembly = parse_xml_docs(xml_docs[0])
            summary = generate_dotnet_summary(assembly, mode=mode)
            typer.echo(json.dumps(summary, indent=2))
        else:
            if not check_pdoc_available():
                if output_format == OutputFormat.JSON:
                    typer.echo(
                        json.dumps(
                            {
                                "error": "pdoc not installed",
                                "install": "pip install 'idlergear[docs]'",
                            }
                        )
                    )
                else:
                    typer.secho(
                        "pdoc is not installed. Install with: pip install 'idlergear[docs]'",
                        fg=typer.colors.RED,
                    )
                raise typer.Exit(1)

            result = generate_summary_json(
                package,
                mode=mode,  # type: ignore
                include_private=include_private,
                max_depth=max_depth,
            )
            typer.echo(result)

    except Exception as e:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"error": str(e)}))
        else:
            typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@docs_app.command("build")
def docs_build(
    ctx: typer.Context,
    package: str = typer.Argument(
        None, help="Package name or path (auto-detects if not provided)"
    ),
    lang: str = typer.Option(
        "auto", "--lang", "-l", help="Language: python, rust, dotnet, auto"
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (Python: docs/api, Rust: target/doc, .NET: docs/api)",
    ),
    open_browser: bool = typer.Option(
        False, "--open", help="Open docs in browser after build"
    ),
    logo: Optional[str] = typer.Option(
        None, "--logo", help="Path to logo image (Python only)"
    ),
    favicon: Optional[str] = typer.Option(
        None, "--favicon", help="Path to favicon (Python only)"
    ),
    configuration: str = typer.Option(
        "Debug", "--config", "-c", help="Build configuration (.NET only)"
    ),
):
    """Build HTML documentation.

    Uses pdoc for Python, cargo doc for Rust, dotnet build for .NET.
    Auto-detects project language if not specified.

    Examples:
        idlergear docs build                    # Auto-detect package
        idlergear docs build mypackage          # Explicit Python package
        idlergear docs build . --lang rust      # Rust project in current dir
        idlergear docs build . --lang dotnet    # .NET project in current dir
        idlergear docs build --open             # Build and open in browser
    """
    from pathlib import Path
    from idlergear.docs import (
        build_html_docs,
        check_pdoc_available,
        detect_python_project,
    )
    from idlergear.docs_rust import (
        build_rust_docs,
        check_cargo_available,
        detect_rust_project,
    )
    from idlergear.docs_dotnet import (
        build_dotnet_docs,
        check_dotnet_available,
        detect_dotnet_project,
    )

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN

    # Auto-detect language if needed
    detected_lang = lang
    if lang == "auto":
        path = Path(package) if package else Path(".")
        rust_project = detect_rust_project(path)
        if rust_project["detected"]:
            detected_lang = "rust"
        else:
            dotnet_project = detect_dotnet_project(path)
            if dotnet_project["detected"]:
                detected_lang = "dotnet"
            else:
                detected_lang = "python"

    if detected_lang == "rust":
        if not check_cargo_available():
            if output_format == OutputFormat.JSON:
                typer.echo(json.dumps({"error": "cargo not found"}))
            else:
                typer.secho(
                    "cargo is not found. Install from https://rustup.rs/",
                    fg=typer.colors.RED,
                )
            raise typer.Exit(1)

        path = Path(package) if package else Path(".")
        if output_format != OutputFormat.JSON:
            typer.echo(f"Building Rust docs for: {path}")

        result = build_rust_docs(path, open_browser=open_browser)

        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps(result))
        else:
            if result["success"]:
                typer.secho("✓ Documentation built successfully", fg=typer.colors.GREEN)
                typer.echo(f"  Output: {result['output_dir']}")
                typer.echo(f"  Files: {result['count']}")
            else:
                typer.secho(
                    f"✗ Build failed: {result.get('error')}", fg=typer.colors.RED
                )
                raise typer.Exit(1)
    elif detected_lang == "dotnet":
        if not check_dotnet_available():
            if output_format == OutputFormat.JSON:
                typer.echo(json.dumps({"error": "dotnet not found"}))
            else:
                typer.secho(
                    "dotnet is not found. Install from https://dotnet.microsoft.com/",
                    fg=typer.colors.RED,
                )
            raise typer.Exit(1)

        path = Path(package) if package else Path(".")
        if output_format != OutputFormat.JSON:
            typer.echo(f"Building .NET docs for: {path}")

        result = build_dotnet_docs(path, configuration=configuration)

        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps(result))
        else:
            if result["success"]:
                typer.secho("✓ XML documentation built successfully", fg=typer.colors.GREEN)
                typer.echo(f"  XML files: {len(result.get('xml_files', []))}")
                for xml_file in result.get("xml_files", []):
                    typer.echo(f"    - {xml_file}")
            else:
                errors = result.get("errors", ["Unknown error"])
                typer.secho(f"✗ Build failed: {errors[0]}", fg=typer.colors.RED)
                raise typer.Exit(1)
    else:
        if not check_pdoc_available():
            if output_format == OutputFormat.JSON:
                typer.echo(
                    json.dumps(
                        {
                            "error": "pdoc not installed",
                            "install": "pip install 'idlergear[docs]'",
                        }
                    )
                )
            else:
                typer.secho(
                    "pdoc is not installed. Install with: pip install 'idlergear[docs]'",
                    fg=typer.colors.RED,
                )
            raise typer.Exit(1)

        # Auto-detect package if not provided
        if not package:
            project = detect_python_project()
            if project.get("packages"):
                package = project["packages"][0]
                if output_format != OutputFormat.JSON:
                    typer.echo(f"Detected package: {package}")
            else:
                if output_format == OutputFormat.JSON:
                    typer.echo(json.dumps({"error": "Could not detect Python package"}))
                else:
                    typer.secho(
                        "Could not detect Python package. Specify one explicitly.",
                        fg=typer.colors.RED,
                    )
                raise typer.Exit(1)

        output_dir = output or "docs/api"
        result = build_html_docs(
            package, output_dir=output_dir, logo=logo, favicon=favicon
        )

        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps(result))
        else:
            if result["success"]:
                typer.secho("✓ Documentation built successfully", fg=typer.colors.GREEN)
                typer.echo(f"  Output: {result['output_dir']}")
                typer.echo(f"  Files: {result['count']}")
            else:
                typer.secho(
                    f"✗ Build failed: {result.get('error')}", fg=typer.colors.RED
                )
                raise typer.Exit(1)


@docs_app.command("serve")
def docs_serve(
    ctx: typer.Context,
    docs_dir: str = typer.Argument(
        "docs/api", help="Directory containing HTML documentation"
    ),
    port: int = typer.Option(8080, "--port", "-p", help="Port to serve on"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser"),
):
    """Serve HTML documentation locally for preview.

    Examples:
        idlergear docs serve                    # Serve docs/api on port 8080
        idlergear docs serve --port 9000        # Custom port
        idlergear docs serve ./my-docs          # Custom directory
    """
    import http.server
    import socketserver

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN
    docs_path = Path(docs_dir)

    if not docs_path.exists():
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"error": f"Directory not found: {docs_path}"}))
        else:
            typer.secho(f"Directory not found: {docs_path}", fg=typer.colors.RED)
            typer.echo("  Run 'idlergear docs build' first to generate documentation.")
        raise typer.Exit(1)

    # Check if docs exist
    html_files = list(docs_path.glob("*.html"))
    if not html_files:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"error": f"No HTML files in {docs_path}"}))
        else:
            typer.secho(f"No HTML files found in {docs_path}", fg=typer.colors.RED)
            typer.echo("  Run 'idlergear docs build' first to generate documentation.")
        raise typer.Exit(1)

    url = f"http://{host}:{port}"

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(docs_path), **kwargs)

        def log_message(self, format, *args):
            if output_format != OutputFormat.JSON:
                typer.echo(f"  {args[0]}")

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"url": url, "docs_dir": str(docs_path.absolute())}))
    else:
        typer.secho(f"Serving documentation at {url}", fg=typer.colors.GREEN)
        typer.echo(f"  Directory: {docs_path.absolute()}")
        typer.echo("  Press Ctrl+C to stop")

    if not no_browser:
        import threading
        import webbrowser

        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        with socketserver.TCPServer((host, port), Handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        if output_format != OutputFormat.JSON:
            typer.echo("\nServer stopped.")
    except OSError as e:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"error": str(e)}))
        else:
            typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@docs_app.command("detect")
def docs_detect(
    ctx: typer.Context,
    path: str = typer.Argument(".", help="Project directory to analyze"),
):
    """Detect project for documentation.

    Detects Python, Rust, and .NET projects, showing package name, version,
    source directory, and configuration.

    Examples:
        idlergear docs detect
        idlergear docs detect /path/to/project
    """
    from idlergear.docs import detect_python_project
    from idlergear.docs_rust import detect_rust_project
    from idlergear.docs_dotnet import detect_dotnet_project

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN

    # Check Rust first, then .NET, then Python
    rust_result = detect_rust_project(path)
    if rust_result["detected"]:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps(rust_result))
        else:
            typer.secho("✓ Rust project detected", fg=typer.colors.GREEN)
            if rust_result.get("name"):
                typer.echo(f"  Name: {rust_result['name']}")
            if rust_result.get("version"):
                typer.echo(f"  Version: {rust_result['version']}")
            if rust_result.get("edition"):
                typer.echo(f"  Edition: {rust_result['edition']}")
            if rust_result.get("config_file"):
                typer.echo(f"  Config: {rust_result['config_file']}")
            if rust_result.get("source_dir"):
                typer.echo(f"  Source: {rust_result['source_dir']}/")
            if rust_result.get("crate_type"):
                typer.echo(f"  Type: {rust_result['crate_type']}")
            if rust_result.get("is_workspace"):
                typer.echo("  Workspace: yes")
                if rust_result.get("workspace_members"):
                    typer.echo(
                        f"  Members: {', '.join(rust_result['workspace_members'])}"
                    )
        return

    dotnet_result = detect_dotnet_project(path)
    if dotnet_result["detected"]:
        dotnet_result["language"] = "dotnet"
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps(dotnet_result))
        else:
            typer.secho("✓ .NET project detected", fg=typer.colors.GREEN)
            if dotnet_result.get("name"):
                typer.echo(f"  Name: {dotnet_result['name']}")
            if dotnet_result.get("config_file"):
                typer.echo(f"  Config: {dotnet_result['config_file']}")
            if dotnet_result.get("projects"):
                typer.echo(f"  Projects: {len(dotnet_result['projects'])}")
                for proj in dotnet_result["projects"][:5]:  # Limit display
                    typer.echo(f"    - {proj['name']} ({proj['type']})")
            if dotnet_result.get("target_frameworks"):
                typer.echo(
                    f"  Frameworks: {', '.join(dotnet_result['target_frameworks'])}"
                )
            if dotnet_result.get("xml_docs"):
                typer.echo(f"  XML docs: {len(dotnet_result['xml_docs'])} files")
        return

    python_result = detect_python_project(path)
    if python_result["detected"]:
        python_result["language"] = "python"
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps(python_result))
        else:
            typer.secho("✓ Python project detected", fg=typer.colors.GREEN)
            if python_result.get("name"):
                typer.echo(f"  Name: {python_result['name']}")
            if python_result.get("version"):
                typer.echo(f"  Version: {python_result['version']}")
            if python_result.get("config_file"):
                typer.echo(f"  Config: {python_result['config_file']}")
            if python_result.get("source_dir"):
                typer.echo(f"  Source: {python_result['source_dir']}/")
            if python_result.get("packages"):
                typer.echo(f"  Packages: {', '.join(python_result['packages'])}")
        return

    # None detected
    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"path": path, "detected": False}))
    else:
        typer.secho(
            "✗ No Python, Rust, or .NET project detected", fg=typer.colors.YELLOW
        )
        typer.echo(f"  Path: {path}")


# Self-update commands
@app.command()
def update(
    ctx: typer.Context,
    check: bool = typer.Option(
        False, "--check", "-c", help="Only check for updates, don't install"
    ),
    version: Optional[str] = typer.Option(
        None, "--version", "-v", help="Install specific version"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be done without doing it"
    ),
    no_cache: bool = typer.Option(
        False, "--no-cache", help="Skip version cache, always query GitHub"
    ),
):
    """Check for updates and upgrade IdlerGear itself.

    Examples:
        idlergear update --check    # Check for available updates
        idlergear update            # Upgrade to latest version
        idlergear update -v 0.3.20  # Install specific version
        idlergear update --dry-run  # Show what would happen
    """
    from idlergear.selfupdate import (
        get_latest_version,
        detect_install_method,
        do_self_update,
    )

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN

    # Get version info
    version_info = get_latest_version(use_cache=not no_cache)

    if version_info.error:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"error": version_info.error}))
        else:
            typer.secho(
                f"Error checking version: {version_info.error}", fg=typer.colors.RED
            )
        raise typer.Exit(1)

    # Get install info
    install_info = detect_install_method()

    if check:
        # Just show version info
        if output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps(
                    {
                        "current_version": version_info.current,
                        "latest_version": version_info.latest,
                        "update_available": version_info.update_available,
                        "install_method": install_info.method.value,
                        "can_upgrade": install_info.can_upgrade,
                        "upgrade_command": install_info.upgrade_command,
                    }
                )
            )
        else:
            typer.echo(f"Current version: {version_info.current}")
            typer.echo(f"Latest version:  {version_info.latest}")
            typer.echo()
            if version_info.update_available:
                typer.secho("Update available!", fg=typer.colors.GREEN)
            else:
                typer.echo("Already at latest version.")
            typer.echo()
            typer.echo(f"Install method:  {install_info.method.value}")
            if install_info.can_upgrade:
                typer.echo(f"Upgrade command: {install_info.upgrade_command}")
            else:
                typer.secho(f"Note: {install_info.message}", fg=typer.colors.YELLOW)
        return

    # Perform update
    if not version_info.update_available and version is None:
        if output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps(
                    {
                        "success": True,
                        "message": "Already at latest version",
                        "current_version": version_info.current,
                    }
                )
            )
        else:
            typer.echo(f"Already at latest version ({version_info.current})")
        return

    if not install_info.can_upgrade:
        if output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps(
                    {
                        "success": False,
                        "error": install_info.message,
                        "install_method": install_info.method.value,
                    }
                )
            )
        else:
            typer.secho(
                f"Cannot auto-upgrade: {install_info.message}", fg=typer.colors.RED
            )
            typer.echo()
            typer.echo(f"Manual upgrade: {install_info.upgrade_command}")
        raise typer.Exit(1)

    target_version = version or version_info.latest

    if dry_run:
        if output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps(
                    {
                        "dry_run": True,
                        "current_version": version_info.current,
                        "target_version": target_version,
                        "upgrade_command": install_info.upgrade_command,
                    }
                )
            )
        else:
            typer.echo(f"Would upgrade: {version_info.current} -> {target_version}")
            typer.echo(f"Command: {install_info.upgrade_command}")
        return

    # Confirm and run upgrade
    if output_format != OutputFormat.JSON:
        typer.echo(f"Upgrading IdlerGear: {version_info.current} -> {target_version}")
        typer.echo(f"Install method: {install_info.method.value}")
        typer.echo()

    result = do_self_update(version=version, dry_run=False)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps(result))
    else:
        if result["success"]:
            typer.secho(f"✓ {result['message']}", fg=typer.colors.GREEN)
        else:
            typer.secho(f"✗ {result['message']}", fg=typer.colors.RED)
            raise typer.Exit(1)


# ============================================================================
# Agents Commands (AGENTS.md generation)
# ============================================================================


@agents_app.command("init")
def agents_init(
    ctx: typer.Context,
    lang: Optional[str] = typer.Option(
        None,
        "--lang",
        "-l",
        help="Language (python, rust, javascript, go, java). Auto-detects if not specified.",
    ),
    with_claude: bool = typer.Option(
        True, "--with-claude/--no-claude", help="Also generate CLAUDE.md"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be generated without writing"
    ),
):
    """Initialize AGENTS.md with language-specific defaults.

    Auto-detects the project language if --lang is not specified.
    Generates build, test, lint, and format commands appropriate for the language.

    Examples:
        idlergear agents init              # Auto-detect language
        idlergear agents init --lang python
        idlergear agents init --dry-run
    """
    from pathlib import Path

    from idlergear.agents import (
        Language,
        TEMPLATES,
        detect_language,
        generate_agents_md,
        generate_claude_md,
    )
    from idlergear.config import find_idlergear_root

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN
    project_path = find_idlergear_root() or Path.cwd()

    # Detect or use specified language
    if lang:
        try:
            language = Language(lang.lower())
        except ValueError:
            if output_format == OutputFormat.JSON:
                typer.echo(
                    json.dumps(
                        {
                            "error": f"Unknown language: {lang}",
                            "supported": [
                                l.value for l in Language if l != Language.UNKNOWN
                            ],
                        }
                    )
                )
            else:
                typer.secho(f"Unknown language: {lang}", fg=typer.colors.RED)
                typer.echo(
                    f"Supported: {', '.join(l.value for l in Language if l != Language.UNKNOWN)}"
                )
            raise typer.Exit(1)
    else:
        language = detect_language(project_path)

    if language == Language.UNKNOWN:
        if output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps(
                    {
                        "error": "Could not detect language",
                        "hint": "Use --lang to specify",
                    }
                )
            )
        else:
            typer.secho("Could not detect project language.", fg=typer.colors.YELLOW)
            typer.echo("Use --lang to specify: python, rust, javascript, go, java")
        raise typer.Exit(1)

    template = TEMPLATES[language]

    # Generate content
    agents_content = generate_agents_md(template, include_idlergear=True)
    claude_content = (
        generate_claude_md(template, include_idlergear=True) if with_claude else None
    )

    if dry_run:
        if output_format == OutputFormat.JSON:
            result = {
                "dry_run": True,
                "language": language.value,
                "files": {"AGENTS.md": len(agents_content)},
            }
            if claude_content:
                result["files"]["CLAUDE.md"] = len(claude_content)
            typer.echo(json.dumps(result))
        else:
            typer.secho(
                f"Would generate for language: {language.value}", fg=typer.colors.CYAN
            )
            typer.echo()
            typer.secho("--- AGENTS.md ---", fg=typer.colors.YELLOW)
            typer.echo(
                agents_content[:500] + "..."
                if len(agents_content) > 500
                else agents_content
            )
            if claude_content:
                typer.echo()
                typer.secho("--- CLAUDE.md ---", fg=typer.colors.YELLOW)
                typer.echo(
                    claude_content[:300] + "..."
                    if len(claude_content) > 300
                    else claude_content
                )
        return

    # Write files
    agents_path = project_path / "AGENTS.md"
    created_agents = not agents_path.exists()
    agents_path.write_text(agents_content)

    created_claude = False
    if claude_content:
        claude_path = project_path / "CLAUDE.md"
        created_claude = not claude_path.exists()
        claude_path.write_text(claude_content)

    if output_format == OutputFormat.JSON:
        result = {
            "success": True,
            "language": language.value,
            "files": {
                "AGENTS.md": "created" if created_agents else "updated",
            },
        }
        if claude_content:
            result["files"]["CLAUDE.md"] = "created" if created_claude else "updated"
        typer.echo(json.dumps(result))
    else:
        typer.secho(f"✓ Generated for {language.value}", fg=typer.colors.GREEN)
        action = "Created" if created_agents else "Updated"
        typer.echo(f"  {action}: AGENTS.md")
        if claude_content:
            action = "Created" if created_claude else "Updated"
            typer.echo(f"  {action}: CLAUDE.md")


@agents_app.command("check")
def agents_check(
    ctx: typer.Context,
):
    """Validate existing AGENTS.md file.

    Checks for common issues like missing sections, empty code blocks, and TODOs.
    """
    from pathlib import Path

    from idlergear.agents import validate_agents_md
    from idlergear.config import find_idlergear_root

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN
    project_path = find_idlergear_root() or Path.cwd()

    agents_path = project_path / "AGENTS.md"

    if not agents_path.exists():
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"error": "AGENTS.md not found", "valid": False}))
        else:
            typer.secho("AGENTS.md not found.", fg=typer.colors.RED)
            typer.echo("Run 'idlergear agents init' to create one.")
        raise typer.Exit(1)

    content = agents_path.read_text()
    issues = validate_agents_md(content)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"valid": len(issues) == 0, "issues": issues}))
    else:
        if issues:
            typer.secho(f"Found {len(issues)} issue(s):", fg=typer.colors.YELLOW)
            for issue in issues:
                typer.echo(f"  - {issue}")
        else:
            typer.secho("✓ AGENTS.md is valid", fg=typer.colors.GREEN)


@agents_app.command("update")
def agents_update(
    ctx: typer.Context,
    lang: Optional[str] = typer.Option(
        None,
        "--lang",
        "-l",
        help="Language to update template for",
    ),
    preserve_custom: bool = typer.Option(
        True,
        "--preserve/--no-preserve",
        help="Preserve custom sections when updating",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would change without writing"
    ),
):
    """Update AGENTS.md with latest template while preserving customizations.

    Merges new template defaults with your existing customizations.
    Use --no-preserve to completely replace with fresh template.
    """
    from pathlib import Path

    from idlergear.agents import (
        Language,
        TEMPLATES,
        detect_language,
        update_agents_md,
        generate_agents_md,
    )
    from idlergear.config import find_idlergear_root

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN
    project_path = find_idlergear_root() or Path.cwd()

    agents_path = project_path / "AGENTS.md"

    if not agents_path.exists():
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"error": "AGENTS.md not found"}))
        else:
            typer.secho("AGENTS.md not found.", fg=typer.colors.RED)
            typer.echo("Run 'idlergear agents init' to create one.")
        raise typer.Exit(1)

    # Determine language
    if lang:
        try:
            language = Language(lang.lower())
        except ValueError:
            if output_format == OutputFormat.JSON:
                typer.echo(json.dumps({"error": f"Unknown language: {lang}"}))
            else:
                typer.secho(f"Unknown language: {lang}", fg=typer.colors.RED)
            raise typer.Exit(1)
    else:
        language = detect_language(project_path)

    if language == Language.UNKNOWN:
        if output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps({"error": "Could not detect language", "hint": "Use --lang"})
            )
        else:
            typer.secho(
                "Could not detect language. Use --lang.", fg=typer.colors.YELLOW
            )
        raise typer.Exit(1)

    template = TEMPLATES[language]
    existing_content = agents_path.read_text()

    if preserve_custom:
        new_content = update_agents_md(existing_content, template, preserve_custom=True)
    else:
        new_content = generate_agents_md(template, include_idlergear=True)

    if dry_run:
        if output_format == OutputFormat.JSON:
            typer.echo(
                json.dumps(
                    {
                        "dry_run": True,
                        "language": language.value,
                        "preserve_custom": preserve_custom,
                        "would_change": existing_content != new_content,
                    }
                )
            )
        else:
            if existing_content == new_content:
                typer.echo("No changes needed.")
            else:
                typer.secho("Would update AGENTS.md", fg=typer.colors.CYAN)
                typer.echo(f"  Language: {language.value}")
                typer.echo(f"  Preserve custom: {preserve_custom}")
        return

    if existing_content == new_content:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"success": True, "changed": False}))
        else:
            typer.echo("AGENTS.md is already up to date.")
        return

    agents_path.write_text(new_content)

    if output_format == OutputFormat.JSON:
        typer.echo(
            json.dumps({"success": True, "changed": True, "language": language.value})
        )
    else:
        typer.secho("✓ Updated AGENTS.md", fg=typer.colors.GREEN)


@agents_app.command("show")
def agents_show(
    ctx: typer.Context,
):
    """Show detected language and available templates."""
    from pathlib import Path

    from idlergear.agents import Language, TEMPLATES, detect_language
    from idlergear.config import find_idlergear_root

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN
    project_path = find_idlergear_root() or Path.cwd()

    detected = detect_language(project_path)
    agents_exists = (project_path / "AGENTS.md").exists()
    claude_exists = (project_path / "CLAUDE.md").exists()

    if output_format == OutputFormat.JSON:
        typer.echo(
            json.dumps(
                {
                    "detected_language": detected.value
                    if detected != Language.UNKNOWN
                    else None,
                    "agents_md_exists": agents_exists,
                    "claude_md_exists": claude_exists,
                    "available_templates": [
                        l.value for l in Language if l != Language.UNKNOWN
                    ],
                }
            )
        )
    else:
        typer.secho("Project Status:", fg=typer.colors.CYAN, bold=True)
        if detected != Language.UNKNOWN:
            typer.echo(f"  Detected language: {detected.value}")
        else:
            typer.echo("  Detected language: (unknown)")
        typer.echo(f"  AGENTS.md: {'exists' if agents_exists else 'not found'}")
        typer.echo(f"  CLAUDE.md: {'exists' if claude_exists else 'not found'}")
        typer.echo()
        typer.secho("Available Templates:", fg=typer.colors.CYAN, bold=True)
        for lang in Language:
            if lang != Language.UNKNOWN:
                template = TEMPLATES[lang]
                commands = ", ".join(template.commands.keys())
                typer.echo(f"  {lang.value}: {commands}")


# Secrets commands
@secrets_app.command("init")
def secrets_init(
    ctx: typer.Context,
):
    """Initialize secrets store for this project.

    Creates an encrypted secrets store for the current project.
    You will be prompted for a master password.
    """
    from getpass import getpass
    from pathlib import Path

    from idlergear.config import find_idlergear_root
    from idlergear.secrets import SecretsManager

    project_path = find_idlergear_root() or Path.cwd()
    manager = SecretsManager(project_path)

    if manager.is_initialized():
        typer.secho("Secrets store already initialized.", fg=typer.colors.YELLOW)
        raise typer.Exit(0)

    # Prompt for password
    typer.echo("Create a master password for encrypting secrets.")
    typer.echo("This password will be required to access secrets.")
    typer.echo()

    password = getpass("Master password: ")
    if not password:
        typer.secho("Password cannot be empty.", fg=typer.colors.RED)
        raise typer.Exit(1)

    confirm = getpass("Confirm password: ")
    if password != confirm:
        typer.secho("Passwords do not match.", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        manager.initialize(password)
        typer.secho("Secrets store initialized.", fg=typer.colors.GREEN)
        typer.echo(f"Project ID: {manager._get_or_create_project_id()}")
    except RuntimeError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@secrets_app.command("set")
def secrets_set(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Secret name (e.g., API_KEY)"),
    value: Optional[str] = typer.Option(
        None, "--value", "-v", help="Secret value (prompts if not provided)"
    ),
    from_file: Optional[Path] = typer.Option(
        None, "--from-file", "-f", help="Read value from file"
    ),
):
    """Set a secret value.

    Prompts for the value if not provided via --value or --from-file.
    Using --value is not recommended as it may appear in shell history.
    """
    from getpass import getpass
    from pathlib import Path

    from idlergear.config import find_idlergear_root
    from idlergear.secrets import SecretsManager

    project_path = find_idlergear_root() or Path.cwd()
    manager = SecretsManager(project_path)

    if not manager.is_initialized():
        typer.secho(
            "Secrets store not initialized. Run 'idlergear secrets init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    # Get password
    password = getpass("Master password: ")
    if not manager.unlock(password):
        typer.secho("Invalid password.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Get value
    if from_file:
        if not from_file.exists():
            typer.secho(f"File not found: {from_file}", fg=typer.colors.RED)
            raise typer.Exit(1)
        secret_value = from_file.read_text().strip()
    elif value:
        typer.secho(
            "Warning: Using --value may expose the secret in shell history.",
            fg=typer.colors.YELLOW,
        )
        secret_value = value
    else:
        secret_value = getpass(f"Enter value for {name}: ")

    if not secret_value:
        typer.secho("Value cannot be empty.", fg=typer.colors.RED)
        raise typer.Exit(1)

    entry = manager.set(name, secret_value)
    typer.secho(f"Set secret: {name}", fg=typer.colors.GREEN)


@secrets_app.command("get")
def secrets_get(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Secret name"),
):
    """Get a secret value (for scripting).

    Outputs the secret value to stdout without any decoration.
    Useful for piping to other commands.
    """
    from getpass import getpass
    from pathlib import Path
    import sys

    from idlergear.config import find_idlergear_root
    from idlergear.secrets import SecretsManager

    project_path = find_idlergear_root() or Path.cwd()
    manager = SecretsManager(project_path)

    if not manager.is_initialized():
        typer.secho("Secrets store not initialized.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    # Read password from stdin if piped, otherwise prompt
    if sys.stdin.isatty():
        password = getpass("Master password: ")
    else:
        # When piping, we can't prompt - this is a limitation
        typer.secho(
            "Cannot prompt for password in non-interactive mode.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    if not manager.unlock(password):
        typer.secho("Invalid password.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    value = manager.get(name)
    if value is None:
        typer.secho(f"Secret not found: {name}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    # Output value without newline for piping
    typer.echo(value, nl=False)


@secrets_app.command("list")
def secrets_list(
    ctx: typer.Context,
):
    """List all secrets (names only, never values)."""
    from getpass import getpass
    from pathlib import Path
    from datetime import datetime

    from idlergear.config import find_idlergear_root
    from idlergear.secrets import SecretsManager

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN
    project_path = find_idlergear_root() or Path.cwd()
    manager = SecretsManager(project_path)

    if not manager.is_initialized():
        typer.secho(
            "Secrets store not initialized. Run 'idlergear secrets init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    password = getpass("Master password: ")
    if not manager.unlock(password):
        typer.secho("Invalid password.", fg=typer.colors.RED)
        raise typer.Exit(1)

    entries = manager.list()

    if output_format == OutputFormat.JSON:
        typer.echo(
            json.dumps(
                {
                    "secrets": [
                        {
                            "name": e.name,
                            "created_at": e.created_at.isoformat(),
                            "updated_at": e.updated_at.isoformat(),
                        }
                        for e in entries
                    ]
                }
            )
        )
    else:
        if not entries:
            typer.echo("No secrets stored.")
            return

        typer.secho("Secrets:", fg=typer.colors.CYAN, bold=True)
        for entry in sorted(entries, key=lambda e: e.name):
            # Calculate relative time
            age = datetime.now() - entry.updated_at
            if age.days > 0:
                age_str = f"{age.days} day{'s' if age.days > 1 else ''} ago"
            elif age.seconds > 3600:
                hours = age.seconds // 3600
                age_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif age.seconds > 60:
                mins = age.seconds // 60
                age_str = f"{mins} minute{'s' if mins > 1 else ''} ago"
            else:
                age_str = "just now"

            typer.echo(f"  {entry.name:<30} [set {age_str}]")


@secrets_app.command("delete")
def secrets_delete(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Secret name to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a secret."""
    from getpass import getpass
    from pathlib import Path

    from idlergear.config import find_idlergear_root
    from idlergear.secrets import SecretsManager

    project_path = find_idlergear_root() or Path.cwd()
    manager = SecretsManager(project_path)

    if not manager.is_initialized():
        typer.secho("Secrets store not initialized.", fg=typer.colors.RED)
        raise typer.Exit(1)

    password = getpass("Master password: ")
    if not manager.unlock(password):
        typer.secho("Invalid password.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not manager.exists(name):
        typer.secho(f"Secret not found: {name}", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not yes and not typer.confirm(f"Delete secret '{name}'?"):
        raise typer.Exit(0)

    manager.delete(name)
    typer.secho(f"Deleted: {name}", fg=typer.colors.GREEN)


@secrets_app.command("export")
def secrets_export(
    ctx: typer.Context,
    output_path: Optional[Path] = typer.Argument(
        None, help="Output file path (default: stdout)"
    ),
):
    """Export secrets to .env format.

    WARNING: Creates an unencrypted file! Do not commit to version control.
    """
    from getpass import getpass
    from pathlib import Path

    from idlergear.config import find_idlergear_root
    from idlergear.secrets import SecretsManager

    project_path = find_idlergear_root() or Path.cwd()
    manager = SecretsManager(project_path)

    if not manager.is_initialized():
        typer.secho("Secrets store not initialized.", fg=typer.colors.RED)
        raise typer.Exit(1)

    password = getpass("Master password: ")
    if not manager.unlock(password):
        typer.secho("Invalid password.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if output_path:
        typer.secho(
            "WARNING: This will create an unencrypted file!",
            fg=typer.colors.YELLOW,
            err=True,
        )
        typer.secho(
            "Do NOT commit this file to version control.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        if not typer.confirm("Continue?"):
            raise typer.Exit(0)

        manager.export_env_file(output_path)
        typer.secho(f"Exported to {output_path}", fg=typer.colors.GREEN, err=True)
    else:
        # Output to stdout
        entries = manager.list()
        for entry in sorted(entries, key=lambda e: e.name):
            value = manager.get(entry.name)
            escaped = (
                value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            )
            typer.echo(f'{entry.name}="{escaped}"')


@secrets_app.command("import")
def secrets_import(
    ctx: typer.Context,
    env_file: Path = typer.Argument(..., help="Path to .env file"),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing secrets"
    ),
):
    """Import secrets from .env format file."""
    from getpass import getpass
    from pathlib import Path

    from idlergear.config import find_idlergear_root
    from idlergear.secrets import SecretsManager

    if not env_file.exists():
        typer.secho(f"File not found: {env_file}", fg=typer.colors.RED)
        raise typer.Exit(1)

    project_path = find_idlergear_root() or Path.cwd()
    manager = SecretsManager(project_path)

    if not manager.is_initialized():
        typer.secho(
            "Secrets store not initialized. Run 'idlergear secrets init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    password = getpass("Master password: ")
    if not manager.unlock(password):
        typer.secho("Invalid password.", fg=typer.colors.RED)
        raise typer.Exit(1)

    imported = manager.import_env_file(env_file, overwrite=overwrite)

    if imported:
        typer.secho(f"Imported {len(imported)} secret(s):", fg=typer.colors.GREEN)
        for name in imported:
            typer.echo(f"  {name}")
    else:
        typer.echo("No new secrets imported.")


@secrets_app.command("run")
def secrets_run(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show secrets that would be injected"
    ),
    command: list[str] = typer.Argument(None, help="Command to run"),
):
    """Run command with secrets injected as environment variables.

    Example:
        idlergear secrets run -- python app.py
        idlergear secrets run -- npm start
    """
    from getpass import getpass
    from pathlib import Path

    from idlergear.config import find_idlergear_root
    from idlergear.secrets import SecretsManager

    if not command:
        typer.secho("No command specified. Use -- before command.", fg=typer.colors.RED)
        typer.echo("Example: idlergear secrets run -- python app.py")
        raise typer.Exit(1)

    project_path = find_idlergear_root() or Path.cwd()
    manager = SecretsManager(project_path)

    if not manager.is_initialized():
        typer.secho("Secrets store not initialized.", fg=typer.colors.RED)
        raise typer.Exit(1)

    password = getpass("Master password: ")
    if not manager.unlock(password):
        typer.secho("Invalid password.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if dry_run:
        preview = manager.get_run_preview()
        if not preview:
            typer.echo("No secrets to inject.")
        else:
            typer.secho("Secrets that would be injected:", fg=typer.colors.CYAN)
            for name, masked in sorted(preview.items()):
                typer.echo(f"  {name}={masked}")
        return

    exit_code = manager.run_with_secrets(command)
    raise typer.Exit(exit_code)


# Release commands
@release_app.command("list")
def release_list(
    ctx: typer.Context,
    limit: int = typer.Option(
        10, "--limit", "-n", help="Maximum number of releases to show"
    ),
):
    """List releases from GitHub."""
    from idlergear.release import check_gh_installed, check_gh_auth, list_releases

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN

    if not check_gh_installed():
        typer.secho("GitHub CLI (gh) is not installed.", fg=typer.colors.RED)
        typer.echo("Install from: https://cli.github.com/")
        raise typer.Exit(1)

    if not check_gh_auth():
        typer.secho("Not authenticated with GitHub CLI.", fg=typer.colors.RED)
        typer.echo("Run: gh auth login")
        raise typer.Exit(1)

    try:
        releases = list_releases(limit=limit)
    except RuntimeError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"releases": [r.to_dict() for r in releases]}))
    else:
        if not releases:
            typer.echo("No releases found.")
            return

        typer.secho("Releases:", fg=typer.colors.CYAN, bold=True)
        for release in releases:
            status = []
            if release.is_draft:
                status.append("draft")
            if release.is_prerelease:
                status.append("prerelease")
            status_str = f" [{', '.join(status)}]" if status else ""

            date_str = ""
            if release.published_at:
                date_str = f" ({release.published_at.strftime('%Y-%m-%d')})"

            typer.echo(f"  {release.tag}{date_str}{status_str}")


@release_app.command("show")
def release_show(
    ctx: typer.Context,
    tag: str = typer.Argument(..., help="Release tag (e.g., v0.3.27)"),
):
    """Show details of a specific release."""
    from idlergear.release import check_gh_installed, check_gh_auth, get_release

    output_format = ctx.obj.output_format if ctx.obj else OutputFormat.HUMAN

    if not check_gh_installed():
        typer.secho("GitHub CLI (gh) is not installed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not check_gh_auth():
        typer.secho("Not authenticated with GitHub CLI.", fg=typer.colors.RED)
        raise typer.Exit(1)

    release = get_release(tag)
    if release is None:
        typer.secho(f"Release not found: {tag}", fg=typer.colors.RED)
        raise typer.Exit(1)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps(release.to_dict()))
    else:
        typer.secho(f"Release: {release.tag}", fg=typer.colors.CYAN, bold=True)
        if release.name != release.tag:
            typer.echo(f"  Title: {release.name}")
        if release.published_at:
            typer.echo(
                f"  Published: {release.published_at.strftime('%Y-%m-%d %H:%M')}"
            )
        if release.is_draft:
            typer.secho("  Status: Draft", fg=typer.colors.YELLOW)
        if release.is_prerelease:
            typer.secho("  Status: Pre-release", fg=typer.colors.YELLOW)
        if release.url:
            typer.echo(f"  URL: {release.url}")
        if release.body:
            typer.echo("")
            typer.secho("Notes:", bold=True)
            typer.echo(release.body)


@release_app.command("create")
def release_create(
    ctx: typer.Context,
    tag: str = typer.Argument(..., help="Release tag (e.g., v0.4.0)"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Release title"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Release notes"),
    notes_from_tasks: bool = typer.Option(
        False, "--notes-from-tasks", help="Generate notes from closed tasks"
    ),
    draft: bool = typer.Option(False, "--draft", help="Create as draft release"),
    prerelease: bool = typer.Option(False, "--prerelease", help="Mark as pre-release"),
    bump: bool = typer.Option(
        False, "--bump", help="Run version command before creating release"
    ),
    target: Optional[str] = typer.Option(
        None, "--target", help="Target branch or commit"
    ),
):
    """Create a new release on GitHub.

    Examples:
        idlergear release create v0.4.0
        idlergear release create v0.4.0 --notes "What's new..."
        idlergear release create v0.4.0 --notes-from-tasks
        idlergear release create v0.4.0 --draft
        idlergear release create v0.4.0 --bump
    """
    from idlergear.release import check_gh_installed, check_gh_auth, create_release

    if not check_gh_installed():
        typer.secho("GitHub CLI (gh) is not installed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not check_gh_auth():
        typer.secho("Not authenticated with GitHub CLI.", fg=typer.colors.RED)
        raise typer.Exit(1)

    success, message, url = create_release(
        tag=tag,
        title=title,
        notes=notes,
        notes_from_tasks=notes_from_tasks,
        draft=draft,
        prerelease=prerelease,
        bump=bump,
        target=target,
    )

    if success:
        typer.secho(message, fg=typer.colors.GREEN)
        if url:
            typer.echo(f"URL: {url}")
    else:
        typer.secho(message, fg=typer.colors.RED)
        raise typer.Exit(1)


@release_app.command("delete")
def release_delete(
    ctx: typer.Context,
    tag: str = typer.Argument(..., help="Release tag to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a release from GitHub."""
    from idlergear.release import check_gh_installed, check_gh_auth, delete_release

    if not check_gh_installed():
        typer.secho("GitHub CLI (gh) is not installed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not check_gh_auth():
        typer.secho("Not authenticated with GitHub CLI.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not yes:
        if not typer.confirm(f"Delete release {tag}?"):
            raise typer.Exit(0)

    success, message = delete_release(tag, yes=True)

    if success:
        typer.secho(message, fg=typer.colors.GREEN)
    else:
        typer.secho(message, fg=typer.colors.RED)
        raise typer.Exit(1)


@release_app.command("notes")
def release_notes(
    ctx: typer.Context,
    since: Optional[str] = typer.Option(
        None, "--since", help="Generate notes since this tag"
    ),
):
    """Generate release notes from closed tasks."""
    from idlergear.release import generate_notes_from_tasks

    notes = generate_notes_from_tasks(since_tag=since)
    typer.echo(notes)


# ==============================================================================
# PRIORITIES COMMANDS
# ==============================================================================

priorities_app = typer.Typer(help="Manage project priorities registry")
app.add_typer(priorities_app, name="priorities")


@priorities_app.command("show")
def priorities_show(
    ctx: typer.Context,
    tier: Optional[str] = typer.Option(None, "--tier", "-t", help="Filter by tier"),
    milestone: Optional[str] = typer.Option(
        None, "--milestone", "-m", help="Filter by milestone"
    ),
):
    """Show current priorities registry."""
    from idlergear.priorities import PrioritiesRegistry

    try:
        registry = PrioritiesRegistry.load()
    except (ValueError, FileNotFoundError):
        typer.secho(
            "No priorities registry found. Run 'idlergear priorities init' to create one.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(1)

    output_format = getattr(ctx.obj, "output_format", OutputFormat.HUMAN) if ctx.obj else OutputFormat.HUMAN

    if output_format == OutputFormat.JSON:
        typer.echo(registry.model_dump_json(indent=2, exclude_none=True))
        return

    # Human-readable output
    typer.secho("\n=== Project Priorities ===\n", fg=typer.colors.BRIGHT_CYAN, bold=True)
    typer.echo(f"Last updated: {registry.last_updated}\n")

    # Show feature areas
    typer.secho("Feature Areas:", fg=typer.colors.BRIGHT_GREEN, bold=True)
    for tier_name, features in registry.feature_areas.items():
        if tier and tier_name.value != tier:
            continue
        if not features:
            continue

        typer.secho(f"\n  {tier_name.value}:", fg=typer.colors.YELLOW)
        for feature in features:
            if milestone and feature.milestone != milestone:
                continue

            status_icon = "✅" if feature.status.value == "complete" else "⬜"
            typer.echo(
                f"    {status_icon} {feature.full_name} "
                f"({feature.completion}% - {feature.milestone or 'unplanned'})"
            )
            if feature.notes:
                typer.echo(f"       {feature.notes}")

    # Show backends
    typer.secho("\n\nBackends:", fg=typer.colors.BRIGHT_GREEN, bold=True)
    for tier_name, backends in registry.backends.items():
        if tier and tier_name.value != tier:
            continue
        if not backends:
            continue

        typer.secho(f"\n  {tier_name.value}:", fg=typer.colors.YELLOW)
        for backend in backends:
            status_icon = "✅" if backend.status.value == "complete" else "⬜"
            typer.echo(f"    {status_icon} {backend.name} ({backend.status.value})")
            if backend.features:
                for feature_name, feature_status in backend.features.items():
                    typer.echo(f"       - {feature_name}: {feature_status}")

    # Show AI assistants
    typer.secho("\n\nAI Assistants:", fg=typer.colors.BRIGHT_GREEN, bold=True)
    for tier_name, assistants in registry.ai_assistants.items():
        if tier and tier_name.value != tier:
            continue
        if not assistants:
            continue

        typer.secho(f"\n  {tier_name.value}:", fg=typer.colors.YELLOW)
        for assistant in assistants:
            status_icon = "✅" if assistant.status.value == "excellent" else "⚠️"
            typer.echo(f"    {status_icon} {assistant.name} ({assistant.status.value})")
            if assistant.context:
                typer.echo(f"       Context: {assistant.context}")


@priorities_app.command("init")
def priorities_init(
    ctx: typer.Context,
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing registry"
    ),
):
    """Initialize priorities registry with defaults."""
    from idlergear.priorities import PrioritiesRegistry
    from idlergear.config import find_idlergear_root

    root = find_idlergear_root()
    if not root:
        typer.secho(
            "Not in an IdlerGear project. Run 'idlergear init' first.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    priorities_file = root / ".idlergear" / "priorities.yaml"

    if priorities_file.exists() and not force:
        typer.secho(
            "Priorities registry already exists. Use --force to overwrite.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(1)

    registry = PrioritiesRegistry.create_default()
    registry.save(root)

    typer.secho(
        f"✅ Created priorities registry at {priorities_file}", fg=typer.colors.GREEN
    )


@priorities_app.command("matrix")
def priorities_matrix(ctx: typer.Context):
    """Show validation matrix."""
    from idlergear.priorities import PrioritiesRegistry

    try:
        registry = PrioritiesRegistry.load()
    except (ValueError, FileNotFoundError):
        typer.secho(
            "No priorities registry found. Run 'idlergear priorities init' to create one.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(1)

    output_format = getattr(ctx.obj, "output_format", OutputFormat.HUMAN) if ctx.obj else OutputFormat.HUMAN

    if output_format == OutputFormat.JSON:
        typer.echo(registry.validation_matrix.model_dump_json(indent=2))
        return

    # Human-readable matrix
    typer.secho(
        "\n=== Validation Matrix ===\n", fg=typer.colors.BRIGHT_CYAN, bold=True
    )

    # Backend × Feature matrix
    if registry.validation_matrix.backend_features:
        typer.secho("Backend × Feature:", fg=typer.colors.BRIGHT_GREEN, bold=True)
        for backend_name, features in registry.validation_matrix.backend_features.items():
            typer.secho(f"\n  {backend_name}:", fg=typer.colors.YELLOW)
            for feature_name, status in features.items():
                typer.echo(f"    {feature_name}: {status}")

    # Assistant × Feature matrix
    if registry.validation_matrix.assistant_features:
        typer.secho("\n\nAssistant × Feature:", fg=typer.colors.BRIGHT_GREEN, bold=True)
        for assistant_name, features in registry.validation_matrix.assistant_features.items():
            typer.secho(f"\n  {assistant_name}:", fg=typer.colors.YELLOW)
            for feature_name, status in features.items():
                typer.echo(f"    {feature_name}: {status}")


@priorities_app.command("coverage")
def priorities_coverage(ctx: typer.Context):
    """Show coverage requirements and status."""
    from idlergear.priorities import PrioritiesRegistry

    try:
        registry = PrioritiesRegistry.load()
    except (ValueError, FileNotFoundError):
        typer.secho(
            "No priorities registry found. Run 'idlergear priorities init' to create one.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(1)

    output_format = getattr(ctx.obj, "output_format", OutputFormat.HUMAN) if ctx.obj else OutputFormat.HUMAN

    if output_format == OutputFormat.JSON:
        typer.echo(registry.coverage_requirements.model_dump_json(indent=2))
        return

    # Human-readable coverage
    typer.secho(
        "\n=== Coverage Requirements ===\n", fg=typer.colors.BRIGHT_CYAN, bold=True
    )

    typer.secho("Tier 1 Feature:", fg=typer.colors.BRIGHT_GREEN, bold=True)
    for req in registry.coverage_requirements.tier_1_feature:
        typer.echo(f"  ✓ {req}")

    typer.secho("\nCritical Backend:", fg=typer.colors.BRIGHT_GREEN, bold=True)
    for req in registry.coverage_requirements.critical_backend:
        typer.echo(f"  ✓ {req}")


@priorities_app.command("validate")
def priorities_validate(
    ctx: typer.Context,
    milestone: Optional[str] = typer.Option(
        None, "--milestone", "-m", help="Validate specific milestone"
    ),
):
    """Check if ready for release based on requirements."""
    from idlergear.priorities import PrioritiesRegistry

    try:
        registry = PrioritiesRegistry.load()
    except (ValueError, FileNotFoundError):
        typer.secho(
            "No priorities registry found. Run 'idlergear priorities init' to create one.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(1)

    output_format = getattr(ctx.obj, "output_format", OutputFormat.HUMAN) if ctx.obj else OutputFormat.HUMAN

    # Calculate validation status
    ready = True
    issues = []

    # Check feature coverage
    tier_1_features = registry.feature_areas.get("tier_1", [])
    if milestone:
        tier_1_features = [f for f in tier_1_features if f.milestone == milestone]

    incomplete_features = [
        f for f in tier_1_features if f.status.value != "complete"
    ]
    if incomplete_features:
        ready = False
        for feature in incomplete_features:
            issues.append(
                f"Feature '{feature.full_name}' not complete ({feature.completion}%)"
            )

    # Check backend coverage
    critical_backends = registry.backends.get("critical", [])
    incomplete_backends = [
        b for b in critical_backends if b.status.value != "complete"
    ]
    if incomplete_backends:
        ready = False
        for backend in incomplete_backends:
            issues.append(f"Backend '{backend.name}' not complete ({backend.status.value})")

    # Check blocking bugs
    if registry.v1_0_requirements.bugs_blocking_release:
        ready = False
        issues.append(
            f"Blocking bugs: {', '.join(f'#{b}' for b in registry.v1_0_requirements.bugs_blocking_release)}"
        )

    if output_format == OutputFormat.JSON:
        result = {"ready": ready, "issues": issues}
        typer.echo(json.dumps(result, indent=2))
        return

    # Human-readable validation
    if milestone:
        typer.secho(
            f"\n=== Release Validation: {milestone} ===\n",
            fg=typer.colors.BRIGHT_CYAN,
            bold=True,
        )
    else:
        typer.secho(
            "\n=== Release Validation: v1.0 ===\n",
            fg=typer.colors.BRIGHT_CYAN,
            bold=True,
        )

    if ready:
        typer.secho("✅ READY FOR RELEASE", fg=typer.colors.GREEN, bold=True)
    else:
        typer.secho("🔴 NOT READY", fg=typer.colors.RED, bold=True)
        typer.echo("\nIssues:")
        for issue in issues:
            typer.secho(f"  ❌ {issue}", fg=typer.colors.RED)

    if not ready:
        raise typer.Exit(1)


# ==============================================================================
# DOCUMENTATION COVERAGE COMMANDS
# ==============================================================================


@app.command("doc-coverage")
def doc_coverage(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show all undocumented items"),
):
    """Check documentation coverage for MCP tools and CLI commands.

    Examples:
        idlergear doc-coverage              # Show coverage summary
        idlergear doc-coverage -v           # Show all undocumented items
    """
    from idlergear.doc_coverage import get_documentation_coverage, format_coverage_report

    try:
        coverage = get_documentation_coverage()
    except ValueError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)

    output_format = getattr(ctx.obj, "output_format", OutputFormat.HUMAN) if ctx.obj else OutputFormat.HUMAN

    if output_format == OutputFormat.JSON:
        result = {
            "mcp_tools": {
                "total": len(coverage.mcp_tools),
                "documented": len(coverage.documented_in_skills),
                "coverage": coverage.mcp_coverage_skills,
                "undocumented": [t.name for t in coverage.undocumented_mcp_tools],
            },
            "cli_commands": {
                "total": len(coverage.cli_commands),
                "documented": len(coverage.documented_in_readme),
                "coverage": coverage.cli_coverage_readme,
                "undocumented": [c.full_name for c in coverage.undocumented_cli_commands],
            },
        }
        typer.echo(json.dumps(result, indent=2))
    else:
        report = format_coverage_report(coverage, verbose=verbose)
        typer.echo(report)

    # Exit with error if coverage is poor
    if coverage.mcp_coverage_skills < 0.85 or coverage.cli_coverage_readme < 0.85:
        raise typer.Exit(1)


@app.command("monitor")
def monitor(
    session_file: str = typer.Option(None, "--file", "-f", help="Session file to monitor (auto-detect if not provided)"),
):
    """Monitor active session in real-time.

    Watch your Claude Code session as it happens. See tool calls,
    task operations, file changes, and more—all in a beautiful TUI.

    Shortcut for: idlergear session monitor
    Also available as standalone command: idlerwatch

    Examples:
        idlergear monitor                     # Monitor current session
        idlergear monitor --file /path/to/session.jsonl
        idlerwatch                              # Shortcut command
    """
    from pathlib import Path
    from idlergear.tui import run_monitor

    session_path = Path(session_file) if session_file else None

    try:
        run_monitor(session_path)
    except KeyboardInterrupt:
        pass


def monitor_shortcut():
    """Entry point for idlerwatch standalone command.

    This is a shortcut for: idlergear session monitor
    """
    import sys

    # Show help if requested
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""idlerwatch - Real-time session monitoring for IdlerGear

Watch your Claude Code session as it happens. See tool calls,
task operations, file changes, and more—all in a beautiful TUI.

This is a shortcut for: idlergear session monitor

Usage:
  idlerwatch [options]

Examples:
  idlerwatch                  # Monitor current session
  idlerwatch --file /path/to/session.jsonl

Options:
  -h, --help                 Show this help message
  -f, --file FILE            Session file to monitor (auto-detect if not provided)

Keyboard Shortcuts (once running):
  q                          Quit
  r                          Refresh display
  c                          Clear event log
  h                          Show help

For more information: idlergear session monitor --help
""")
        sys.exit(0)

    # Parse arguments and call monitor command
    from pathlib import Path
    from idlergear.tui import run_monitor

    session_path = None

    # Simple argument parsing
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ("-f", "--file"):
            if i + 1 < len(sys.argv):
                session_path = Path(sys.argv[i + 1])
                i += 2
            else:
                print("Error: --file requires a value")
                sys.exit(1)
        else:
            i += 1

    try:
        run_monitor(session_path)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


# ============================================
# File Registry Commands
# ============================================


@file_app.command("register")
def file_register(
    path: str = typer.Argument(..., help="File path to register"),
    status: str = typer.Option("current", "--status", "-s", help="File status: current, deprecated, archived, problematic"),
    reason: Optional[str] = typer.Option(None, "--reason", "-r", help="Reason for status"),
):
    """Register a file with explicit status."""
    from idlergear.file_registry import FileRegistry, FileStatus

    try:
        status_enum = FileStatus(status)
    except ValueError:
        typer.secho(f"Invalid status: {status}. Must be one of: current, deprecated, archived, problematic", fg=typer.colors.RED)
        raise typer.Exit(1)

    registry = FileRegistry()
    registry.register_file(path, status_enum, reason=reason)

    # Status color mapping
    color = {
        FileStatus.CURRENT: typer.colors.GREEN,
        FileStatus.DEPRECATED: typer.colors.YELLOW,
        FileStatus.ARCHIVED: typer.colors.BLUE,
        FileStatus.PROBLEMATIC: typer.colors.RED,
    }[status_enum]

    typer.secho(f"✅ Registered {path} as {status}", fg=color)
    if reason:
        typer.secho(f"   Reason: {reason}", fg=typer.colors.BRIGHT_BLACK)


@file_app.command("deprecate")
def file_deprecate(
    path: str = typer.Argument(..., help="File path to deprecate"),
    successor: Optional[str] = typer.Option(None, "--successor", "-s", help="Current version path"),
    reason: str = typer.Option(..., "--reason", "-r", help="Reason for deprecation"),
):
    """Mark a file as deprecated."""
    from idlergear.file_registry import FileRegistry

    registry = FileRegistry()
    registry.deprecate_file(path, successor=successor, reason=reason)

    typer.secho(f"⚠️  Deprecated {path}", fg=typer.colors.YELLOW)
    if successor:
        typer.secho(f"   Current version: {successor}", fg=typer.colors.GREEN)
    typer.secho(f"   Reason: {reason}", fg=typer.colors.BRIGHT_BLACK)


@file_app.command("status")
def file_status(
    path: str = typer.Argument(..., help="File path to check"),
):
    """Show status of a file."""
    from idlergear.file_registry import FileRegistry

    registry = FileRegistry()
    entry = registry.get_entry(path)

    if not entry:
        typer.secho(f"File not registered: {path}", fg=typer.colors.BRIGHT_BLACK)
        status = registry.get_status(path)
        if status:
            typer.secho(f"Matches pattern rule: {status.value}", fg=typer.colors.YELLOW)
        else:
            typer.secho("No status information available", fg=typer.colors.BRIGHT_BLACK)
        raise typer.Exit(0)

    # Status color mapping
    color = {
        "current": typer.colors.GREEN,
        "deprecated": typer.colors.YELLOW,
        "archived": typer.colors.BLUE,
        "problematic": typer.colors.RED,
    }[entry.status.value]

    status_symbols = {
        "current": "✅",
        "deprecated": "⚠️ ",
        "archived": "📦",
        "problematic": "❌",
    }

    symbol = status_symbols[entry.status.value]
    typer.secho(f"\n{symbol} {path}", fg=color, bold=True)
    typer.secho(f"Status: {entry.status.value}", fg=color)

    if entry.reason:
        typer.secho(f"Reason: {entry.reason}", fg=typer.colors.BRIGHT_BLACK)

    if entry.current_version:
        typer.secho(f"Current version: {entry.current_version}", fg=typer.colors.GREEN)

    if entry.deprecated_at:
        typer.secho(f"Deprecated at: {entry.deprecated_at}", fg=typer.colors.BRIGHT_BLACK)

    if entry.description:
        typer.secho(f"\nDescription: {entry.description}", fg=typer.colors.CYAN)

    if entry.tags:
        typer.secho(f"Tags: {', '.join(entry.tags)}", fg=typer.colors.MAGENTA)

    if entry.components:
        typer.secho(f"Components: {', '.join(entry.components)}", fg=typer.colors.BLUE)

    if entry.related_files:
        typer.secho(f"Related files:", fg=typer.colors.YELLOW)
        for rf in entry.related_files:
            typer.secho(f"  - {rf}", fg=typer.colors.BRIGHT_BLACK)

    typer.echo()


@file_app.command("list")
def file_list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
):
    """List all registered files."""
    from idlergear.file_registry import FileRegistry, FileStatus

    registry = FileRegistry()

    status_filter = None
    if status:
        try:
            status_filter = FileStatus(status)
        except ValueError:
            typer.secho(f"Invalid status: {status}. Must be one of: current, deprecated, archived, problematic", fg=typer.colors.RED)
            raise typer.Exit(1)

    files = registry.list_files(status_filter)

    if not files:
        typer.secho("No files registered", fg=typer.colors.BRIGHT_BLACK)
        raise typer.Exit(0)

    # Group by status
    by_status = {}
    for entry in files:
        status_key = entry.status.value
        if status_key not in by_status:
            by_status[status_key] = []
        by_status[status_key].append(entry)

    # Display
    typer.secho(f"\n📁 Registered Files ({len(files)} total)\n", fg=typer.colors.BRIGHT_CYAN, bold=True)

    status_order = ["current", "deprecated", "archived", "problematic"]
    status_colors = {
        "current": typer.colors.GREEN,
        "deprecated": typer.colors.YELLOW,
        "archived": typer.colors.BLUE,
        "problematic": typer.colors.RED,
    }
    status_symbols = {
        "current": "✅",
        "deprecated": "⚠️ ",
        "archived": "📦",
        "problematic": "❌",
    }

    for status_key in status_order:
        if status_key not in by_status:
            continue

        entries = by_status[status_key]
        color = status_colors[status_key]
        symbol = status_symbols[status_key]

        typer.secho(f"{symbol} {status_key.upper()} ({len(entries)} files)", fg=color, bold=True)

        for entry in sorted(entries, key=lambda e: e.path):
            typer.secho(f"  {entry.path}", fg=color)
            if entry.reason:
                typer.secho(f"    → {entry.reason}", fg=typer.colors.BRIGHT_BLACK)
            if entry.current_version:
                typer.secho(f"    → Use: {entry.current_version}", fg=typer.colors.GREEN)

        typer.echo()


@file_app.command("annotate")
def file_annotate(
    path: str = typer.Argument(..., help="File path to annotate"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="File description"),
    tags: Optional[List[str]] = typer.Option(None, "--tag", "-t", help="Tags (can be specified multiple times)"),
    components: Optional[List[str]] = typer.Option(None, "--component", "-c", help="Components (can be specified multiple times)"),
):
    """Annotate a file with description, tags, and components."""
    from idlergear.file_registry import FileRegistry

    registry = FileRegistry()
    entry = registry.annotate_file(
        path,
        description=description,
        tags=tags or [],
        components=components or [],
    )

    typer.secho(f"✅ Annotated {path}", fg=typer.colors.GREEN)

    if description:
        typer.secho(f"   Description: {description}", fg=typer.colors.CYAN)
    if tags:
        typer.secho(f"   Tags: {', '.join(tags)}", fg=typer.colors.MAGENTA)
    if components:
        typer.secho(f"   Components: {', '.join(components)}", fg=typer.colors.BLUE)


@file_app.command("search")
def file_search(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search in descriptions"),
    tags: Optional[List[str]] = typer.Option(None, "--tag", "-t", help="Filter by tags"),
    components: Optional[List[str]] = typer.Option(None, "--component", "-c", help="Filter by components"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
):
    """Search files by annotations."""
    from idlergear.file_registry import FileRegistry, FileStatus

    registry = FileRegistry()

    status_filter = None
    if status:
        try:
            status_filter = FileStatus(status)
        except ValueError:
            typer.secho(f"Invalid status: {status}", fg=typer.colors.RED)
            raise typer.Exit(1)

    results = registry.search_files(
        query=query,
        tags=tags or [],
        components=components or [],
        status=status_filter,
    )

    if not results:
        typer.secho("No files found", fg=typer.colors.BRIGHT_BLACK)
        raise typer.Exit(0)

    typer.secho(f"\n🔍 Found {len(results)} files\n", fg=typer.colors.BRIGHT_CYAN, bold=True)

    for entry in results:
        # Status color
        color = {
            "current": typer.colors.GREEN,
            "deprecated": typer.colors.YELLOW,
            "archived": typer.colors.BLUE,
            "problematic": typer.colors.RED,
        }.get(entry.status.value, typer.colors.WHITE)

        typer.secho(f"📄 {entry.path}", fg=color, bold=True)

        if entry.description:
            typer.secho(f"   {entry.description}", fg=typer.colors.BRIGHT_BLACK)

        if entry.tags:
            typer.secho(f"   Tags: {', '.join(entry.tags)}", fg=typer.colors.MAGENTA)

        if entry.components:
            typer.secho(f"   Components: {', '.join(entry.components)}", fg=typer.colors.BLUE)

        typer.echo()


@file_app.command("audit")
def file_audit(
    ctx: typer.Context,
    since: int = typer.Option(24, "--since", help="Audit access log for last N hours (default: 24)"),
    include_code: bool = typer.Option(False, "--include-code", help="Include static code analysis"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json or text (default: text)"),
):
    """Audit project for deprecated file usage.

    Scans:
    - Access log for recent deprecated file access
    - (Optional) Code for string references to deprecated files

    Examples:
      idlergear file audit
      idlergear file audit --since 48 --include-code
      idlergear file audit --output json
    """
    from idlergear.file_registry import FileRegistry

    registry = FileRegistry()
    report = registry.audit_project(since_hours=since, include_code_scan=include_code)

    # JSON output
    if output == "json" or ctx.obj.get("output_mode") == "json":
        typer.echo(json.dumps(report, indent=2))
        return

    # Text output
    typer.secho("\n📋 File Registry Audit Report", fg=typer.colors.BRIGHT_BLUE, bold=True)
    typer.secho("=" * 60, fg=typer.colors.BRIGHT_BLUE)

    # Accessed files section
    accessed = report["accessed"]
    if accessed:
        typer.secho(f"\n⚠️  Deprecated Files Recently Accessed ({len(accessed)}):", fg=typer.colors.YELLOW, bold=True)
        for item in accessed:
            typer.secho(f"\n  ✗ {item['file']}", fg=typer.colors.RED, bold=True)
            if item.get("current_version"):
                typer.secho(f"    Current version: {item['current_version']}", fg=typer.colors.GREEN)
            typer.secho(f"    Access count: {item['access_count']}")
            typer.secho(f"    Last accessed: {item['last_accessed']}")
            if item.get("accessed_by"):
                agents = ", ".join(item["accessed_by"])
                typer.secho(f"    Accessed by: {agents}")
            if item.get("tools_used"):
                tools = ", ".join(item["tools_used"])
                typer.secho(f"    Tools used: {tools}")
    else:
        typer.secho(f"\n✅ No deprecated files accessed in last {since} hours", fg=typer.colors.GREEN)

    # Code references section
    if include_code:
        code_refs = report["code_references"]
        if code_refs:
            typer.secho(f"\n⚠️  Deprecated Files Referenced in Code ({len(code_refs)}):", fg=typer.colors.YELLOW, bold=True)
            for ref in code_refs:
                typer.secho(f"\n  ⚠️  {ref['file']}:{ref['line']}", fg=typer.colors.YELLOW, bold=True)
                typer.secho(f"    References: {ref['deprecated_file']}", fg=typer.colors.RED)
                if ref.get("current_version"):
                    typer.secho(f"    Suggestion: Update to {ref['current_version']}", fg=typer.colors.GREEN)
                typer.secho(f"    Code: {ref['code'][:80]}{'...' if len(ref['code']) > 80 else ''}")
        else:
            typer.secho("\n✅ No deprecated file references found in code", fg=typer.colors.GREEN)

    # Summary
    typer.secho("\n" + "=" * 60, fg=typer.colors.BRIGHT_BLUE)
    typer.secho("Summary:", fg=typer.colors.BRIGHT_BLUE, bold=True)
    typer.echo(f"  Audit period: Last {report['summary']['audit_period_hours']} hours")
    typer.echo(f"  Deprecated files accessed: {report['summary']['deprecated_files_accessed']}")
    if include_code:
        typer.echo(f"  Code references found: {report['summary']['code_references_found']}")

    if report['summary']['deprecated_files_accessed'] > 0 or report['summary']['code_references_found'] > 0:
        typer.secho("\n💡 Action Required:", fg=typer.colors.CYAN, bold=True)
        typer.echo("  - Review and update references to deprecated files")
        typer.echo("  - Use 'idlergear file status <path>' to find current versions")
        typer.echo("  - Consider adding to pre-commit hook for automated checks")

    typer.echo()


@file_app.command("unregister")
def file_unregister(
    path: str = typer.Argument(..., help="File path to unregister"),
):
    """Remove a file from the registry."""
    from idlergear.file_registry import FileRegistry

    registry = FileRegistry()

    if not registry.unregister(path):
        typer.secho(f"File not registered: {path}", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    typer.secho(f"✅ Unregistered {path}", fg=typer.colors.GREEN)


@file_app.command("scan")
def file_scan(
    ctx: typer.Context,
    auto: bool = typer.Option(False, "--auto", help="Automatically apply high-confidence suggestions"),
    confidence: str = typer.Option("low", "--confidence", "-c", help="Minimum confidence: high, medium, low"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show suggestions without applying"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json or text"),
):
    """Auto-detect versioned files and suggest registry entries.

    Scans project for:
    - Git rename history (high confidence)
    - Filename patterns (_old, _v1, .bak, timestamps)
    - Archive directories (archive/, old/, backup/)

    Examples:
        idlergear file scan                    # Interactive mode
        idlergear file scan --auto             # Auto-apply high confidence
        idlergear file scan --confidence high  # Only show high confidence
        idlergear file scan --dry-run          # Preview without applying
    """
    from idlergear.file_registry import FileRegistry
    from idlergear.file_registry_scanner import FileRegistryScanner

    scanner = FileRegistryScanner()
    suggestions = scanner.scan(min_confidence=confidence)

    if not suggestions:
        typer.secho("✅ No versioned files detected", fg=typer.colors.GREEN)
        return

    # JSON output
    if output == "json" or (hasattr(ctx.obj, "output_mode") and ctx.obj.output_mode == "json"):
        result = {
            "suggestions": [
                {
                    "file_path": s.file_path,
                    "suggested_status": s.suggested_status.value,
                    "confidence": s.confidence,
                    "reason": s.reason,
                    "current_version": s.current_version,
                    "evidence": s.evidence,
                }
                for s in suggestions
            ],
            "total": len(suggestions),
        }
        typer.echo(json.dumps(result, indent=2))
        return

    # Text output
    typer.secho(f"\n🔍 File Registry Auto-Detection Report", fg=typer.colors.BRIGHT_BLUE, bold=True)
    typer.secho(f"Found {len(suggestions)} suggestions\n", fg=typer.colors.CYAN)

    # Group by confidence
    grouped = scanner.group_suggestions_by_confidence(suggestions)

    registry = FileRegistry()
    applied = 0
    skipped = 0

    for conf_level in ["high", "medium", "low"]:
        conf_suggestions = grouped.get(conf_level, [])
        if not conf_suggestions:
            continue

        # Confidence color
        conf_color = {
            "high": typer.colors.GREEN,
            "medium": typer.colors.YELLOW,
            "low": typer.colors.WHITE,
        }[conf_level]

        typer.secho(f"\n{conf_level.upper()} CONFIDENCE ({len(conf_suggestions)}):", fg=conf_color, bold=True)
        typer.secho("=" * 60, fg=conf_color)

        for suggestion in conf_suggestions:
            typer.echo()
            typer.secho(f"  📄 {suggestion.file_path}", fg=typer.colors.CYAN, bold=True)
            typer.echo(f"     Status: {suggestion.suggested_status.value}")
            typer.echo(f"     Reason: {suggestion.reason}")

            if suggestion.current_version:
                typer.secho(f"     Current: {suggestion.current_version}", fg=typer.colors.GREEN)

            if suggestion.evidence:
                typer.echo(f"     Evidence:")
                for ev in suggestion.evidence:
                    typer.echo(f"       - {ev}")

            # Auto-apply logic
            should_apply = False

            if dry_run:
                typer.secho("     [DRY RUN - Would register]", fg=typer.colors.MAGENTA)
                continue

            if auto and conf_level == "high":
                should_apply = True
                typer.secho("     [AUTO-APPLYING]", fg=typer.colors.GREEN)
            elif not auto:
                # Interactive mode
                response = typer.prompt(
                    "     Apply this suggestion? [Y/n/skip]",
                    default="y",
                    show_default=False,
                )
                should_apply = response.lower() in ["y", "yes", ""]
                if response.lower() in ["skip", "s"]:
                    skipped += 1
                    continue

            # Apply suggestion
            if should_apply:
                try:
                    if suggestion.suggested_status.value == "deprecated":
                        registry.deprecate(
                            suggestion.file_path,
                            successor=suggestion.current_version,
                            reason=suggestion.reason,
                        )
                    else:
                        registry.register(
                            suggestion.file_path,
                            status=suggestion.suggested_status,
                            reason=suggestion.reason,
                        )

                    typer.secho(f"     ✅ Registered as {suggestion.suggested_status.value}", fg=typer.colors.GREEN)
                    applied += 1

                except Exception as e:
                    typer.secho(f"     ❌ Failed to register: {e}", fg=typer.colors.RED)
            else:
                skipped += 1

    # Summary
    if not dry_run:
        typer.secho("\n" + "=" * 60, fg=typer.colors.BRIGHT_BLUE)
        typer.secho("Summary:", fg=typer.colors.BRIGHT_BLUE, bold=True)
        typer.echo(f"  Total suggestions: {len(suggestions)}")
        typer.echo(f"  Applied: {applied}")
        typer.echo(f"  Skipped: {skipped}")

        if applied > 0:
            typer.secho("\n✅ Registry updated successfully", fg=typer.colors.GREEN)
    else:
        typer.secho("\n💡 Run without --dry-run to apply changes", fg=typer.colors.CYAN)


# Plugin commands
@plugin_app.command("list")
def plugin_list(
    loaded_only: bool = typer.Option(
        False, "--loaded", "-l", help="Only show loaded plugins"
    ),
):
    """List available and loaded plugins."""
    from idlergear.plugins import LangfusePlugin, LlamaIndexPlugin, PluginRegistry

    registry = PluginRegistry()

    # Register available plugins
    registry.register_plugin_class(LangfusePlugin)
    registry.register_plugin_class(LlamaIndexPlugin)

    if loaded_only:
        plugins = registry.list_loaded_plugins()
        title = "Loaded Plugins"
    else:
        plugins = registry.list_available_plugins()
        title = "Available Plugins"
        loaded = registry.list_loaded_plugins()

    if not plugins:
        typer.secho(f"No plugins {'loaded' if loaded_only else 'available'}", fg=typer.colors.YELLOW)
        return

    typer.secho(f"\n{title} ({len(plugins)} total):", fg=typer.colors.BRIGHT_BLUE, bold=True)

    for name in plugins:
        enabled = registry.config.is_plugin_enabled(name)
        is_loaded = name in (loaded if not loaded_only else plugins)

        # Status symbol
        if is_loaded:
            symbol = "●"
            color = typer.colors.GREEN
        elif enabled:
            symbol = "○"
            color = typer.colors.YELLOW
        else:
            symbol = "○"
            color = typer.colors.WHITE

        typer.secho(f"  {symbol} {name}", fg=color, end="")

        # Status text
        if is_loaded:
            typer.secho(" (loaded)", fg=typer.colors.GREEN)
        elif enabled:
            typer.secho(" (enabled, not loaded)", fg=typer.colors.YELLOW)
        else:
            typer.secho(" (available)", fg=typer.colors.WHITE)


@plugin_app.command("status")
def plugin_status(
    plugin_name: Optional[str] = typer.Argument(None, help="Plugin name (omit for all)"),
):
    """Show detailed plugin status."""
    from idlergear.plugins import LangfusePlugin, LlamaIndexPlugin, PluginRegistry

    registry = PluginRegistry()

    # Register available plugins
    registry.register_plugin_class(LangfusePlugin)
    registry.register_plugin_class(LlamaIndexPlugin)

    if plugin_name:
        # Show status for specific plugin
        plugin = registry.get_plugin(plugin_name)
        if not plugin:
            # Try to load it
            plugin = registry.load_plugin(plugin_name)

        if plugin:
            typer.secho(f"\nPlugin: {plugin_name}", fg=typer.colors.BRIGHT_BLUE, bold=True)
            typer.secho(f"  Status: Loaded", fg=typer.colors.GREEN)
            typer.secho(f"  Initialized: {plugin.is_initialized()}", fg=typer.colors.WHITE)
            typer.secho(f"  Healthy: {plugin.health_check()}", fg=typer.colors.WHITE)
            typer.secho(f"  Capabilities:", fg=typer.colors.WHITE)
            for cap in plugin.capabilities():
                typer.secho(f"    - {cap.value}", fg=typer.colors.WHITE)
        else:
            enabled = registry.config.is_plugin_enabled(plugin_name)
            available = plugin_name in registry.list_available_plugins()

            typer.secho(f"\nPlugin: {plugin_name}", fg=typer.colors.BRIGHT_BLUE, bold=True)
            typer.secho(f"  Status: Not loaded", fg=typer.colors.YELLOW)
            typer.secho(f"  Enabled: {enabled}", fg=typer.colors.WHITE)
            typer.secho(f"  Available: {available}", fg=typer.colors.WHITE)
    else:
        # Show status for all plugins
        typer.secho("\nPlugin Status:", fg=typer.colors.BRIGHT_BLUE, bold=True)

        for name in registry.list_available_plugins():
            plugin = registry.get_plugin(name)
            enabled = registry.config.is_plugin_enabled(name)

            if plugin:
                symbol = "●"
                color = typer.colors.GREEN
                status = "loaded"
            elif enabled:
                symbol = "○"
                color = typer.colors.YELLOW
                status = "enabled, not loaded"
            else:
                symbol = "○"
                color = typer.colors.WHITE
                status = "available"

            typer.secho(f"  {symbol} {name}: {status}", fg=color)


@plugin_app.command("enable")
def plugin_enable(
    plugin_name: str = typer.Argument(..., help="Plugin name (e.g., langfuse, llamaindex)"),
):
    """Enable a plugin in config.toml."""
    import toml
    from pathlib import Path

    config_path = Path.cwd() / ".idlergear" / "config.toml"
    if config_path.exists():
        config = toml.load(config_path)
    else:
        config = {}

    # Update plugin config
    if "plugins" not in config:
        config["plugins"] = {}
    if plugin_name not in config["plugins"]:
        config["plugins"][plugin_name] = {}

    config["plugins"][plugin_name]["enabled"] = True

    # Write back
    with open(config_path, "w") as f:
        toml.dump(config, f)

    typer.secho(f"✅ Enabled plugin: {plugin_name}", fg=typer.colors.GREEN)
    typer.secho(f"   Config: {config_path}", fg=typer.colors.WHITE)


@plugin_app.command("disable")
def plugin_disable(
    plugin_name: str = typer.Argument(..., help="Plugin name"),
):
    """Disable a plugin in config.toml."""
    import toml
    from pathlib import Path

    config_path = Path.cwd() / ".idlergear" / "config.toml"
    if config_path.exists():
        config = toml.load(config_path)
    else:
        config = {}

    # Update plugin config
    if "plugins" not in config:
        config["plugins"] = {}
    if plugin_name not in config["plugins"]:
        config["plugins"][plugin_name] = {}

    config["plugins"][plugin_name]["enabled"] = False

    # Write back
    with open(config_path, "w") as f:
        toml.dump(config, f)

    typer.secho(f"✅ Disabled plugin: {plugin_name}", fg=typer.colors.YELLOW)
    typer.secho(f"   Config: {config_path}", fg=typer.colors.WHITE)


@plugin_app.command("search")
def plugin_search(
    query: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results to return"),
    knowledge_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type: reference or note"),
):
    """Semantic search using LlamaIndex plugin."""
    from idlergear.plugins import LlamaIndexPlugin, PluginRegistry

    registry = PluginRegistry()

    # Register and load LlamaIndex plugin
    registry.register_plugin_class(LlamaIndexPlugin)
    plugin = registry.load_plugin("llamaindex")

    if not plugin:
        typer.secho("❌ LlamaIndex plugin not enabled", fg=typer.colors.RED)
        typer.secho("   Enable it first: idlergear plugin enable llamaindex", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    # Perform search
    results = plugin.search(query, top_k=top_k, knowledge_type=knowledge_type)

    if not results:
        typer.secho(f"No results found for: {query}", fg=typer.colors.YELLOW)
        return

    typer.secho(f"\nSearch Results ({len(results)} found):", fg=typer.colors.BRIGHT_BLUE, bold=True)
    typer.secho(f"Query: {query}\n", fg=typer.colors.WHITE)

    for i, result in enumerate(results, 1):
        score = result.get("score", 0)
        text = result.get("text", "")[:200]  # Truncate long text
        metadata = result.get("metadata", {})

        typer.secho(f"{i}. Score: {score:.3f}", fg=typer.colors.GREEN)
        typer.secho(f"   Type: {metadata.get('type', 'unknown')}", fg=typer.colors.WHITE)
        typer.secho(f"   {text}...", fg=typer.colors.WHITE)
        typer.secho("")


# ============================================================================
# Graph Commands (add before if __name__ == "__main__":)



# ============================================================================
# Graph Commands
# ============================================================================

@graph_app.command("populate")
def graph_populate(
    ctx: typer.Context,
    max_commits: int = typer.Option(100, "--max-commits", help="Maximum commits to index"),
    code_dir: str = typer.Option("src", "--code-dir", help="Directory to scan for code"),
    incremental: bool = typer.Option(True, "--incremental/--full", help="Skip already-indexed data"),
    verbose: bool = typer.Option(True, "--verbose/--quiet", help="Print progress messages"),
):
    """Populate entire knowledge graph in one command.

    Runs all populators: git history, code symbols, tasks, commit-task links, references, and wiki.
    Safe to re-run with --incremental (default).
    """
    from idlergear.graph import populate_all
    from pathlib import Path

    project_path = Path.cwd()

    try:
        results = populate_all(
            project_path=project_path,
            max_commits=max_commits,
            code_directory=code_dir,
            incremental=incremental,
            verbose=verbose
        )

        if ctx.obj.get("output_mode") == "json":
            typer.echo(json.dumps(results, indent=2))
        # Human output is handled by populate_all's verbose mode

    except Exception as e:
        typer.secho(f"Failed to populate knowledge graph: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("schema")
def graph_schema(ctx: typer.Context):
    """Show knowledge graph schema (node types, relationship types, counts)."""
    try:
        from idlergear.graph.database import get_database

        db = get_database()

        # Query for node types and counts
        node_query = """
        MATCH (n)
        RETURN labels(n)[0] AS type, COUNT(*) AS count
        ORDER BY count DESC
        """
        node_results = db.execute(node_query)

        # Query for relationship types and counts
        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) AS type, COUNT(*) AS count
        ORDER BY count DESC
        """
        rel_results = db.execute(rel_query)

        if ctx.obj.get("output_mode") == "json":
            output = {
                "node_types": [{"type": r[0], "count": r[1]} for r in node_results],
                "relationship_types": [{"type": r[0], "count": r[1]} for r in rel_results]
            }
            typer.echo(json.dumps(output, indent=2))
        else:
            typer.secho("\n📊 Knowledge Graph Schema\n", fg=typer.colors.BRIGHT_BLUE, bold=True)

            typer.secho("Node Types:", fg=typer.colors.GREEN, bold=True)
            for node_type, count in node_results:
                typer.echo(f"  {node_type}: {count:,}")

            typer.secho("\nRelationship Types:", fg=typer.colors.GREEN, bold=True)
            for rel_type, count in rel_results:
                typer.echo(f"  {rel_type}: {count:,}")
            typer.echo()

    except Exception as e:
        typer.secho(f"Failed to get schema: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("stats")
def graph_stats(ctx: typer.Context):
    """Show knowledge graph statistics (total nodes, relationships)."""
    try:
        from idlergear.graph.database import get_database

        db = get_database()

        # Count total nodes
        node_count_query = "MATCH (n) RETURN COUNT(n) AS count"
        node_count = db.execute(node_count_query)[0][0]

        # Count total relationships
        rel_count_query = "MATCH ()-[r]->() RETURN COUNT(r) AS count"
        rel_count = db.execute(rel_count_query)[0][0]

        if ctx.obj.get("output_mode") == "json":
            output = {
                "total_nodes": node_count,
                "total_relationships": rel_count
            }
            typer.echo(json.dumps(output, indent=2))
        else:
            typer.secho("\n📊 Knowledge Graph Statistics\n", fg=typer.colors.BRIGHT_BLUE, bold=True)
            typer.echo(f"Total Nodes: {node_count:,}")
            typer.echo(f"Total Relationships: {rel_count:,}")
            typer.echo()

    except Exception as e:
        typer.secho(f"Failed to get stats: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("query-task")
def graph_query_task(
    ctx: typer.Context,
    task_id: int = typer.Argument(..., help="Task ID to query"),
):
    """Query knowledge graph for task context (files, commits, symbols)."""
    try:
        from idlergear.graph.database import get_database

        db = get_database()

        # Query for task and related entities
        query = """
        MATCH (t:Task {id: $task_id})
        OPTIONAL MATCH (t)-[:IMPLEMENTED_IN]->(f:File)
        OPTIONAL MATCH (c:Commit)-[:MODIFIES]->(t)
        OPTIONAL MATCH (f)-[:CONTAINS]->(s:Symbol)
        RETURN t, COLLECT(DISTINCT f) AS files, COLLECT(DISTINCT c) AS commits, COLLECT(DISTINCT s) AS symbols
        """

        result = db.execute(query, {"task_id": task_id})

        if not result:
            typer.secho(f"Task #{task_id} not found in knowledge graph", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

        task, files, commits, symbols = result[0]

        if ctx.obj.get("output_mode") == "json":
            output = {
                "task": dict(task),
                "files": [dict(f) for f in files if f],
                "commits": [dict(c) for c in commits if c],
                "symbols": [dict(s) for s in symbols if s]
            }
            typer.echo(json.dumps(output, indent=2))
        else:
            typer.secho(f"\n📋 Task #{task_id} Context\n", fg=typer.colors.BRIGHT_BLUE, bold=True)

            if files and any(files):
                typer.secho(f"Files ({len([f for f in files if f])}):", fg=typer.colors.GREEN)
                for f in files:
                    if f:
                        typer.echo(f"  - {f.get('path', 'unknown')}")

            if commits and any(commits):
                typer.secho(f"\nCommits ({len([c for c in commits if c])}):", fg=typer.colors.GREEN)
                for c in commits:
                    if c:
                        typer.echo(f"  - {c.get('sha', 'unknown')[:8]}: {c.get('message', '')[:60]}")

            if symbols and any(symbols):
                typer.secho(f"\nSymbols ({len([s for s in symbols if s])}):", fg=typer.colors.GREEN)
                for s in symbols:
                    if s:
                        typer.echo(f"  - {s.get('name', 'unknown')} ({s.get('type', 'unknown')})")
            typer.echo()

    except Exception as e:
        typer.secho(f"Failed to query task: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("query-file")
def graph_query_file(
    ctx: typer.Context,
    file_path: str = typer.Argument(..., help="File path to query"),
):
    """Query knowledge graph for file context (symbols, tasks, commits)."""
    try:
        from idlergear.graph.database import get_database

        db = get_database()

        # Query for file and related entities
        query = """
        MATCH (f:File {path: $file_path})
        OPTIONAL MATCH (f)-[:CONTAINS]->(s:Symbol)
        OPTIONAL MATCH (f)<-[:IMPLEMENTED_IN]-(t:Task)
        OPTIONAL MATCH (c:Commit)-[:CHANGES]->(f)
        RETURN f, COLLECT(DISTINCT s) AS symbols, COLLECT(DISTINCT t) AS tasks, COLLECT(DISTINCT c) AS commits
        """

        result = db.execute(query, {"file_path": file_path})

        if not result:
            typer.secho(f"File '{file_path}' not found in knowledge graph", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

        file, symbols, tasks, commits = result[0]

        if ctx.obj.get("output_mode") == "json":
            output = {
                "file": dict(file),
                "symbols": [dict(s) for s in symbols if s],
                "tasks": [dict(t) for t in tasks if t],
                "commits": [dict(c) for c in commits if c]
            }
            typer.echo(json.dumps(output, indent=2))
        else:
            typer.secho(f"\n📄 File: {file_path}\n", fg=typer.colors.BRIGHT_BLUE, bold=True)

            if symbols and any(symbols):
                typer.secho(f"Symbols ({len([s for s in symbols if s])}):", fg=typer.colors.GREEN)
                for s in symbols:
                    if s:
                        typer.echo(f"  - {s.get('name', 'unknown')} ({s.get('type', 'unknown')}) at line {s.get('line', '?')}")

            if tasks and any(tasks):
                typer.secho(f"\nRelated Tasks ({len([t for t in tasks if t])}):", fg=typer.colors.GREEN)
                for t in tasks:
                    if t:
                        typer.echo(f"  - #{t.get('id', '?')}: {t.get('title', 'unknown')}")

            if commits and any(commits):
                typer.secho(f"\nRecent Commits ({len([c for c in commits if c])}):", fg=typer.colors.GREEN)
                for c in commits:
                    if c:
                        typer.echo(f"  - {c.get('sha', 'unknown')[:8]}: {c.get('message', '')[:60]}")
            typer.echo()

    except Exception as e:
        typer.secho(f"Failed to query file: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("query-symbols")
def graph_query_symbols(
    ctx: typer.Context,
    pattern: str = typer.Argument(..., help="Symbol name pattern (case-insensitive substring match)"),
    limit: int = typer.Option(10, "--limit", help="Maximum number of results"),
):
    """Search for code symbols (functions, classes, methods) by name pattern."""
    try:
        from idlergear.graph.database import get_database

        db = get_database()

        # Query for symbols matching pattern
        query = """
        MATCH (s:Symbol)
        WHERE toLower(s.name) CONTAINS toLower($pattern)
        OPTIONAL MATCH (f:File)-[:CONTAINS]->(s)
        RETURN s, f
        LIMIT $limit
        """

        results = db.execute(query, {"pattern": pattern, "limit": limit})

        if not results:
            typer.secho(f"No symbols found matching '{pattern}'", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

        if ctx.obj.get("output_mode") == "json":
            output = {
                "pattern": pattern,
                "count": len(results),
                "results": [
                    {
                        "symbol": dict(symbol),
                        "file": dict(file) if file else None
                    }
                    for symbol, file in results
                ]
            }
            typer.echo(json.dumps(output, indent=2))
        else:
            typer.secho(f"\n🔍 Symbols matching '{pattern}' ({len(results)} found)\n", fg=typer.colors.BRIGHT_BLUE, bold=True)

            for symbol, file in results:
                name = symbol.get('name', 'unknown')
                sym_type = symbol.get('type', 'unknown')
                line = symbol.get('line', '?')
                file_path = file.get('path', 'unknown') if file else 'unknown'

                typer.secho(f"{name}", fg=typer.colors.GREEN, bold=True)
                typer.echo(f"  Type: {sym_type}")
                typer.echo(f"  Location: {file_path}:{line}")
                typer.echo()

    except Exception as e:
        typer.secho(f"Failed to search symbols: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("impact")
def graph_impact_analysis(
    ctx: typer.Context,
    symbol_name: str = typer.Argument(..., help="Symbol name to analyze"),
):
    """Analyze what would be affected if a symbol breaks or changes."""
    try:
        from idlergear.graph.database import get_database
        from idlergear.graph.queries import query_impact_analysis

        db = get_database()
        result = query_impact_analysis(db, symbol_name)

        if ctx.obj.get("output_mode") == "json":
            typer.echo(json.dumps(result, indent=2))
        else:
            if not result.get("found"):
                typer.secho(f"\n❌ Symbol '{symbol_name}' not found in knowledge graph\n", fg=typer.colors.RED)
                raise typer.Exit(1)

            typer.secho(f"\n💥 Impact Analysis: {symbol_name}\n", fg=typer.colors.BRIGHT_BLUE, bold=True)
            typer.echo(f"Defined in: {result['defined_in']}")
            typer.echo(f"Type: {result['type']}")

            if result['callers']:
                typer.secho(f"\n📞 Callers ({len(result['callers'])}):", fg=typer.colors.YELLOW)
                for caller in result['callers']:
                    typer.echo(f"  - {caller}")

            if result['affected_files']:
                typer.secho(f"\n📄 Affected Files ({len(result['affected_files'])}):", fg=typer.colors.YELLOW)
                for file in result['affected_files']:
                    typer.echo(f"  - {file}")

            if result['related_tasks']:
                typer.secho(f"\n📋 Related Tasks ({len(result['related_tasks'])}):", fg=typer.colors.YELLOW)
                for task_id in result['related_tasks']:
                    typer.echo(f"  - Task #{task_id}")
            typer.echo()

    except Exception as e:
        typer.secho(f"Failed to analyze impact: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("test-coverage")
def graph_test_coverage(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="File path or symbol name"),
    target_type: str = typer.Option("file", "--type", help="Target type: file or symbol"),
):
    """Find test files that cover a given file or symbol."""
    try:
        from idlergear.graph.database import get_database
        from idlergear.graph.queries import query_test_coverage

        db = get_database()
        result = query_test_coverage(db, target, target_type)

        if ctx.obj.get("output_mode") == "json":
            typer.echo(json.dumps(result, indent=2))
        else:
            typer.secho(f"\n🧪 Test Coverage: {target} ({target_type})\n", fg=typer.colors.BRIGHT_BLUE, bold=True)

            if result['test_files']:
                typer.secho(f"Test Files ({len(result['test_files'])}):", fg=typer.colors.GREEN)
                for test_file in result['test_files']:
                    typer.echo(f"  - {test_file}")
            else:
                typer.secho("No test files found", fg=typer.colors.YELLOW)

            if result['test_functions']:
                typer.secho(f"\nTest Functions ({len(result['test_functions'])}):", fg=typer.colors.GREEN)
                for test_func in result['test_functions']:
                    typer.echo(f"  - {test_func}")
            typer.echo()

    except Exception as e:
        typer.secho(f"Failed to check test coverage: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("history")
def graph_change_history(
    ctx: typer.Context,
    symbol_name: str = typer.Argument(..., help="Symbol name to trace"),
):
    """Get all commits that touched a specific symbol."""
    try:
        from idlergear.graph.database import get_database
        from idlergear.graph.queries import query_change_history

        db = get_database()
        commits = query_change_history(db, symbol_name)

        if ctx.obj.get("output_mode") == "json":
            typer.echo(json.dumps({"symbol": symbol_name, "commits": commits}, indent=2))
        else:
            typer.secho(f"\n📜 Change History: {symbol_name}\n", fg=typer.colors.BRIGHT_BLUE, bold=True)

            if not commits:
                typer.secho("No commits found for this symbol", fg=typer.colors.YELLOW)
            else:
                for commit in commits:
                    typer.secho(f"{commit['hash']}", fg=typer.colors.GREEN, bold=True)
                    typer.echo(f"  Author: {commit['author']}")
                    typer.echo(f"  Date: {commit['timestamp']}")
                    typer.echo(f"  File: {commit['file']}")
                    typer.echo(f"  Message: {commit['message'][:60]}...")
                    typer.echo()

    except Exception as e:
        typer.secho(f"Failed to get change history: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("dependencies")
def graph_dependency_chain(
    ctx: typer.Context,
    file_path: str = typer.Argument(..., help="File path to analyze"),
    max_depth: int = typer.Option(5, "--max-depth", help="Maximum traversal depth"),
):
    """Find transitive dependency chain for a file."""
    try:
        from idlergear.graph.database import get_database
        from idlergear.graph.queries import query_dependency_chain

        db = get_database()
        result = query_dependency_chain(db, file_path, max_depth)

        if ctx.obj.get("output_mode") == "json":
            typer.echo(json.dumps(result, indent=2))
        else:
            typer.secho(f"\n🔗 Dependency Chain: {file_path}\n", fg=typer.colors.BRIGHT_BLUE, bold=True)
            typer.echo(f"Total dependencies: {result['total_dependencies']}")

            if result['dependencies']:
                typer.secho("\nDependencies (by distance):", fg=typer.colors.GREEN)
                for dep in result['dependencies']:
                    typer.echo(f"  [{dep['distance']} hops] {dep['file']}")
            else:
                typer.secho("\nNo dependencies found", fg=typer.colors.YELLOW)
            typer.echo()

    except Exception as e:
        typer.secho(f"Failed to get dependency chain: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("orphans")
def graph_orphan_detection(ctx: typer.Context):
    """Find orphaned/unused code - functions with no callers, files with no imports."""
    try:
        from idlergear.graph.database import get_database
        from idlergear.graph.queries import query_orphan_detection

        db = get_database()
        result = query_orphan_detection(db)

        if ctx.obj.get("output_mode") == "json":
            typer.echo(json.dumps(result, indent=2))
        else:
            typer.secho("\n🗑️  Orphan Detection\n", fg=typer.colors.BRIGHT_BLUE, bold=True)

            typer.secho(f"Unused Symbols: {result['unused_symbol_count']}", fg=typer.colors.YELLOW, bold=True)
            if result['unused_symbols']:
                for symbol in result['unused_symbols'][:20]:  # Show first 20
                    typer.echo(f"  - {symbol['name']} ({symbol['type']}) in {symbol['file']}:{symbol['line']}")
                if result['unused_symbol_count'] > 20:
                    typer.echo(f"  ... and {result['unused_symbol_count'] - 20} more")

            typer.echo()
            typer.secho(f"Unreferenced Files: {result['unreferenced_file_count']}", fg=typer.colors.YELLOW, bold=True)
            if result['unreferenced_files']:
                for file in result['unreferenced_files'][:20]:  # Show first 20
                    typer.echo(f"  - {file['file']} ({file['lines']} lines)")
                if result['unreferenced_file_count'] > 20:
                    typer.echo(f"  ... and {result['unreferenced_file_count'] - 20} more")
            typer.echo()

    except Exception as e:
        typer.secho(f"Failed to detect orphans: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("callers")
def graph_symbol_callers(
    ctx: typer.Context,
    symbol_name: str = typer.Argument(..., help="Symbol to find callers for"),
):
    """Find all symbols that call a given symbol (reverse lookup)."""
    try:
        from idlergear.graph.database import get_database
        from idlergear.graph.queries import query_symbol_callers

        db = get_database()
        result = query_symbol_callers(db, symbol_name)

        if ctx.obj.get("output_mode") == "json":
            typer.echo(json.dumps(result, indent=2))
        else:
            typer.secho(f"\n📞 Callers of: {symbol_name}\n", fg=typer.colors.BRIGHT_BLUE, bold=True)
            typer.echo(f"Total callers: {result['caller_count']}")

            if result['callers']:
                typer.secho("\nCaller Functions:", fg=typer.colors.GREEN)
                for caller in result['callers']:
                    typer.echo(f"  - {caller['name']} ({caller['type']}) in {caller['file']}:{caller['line']}")
            else:
                typer.secho("\nNo callers found", fg=typer.colors.YELLOW)
            typer.echo()

    except Exception as e:
        typer.secho(f"Failed to find callers: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("timeline")
def graph_file_timeline(
    ctx: typer.Context,
    file_path: str = typer.Argument(..., help="File to trace"),
    limit: int = typer.Option(20, "--limit", help="Max commits to return"),
):
    """Get evolution of a file over time via commits."""
    try:
        from idlergear.graph.database import get_database
        from idlergear.graph.queries import query_file_timeline

        db = get_database()
        result = query_file_timeline(db, file_path, limit)

        if ctx.obj.get("output_mode") == "json":
            typer.echo(json.dumps(result, indent=2))
        else:
            typer.secho(f"\n📅 Timeline: {file_path}\n", fg=typer.colors.BRIGHT_BLUE, bold=True)
            typer.echo(f"Total commits: {result['commit_count']}")

            if result['commits']:
                typer.secho("\nRecent Commits:", fg=typer.colors.GREEN)
                for commit in result['commits']:
                    typer.secho(f"{commit['hash']}", fg=typer.colors.CYAN, bold=True)
                    typer.echo(f"  Author: {commit['author']}")
                    typer.echo(f"  Date: {commit['timestamp']}")
                    typer.echo(f"  Message: {commit['message'][:60]}...")
                    typer.echo()
            else:
                typer.secho("\nNo commits found for this file", fg=typer.colors.YELLOW)

    except Exception as e:
        typer.secho(f"Failed to get file timeline: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("task-coverage")
def graph_task_coverage(ctx: typer.Context):
    """Find tasks with no associated commits (not yet implemented)."""
    try:
        from idlergear.graph.database import get_database
        from idlergear.graph.queries import query_task_coverage

        db = get_database()
        result = query_task_coverage(db)

        if ctx.obj.get("output_mode") == "json":
            typer.echo(json.dumps(result, indent=2))
        else:
            typer.secho("\n📊 Task Coverage Analysis\n", fg=typer.colors.BRIGHT_BLUE, bold=True)
            typer.echo(f"Tasks with commits: {result['tasks_with_commits_count']}")
            typer.echo(f"Tasks without commits: {result['tasks_without_commits_count']}")
            typer.echo(f"Coverage: {result['coverage_percentage']:.1f}%")

            if result['tasks_without_commits']:
                typer.secho(f"\nTasks Without Commits ({len(result['tasks_without_commits'])}):", fg=typer.colors.YELLOW)
                for task in result['tasks_without_commits'][:20]:  # Show first 20
                    priority = task['priority'] or 'none'
                    typer.echo(f"  - #{task['id']}: {task['title']} (priority: {priority}, state: {task['state']})")
                if result['tasks_without_commits_count'] > 20:
                    typer.echo(f"  ... and {result['tasks_without_commits_count'] - 20} more")
            typer.echo()

    except Exception as e:
        typer.secho(f"Failed to check task coverage: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("visualize")
def graph_visualize_export(
    ctx: typer.Context,
    output: Path = typer.Argument(..., help="Output file path (.graphml, .dot, or .json)"),
    node_types: Optional[str] = typer.Option(None, help="Comma-separated node types (e.g., 'Task,File,Symbol')"),
    relationship_types: Optional[str] = typer.Option(None, help="Comma-separated relationship types"),
    max_nodes: int = typer.Option(1000, help="Maximum nodes to export"),
    format: str = typer.Option(None, help="Format: graphml, dot, json (auto-detected from extension)"),
    d3: bool = typer.Option(False, help="Export in D3.js format (for JSON only)"),
    layout: str = typer.Option("dot", help="Graphviz layout: dot, neato, fdp, circo, twopi"),
):
    """Export knowledge graph to visualization format.

    Formats:
    - GraphML (.graphml): For Gephi, Cytoscape, yEd
    - DOT (.dot): For Graphviz (render with: dot -Tpng output.dot -o output.png)
    - JSON (.json): For custom visualization or D3.js

    Examples:
      idlergear graph visualize graph.graphml --node-types "Task,File"
      idlergear graph visualize graph.dot --max-nodes 100 --layout neato
      idlergear graph visualize graph.json --d3
    """
    try:
        from idlergear.graph.database import get_database
        from idlergear.graph.visualize import GraphVisualizer

        # Parse node/relationship types
        node_list = node_types.split(",") if node_types else None
        rel_list = relationship_types.split(",") if relationship_types else None

        # Auto-detect format from extension
        if format is None:
            suffix = output.suffix.lower()
            if suffix == ".graphml":
                format = "graphml"
            elif suffix == ".dot":
                format = "dot"
            elif suffix == ".json":
                format = "json"
            else:
                typer.secho("Unknown file extension. Please specify --format", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)

        db = get_database()
        viz = GraphVisualizer(db)

        # Export based on format
        if format == "graphml":
            result = viz.export_graphml(output, node_list, rel_list, max_nodes)
        elif format == "dot":
            result = viz.export_dot(output, node_list, rel_list, max_nodes, layout)
        elif format == "json":
            json_format = "d3" if d3 else "raw"
            result = viz.export_json(output, node_list, rel_list, max_nodes, json_format)
        else:
            typer.secho(f"Unknown format: {format}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

        if ctx.obj.get("output_mode") == "json":
            typer.echo(json.dumps(result, indent=2))
        else:
            typer.secho(f"\n✅ Graph exported successfully!", fg=typer.colors.GREEN)
            typer.echo(f"Format: {format}")
            typer.echo(f"Nodes: {result['nodes']}")
            typer.echo(f"Edges: {result['edges']}")
            typer.echo(f"Output: {result['output']}")

            if 'render_command' in result:
                typer.secho(f"\n💡 Render with:", fg=typer.colors.CYAN)
                typer.echo(f"  {result['render_command']}")
            typer.echo()

    except Exception as e:
        typer.secho(f"Failed to export graph: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("visualize-task")
def graph_visualize_task(
    ctx: typer.Context,
    task_id: int = typer.Argument(..., help="Task ID to visualize"),
    output: Path = typer.Argument(..., help="Output file path"),
    depth: int = typer.Option(2, help="Relationship depth (1=direct, 2=2nd degree)"),
    format: str = typer.Option("dot", help="Format: graphml, dot, json"),
):
    """Visualize task and its connected nodes (commits, files, symbols).

    Shows the task's implementation network:
    - Files modified by the task
    - Commits implementing the task
    - Symbols changed

    Example:
      idlergear graph visualize-task 337 task_337.dot --depth 2
      dot -Tpng task_337.dot -o task_337.png
    """
    try:
        from idlergear.graph.database import get_database
        from idlergear.graph.visualize import GraphVisualizer

        db = get_database()
        viz = GraphVisualizer(db)

        result = viz.visualize_task_network(task_id, output, depth, format)

        if ctx.obj.get("output_mode") == "json":
            typer.echo(json.dumps(result, indent=2))
        else:
            typer.secho(f"\n✅ Task network exported!", fg=typer.colors.GREEN)
            typer.echo(f"Task: #{task_id}")
            typer.echo(f"Nodes: {result['nodes']}")
            typer.echo(f"Edges: {result['edges']}")
            typer.echo(f"Output: {result['output']}")
            typer.echo()

    except Exception as e:
        typer.secho(f"Failed to visualize task: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@graph_app.command("visualize-deps")
def graph_visualize_deps(
    ctx: typer.Context,
    file_path: str = typer.Argument(..., help="File path to analyze"),
    output: Path = typer.Argument(..., help="Output file path"),
    depth: int = typer.Option(2, help="Import depth (how many hops to follow)"),
    format: str = typer.Option("dot", help="Format: graphml, dot, json"),
):
    """Visualize file dependencies (imports, calls).

    Shows the dependency network:
    - Files imported by this file
    - Files that import this file
    - Transitive dependencies

    Example:
      idlergear graph visualize-deps src/main.py deps.dot --depth 3
      dot -Tpng deps.dot -o deps.png
    """
    try:
        from idlergear.graph.database import get_database
        from idlergear.graph.visualize import GraphVisualizer

        db = get_database()
        viz = GraphVisualizer(db)

        result = viz.visualize_dependency_graph(file_path, output, depth, format)

        if ctx.obj.get("output_mode") == "json":
            typer.echo(json.dumps(result, indent=2))
        else:
            typer.secho(f"\n✅ Dependency graph exported!", fg=typer.colors.GREEN)
            typer.echo(f"File: {file_path}")
            typer.echo(f"Nodes: {result['nodes']}")
            typer.echo(f"Edges: {result['edges']}")
            typer.echo(f"Output: {result['output']}")
            typer.echo()

    except Exception as e:
        typer.secho(f"Failed to visualize dependencies: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
