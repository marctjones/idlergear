"""Vision management for IdlerGear.

In v0.3+, vision is stored at .idlergear/vision/VISION.md.
For backward compatibility, also checks .idlergear/vision.md.
"""

from __future__ import annotations

from pathlib import Path

from idlergear.config import find_idlergear_root


def get_vision_path(project_path: Path | None = None) -> Path | None:
    """Get the vision file path.

    Returns the vision/VISION.md path (v0.3+) if it exists, otherwise
    falls back to vision.md (legacy) for backward compatibility.
    New projects will use vision/VISION.md.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None

    idlergear_dir = project_path / ".idlergear"

    # Prefer v0.3 vision/VISION.md
    vision_dir = idlergear_dir / "vision"
    v03_path = vision_dir / "VISION.md"
    if v03_path.exists():
        return v03_path

    # Fall back to legacy vision.md
    legacy_path = idlergear_dir / "vision.md"
    if legacy_path.exists():
        return legacy_path

    # For new projects, use v0.3 path
    return v03_path


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

    # Ensure parent directory exists (for v0.3 path)
    vision_path.parent.mkdir(parents=True, exist_ok=True)
    vision_path.write_text(content)
