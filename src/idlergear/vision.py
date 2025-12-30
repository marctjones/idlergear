"""Vision management for IdlerGear."""

from pathlib import Path

from idlergear.config import find_idlergear_root


def get_vision_path(project_path: Path | None = None) -> Path | None:
    """Get the vision file path."""
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None
    return project_path / ".idlergear" / "vision.md"


def get_vision(project_path: Path | None = None) -> str | None:
    """Get the project vision content.

    Returns the vision markdown content, or None if not initialized.
    """
    vision_path = get_vision_path(project_path)
    if vision_path is None or not vision_path.exists():
        return None
    return vision_path.read_text()


def set_vision(content: str, project_path: Path | None = None) -> None:
    """Set the project vision content.

    Raises RuntimeError if IdlerGear is not initialized.
    """
    vision_path = get_vision_path(project_path)
    if vision_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    vision_path.write_text(content)
