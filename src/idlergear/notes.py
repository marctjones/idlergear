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


def create_note(content: str, project_path: Path | None = None) -> dict[str, Any]:
    """Create a new note.

    Returns the created note data including its ID.
    """
    notes_dir = get_notes_dir(project_path)
    if notes_dir is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    notes_dir.mkdir(parents=True, exist_ok=True)

    note_id = get_next_id(notes_dir)
    filename = f"{note_id:03d}.md"
    filepath = notes_dir / filename

    frontmatter = {
        "id": note_id,
        "created": now_iso(),
    }

    file_content = render_frontmatter(frontmatter, content.strip() + "\n")
    filepath.write_text(file_content)

    return {
        "id": note_id,
        "content": content.strip(),
        "created": frontmatter["created"],
        "path": str(filepath),
    }


def list_notes(project_path: Path | None = None) -> list[dict[str, Any]]:
    """List all notes.

    Returns list of note data dicts sorted by ID.
    """
    notes_dir = get_notes_dir(project_path)
    if notes_dir is None or not notes_dir.exists():
        return []

    notes = []
    for filepath in sorted(notes_dir.glob("*.md")):
        note = load_note_from_file(filepath)
        if note:
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
        "created": frontmatter.get("created"),
        "path": str(filepath),
    }


def get_note(note_id: int, project_path: Path | None = None) -> dict[str, Any] | None:
    """Get a note by ID."""
    notes_dir = get_notes_dir(project_path)
    if notes_dir is None:
        return None

    # Try direct filename match first
    filepath = notes_dir / f"{note_id:03d}.md"
    if filepath.exists():
        return load_note_from_file(filepath)

    # Fallback: scan directory for matching ID in frontmatter
    for filepath in notes_dir.glob("*.md"):
        note = load_note_from_file(filepath)
        if note and note.get("id") == note_id:
            return note

    return None


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
    """Promote a note to another type (task, explore, reference).

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
    elif to_type == "explore":
        from idlergear.explorations import create_exploration

        lines = content.split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else None
        result = create_exploration(title, body=body, project_path=project_path)
    elif to_type == "reference":
        from idlergear.reference import add_reference

        lines = content.split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else None
        result = add_reference(title, body=body, project_path=project_path)
    else:
        raise ValueError(f"Unknown promotion target: {to_type}")

    # Delete the original note after successful promotion
    delete_note(note_id, project_path)

    return result
