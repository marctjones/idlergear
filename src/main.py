import typer
import os
import subprocess
from dotenv import load_dotenv
from github import Github
from src.status import ProjectStatus
from src.context import ProjectContext
from src.check import ProjectChecker
from src.sync import ProjectSync

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
    if not token:
        typer.secho(
            "Error: GitHub token not found.\n"
            "Please either log in with the GitHub CLI (`gh auth login`) "
            "or create a .env file with GITHUB_TOKEN='your_pat_here'.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    g = Github(token)
    ctx.obj = g


@app.command()
def setup_template(ctx: typer.Context):
    """
    Creates the 'idlergear-template' repository on GitHub.
    This repository will be used as the template for all new projects.
    """
    g: Github = ctx.obj
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
    path: str = typer.Option(None, "--path", "-p", help="Directory to create project in (default: current directory)"),
):
    """
    Creates a new project from the idlergear-template.
    """
    g: Github = ctx.obj
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
            cwd=target_dir
        ).stdout.strip()
        
        if "idlergear" in idlergear_root.lower() and target_dir.startswith(idlergear_root):
            typer.secho(
                f"Warning: You're trying to create a project inside the idlergear repository.",
                fg=typer.colors.YELLOW,
            )
            typer.secho(
                f"Consider using --path to specify a different location (e.g., ~/projects)",
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
                ["git", "config", "user.email", user.email or f"{user.login}@users.noreply.github.com"],
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
            typer.secho("Changes committed and pushed successfully.", fg=typer.colors.GREEN)
        else:
            typer.secho("No changes to commit (template already customized).", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        typer.secho(f"Failed to commit and push: {error_msg}", fg=typer.colors.RED)
        typer.secho(f"Project created but not fully configured. You can manually complete setup.", fg=typer.colors.YELLOW)
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
def status(path: str = typer.Option(".", "--path", "-p", help="Project directory to check")):
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
def check(path: str = typer.Option(".", "--path", "-p", help="Project directory to check")):
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
    include_untracked: bool = typer.Option(False, "--include-untracked", "-u", help="Include untracked files (push only)"),
    no_cleanup: bool = typer.Option(False, "--no-cleanup", help="Don't cleanup sync branch (pull only)"),
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
            
            typer.secho(f"✅ Pushed to sync branch: {result['sync_branch']}", fg=typer.colors.GREEN)
            typer.echo(f"   From: {result['current_branch']}")
            if result['created_branch']:
                typer.echo("   Created new sync branch")
            if result['committed_changes']:
                typer.echo("   Committed changes")
            typer.echo("")
            typer.echo("📱 Next steps:")
            typer.echo(f"   1. Open your web LLM tool (Claude Web, Copilot Web, etc.)")
            typer.echo(f"   2. Switch to branch: {result['sync_branch']}")
            typer.echo(f"   3. Work in web environment")
            typer.echo(f"   4. Run: idlergear sync pull")
            
        elif action == "pull":
            typer.echo("🔄 Pulling from web sync branch...")
            result = syncer.sync_pull(cleanup=not no_cleanup)
            
            typer.secho(f"✅ Pulled from sync branch: {result['sync_branch']}", fg=typer.colors.GREEN)
            typer.echo(f"   To: {result['current_branch']}")
            if result['merged']:
                typer.echo("   Merged changes successfully")
            if result['cleaned_up']:
                typer.echo("   Cleaned up sync branch")
            
        elif action == "status":
            result = syncer.sync_status()
            
            typer.echo("")
            typer.echo(f"📊 Sync Status")
            typer.echo(f"   Current branch: {result['current_branch']}")
            typer.echo(f"   Sync branch: {result['sync_branch']}")
            typer.echo(f"   Local exists: {'Yes ✅' if result['local_exists'] else 'No'}")
            typer.echo(f"   Remote exists: {'Yes ✅' if result['remote_exists'] else 'No'}")
            typer.echo(f"   Uncommitted changes: {result['uncommitted_changes']}")
            
            if result['ahead_behind']:
                ahead = result['ahead_behind']['ahead']
                behind = result['ahead_behind']['behind']
                typer.echo(f"   Status: {ahead} ahead, {behind} behind")
                
                if behind > 0:
                    typer.echo("")
                    typer.secho("   💡 Web environment has changes. Run: idlergear sync pull", fg=typer.colors.YELLOW)
                elif ahead > 0:
                    typer.echo("")
                    typer.secho("   💡 Local has changes. Run: idlergear sync push", fg=typer.colors.YELLOW)
            typer.echo("")
            
        else:
            typer.secho(f"Unknown action: {action}. Use: push, pull, or status", fg=typer.colors.RED)
            raise typer.Exit(1)
            
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
