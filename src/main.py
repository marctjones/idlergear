import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import typer

from dotenv import load_dotenv
from github import Github

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ProjectStatus = importlib.import_module("src.status").ProjectStatus
ProjectContext = importlib.import_module("src.context").ProjectContext
ProjectChecker = importlib.import_module("src.check").ProjectChecker
ProjectSync = importlib.import_module("src.sync").ProjectSync
LogCoordinator = importlib.import_module("src.logs").LogCoordinator
MessageManager = importlib.import_module("src.messages").MessageManager
CoordRepo = importlib.import_module("src.coord").CoordRepo
TeleportTracker = importlib.import_module("src.teleport").TeleportTracker

app = typer.Typer()
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def get_github_token():
    """


    Retrieves the GitHub token using a multi-step strategy.


    1. Prioritize the .env file for a user-provided token.


    2. Fall back to the gh CLI.


    """

    # 1. Prioritize .env file

    load_dotenv()

    token = os.getenv("GITHUB_TOKEN")

    if token:

        return token

    # 2. Fallback to gh CLI

    try:

        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        )

        return result.stdout.strip()

    except (subprocess.CalledProcessError, FileNotFoundError):

        # gh CLI not installed or not logged in

        return None


@app.callback(context_settings=CONTEXT_SETTINGS)
def main(ctx: typer.Context):
    """
    IdlerGear: A meta-assistant for managing development workflows.
    """
    token = get_github_token()
    if token:
        from github import Auth

        auth = Auth.Token(token)
        g = Github(auth=auth)
        ctx.obj = g
    else:
        # GitHub not available - commands that need it will check ctx.obj
        ctx.obj = None


@app.command()
def setup_template(ctx: typer.Context):
    """
    Creates the 'idlergear-template' repository on GitHub.
    This repository will be used as the template for all new projects.
    """
    g: Github = ctx.obj
    if not g:
        typer.secho(
            "Error: GitHub token not found.\n"
            "Please either log in with the GitHub CLI (`gh auth login`) "
            "or create a .env file with GITHUB_TOKEN='your_pat_here'.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    user = g.get_user()
    repo_name = "idlergear-template"

    typer.echo(f"Checking for repository '{repo_name}' on user '{user.login}'...")

    try:
        user.get_repo(repo_name)
        typer.secho(f"Repository '{repo_name}' already exists.", fg=typer.colors.YELLOW)
        raise typer.Exit()
    except Exception:
        typer.echo(f"Repository '{repo_name}' not found. Creating it now...")

    try:
        repo = user.create_repo(
            name=repo_name,
            description="The template repository for projects created with IdlerGear.",
            private=True,
            auto_init=True,  # Creates with a README
        )
        typer.secho(
            f"Successfully created private repository '{repo.full_name}'",
            fg=typer.colors.GREEN,
        )
    except Exception as e:
        typer.secho(f"Failed to create repository: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


def replace_placeholders(directory: str, context: dict):
    """
    Replaces placeholders in all files in a directory.
    """
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, "r") as f:
                    content = f.read()

                for key, value in context.items():
                    content = content.replace(f"{{{{{key}}}}}", value)

                with open(filepath, "w") as f:
                    f.write(content)
            except UnicodeDecodeError:
                # Ignore binary files that can't be read as text
                pass


@app.command()
def new(
    ctx: typer.Context,
    project_name: str,
    lang: str = typer.Option("python", "--lang", "-l"),
    path: str = typer.Option(
        None,
        "--path",
        "-p",
        help="Directory to create project in (default: current directory)",
    ),
):
    """
    Creates a new project from the idlergear-template.
    """
    g: Github = ctx.obj
    if not g:
        typer.secho(
            "Error: GitHub token not found.\n"
            "Please either log in with the GitHub CLI (`gh auth login`) "
            "or create a .env file with GITHUB_TOKEN='your_pat_here'.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    user = g.get_user()
    template_repo_name = "idlergear-template"

    typer.echo(f"Authenticated as {user.login}.")

    # Determine the target directory
    if path:
        target_dir = os.path.abspath(path)
    else:
        target_dir = os.getcwd()

    project_path = os.path.join(target_dir, project_name)

    # Check if we're inside the idlergear repository
    try:
        idlergear_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            cwd=target_dir,
        ).stdout.strip()

        if "idlergear" in idlergear_root.lower() and target_dir.startswith(
            idlergear_root
        ):
            typer.secho(
                "Warning: You're trying to create a project inside the idlergear repository.",
                fg=typer.colors.YELLOW,
            )
            typer.secho(
                "Consider using --path to specify a different location (e.g., ~/projects)",
                fg=typer.colors.YELLOW,
            )
            if not typer.confirm("Continue anyway?"):
                raise typer.Exit(0)
    except subprocess.CalledProcessError:
        # Not in a git repository, that's fine
        pass

    # 1. Get the template repository
    try:
        template_repo = user.get_repo(template_repo_name)
        typer.echo(f"Found template repository: {template_repo.full_name}")
    except Exception:
        typer.secho(
            f"Error: Template repository '{template_repo_name}' not found.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    # 2. Create a new repository from the template
    try:
        typer.echo(f"Creating new private repository '{project_name}' from template...")
        new_repo = user.create_repo_from_template(
            name=project_name,
            repo=template_repo,
            private=True,
        )
        typer.secho(
            f"Successfully created repository '{new_repo.full_name}'",
            fg=typer.colors.GREEN,
        )

        # Wait for GitHub to finish generating the repository from template
        import time

        typer.echo("Waiting for GitHub to generate repository from template...")
        time.sleep(5)

    except Exception as e:
        typer.secho(
            f"Failed to create repository from template: {e}", fg=typer.colors.RED
        )
        raise typer.Exit(1)

    # 3. Clone the new repository
    try:
        typer.echo(f"Cloning repository into '{project_path}'...")
        subprocess.run(
            ["git", "clone", new_repo.clone_url, project_path],
            check=True,
            capture_output=True,
        )
        typer.secho("Successfully cloned repository.", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError as e:
        typer.secho(
            f"Failed to clone repository: {e.stderr.decode()}", fg=typer.colors.RED
        )
        raise typer.Exit(1)

    # 4. Replace placeholders
    typer.echo("Replacing placeholders...")
    replace_placeholders(project_path, {"PROJECT_NAME": project_name})
    typer.secho("Placeholders replaced.", fg=typer.colors.GREEN)

    # 5. Initial commit and push (only if there are changes)
    try:
        # Check if there are any files to commit
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True,
        )

        if status_result.stdout.strip():
            typer.echo("Configuring git user...")
            subprocess.run(
                ["git", "config", "user.name", user.login],
                cwd=project_path,
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "config",
                    "user.email",
                    user.email or f"{user.login}@users.noreply.github.com",
                ],
                cwd=project_path,
                check=True,
            )

            typer.echo("Committing and pushing initial project setup...")
            subprocess.run(
                ["git", "add", "."],
                cwd=project_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "feat: Customize project from template"],
                cwd=project_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "push"],
                cwd=project_path,
                check=True,
                capture_output=True,
            )
            typer.secho(
                "Changes committed and pushed successfully.", fg=typer.colors.GREEN
            )
        else:
            typer.secho(
                "No changes to commit (template already customized).",
                fg=typer.colors.GREEN,
            )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        typer.secho(f"Failed to commit and push: {error_msg}", fg=typer.colors.RED)
        typer.secho(
            "Project created but not fully configured. You can manually complete setup.",
            fg=typer.colors.YELLOW,
        )
        # Don't exit - project was created successfully

    typer.echo(f"\n✅ Project '{project_name}' created successfully!")
    typer.echo(f"   cd {project_path}")


@app.command()
def ask(llm: str, prompt: str):
    """
    Asks a question to the specified LLM.
    """
    typer.echo(f"Asking {llm}: '{prompt}'")


@app.command()
def status(
    path: str = typer.Option(".", "--path", "-p", help="Project directory to check")
):
    """
    Show project health and status.

    Displays:
    - Git status (branch, uncommitted changes, recent commits)
    - Charter document freshness (VISION.md, TODO.md, etc.)
    - LLM-managed branches
    - Project location and name
    """
    try:
        project_status = ProjectStatus(path)
        output = project_status.format_status()
        typer.echo(output)
    except Exception as e:
        typer.secho(f"Error getting project status: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def context(
    path: str = typer.Option(".", "--path", "-p", help="Project directory"),
    format: str = typer.Option(
        "markdown", "--format", "-f", help="Output format: markdown or json"
    ),
    output: str = typer.Option(
        None, "--output", "-o", help="Write to file instead of stdout"
    ),
):
    """
    Generate LLM-ready project context.

    Collects and formats:
    - All charter documents (VISION, TODO, IDEAS, DESIGN, etc.)
    - Recent git activity and current status
    - Project structure overview
    - Formatted for easy LLM consumption

    Output can be piped directly to an LLM or saved to a file.

    Examples:
      # Generate context and display
      idlergear context

      # Save to file
      idlergear context --output context.md

      # JSON format for programmatic use
      idlergear context --format json

      # Pipe to LLM
      idlergear context | gemini "Analyze this project"
    """
    try:
        context_gen = ProjectContext(path)

        if format == "json":
            output_text = context_gen.format_json()
        else:
            output_text = context_gen.format_markdown()

        if output:
            # Write to file
            output_path = Path(output)
            output_path.write_text(output_text)
            typer.secho(f"✅ Context written to {output}", fg=typer.colors.GREEN)
        else:
            # Print to stdout
            typer.echo(output_text)

    except Exception as e:
        typer.secho(f"Error generating context: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def check(
    path: str = typer.Option(".", "--path", "-p", help="Project directory to check")
):
    """
    Analyze project for best practice adherence.

    Checks for:
    - Missing tests in recent commits
    - Stale charter documents
    - Excessive uncommitted changes
    - Dangling branches needing cleanup
    - Missing project files
    - Multi-LLM coordination opportunities

    Provides actionable suggestions for improvement.
    """
    try:
        checker = ProjectChecker(path)
        checker.run_all_checks()
        report = checker.format_report()
        typer.echo(report)
    except Exception as e:
        typer.secho(f"Error checking project: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command(name="sync")
def sync_command(
    action: str = typer.Argument(..., help="Action: push, pull, or status"),
    path: str = typer.Option(".", "--path", "-p", help="Project directory"),
    include_untracked: bool = typer.Option(
        False, "--include-untracked", "-u", help="Include untracked files (push only)"
    ),
    no_cleanup: bool = typer.Option(
        False, "--no-cleanup", help="Don't cleanup sync branch (pull only)"
    ),
):
    """
    Coordinate work between local and web LLM environments.

    Actions:
      push   - Push current state to sync branch for web environment
      pull   - Pull changes from sync branch to current branch
      status - Check sync branch status

    Workflow:
      1. Work locally with Gemini CLI
      2. idlergear sync push
      3. Open Claude Code Web, switch to sync branch
      4. Work in web environment
      5. idlergear sync pull
      6. Continue locally
    """
    try:
        syncer = ProjectSync(path)

        if action == "push":
            typer.echo("🔄 Pushing to web sync branch...")
            result = syncer.sync_push(include_untracked=include_untracked)

            typer.secho(
                f"✅ Pushed to sync branch: {result['sync_branch']}",
                fg=typer.colors.GREEN,
            )
            typer.echo(f"   From: {result['current_branch']}")
            if result["created_branch"]:
                typer.echo("   Created new sync branch")
            if result["committed_changes"]:
                typer.echo("   Committed changes")
            typer.echo("")
            typer.echo("📱 Next steps:")
            typer.echo("   1. Open your web LLM tool (Claude Web, Copilot Web, etc.)")
            typer.echo(f"   2. Switch to branch: {result['sync_branch']}")
            typer.echo("   3. Work in web environment")
            typer.echo("   4. Run: idlergear sync pull")

        elif action == "pull":
            typer.echo("🔄 Pulling from web sync branch...")
            result = syncer.sync_pull(cleanup=not no_cleanup)

            typer.secho(
                f"✅ Pulled from sync branch: {result['sync_branch']}",
                fg=typer.colors.GREEN,
            )
            typer.echo(f"   To: {result['current_branch']}")
            if result["merged"]:
                typer.echo("   Merged changes successfully")
            if result["cleaned_up"]:
                typer.echo("   Cleaned up sync branch")

        elif action == "status":
            result = syncer.sync_status()

            typer.echo("")
            typer.echo("📊 Sync Status")
            typer.echo(f"   Current branch: {result['current_branch']}")
            typer.echo(f"   Sync branch: {result['sync_branch']}")
            typer.echo(
                f"   Local exists: {'Yes ✅' if result['local_exists'] else 'No'}"
            )
            typer.echo(
                f"   Remote exists: {'Yes ✅' if result['remote_exists'] else 'No'}"
            )
            typer.echo(f"   Uncommitted changes: {result['uncommitted_changes']}")

            if result["ahead_behind"]:
                ahead = result["ahead_behind"]["ahead"]
                behind = result["ahead_behind"]["behind"]
                typer.echo(f"   Status: {ahead} ahead, {behind} behind")

                if behind > 0:
                    typer.echo("")
                    typer.secho(
                        "   💡 Web environment has changes. Run: idlergear sync pull",
                        fg=typer.colors.YELLOW,
                    )
                elif ahead > 0:
                    typer.echo("")
                    typer.secho(
                        "   💡 Local has changes. Run: idlergear sync push",
                        fg=typer.colors.YELLOW,
                    )
            typer.echo("")

        else:
            typer.secho(
                f"Unknown action: {action}. Use: push, pull, or status",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)

    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def logs(
    action: str = typer.Argument(
        ..., help="Action: run, pipe, list, show, export, or cleanup"
    ),
    session_id: int = typer.Option(None, "--session", "-s", help="Session ID"),
    command: str = typer.Option(
        None, "--command", "-c", help="Command to run with capture"
    ),
    name: str = typer.Option(None, "--name", "-n", help="Session name"),
    source: str = typer.Option(
        None, "--source", help="Source description for piped input"
    ),
    tail: int = typer.Option(None, "--tail", "-t", help="Show last N lines"),
    output: str = typer.Option(None, "--output", "-o", help="Export output file"),
    days: int = typer.Option(7, "--days", "-d", help="Days to keep logs (cleanup)"),
    path: str = typer.Option(".", "--path", "-p", help="Project directory"),
):
    """
    Capture and manage logs from shell scripts and processes.

    Actions:
      run     - Run command and capture all output
      pipe    - Capture input from stdin (piped data)
      list    - List all log sessions
      show    - Show log for a session
      export  - Export session log to file
      cleanup - Delete old log files

    Examples:
      # Run a script and capture logs
      idlergear logs run --command "npm run dev" --name dev-server

      # Pipe output from another command
      ./run.sh | idlergear logs pipe --name my-app --source run.sh
      tail -f /var/log/app.log | idlergear logs pipe --name app-monitor

      # List all sessions
      idlergear logs list

      # Show log output
      idlergear logs show --session 1
      idlergear logs show --session 1 --tail 50

      # Export a log
      idlergear logs export --session 1 --output dev.log

      # Clean up old logs
      idlergear logs cleanup --days 7
    """
    try:
        coordinator = LogCoordinator(path)

        if action == "run":
            if not command:
                typer.secho(
                    "Error: --command required for 'run' action", fg=typer.colors.RED
                )
                raise typer.Exit(1)

            # Parse command string into list
            import shlex

            cmd_parts = shlex.split(command)

            typer.echo("🎬 Starting log capture...")
            typer.echo(f"   Command: {command}")
            if name:
                typer.echo(f"   Name: {name}")

            session = coordinator.run_with_capture(cmd_parts, name=name, cwd=path)

            typer.secho(
                f"\n✅ Session {session['session_id']} started", fg=typer.colors.GREEN
            )
            typer.echo(f"   Log file: {session['log_file']}")
            typer.echo(f"   PID: {session.get('pid', 'starting...')}")
            typer.echo(
                f"\n   View logs: idlergear logs show --session {session['session_id']}"
            )
            typer.echo(
                f"   Tail logs: idlergear logs show --session {session['session_id']} --tail 50"
            )

        elif action == "pipe":
            # Capture from stdin
            typer.echo("📥 Capturing from stdin...")
            if name:
                typer.echo(f"   Name: {name}")
            if source:
                typer.echo(f"   Source: {source}")
            typer.echo("   Reading... (Ctrl+D to end, Ctrl+C to stop)")
            typer.echo("")

            session = coordinator.capture_stdin(name=name, source=source)

            typer.echo("")
            status_icon = {"completed": "✅", "stopped": "⏹️", "failed": "❌"}.get(
                session["status"], "❓"
            )

            typer.secho(
                f"{status_icon} Capture {session['status']}",
                fg=(
                    typer.colors.GREEN
                    if session["status"] == "completed"
                    else typer.colors.YELLOW
                ),
            )
            typer.echo(f"   Session ID: {session['session_id']}")
            typer.echo(f"   Lines captured: {session.get('line_count', 0)}")
            typer.echo(f"   Log file: {session['log_file']}")
            typer.echo(
                f"\n   View: idlergear logs show --session {session['session_id']}"
            )

        elif action == "list":
            sessions = coordinator.list_sessions()

            if not sessions:
                typer.echo("📋 No log sessions found")
                return

            typer.echo("")
            typer.echo(f"📋 Log Sessions ({len(sessions)} total)")
            typer.echo("=" * 80)
            typer.echo("")

            for session in sessions:
                status_icon = {
                    "running": "🟢",
                    "completed": "✅",
                    "stopped": "⏹️",
                    "failed": "❌",
                }.get(session["status"], "❓")

                typer.echo(
                    f"{status_icon} Session {session['session_id']}: {session['name']}"
                )
                typer.echo(f"   Status: {session['status']}")
                typer.echo(f"   Started: {session['started']}")
                if "command" in session:
                    typer.echo(f"   Command: {session['command']}")
                if (
                    session["status"] in ["completed", "stopped", "failed"]
                    and "ended" in session
                ):
                    typer.echo(f"   Ended: {session['ended']}")
                typer.echo("")

        elif action == "show":
            if session_id is None:
                typer.secho(
                    "Error: --session required for 'show' action", fg=typer.colors.RED
                )
                raise typer.Exit(1)

            session = coordinator.get_session(session_id)
            if not session:
                typer.secho(
                    f"Error: Session {session_id} not found", fg=typer.colors.RED
                )
                raise typer.Exit(1)

            log_content = coordinator.read_log(session_id, tail=tail)

            typer.echo("")
            typer.echo(f"📄 Session {session_id}: {session['name']}")
            typer.echo(f"   Status: {session['status']}")
            if tail:
                typer.echo(f"   Showing last {tail} lines")
            typer.echo("─" * 80)
            typer.echo(log_content)

        elif action == "export":
            if session_id is None:
                typer.secho(
                    "Error: --session required for 'export' action", fg=typer.colors.RED
                )
                raise typer.Exit(1)
            if not output:
                typer.secho(
                    "Error: --output required for 'export' action", fg=typer.colors.RED
                )
                raise typer.Exit(1)

            result_path = coordinator.export_session(session_id, output)
            typer.secho(f"✅ Exported to: {result_path}", fg=typer.colors.GREEN)

        elif action == "cleanup":
            typer.echo(f"🧹 Cleaning up logs older than {days} days...")
            deleted = coordinator.cleanup_old_logs(days=days)
            typer.secho(f"✅ Deleted {deleted} old log file(s)", fg=typer.colors.GREEN)

        else:
            typer.secho(f"Unknown action: {action}", fg=typer.colors.RED)
            typer.echo("Valid actions: run, pipe, list, show, export, cleanup")
            raise typer.Exit(1)

    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command(name="message")
def message_command(
    action: str = typer.Argument(..., help="Action: send, list, read, or respond"),
    message_id: str = typer.Option(None, "--id", help="Message ID"),
    to: str = typer.Option(None, "--to", help="Target environment for send/respond"),
    body: str = typer.Option(None, "--body", help="Message content"),
    from_env: str = typer.Option("local", "--from", help="Source environment"),
    unread_only: bool = typer.Option(False, "--unread", help="Show only unread"),
    filter_to: str = typer.Option(
        None, "--filter-to", help="Only list messages for this destination"
    ),
    filter_from: str = typer.Option(
        None, "--filter-from", help="Only list messages from this source"
    ),
    path: str = typer.Option(".", "--path", "-p", help="Project directory"),
):
    """Send/receive messages between LLM environments via git sync branches."""
    try:
        manager = MessageManager(path)

        if action == "send":
            if not to or not body:
                typer.secho("Error: --to and --body required", fg=typer.colors.RED)
                raise typer.Exit(1)
            msg_id = manager.send_message(to=to, body=body, from_env=from_env)
            typer.secho(f"✅ Message {msg_id} sent", fg=typer.colors.GREEN)
            typer.echo("Next: idlergear sync push --include-untracked")

        elif action == "list":
            messages = manager.list_messages(
                filter_to=filter_to,
                filter_from=filter_from,
                unread_only=unread_only,
            )
            typer.echo(manager.format_message_list(messages))

        elif action == "read":
            if not message_id:
                typer.secho("Error: --id required", fg=typer.colors.RED)
                raise typer.Exit(1)
            message = manager.read_message(message_id)
            if not message:
                typer.secho(f"Message {message_id} not found", fg=typer.colors.RED)
                raise typer.Exit(1)
            typer.echo(manager.format_message(message))

        elif action == "respond":
            if not message_id or not body:
                typer.secho("Error: --id and --body required", fg=typer.colors.RED)
                raise typer.Exit(1)
            response_id = manager.respond_to_message(message_id, body, from_env)
            typer.secho(f"✅ Response {response_id} sent", fg=typer.colors.GREEN)

        else:
            typer.secho(f"Unknown action: {action}", fg=typer.colors.RED)
            raise typer.Exit(1)

    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command(name="coord")
def coord_command(
    action: str = typer.Argument(..., help="Action: init, send, or read"),
    project: str = typer.Option(None, "--project", help="Project name for messaging"),
    message: str = typer.Option(None, "--message", "-m", help="Message to send"),
    to: str = typer.Option("web", "--to", help="Target environment"),
    via: str = typer.Option("file", "--via", help="Method: file or issue"),
):
    """
    Coordinate between LLM environments via private coordination repo.

    The coordination repo is a private GitHub repository used for:
    - Message passing between local and web LLM tools
    - Coordination data storage across environments
    - Issue-based or file-based communication

    Actions:
      init  - Initialize coordination repository
      send  - Send message to another LLM environment
      read  - Read messages for current project

    Examples:
      # Initialize coordination repo (one-time setup)
      idlergear coord init

      # Send message via files
      idlergear coord send --project my-app --message "Please review auth.py"

      # Send message via GitHub issues
      idlergear coord send --project my-app --message "Fix tests" --via issue

      # Read messages
      idlergear coord read --project my-app
      idlergear coord read --project my-app --via issue
    """
    try:
        coordinator = CoordRepo()

        if action == "init":
            typer.echo("🔧 Initializing coordination repository...")
            result = coordinator.init()

            if result["status"] == "created":
                typer.secho("✅ Created coordination repo", fg=typer.colors.GREEN)
                typer.echo(f"   Repo: {result['repo_url']}")
                typer.echo(f"   Path: {result['path']}")
            elif result["status"] == "already_exists":
                typer.secho(
                    "ℹ️  Coordination repo already exists", fg=typer.colors.YELLOW
                )
                typer.echo(f"   Path: {result['path']}")
            else:
                typer.secho(
                    f"❌ Error: {result.get('error', 'Unknown error')}",
                    fg=typer.colors.RED,
                )
                raise typer.Exit(1)

        elif action == "send":
            if not project or not message:
                typer.secho(
                    "Error: --project and --message required", fg=typer.colors.RED
                )
                raise typer.Exit(1)

            typer.echo(f"📤 Sending message to {to} environment...")
            result = coordinator.send_message(project, message, to=to, via=via)

            if result["status"] == "sent":
                typer.secho("✅ Message sent", fg=typer.colors.GREEN)
                if via == "file":
                    typer.echo(f"   Message ID: {result['message_id']}")
                    typer.echo("   Method: File-based")
                elif via == "issue":
                    typer.echo(f"   Issue: {result['issue_url']}")
                    typer.echo("   Method: GitHub Issue")
            else:
                typer.secho(
                    f"❌ Error: {result.get('error', 'Unknown error')}",
                    fg=typer.colors.RED,
                )
                raise typer.Exit(1)

        elif action == "read":
            if not project:
                typer.secho("Error: --project required", fg=typer.colors.RED)
                raise typer.Exit(1)

            typer.echo(f"📥 Reading messages for project: {project}")
            result = coordinator.read_messages(project, via=via)

            if result["status"] == "ok":
                messages = result["messages"]
                if not messages:
                    typer.echo("   No messages found")
                else:
                    typer.echo(f"   Found {result['count']} message(s)")
                    typer.echo("")

                    for msg in messages:
                        if via == "file":
                            typer.echo(f"📨 Message {msg['id']}")
                            typer.echo(f"   From: {msg['from']} → To: {msg['to']}")
                            typer.echo(f"   Time: {msg['timestamp']}")
                            typer.echo(f"   {msg['message']}")
                        elif via == "issue":
                            typer.echo(f"📨 Issue #{msg['number']}: {msg['title']}")
                            typer.echo(f"   Created: {msg['createdAt']}")
                            typer.echo(f"   State: {msg['state']}")
                            typer.echo(f"   {msg['body'][:100]}...")
                        typer.echo("")
            else:
                typer.secho(
                    f"❌ Error: {result.get('error', 'Unknown error')}",
                    fg=typer.colors.RED,
                )
                raise typer.Exit(1)

        else:
            typer.secho(
                f"Unknown action: {action}. Use: init, send, or read",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)

    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def mcp(
    action: str = typer.Argument("start", help="Action: start or info"),
):
    """
    Start or manage the MCP (Model Context Protocol) server.

    The MCP server exposes IdlerGear tools for LLM clients.
    - Runs on stdio (not network) for security
    - Local LLM tools can connect and invoke IdlerGear commands
    - Works with Gemini CLI, Claude Desktop, etc.

    Actions:
      start - Start the MCP server (runs until interrupted)
      info  - Show MCP server information

    Usage:
      idlergear mcp start    # Start server

    LLM tools can then discover and invoke:
      - project_status
      - project_context
      - project_check
      - sync_status, sync_push, sync_pull
    """
    if action == "start":
        try:
            import asyncio
            from src.mcp_server import main as mcp_main

            typer.secho("🚀 Starting IdlerGear MCP server...", fg=typer.colors.GREEN)
            typer.echo("   Protocol: stdio (standard input/output)")
            typer.echo("   Security: Local only")
            typer.echo("   Tools: status, context, check, sync")
            typer.echo("")
            typer.echo("   Press Ctrl+C to stop")
            typer.echo("")

            asyncio.run(mcp_main())

        except KeyboardInterrupt:
            typer.echo("")
            typer.secho("✅ MCP server stopped", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"❌ Error starting MCP server: {e}", fg=typer.colors.RED)
            raise typer.Exit(1)

    elif action == "info":
        typer.echo("")
        typer.echo("📡 IdlerGear MCP Server")
        typer.echo("=" * 60)
        typer.echo("")
        typer.echo("Protocol: Model Context Protocol (MCP)")
        typer.echo("Transport: stdio (standard input/output)")
        typer.echo("Security: Local only - no network exposure")
        typer.echo("")
        typer.echo("Available Tools:")
        typer.echo("  • project_status - Get project health and status")
        typer.echo("  • project_context - Generate LLM-ready context")
        typer.echo("  • project_check - Analyze best practices")
        typer.echo("  • sync_status - Check web sync status")
        typer.echo("  • sync_push - Push to web environment")
        typer.echo("  • sync_pull - Pull from web environment")
        typer.echo("")
        typer.echo("Compatible LLM Tools:")
        typer.echo("  • Gemini CLI")
        typer.echo("  • Claude Desktop")
        typer.echo("  • Any MCP-compatible client")
        typer.echo("")
        typer.echo("Start server:")
        typer.echo("  idlergear mcp start")
        typer.echo("")

    else:
        typer.secho(
            f"Unknown action: {action}. Use 'start' or 'info'", fg=typer.colors.RED
        )
        raise typer.Exit(1)


@app.command(name="teleport")
def teleport_command(
    action: str = typer.Argument(
        ..., help="Action: prepare, log, list, show, export, or restore-stash"
    ),
    session_id: str = typer.Option(
        None, "--session-id", "--id", help="Teleport session UUID"
    ),
    description: str = typer.Option(
        None, "--description", "-d", help="Session description"
    ),
    files: str = typer.Option(
        None, "--files", help="Comma-separated list of changed files"
    ),
    branch: str = typer.Option(None, "--branch", "-b", help="Branch name"),
    limit: int = typer.Option(
        10, "--limit", "-n", help="Limit number of sessions to show"
    ),
    output_format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text, json, or markdown"
    ),
    path: str = typer.Option(".", "--path", "-p", help="Project directory"),
):
    """
    Track and manage Claude Code web teleport sessions.

    Teleport restore is a feature in Claude Code web that transfers your
    web-based coding session to your local CLI environment. This command
    helps you track these sessions.

    Actions:
      prepare       - Prepare local environment for teleport (fetch, stash, checkout)
      log           - Log a new teleport session
      list          - List past teleport sessions
      show          - Show details of a specific session
      export        - Export session information
      restore-stash - Restore stashed changes after teleport

    Examples:
      # Prepare for teleport (recommended first step)
      idlergear teleport prepare --branch feature/my-feature

      # Then run teleport
      claude --teleport abc-123-def

      # Log the session
      idlergear teleport log --session-id abc-123-def --description "Feature X"

      # Restore any stashed changes
      idlergear teleport restore-stash

      # List recent sessions
      idlergear teleport list

      # Show session details
      idlergear teleport show --session-id abc-123
    """
    try:
        tracker = TeleportTracker(path)

        if action == "prepare":
            if not branch:
                typer.secho("Error: --branch required for prepare", fg=typer.colors.RED)
                raise typer.Exit(1)

            typer.echo(f"🚀 Preparing for teleport to branch '{branch}'...")
            typer.echo("")

            result = tracker.prepare_for_teleport(branch)

            for message in result.get("messages", []):
                typer.echo(message)

            if result["status"] == "ok":
                typer.echo("")
                typer.secho("✅ Ready for teleport!", fg=typer.colors.GREEN)
            else:
                typer.echo("")
                typer.secho(
                    f"❌ Error: {result.get('error', 'Unknown error')}",
                    fg=typer.colors.RED,
                )
                raise typer.Exit(1)

        elif action == "restore-stash":
            typer.echo("🔄 Restoring stashed changes...")

            result = tracker.restore_stash()

            if result["status"] == "restored":
                typer.secho(f"✅ {result['message']}", fg=typer.colors.GREEN)
            elif result["status"] == "no_stash":
                typer.secho(f"ℹ️  {result['message']}", fg=typer.colors.YELLOW)
            else:
                typer.secho(
                    f"❌ {result.get('message', result.get('error', 'Unknown error'))}",
                    fg=typer.colors.RED,
                )
                raise typer.Exit(1)

        elif action == "log":
            if not session_id:
                typer.secho("Error: --session-id required", fg=typer.colors.RED)
                raise typer.Exit(1)

            # Parse files if provided
            files_list = None
            if files:
                files_list = [f.strip() for f in files.split(",")]

            typer.echo(f"📍 Logging teleport session: {session_id[:8]}...")

            result = tracker.log_session(
                session_id=session_id,
                description=description,
                files_changed=files_list,
                branch=branch,
            )

            if result["status"] == "created":
                typer.secho("✅ Session logged", fg=typer.colors.GREEN)
            else:
                typer.secho("✅ Session updated", fg=typer.colors.GREEN)

            session = result["session"]
            typer.echo(f"   Session: {session['session_id'][:8]}")
            typer.echo(f"   Branch: {session['branch']}")
            typer.echo(f"   Files changed: {session['files_count']}")
            typer.echo(f"   Saved to: {result['session_file']}")

        elif action == "list":
            # Get branch filter if specified
            branch_filter = branch

            sessions = tracker.list_sessions(limit=limit, branch=branch_filter)

            if output_format == "json":
                typer.echo(json.dumps(sessions, indent=2))
            elif output_format == "markdown":
                if not sessions:
                    typer.echo("No sessions found.")
                else:
                    for session in sessions:
                        typer.echo(tracker._format_session_markdown(session))
                        typer.echo("")
            else:  # text
                typer.echo(tracker.format_session_list(sessions))

        elif action == "show":
            if not session_id:
                typer.secho("Error: --session-id required", fg=typer.colors.RED)
                raise typer.Exit(1)

            session = tracker.get_session(session_id)

            if not session:
                typer.secho(f"Session not found: {session_id}", fg=typer.colors.RED)
                raise typer.Exit(1)

            if output_format == "json":
                typer.echo(json.dumps(session, indent=2))
            elif output_format == "markdown":
                typer.echo(tracker._format_session_markdown(session))
            else:  # text
                typer.echo(tracker.format_session(session))

        elif action == "export":
            if not session_id:
                typer.secho("Error: --session-id required", fg=typer.colors.RED)
                raise typer.Exit(1)

            export_format = (
                output_format if output_format in ["json", "markdown"] else "json"
            )
            result = tracker.export_session(session_id, export_format)

            typer.echo(result["content"])

        else:
            typer.secho(
                f"Unknown action: {action}. Use: prepare, log, list, show, export, or restore-stash",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)

    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
