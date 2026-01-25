"""GitHub Projects v2 integration for IdlerGear.

This module provides Kanban-style project boards that sync with GitHub Projects v2.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root
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
                "project",
                "create",
                "--owner",
                owner,
                "--title",
                title,
                "--format",
                "json",
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
                "project",
                "delete",
                str(project["github_project_number"]),
                "--owner",
                owner,
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
        raise ValueError(
            f"Column '{column}' not found. Available: {project['columns']}"
        )

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
        raise RuntimeError(
            "Could not determine GitHub owner. Ensure you're in a git repo with a GitHub remote."
        )

    # Create project on GitHub if not already linked
    if not project.get("github_project_number"):
        success, output = _run_gh(
            "project",
            "create",
            "--owner",
            owner,
            "--title",
            project["title"],
            "--format",
            "json",
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
    success, repo_output = _run_gh(
        "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"
    )
    if not success:
        raise RuntimeError("Could not determine repository")
    repo = repo_output.strip()

    # Add tasks to GitHub project
    for column, task_ids in project["tasks"].items():
        for task_id in task_ids:
            issue_url = f"https://github.com/{repo}/issues/{task_id}"
            _run_gh(
                "project",
                "item-add",
                str(project["github_project_number"]),
                "--owner",
                owner,
                "--url",
                issue_url,
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
        "project",
        "list",
        "--owner",
        owner,
        "--format",
        "json",
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
        "project",
        "view",
        str(github_project_number),
        "--owner",
        owner,
        "--format",
        "json",
    )

    if not success:
        raise RuntimeError(
            f"GitHub project #{github_project_number} not found: {output}"
        )

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


def auto_add_task_if_configured(
    task_id: str | int,
    project_path: Path | None = None,
) -> bool:
    """Automatically add task to default project if configured.

    Args:
        task_id: Task ID to add
        project_path: Override project path

    Returns:
        True if task was added, False otherwise
    """
    from idlergear.config import get_config_value

    # Check if auto-add is enabled
    auto_add = get_config_value("projects.auto_add", project_path)
    if not auto_add:
        return False

    # Get default project
    default_project = get_config_value("projects.default_project", project_path)
    if not default_project:
        return False

    # Get default column
    default_column = get_config_value("projects.default_column", project_path)

    # Add task to project
    try:
        result = add_task_to_project(
            project_name=default_project,
            task_id=str(task_id),
            column=default_column,
            project_path=project_path,
        )
        return result is not None
    except Exception:
        # Silently fail - don't break task creation if project add fails
        return False


def auto_move_task_on_state_change(
    task_id: str | int,
    new_state: str,
    project_path: Path | None = None,
) -> bool:
    """Automatically move task to appropriate column when state changes.

    Uses projects.column_mapping configuration to map task states to project columns.

    Args:
        task_id: Task ID
        new_state: New task state (e.g., "open", "in_progress", "completed")
        project_path: Override project path

    Returns:
        True if task was moved, False otherwise

    Configuration example:
        [projects.column_mapping]
        open = "Backlog"
        in_progress = "In Progress"
        completed = "Done"

    Example:
        >>> auto_move_task_on_state_change(278, "in_progress")
        True  # Task moved to "In Progress" column
    """
    from idlergear.config import get_config_value

    # Check if column mapping is enabled
    auto_move = get_config_value("projects.auto_move", project_path)
    if auto_move is False:  # Explicitly disabled
        return False

    # Get default project
    default_project = get_config_value("projects.default_project", project_path)
    if not default_project:
        return False

    # Get column mapping for the state
    column_mapping_key = f"projects.column_mapping.{new_state}"
    target_column = get_config_value(column_mapping_key, project_path)

    if not target_column:
        # No mapping for this state, don't move
        return False

    # Check if task is in the project
    project = get_project(default_project, project_path)
    if not project:
        return False

    # Check if task exists in any column
    task_id_str = str(task_id)
    task_in_project = False
    for col_tasks in project["tasks"].values():
        if task_id_str in col_tasks:
            task_in_project = True
            break

    if not task_in_project:
        # Task not in project, don't try to move it
        return False

    # Move task to target column
    try:
        result = move_task(
            project_name=default_project,
            task_id=task_id_str,
            column=target_column,
            project_path=project_path,
        )
        return result is not None
    except Exception:
        # Silently fail - don't break task updates if project move fails
        return False


def sync_task_fields_to_github(
    task_id: str | int,
    task_data: dict[str, Any],
    project_path: Path | None = None,
) -> bool:
    """Sync task metadata to GitHub Projects custom fields.

    Uses projects.field_mapping configuration to map IdlerGear task properties
    to GitHub Projects v2 custom fields.

    Args:
        task_id: Task ID
        task_data: Task data dict (must include priority, labels, due, etc.)
        project_path: Override project path

    Returns:
        True if fields were synced, False otherwise

    Configuration example:
        [projects.field_mapping]
        priority = "Priority"
        due = "Due Date"
        labels = "Labels"

    Example:
        >>> sync_task_fields_to_github(278, {"priority": "high", "due": "2026-02-01"})
        True  # Synced priority and due date to GitHub Projects
    """
    from idlergear.config import get_config_value
    from idlergear.github_graphql import GitHubGraphQL, GitHubGraphQLError

    # Check if field sync is enabled
    field_sync_enabled = get_config_value("projects.field_sync", project_path)
    if field_sync_enabled is False:
        return False

    # Get default project
    default_project_name = get_config_value("projects.default_project", project_path)
    if not default_project_name:
        return False

    project = get_project(default_project_name, project_path)
    if not project:
        return False

    # Must be linked to GitHub
    github_project_id = project.get("github_project_id")
    github_project_number = project.get("github_project_number")
    if not github_project_id or not github_project_number:
        return False

    # Check if task is in project
    task_id_str = str(task_id)
    task_in_project = any(
        task_id_str in col_tasks
        for col_tasks in project["tasks"].values()
    )
    if not task_in_project:
        return False

    # Get repo info
    root = project_path or find_idlergear_root()
    owner = get_github_owner(root)
    if not owner:
        return False

    # Determine repo name from git remote
    try:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False
        repo_full = result.stdout.strip()
        _, repo_name = repo_full.split("/")
    except Exception:
        return False

    try:
        graphql = GitHubGraphQL()

        # Get project fields
        project_data = graphql.get_project_v2(owner, github_project_number)
        fields_by_name = {}
        for field in project_data.get("fields", {}).get("nodes", []):
            field_name = field.get("name")
            if field_name:
                fields_by_name[field_name] = field

        # Get project item for this issue
        project_item = graphql.get_project_item_by_content(
            github_project_id, owner, repo_name, int(task_id)
        )
        if not project_item:
            return False

        item_id = project_item["id"]
        synced_any = False

        # Sync priority field (single-select)
        priority = task_data.get("priority")
        priority_field_name = get_config_value("projects.field_mapping.priority", project_path)
        if priority and priority_field_name and priority_field_name in fields_by_name:
            field_data = fields_by_name[priority_field_name]
            field_id = field_data["id"]

            # Find option ID for priority value
            options = field_data.get("options", [])
            option_id = None
            for option in options:
                if option["name"].lower() == priority.lower():
                    option_id = option["id"]
                    break

            if option_id:
                try:
                    graphql.update_project_item_field_single_select(
                        github_project_id, item_id, field_id, option_id
                    )
                    synced_any = True
                except GitHubGraphQLError:
                    pass

        # Sync due date field (date)
        due_date = task_data.get("due")
        due_field_name = get_config_value("projects.field_mapping.due", project_path)
        if due_date and due_field_name and due_field_name in fields_by_name:
            field_data = fields_by_name[due_field_name]
            field_id = field_data["id"]

            try:
                graphql.update_project_item_field_date(
                    github_project_id, item_id, field_id, due_date
                )
                synced_any = True
            except GitHubGraphQLError:
                pass

        # Sync labels field (text, comma-separated)
        labels = task_data.get("labels", [])
        labels_field_name = get_config_value("projects.field_mapping.labels", project_path)
        if labels and labels_field_name and labels_field_name in fields_by_name:
            field_data = fields_by_name[labels_field_name]
            field_id = field_data["id"]

            labels_text = ", ".join(labels)
            try:
                graphql.update_project_item_field_text(
                    github_project_id, item_id, field_id, labels_text
                )
                synced_any = True
            except GitHubGraphQLError:
                pass

        return synced_any

    except Exception:
        # Silently fail - don't break task operations if sync fails
        return False


def pull_project_from_github(
    name: str,
    project_path: Path | None = None,
) -> dict[str, Any]:
    """Pull changes from GitHub Projects and update local IdlerGear tasks.

    Syncs changes made in GitHub Projects UI back to IdlerGear (bidirectional sync).
    GitHub is treated as source of truth for conflicts.

    Args:
        name: Project name or slug
        project_path: Override project path

    Returns:
        Summary dict with updated task counts and details

    Operations:
        - Issue marked CLOSED in GitHub → close IdlerGear task
        - Priority changed in GitHub → update IdlerGear task priority
        - Due date changed in GitHub → update IdlerGear task due date
        - Labels changed in GitHub → update IdlerGear task labels

    Example:
        >>> result = pull_project_from_github("main")
        >>> result
        {
            "updated": 3,
            "closed": 1,
            "tasks": [{"id": 278, "changes": ["priority", "due"]}, ...]
        }
    """
    from idlergear.config import get_config_value
    from idlergear.github_graphql import GitHubGraphQL, GitHubGraphQLError
    from idlergear.tasks import get_task, update_task, close_task

    # Get project
    project = get_project(name, project_path)
    if not project:
        raise ValueError(f"Project '{name}' not found")

    # Must be linked to GitHub
    github_project_id = project.get("github_project_id")
    github_project_number = project.get("github_project_number")
    if not github_project_id or not github_project_number:
        raise ValueError(f"Project '{name}' is not linked to GitHub Projects")

    # Get repo info
    root = project_path or find_idlergear_root()
    owner = get_github_owner(root)
    if not owner:
        raise RuntimeError("Could not determine GitHub owner")

    # Get field mapping configuration
    priority_field_name = get_config_value("projects.field_mapping.priority", project_path)
    due_field_name = get_config_value("projects.field_mapping.due", project_path)
    labels_field_name = get_config_value("projects.field_mapping.labels", project_path)

    try:
        graphql = GitHubGraphQL()

        # Fetch all project items with field values
        items = graphql.get_project_items_with_fields(
            github_project_id, owner, owner
        )

        summary = {
            "updated": 0,
            "closed": 0,
            "tasks": []
        }

        for item in items:
            content = item.get("content", {})
            if not content:
                continue

            issue_number = content.get("number")
            issue_state = content.get("state")
            if not issue_number:
                continue

            # Get local task
            task = get_task(issue_number, project_path)
            if not task:
                # Task doesn't exist locally, skip
                continue

            changes = []
            update_params = {}

            # Check if issue is closed in GitHub
            if issue_state == "CLOSED" and task.get("state") != "closed":
                close_task(issue_number, project_path)
                summary["closed"] += 1
                changes.append("closed")

            # Parse field values from GitHub
            field_values = item.get("fieldValues", {}).get("nodes", [])
            github_fields = {}

            for field_value in field_values:
                field_info = field_value.get("field", {})
                field_name = field_info.get("name")
                if not field_name:
                    continue

                # Extract value based on type
                if "text" in field_value:
                    github_fields[field_name] = field_value["text"]
                elif "date" in field_value:
                    github_fields[field_name] = field_value["date"]
                elif "name" in field_value:
                    # Single-select field
                    github_fields[field_name] = field_value["name"]

            # Compare and update priority
            if priority_field_name and priority_field_name in github_fields:
                gh_priority = github_fields[priority_field_name].lower()
                local_priority = task.get("priority", "").lower() if task.get("priority") else ""
                if gh_priority != local_priority:
                    update_params["priority"] = gh_priority
                    changes.append("priority")

            # Compare and update due date
            if due_field_name and due_field_name in github_fields:
                gh_due = github_fields[due_field_name]
                local_due = task.get("due", "")
                if gh_due != local_due:
                    update_params["due"] = gh_due
                    changes.append("due")

            # Compare and update labels
            if labels_field_name and labels_field_name in github_fields:
                gh_labels_text = github_fields[labels_field_name]
                gh_labels = [label.strip() for label in gh_labels_text.split(",") if label.strip()]
                local_labels = task.get("labels", [])
                if set(gh_labels) != set(local_labels):
                    update_params["labels"] = gh_labels
                    changes.append("labels")

            # Apply updates if any changes detected
            if update_params and issue_state != "CLOSED":
                update_task(issue_number, **update_params, project_path=project_path)
                summary["updated"] += 1

            if changes:
                summary["tasks"].append({
                    "id": issue_number,
                    "title": task.get("title"),
                    "changes": changes
                })

        return summary

    except GitHubGraphQLError as e:
        raise RuntimeError(f"Failed to fetch project data from GitHub: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to pull project from GitHub: {e}")
