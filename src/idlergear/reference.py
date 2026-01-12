"""Reference document management for IdlerGear.

Unified Reference Model (v0.4+):
- pinned: Special repo files (VISION.md, README.md, etc.)
- wiki: User-created references in .idlergear/wiki/
- generated: Auto-generated from code (OpenAPI, rustdoc, etc.)

For backward compatibility, also checks .idlergear/reference/.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root, get_config_value
from idlergear.storage import (
    get_next_id,
    now_iso,
    parse_frontmatter,
    render_frontmatter,
    slugify,
)


class ReferenceSource(str, Enum):
    """Source type for references."""

    PINNED = "pinned"  # Special repo files (VISION.md, README.md)
    WIKI = "wiki"  # User-created in .idlergear/wiki/
    GENERATED = "generated"  # Auto-generated from code


# Pinned references - special files in the repo root
PINNED_REFERENCES: dict[str, str] = {
    "vision": "VISION.md",
    "readme": "README.md",
    "contributing": "CONTRIBUTING.md",
    "changelog": "CHANGELOG.md",
    "design": "DESIGN.md",
    "development": "DEVELOPMENT.md",
}


def get_pinned_reference(
    name: str, project_path: Path | None = None
) -> dict[str, Any] | None:
    """Get a pinned reference by name.

    Pinned references are special repo files like VISION.md, README.md, etc.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None

    name_lower = name.lower()
    if name_lower not in PINNED_REFERENCES:
        return None

    filename = PINNED_REFERENCES[name_lower]
    filepath = project_path / filename

    if not filepath.exists():
        return None

    content = filepath.read_text()

    return {
        "id": None,
        "title": name_lower,
        "body": content,
        "source": ReferenceSource.PINNED.value,
        "filename": filename,
        "path": str(filepath),
        "created": None,
        "updated": None,
    }


def list_pinned_references(project_path: Path | None = None) -> list[dict[str, Any]]:
    """List all pinned references that exist.

    Returns list of pinned reference data for files that exist.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return []

    refs = []
    for name, filename in PINNED_REFERENCES.items():
        filepath = project_path / filename
        if filepath.exists():
            content = filepath.read_text()
            refs.append(
                {
                    "id": None,
                    "title": name,
                    "body": content,
                    "source": ReferenceSource.PINNED.value,
                    "filename": filename,
                    "path": str(filepath),
                    "created": None,
                    "updated": None,
                }
            )
    return refs


def update_pinned_reference(
    name: str, content: str, project_path: Path | None = None
) -> dict[str, Any] | None:
    """Update a pinned reference.

    Creates the file if it doesn't exist.
    Returns the updated reference, or None if name is not a valid pinned reference.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None

    name_lower = name.lower()
    if name_lower not in PINNED_REFERENCES:
        return None

    filename = PINNED_REFERENCES[name_lower]
    filepath = project_path / filename

    filepath.write_text(content)

    return {
        "id": None,
        "title": name_lower,
        "body": content,
        "source": ReferenceSource.PINNED.value,
        "filename": filename,
        "path": str(filepath),
        "created": None,
        "updated": None,
    }


def get_reference_dir(project_path: Path | None = None) -> Path | None:
    """Get the reference/wiki directory path.

    Returns the wiki/ directory (v0.3+) if it exists, otherwise
    falls back to reference/ (legacy) for backward compatibility.
    New projects will use wiki/.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None

    idlergear_dir = project_path / ".idlergear"

    # Prefer v0.3 wiki/ directory
    wiki_dir = idlergear_dir / "wiki"
    if wiki_dir.exists():
        return wiki_dir

    # Fall back to legacy reference/ directory
    reference_dir = idlergear_dir / "reference"
    if reference_dir.exists():
        return reference_dir

    # For new projects, use wiki/
    return wiki_dir


def add_reference(
    title: str,
    body: str | None = None,
    project_path: Path | None = None,
) -> dict[str, Any]:
    """Add a new wiki reference document.

    Returns the created reference data including its ID.
    Note: Use update_pinned_reference() for pinned references.
    """
    reference_dir = get_reference_dir(project_path)
    if reference_dir is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    reference_dir.mkdir(parents=True, exist_ok=True)

    reference_id = get_next_id(reference_dir)
    slug = slugify(title)
    filename = f"{slug}.md"
    filepath = reference_dir / filename

    # Handle duplicate filenames
    if filepath.exists():
        filename = f"{slug}-{reference_id}.md"
        filepath = reference_dir / filename

    frontmatter = {
        "id": reference_id,
        "title": title,
        "created": now_iso(),
        "updated": now_iso(),
    }

    content = render_frontmatter(frontmatter, (body or "").strip() + "\n")
    filepath.write_text(content)

    return {
        "id": reference_id,
        "title": title,
        "body": body,
        "source": ReferenceSource.WIKI.value,
        "created": frontmatter["created"],
        "updated": frontmatter["updated"],
        "path": str(filepath),
    }


def list_references(
    project_path: Path | None = None,
    include_pinned: bool = True,
    include_wiki: bool = True,
    include_generated: bool = True,
) -> list[dict[str, Any]]:
    """List all reference documents.

    Args:
        project_path: Optional project path
        include_pinned: Include pinned references (VISION.md, README.md, etc.)
        include_wiki: Include wiki references (.idlergear/wiki/)
        include_generated: Include generated references (future)

    Returns list of reference data dicts sorted by source then title.
    """
    references = []

    # Add pinned references first
    if include_pinned:
        references.extend(list_pinned_references(project_path))

    # Add wiki references
    if include_wiki:
        reference_dir = get_reference_dir(project_path)
        if reference_dir is not None and reference_dir.exists():
            for filepath in sorted(reference_dir.glob("*.md")):
                ref = load_reference_from_file(filepath)
                if ref:
                    references.append(ref)

    # Generated references will be added in a future implementation
    # when the generator system is complete

    # Sort by source (pinned first), then by title
    source_order = {
        ReferenceSource.PINNED.value: 0,
        ReferenceSource.WIKI.value: 1,
        ReferenceSource.GENERATED.value: 2,
    }
    return sorted(
        references,
        key=lambda r: (
            source_order.get(r.get("source", ReferenceSource.WIKI.value), 1),
            r.get("title", "").lower(),
        ),
    )


def load_reference_from_file(filepath: Path) -> dict[str, Any] | None:
    """Load a wiki reference from a file path."""
    if not filepath.exists():
        return None

    content = filepath.read_text()
    frontmatter, body = parse_frontmatter(content)

    return {
        "id": frontmatter.get("id"),
        "title": frontmatter.get("title", filepath.stem),
        "body": body.strip() if body else None,
        "source": ReferenceSource.WIKI.value,
        "created": frontmatter.get("created"),
        "updated": frontmatter.get("updated"),
        "path": str(filepath),
    }


def get_reference(
    title: str, project_path: Path | None = None
) -> dict[str, Any] | None:
    """Get a reference by title (case-insensitive).

    Checks pinned references first, then wiki references.
    """
    # Check pinned references first
    pinned = get_pinned_reference(title, project_path)
    if pinned is not None:
        return pinned

    # Check wiki references
    reference_dir = get_reference_dir(project_path)
    if reference_dir is None:
        return None

    title_lower = title.lower()
    for filepath in reference_dir.glob("*.md"):
        ref = load_reference_from_file(filepath)
        if ref and ref.get("title", "").lower() == title_lower:
            return ref

    # Try direct file match
    slug = slugify(title)
    filepath = reference_dir / f"{slug}.md"
    if filepath.exists():
        return load_reference_from_file(filepath)

    return None


def get_reference_by_id(
    reference_id: int, project_path: Path | None = None
) -> dict[str, Any] | None:
    """Get a reference by ID."""
    reference_dir = get_reference_dir(project_path)
    if reference_dir is None:
        return None

    for filepath in reference_dir.glob("*.md"):
        ref = load_reference_from_file(filepath)
        if ref and ref.get("id") == reference_id:
            return ref

    return None


def update_reference(
    title: str,
    new_title: str | None = None,
    body: str | None = None,
    project_path: Path | None = None,
) -> dict[str, Any] | None:
    """Update a reference document.

    For pinned references, only body can be updated (title is fixed).
    For wiki references, both title and body can be updated.

    Returns the updated reference data, or None if not found.
    """
    ref = get_reference(title, project_path)
    if ref is None:
        return None

    # Handle pinned references differently
    if ref.get("source") == ReferenceSource.PINNED.value:
        if body is not None:
            return update_pinned_reference(title, body, project_path)
        return ref  # No changes requested

    # Handle wiki references
    filepath = Path(ref["path"])
    content = filepath.read_text()
    frontmatter, old_body = parse_frontmatter(content)

    if new_title is not None:
        frontmatter["title"] = new_title
    frontmatter["updated"] = now_iso()

    new_body = body if body is not None else old_body

    new_content = render_frontmatter(frontmatter, new_body.strip() + "\n")
    filepath.write_text(new_content)

    return load_reference_from_file(filepath)


def search_references(
    query: str, project_path: Path | None = None
) -> list[dict[str, Any]]:
    """Search reference documents by title and content.

    Returns list of matching references.
    """
    references = list_references(project_path)
    query_lower = query.lower()

    results = []
    for ref in references:
        title_match = query_lower in ref.get("title", "").lower()
        body_match = ref.get("body") and query_lower in ref["body"].lower()

        if title_match or body_match:
            results.append(ref)

    return results


def delete_reference(title: str, project_path: Path | None = None) -> bool:
    """Delete a reference by title.

    Pinned references cannot be deleted (they're special repo files).
    Only wiki references can be deleted.

    Returns True if deleted, False if not found or cannot be deleted.
    """
    ref = get_reference(title, project_path)
    if ref is None:
        return False

    # Pinned references cannot be deleted
    if ref.get("source") == ReferenceSource.PINNED.value:
        return False

    filepath = Path(ref["path"])
    filepath.unlink()
    return True


def is_pinned_reference(title: str) -> bool:
    """Check if a title refers to a pinned reference."""
    return title.lower() in PINNED_REFERENCES
