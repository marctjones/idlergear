"""GitHub Projects v2 integration for IdlerGear.

This module provides Kanban-style project boards that sync with GitHub Projects v2.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root, get_config_value
from idlergear.storage import now_iso, slugify
from idlergear.github_detect import get_github_owner


DEFAULT_COLUMNS = ["Backlog", "In Progress", "Review", "Done"]


def get_projects_dir(project_path: Path | None = None) -> Path | None:
    """Get the projects directory path."""
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None
    return project_path / ".idlergear" / "projects"


def _run_gh(*args: str) -> tuple[bool, str]:
    """Run a gh CLI command.

    Returns (success, output).
    """
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except FileNotFoundError:
        return False, "gh CLI not found. Install from https://cli.github.com/"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"


def create_project(
    title: str,
    columns: list[str] | None = None,
    create_on_github: bool = False,
    project_path: Path | None = None,
) -> dict[str, Any]:
    """Create a new project board.

    Args:
        title: Project title
        columns: List of column names (default: Backlog, In Progress, Review, Done)
        create_on_github: Also create on GitHub Projects v2
        project_path: Override project path

    Returns:
        Created project data
    """
    projects_dir = get_projects_dir(project_path)
    if projects_dir is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    projects_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify(title)
    filepath = projects_dir / f"{slug}.json"

    if filepath.exists():
        raise ValueError(f"Project '{title}' already exists")

    if columns is None:
        columns = DEFAULT_COLUMNS.copy()

    project_data = {
        "id": slug,
        "title": title,
        "columns": columns,
        "tasks": {col: [] for col in columns},
        "github_project_number": None,
        "github_project_id": None,
        "created_at": now_iso(),
    }

    # Create on GitHub if requested
    if create_on_github:
        owner = get_github_owner(project_path or find_idlergear_root())
        if owner:
            success, output = _run_gh(
                "project", "create",
                "--owner", owner,
                "--title", title,
                "--format", "json",
            )
            if success:
                try:
                    gh_data = json.loads(output)
                    project_data["github_project_number"] = gh_data.get("number")
                    project_data["github_project_id"] = gh_data.get("id")
                except json.JSONDecodeError:
                    pass

    filepath.write_text(json.dumps(project_data, indent=2))

    return project_data


def list_projects(project_path: Path | None = None) -> list[dict[str, Any]]:
    """List all projects.

    Returns list of project data dicts sorted by title.
    """
    projects_dir = get_projects_dir(project_path)
    if projects_dir is None or not projects_dir.exists():
        return []

    projects = []
    for filepath in sorted(projects_dir.glob("*.json")):
        try:
            data = json.loads(filepath.read_text())
            data["path"] = str(filepath)
            projects.append(data)
        except json.JSONDecodeError:
            continue

    return sorted(projects, key=lambda p: p.get("title", "").lower())


def get_project(name: str, project_path: Path | None = None) -> dict[str, Any] | None:
    """Get a project by name or slug."""
    projects_dir = get_projects_dir(project_path)
    if projects_dir is None:
        return None

    # Try direct slug match
    slug = slugify(name)
    filepath = projects_dir / f"{slug}.json"
    if filepath.exists():
        try:
            data = json.loads(filepath.read_text())
            data["path"] = str(filepath)
            return data
        except json.JSONDecodeError:
            return None

    # Fallback: scan for matching title
    for filepath in projects_dir.glob("*.json"):
        try:
            data = json.loads(filepath.read_text())
            if data.get("title", "").lower() == name.lower():
                data["path"] = str(filepath)
                return data
        except json.JSONDecodeError:
            continue

    return None


def delete_project(
    name: str,
    delete_on_github: bool = False,
    project_path: Path | None = None,
) -> bool:
    """Delete a project.

    Args:
        name: Project name or slug
        delete_on_github: Also delete from GitHub Projects
        project_path: Override project path

    Returns:
        True if deleted, False if not found
    """
    project = get_project(name, project_path)
    if project is None:
        return False

    # Delete from GitHub if requested
    if delete_on_github and project.get("github_project_id"):
        owner = get_github_owner(project_path or find_idlergear_root())
        if owner:
            _run_gh(
                "project", "delete",
                str(project["github_project_number"]),
                "--owner", owner,
                "--yes",
            )

    Path(project["path"]).unlink()
    return True


def add_task_to_project(
    project_name: str,
    task_id: str,
    column: str | None = None,
    project_path: Path | None = None,
) -> dict[str, Any] | None:
    """Add a task to a project.

    Args:
        project_name: Project name or slug
        task_id: Task ID to add
        column: Column to add to (default: first column)
        project_path: Override project path

    Returns:
        Updated project data, or None if project not found
    """
    project = get_project(project_name, project_path)
    if project is None:
        return None

    if column is None:
        column = project["columns"][0]

    if column not in project["columns"]:
        raise ValueError(f"Column '{column}' not found. Available: {project['columns']}")

    # Remove from any existing column first
    for col in project["columns"]:
        if task_id in project["tasks"].get(col, []):
            project["tasks"][col].remove(task_id)

    # Add to target column
    if task_id not in project["tasks"][column]:
        project["tasks"][column].append(task_id)

    # Save
    filepath = Path(project["path"])
    save_data = {k: v for k, v in project.items() if k != "path"}
    filepath.write_text(json.dumps(save_data, indent=2))

    return project


def remove_task_from_project(
    project_name: str,
    task_id: str,
    project_path: Path | None = None,
) -> dict[str, Any] | None:
    """Remove a task from a project.

    Returns:
        Updated project data, or None if project not found
    """
    project = get_project(project_name, project_path)
    if project is None:
        return None

    # Remove from all columns
    for col in project["columns"]:
        if task_id in project["tasks"].get(col, []):
            project["tasks"][col].remove(task_id)

    # Save
    filepath = Path(project["path"])
    save_data = {k: v for k, v in project.items() if k != "path"}
    filepath.write_text(json.dumps(save_data, indent=2))

    return project


def move_task(
    project_name: str,
    task_id: str,
    column: str,
    project_path: Path | None = None,
) -> dict[str, Any] | None:
    """Move a task to a different column.

    Returns:
        Updated project data, or None if project not found
    """
    return add_task_to_project(project_name, task_id, column, project_path)


def sync_project_to_github(
    name: str,
    project_path: Path | None = None,
) -> dict[str, Any] | None:
    """Sync a local project to GitHub Projects v2.

    Creates the project on GitHub if it doesn't exist, then syncs tasks.

    Returns:
        Updated project data with GitHub IDs, or None if project not found
    """
    project = get_project(name, project_path)
    if project is None:
        return None

    root = project_path or find_idlergear_root()
    owner = get_github_owner(root)
    if not owner:
        raise RuntimeError("Could not determine GitHub owner. Ensure you're in a git repo with a GitHub remote.")

    # Create project on GitHub if not already linked
    if not project.get("github_project_number"):
        success, output = _run_gh(
            "project", "create",
            "--owner", owner,
            "--title", project["title"],
            "--format", "json",
        )
        if success:
            try:
                gh_data = json.loads(output)
                project["github_project_number"] = gh_data.get("number")
                project["github_project_id"] = gh_data.get("id")
            except json.JSONDecodeError:
                raise RuntimeError(f"Failed to parse GitHub response: {output}")
        else:
            raise RuntimeError(f"Failed to create GitHub project: {output}")

    # Get repo for issue URLs
    success, repo_output = _run_gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
    if not success:
        raise RuntimeError("Could not determine repository")
    repo = repo_output.strip()

    # Add tasks to GitHub project
    for column, task_ids in project["tasks"].items():
        for task_id in task_ids:
            issue_url = f"https://github.com/{repo}/issues/{task_id}"
            _run_gh(
                "project", "item-add",
                str(project["github_project_number"]),
                "--owner", owner,
                "--url", issue_url,
            )

    # Save updated project
    filepath = Path(project["path"])
    save_data = {k: v for k, v in project.items() if k != "path"}
    filepath.write_text(json.dumps(save_data, indent=2))

    return project


def list_github_projects(project_path: Path | None = None) -> list[dict[str, Any]]:
    """List GitHub Projects for the repository owner.

    Returns list of GitHub projects with their numbers and titles.
    """
    root = project_path or find_idlergear_root()
    owner = get_github_owner(root)
    if not owner:
        return []

    success, output = _run_gh(
        "project", "list",
        "--owner", owner,
        "--format", "json",
    )

    if not success:
        return []

    try:
        return json.loads(output).get("projects", [])
    except json.JSONDecodeError:
        return []


def link_to_github_project(
    name: str,
    github_project_number: int,
    project_path: Path | None = None,
) -> dict[str, Any] | None:
    """Link a local project to an existing GitHub project.

    Returns:
        Updated project data, or None if local project not found
    """
    project = get_project(name, project_path)
    if project is None:
        return None

    root = project_path or find_idlergear_root()
    owner = get_github_owner(root)
    if not owner:
        raise RuntimeError("Could not determine GitHub owner")

    # Get GitHub project ID
    success, output = _run_gh(
        "project", "view",
        str(github_project_number),
        "--owner", owner,
        "--format", "json",
    )

    if not success:
        raise RuntimeError(f"GitHub project #{github_project_number} not found: {output}")

    try:
        gh_data = json.loads(output)
        project["github_project_number"] = github_project_number
        project["github_project_id"] = gh_data.get("id")
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse GitHub response: {output}")

    # Save
    filepath = Path(project["path"])
    save_data = {k: v for k, v in project.items() if k != "path"}
    filepath.write_text(json.dumps(save_data, indent=2))

    return project
