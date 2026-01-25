"""Note management for IdlerGear."""

from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root
from idlergear.storage import (
    get_next_id,
    now_iso,
    parse_frontmatter,
    render_frontmatter,
)


def get_notes_dir(project_path: Path | None = None) -> Path | None:
    """Get the notes directory path."""
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None
    return project_path / ".idlergear" / "notes"


def create_note(
    content: str,
    tags: list[str] | None = None,
    project_path: Path | None = None,
) -> dict[str, Any]:
    """Create a new note.

    Args:
        content: The note content
        tags: Optional list of tags (e.g., ["explore", "idea"])
        project_path: Optional project path

    Returns the created note data including its ID.
    """
    notes_dir = get_notes_dir(project_path)
    if notes_dir is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    notes_dir.mkdir(parents=True, exist_ok=True)

    note_id = get_next_id(notes_dir)
    filename = f"{note_id:03d}.md"
    filepath = notes_dir / filename

    frontmatter: dict[str, Any] = {
        "id": note_id,
        "created": now_iso(),
        "accessed": None,
        "access_count": 0,
        "relevance_score": 1.0,
    }
    if tags:
        frontmatter["tags"] = tags

    file_content = render_frontmatter(frontmatter, content.strip() + "\n")
    filepath.write_text(file_content)

    return {
        "id": note_id,
        "content": content.strip(),
        "tags": tags or [],
        "created": frontmatter["created"],
        "accessed": frontmatter["accessed"],
        "access_count": frontmatter["access_count"],
        "relevance_score": frontmatter["relevance_score"],
        "path": str(filepath),
    }


def list_notes(
    tag: str | None = None,
    project_path: Path | None = None,
) -> list[dict[str, Any]]:
    """List notes, optionally filtered by tag.

    Args:
        tag: Optional tag to filter by (e.g., "explore", "idea")
        project_path: Optional project path

    Returns list of note data dicts sorted by ID.
    """
    notes_dir = get_notes_dir(project_path)
    if notes_dir is None or not notes_dir.exists():
        return []

    notes = []
    for filepath in sorted(notes_dir.glob("*.md")):
        note = load_note_from_file(filepath)
        if note:
            if tag is None or tag in note.get("tags", []):
                notes.append(note)

    return sorted(notes, key=lambda n: n.get("id", 0))


def load_note_from_file(filepath: Path) -> dict[str, Any] | None:
    """Load a note from a file path."""
    if not filepath.exists():
        return None

    content = filepath.read_text()
    frontmatter, body = parse_frontmatter(content)

    return {
        "id": frontmatter.get("id"),
        "content": body.strip(),
        "tags": frontmatter.get("tags", []),
        "created": frontmatter.get("created"),
        "accessed": frontmatter.get("accessed"),
        "access_count": frontmatter.get("access_count", 0),
        "relevance_score": frontmatter.get("relevance_score", 1.0),
        "path": str(filepath),
    }


def get_note(
    note_id: int,
    project_path: Path | None = None,
    update_access: bool = True,
) -> dict[str, Any] | None:
    """Get a note by ID.

    Args:
        note_id: ID of the note to retrieve
        project_path: Optional project path override
        update_access: If True, updates access timestamp and relevance score

    Returns the note data, or None if not found.
    """
    notes_dir = get_notes_dir(project_path)
    if notes_dir is None:
        return None

    # Try direct filename match first
    filepath = notes_dir / f"{note_id:03d}.md"
    if filepath.exists():
        note = load_note_from_file(filepath)
        if note and update_access:
            _update_note_access(filepath, note)
            note = load_note_from_file(filepath)
        return note

    # Fallback: scan directory for matching ID in frontmatter
    for filepath in notes_dir.glob("*.md"):
        note = load_note_from_file(filepath)
        if note and note.get("id") == note_id:
            if update_access:
                _update_note_access(filepath, note)
                note = load_note_from_file(filepath)
            return note

    return None


def _update_note_access(filepath: Path, note: dict[str, Any]) -> None:
    """Update note access timestamp and relevance score."""
    from datetime import datetime, timezone
    from idlergear.relevance import calculate_relevance
    from idlergear.storage import parse_iso

    content = filepath.read_text()
    frontmatter, body = parse_frontmatter(content)

    frontmatter["accessed"] = now_iso()
    frontmatter["access_count"] = frontmatter.get("access_count", 0) + 1

    # Recalculate relevance score
    created = parse_iso(frontmatter.get("created", ""))
    if created:
        frontmatter["relevance_score"] = calculate_relevance(
            created=created,
            accessed=datetime.now(timezone.utc),
            access_count=frontmatter["access_count"],
        )

    # Save updated note
    new_content = render_frontmatter(frontmatter, body.strip() + "\n")
    filepath.write_text(new_content)


def update_note(
    note_id: int,
    content: str | None = None,
    tags: list[str] | None = None,
    project_path: Path | None = None,
) -> dict[str, Any] | None:
    """Update a note.

    Args:
        note_id: The note ID
        content: New content (None to keep existing)
        tags: New tags (None to keep existing)
        project_path: Optional project path

    Returns the updated note data, or None if not found.
    """
    note = get_note(note_id, project_path, update_access=False)
    if note is None:
        return None

    filepath = Path(note["path"])
    file_content = filepath.read_text()
    frontmatter, old_content = parse_frontmatter(file_content)

    # Update access metadata
    from datetime import datetime, timezone
    from idlergear.relevance import calculate_relevance
    from idlergear.storage import parse_iso

    frontmatter["accessed"] = now_iso()
    frontmatter["access_count"] = frontmatter.get("access_count", 0) + 1

    # Recalculate relevance score
    created = parse_iso(frontmatter.get("created", ""))
    if created:
        frontmatter["relevance_score"] = calculate_relevance(
            created=created,
            accessed=datetime.now(timezone.utc),
            access_count=frontmatter["access_count"],
        )

    # Update tags if provided
    if tags is not None:
        frontmatter["tags"] = tags

    # Use new content or keep old
    new_content = content if content is not None else old_content.strip()

    new_file_content = render_frontmatter(frontmatter, new_content.strip() + "\n")
    filepath.write_text(new_file_content)

    return {
        "id": note_id,
        "content": new_content.strip(),
        "tags": frontmatter.get("tags", []),
        "created": frontmatter.get("created"),
        "path": str(filepath),
    }


def delete_note(note_id: int, project_path: Path | None = None) -> bool:
    """Delete a note by ID.

    Returns True if deleted, False if not found.
    """
    note = get_note(note_id, project_path)
    if note is None:
        return False

    Path(note["path"]).unlink()
    return True


def promote_note(
    note_id: int, to_type: str, project_path: Path | None = None
) -> dict[str, Any] | None:
    """Promote a note to another type (task or reference).

    Returns the created item data, or None if note not found.
    """
    note = get_note(note_id, project_path)
    if note is None:
        return None

    content = note["content"]

    if to_type == "task":
        from idlergear.tasks import create_task

        # Use first line as title, rest as body
        lines = content.split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else None
        result = create_task(title, body=body, project_path=project_path)
    elif to_type == "reference":
        from idlergear.reference import add_reference

        lines = content.split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else None
        result = add_reference(title, body=body, project_path=project_path)
    else:
        raise ValueError(
            f"Unknown promotion target: {to_type}. Valid targets: task, reference"
        )

    # Delete the original note after successful promotion
    delete_note(note_id, project_path)

    return result
