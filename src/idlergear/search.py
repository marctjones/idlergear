"""Cross-type search for IdlerGear."""

from pathlib import Path
from typing import Any

from idlergear.explorations import list_explorations
from idlergear.notes import list_notes
from idlergear.plans import list_plans
from idlergear.reference import list_references
from idlergear.tasks import list_tasks


def search_all(
    query: str,
    types: list[str] | None = None,
    project_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Search across all knowledge types.

    Args:
        query: Search query (case-insensitive substring match)
        types: List of types to search (default: all).
               Valid types: task, note, explore, reference, plan
        project_path: Optional project path override

    Returns:
        List of matching items with their type and relevance info.
    """
    query_lower = query.lower()
    results = []

    # Define which types to search
    all_types = ["task", "note", "explore", "reference", "plan"]
    search_types = types if types else all_types

    # Search tasks
    if "task" in search_types:
        for task in list_tasks(state="all", project_path=project_path):
            if _matches(task, query_lower, ["title", "body"]):
                results.append(
                    {
                        "type": "task",
                        "id": task["id"],
                        "title": task.get("title", ""),
                        "preview": _get_preview(task, query_lower),
                        "state": task.get("state"),
                        "priority": task.get("priority"),
                        "due": task.get("due"),
                        "path": task.get("path"),
                    }
                )

    # Search notes
    if "note" in search_types:
        for note in list_notes(project_path=project_path):
            if _matches(note, query_lower, ["content"]):
                results.append(
                    {
                        "type": "note",
                        "id": note["id"],
                        "title": _get_note_title(note),
                        "preview": _get_preview(
                            note, query_lower, content_field="content"
                        ),
                        "path": note.get("path"),
                    }
                )

    # Search explorations
    if "explore" in search_types:
        for exp in list_explorations(state="all", project_path=project_path):
            if _matches(exp, query_lower, ["title", "body"]):
                results.append(
                    {
                        "type": "explore",
                        "id": exp["id"],
                        "title": exp.get("title", ""),
                        "preview": _get_preview(exp, query_lower),
                        "state": exp.get("state"),
                        "path": exp.get("path"),
                    }
                )

    # Search references
    if "reference" in search_types:
        for ref in list_references(project_path=project_path):
            if _matches(ref, query_lower, ["title", "body"]):
                results.append(
                    {
                        "type": "reference",
                        "id": ref.get("id"),
                        "title": ref.get("title", ""),
                        "preview": _get_preview(ref, query_lower),
                        "path": ref.get("path"),
                    }
                )

    # Search plans
    if "plan" in search_types:
        for plan in list_plans(project_path=project_path):
            if _matches(plan, query_lower, ["name", "title", "body"]):
                results.append(
                    {
                        "type": "plan",
                        "name": plan.get("name"),
                        "title": plan.get("title", plan.get("name", "")),
                        "preview": _get_preview(plan, query_lower),
                        "state": plan.get("state"),
                        "path": plan.get("path"),
                    }
                )

    return results


def _matches(item: dict[str, Any], query: str, fields: list[str]) -> bool:
    """Check if item matches query in any of the specified fields."""
    for field in fields:
        value = item.get(field)
        if value and query in str(value).lower():
            return True
    return False


def _get_preview(
    item: dict[str, Any],
    query: str,
    content_field: str = "body",
    max_length: int = 100,
) -> str:
    """Get a preview snippet around the match."""
    # Check title first
    title = item.get("title", "")
    if query in title.lower():
        return title[:max_length]

    # Then check body/content
    content = item.get(content_field, "") or ""
    if not content:
        return title[:max_length] if title else ""

    content_lower = content.lower()
    pos = content_lower.find(query)
    if pos == -1:
        # Match was in another field, just return start of content
        return content[:max_length] + ("..." if len(content) > max_length else "")

    # Show context around the match
    start = max(0, pos - 30)
    end = min(len(content), pos + len(query) + 70)

    preview = content[start:end].replace("\n", " ")
    if start > 0:
        preview = "..." + preview
    if end < len(content):
        preview = preview + "..."

    return preview


def _get_note_title(note: dict[str, Any]) -> str:
    """Extract a title from a note's content."""
    content = note.get("content", "")
    if not content:
        return f"Note #{note.get('id', '?')}"

    # Use first line as title
    first_line = content.split("\n")[0].strip()
    if len(first_line) > 50:
        return first_line[:47] + "..."
    return first_line or f"Note #{note.get('id', '?')}"
