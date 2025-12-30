"""Reference document management for IdlerGear."""

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


def get_reference_dir(project_path: Path | None = None) -> Path | None:
    """Get the reference directory path."""
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None
    return project_path / ".idlergear" / "reference"


def add_reference(
    title: str,
    body: str | None = None,
    project_path: Path | None = None,
) -> dict[str, Any]:
    """Add a new reference document.

    Returns the created reference data including its ID.
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
        "created": frontmatter["created"],
        "updated": frontmatter["updated"],
        "path": str(filepath),
    }


def list_references(project_path: Path | None = None) -> list[dict[str, Any]]:
    """List all reference documents.

    Returns list of reference data dicts sorted by title.
    """
    reference_dir = get_reference_dir(project_path)
    if reference_dir is None or not reference_dir.exists():
        return []

    references = []
    for filepath in sorted(reference_dir.glob("*.md")):
        ref = load_reference_from_file(filepath)
        if ref:
            references.append(ref)

    return sorted(references, key=lambda r: r.get("title", "").lower())


def load_reference_from_file(filepath: Path) -> dict[str, Any] | None:
    """Load a reference from a file path."""
    if not filepath.exists():
        return None

    content = filepath.read_text()
    frontmatter, body = parse_frontmatter(content)

    return {
        "id": frontmatter.get("id"),
        "title": frontmatter.get("title", filepath.stem),
        "body": body.strip() if body else None,
        "created": frontmatter.get("created"),
        "updated": frontmatter.get("updated"),
        "path": str(filepath),
    }


def get_reference(
    title: str, project_path: Path | None = None
) -> dict[str, Any] | None:
    """Get a reference by title (case-insensitive)."""
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

    Returns the updated reference data, or None if not found.
    """
    ref = get_reference(title, project_path)
    if ref is None:
        return None

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
