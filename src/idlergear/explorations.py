"""Exploration management for IdlerGear."""

from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root
from idlergear.storage import (
    get_next_id,
    now_iso,
    parse_frontmatter,
    render_frontmatter,
    slugify,
)


def get_explorations_dir(project_path: Path | None = None) -> Path | None:
    """Get the explorations directory path."""
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None
    return project_path / ".idlergear" / "explorations"


def create_exploration(
    title: str,
    body: str | None = None,
    project_path: Path | None = None,
) -> dict[str, Any]:
    """Create a new exploration.

    Returns the created exploration data including its ID.
    """
    explorations_dir = get_explorations_dir(project_path)
    if explorations_dir is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    explorations_dir.mkdir(parents=True, exist_ok=True)

    exploration_id = get_next_id(explorations_dir)
    slug = slugify(title)
    filename = f"{exploration_id:03d}-{slug}.md"
    filepath = explorations_dir / filename

    frontmatter = {
        "id": exploration_id,
        "title": title,
        "state": "open",
        "created": now_iso(),
    }

    content = render_frontmatter(frontmatter, (body or "").strip() + "\n")
    filepath.write_text(content)

    return {
        "id": exploration_id,
        "title": title,
        "body": body,
        "state": "open",
        "created": frontmatter["created"],
        "path": str(filepath),
    }


def list_explorations(
    state: str = "open", project_path: Path | None = None
) -> list[dict[str, Any]]:
    """List explorations filtered by state.

    State can be 'open', 'closed', or 'all'.
    Returns list of exploration data dicts sorted by ID.
    """
    explorations_dir = get_explorations_dir(project_path)
    if explorations_dir is None or not explorations_dir.exists():
        return []

    explorations = []
    for filepath in sorted(explorations_dir.glob("*.md")):
        exploration = load_exploration_from_file(filepath)
        if exploration:
            if state == "all" or exploration.get("state") == state:
                explorations.append(exploration)

    return sorted(explorations, key=lambda e: e.get("id", 0))


def load_exploration_from_file(filepath: Path) -> dict[str, Any] | None:
    """Load an exploration from a file path."""
    if not filepath.exists():
        return None

    content = filepath.read_text()
    frontmatter, body = parse_frontmatter(content)

    return {
        "id": frontmatter.get("id"),
        "title": frontmatter.get("title", "Untitled"),
        "body": body.strip() if body else None,
        "state": frontmatter.get("state", "open"),
        "created": frontmatter.get("created"),
        "github_discussion": frontmatter.get("github_discussion"),
        "path": str(filepath),
    }


def get_exploration(
    exploration_id: int, project_path: Path | None = None
) -> dict[str, Any] | None:
    """Get an exploration by ID."""
    explorations_dir = get_explorations_dir(project_path)
    if explorations_dir is None:
        return None

    for filepath in explorations_dir.glob("*.md"):
        exploration = load_exploration_from_file(filepath)
        if exploration and exploration.get("id") == exploration_id:
            return exploration

    return None


def update_exploration(
    exploration_id: int,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
    project_path: Path | None = None,
) -> dict[str, Any] | None:
    """Update an exploration.

    Returns the updated exploration data, or None if not found.
    """
    exploration = get_exploration(exploration_id, project_path)
    if exploration is None:
        return None

    filepath = Path(exploration["path"])
    content = filepath.read_text()
    frontmatter, old_body = parse_frontmatter(content)

    if title is not None:
        frontmatter["title"] = title
    if state is not None:
        frontmatter["state"] = state

    new_body = body if body is not None else old_body

    new_content = render_frontmatter(frontmatter, new_body.strip() + "\n")
    filepath.write_text(new_content)

    return load_exploration_from_file(filepath)


def close_exploration(
    exploration_id: int, project_path: Path | None = None
) -> dict[str, Any] | None:
    """Close an exploration.

    Returns the updated exploration data, or None if not found.
    """
    return update_exploration(exploration_id, state="closed", project_path=project_path)
