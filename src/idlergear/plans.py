"""Plan management for IdlerGear."""

from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root, get_config_value, set_config_value
from idlergear.storage import (
    now_iso,
    parse_frontmatter,
    render_frontmatter,
    slugify,
)


def get_plans_dir(project_path: Path | None = None) -> Path | None:
    """Get the plans directory path."""
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None
    return project_path / ".idlergear" / "plans"


def create_plan(
    name: str,
    title: str | None = None,
    body: str | None = None,
    project_path: Path | None = None,
) -> dict[str, Any]:
    """Create a new plan.

    Returns the created plan data.
    """
    plans_dir = get_plans_dir(project_path)
    if plans_dir is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    plans_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify(name)
    filename = f"{slug}.md"
    filepath = plans_dir / filename

    if filepath.exists():
        raise ValueError(f"Plan '{name}' already exists")

    frontmatter = {
        "name": name,
        "title": title or name,
        "state": "active",
        "created": now_iso(),
    }

    content = render_frontmatter(frontmatter, (body or "").strip() + "\n")
    filepath.write_text(content)

    return {
        "name": name,
        "title": frontmatter["title"],
        "body": body,
        "state": "active",
        "created": frontmatter["created"],
        "path": str(filepath),
    }


def list_plans(project_path: Path | None = None) -> list[dict[str, Any]]:
    """List all plans.

    Returns list of plan data dicts sorted by name.
    """
    plans_dir = get_plans_dir(project_path)
    if plans_dir is None or not plans_dir.exists():
        return []

    plans = []
    for filepath in sorted(plans_dir.glob("*.md")):
        plan = load_plan_from_file(filepath)
        if plan:
            plans.append(plan)

    return sorted(plans, key=lambda p: p.get("name", "").lower())


def load_plan_from_file(filepath: Path) -> dict[str, Any] | None:
    """Load a plan from a file path."""
    if not filepath.exists():
        return None

    content = filepath.read_text()
    frontmatter, body = parse_frontmatter(content)

    return {
        "name": frontmatter.get("name", filepath.stem),
        "title": frontmatter.get("title", filepath.stem),
        "body": body.strip() if body else None,
        "state": frontmatter.get("state", "active"),
        "created": frontmatter.get("created"),
        "github_project": frontmatter.get("github_project"),
        "path": str(filepath),
    }


def get_plan(name: str, project_path: Path | None = None) -> dict[str, Any] | None:
    """Get a plan by name."""
    plans_dir = get_plans_dir(project_path)
    if plans_dir is None:
        return None

    # Try direct file match
    slug = slugify(name)
    filepath = plans_dir / f"{slug}.md"
    if filepath.exists():
        return load_plan_from_file(filepath)

    # Fallback: scan for matching name in frontmatter
    for filepath in plans_dir.glob("*.md"):
        plan = load_plan_from_file(filepath)
        if plan and plan.get("name", "").lower() == name.lower():
            return plan

    return None


def get_current_plan(project_path: Path | None = None) -> dict[str, Any] | None:
    """Get the current active plan."""
    current_name = get_config_value("plan.current", project_path)
    if not current_name:
        return None
    return get_plan(current_name, project_path)


def switch_plan(name: str, project_path: Path | None = None) -> dict[str, Any] | None:
    """Switch to a plan.

    Returns the plan data, or None if not found.
    """
    plan = get_plan(name, project_path)
    if plan is None:
        return None

    set_config_value("plan.current", plan["name"], project_path)
    return plan


def update_plan(
    name: str,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
    project_path: Path | None = None,
) -> dict[str, Any] | None:
    """Update a plan.

    Returns the updated plan data, or None if not found.
    """
    plan = get_plan(name, project_path)
    if plan is None:
        return None

    filepath = Path(plan["path"])
    content = filepath.read_text()
    frontmatter, old_body = parse_frontmatter(content)

    if title is not None:
        frontmatter["title"] = title
    if state is not None:
        frontmatter["state"] = state

    new_body = body if body is not None else old_body

    new_content = render_frontmatter(frontmatter, new_body.strip() + "\n")
    filepath.write_text(new_content)

    return load_plan_from_file(filepath)


def delete_plan(name: str, project_path: Path | None = None) -> bool:
    """Delete a plan by name.

    Returns True if deleted, False if not found.
    """
    plan = get_plan(name, project_path)
    if plan is None:
        return False

    filepath = Path(plan["path"])
    filepath.unlink()

    # Clear current plan if it was the deleted plan
    current = get_current_plan(project_path)
    if current and current.get("name") == name:
        set_config_value("plan.current", None, project_path)

    return True


def complete_plan(name: str, project_path: Path | None = None) -> dict[str, Any] | None:
    """Mark a plan as completed.

    Returns the updated plan data, or None if not found.
    """
    return update_plan(name, state="completed", project_path=project_path)
