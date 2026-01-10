"""Vision management for IdlerGear.

Vision is special - it's the foundation of the project and should always be:
1. In VISION.md at the repo root
2. Committed to git
3. The single source of truth

No backend abstraction needed. Just a file in the repo.
"""

from __future__ import annotations

from pathlib import Path

from idlergear.config import find_idlergear_root


def get_vision_path(project_path: Path | None = None) -> Path | None:
    """Get the vision file path.

    Vision is always VISION.md in the project root (not in .idlergear/).
    This ensures it's committed to git and shared with all collaborators.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None

    return project_path / "VISION.md"


def get_vision(project_path: Path | None = None) -> str | None:
    """Get the project vision content.

    Returns the vision markdown content, or None if VISION.md doesn't exist.
    """
    vision_path = get_vision_path(project_path)
    if vision_path is None or not vision_path.exists():
        return None
    return vision_path.read_text()


def set_vision(content: str, project_path: Path | None = None) -> None:
    """Set the project vision content.

    Writes to VISION.md in the project root.
    Raises RuntimeError if not in an IdlerGear project.
    """
    vision_path = get_vision_path(project_path)
    if vision_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    vision_path.write_text(content)
