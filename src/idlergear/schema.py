"""Filesystem schema definitions for IdlerGear v0.3.

Defines the canonical directory structure and paths for .idlergear/.
This module is the single source of truth for all file locations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Schema version - increment when structure changes
SCHEMA_VERSION = "0.3"


@dataclass
class IdlerGearSchema:
    """Defines the .idlergear/ directory structure.

    Usage:
        schema = IdlerGearSchema(project_path)
        schema.issues_dir  # Path to issues directory
        schema.validate()  # Check structure integrity
    """

    root: Path  # Project root (contains .idlergear/)

    def __post_init__(self) -> None:
        if isinstance(self.root, str):
            self.root = Path(self.root)
        self.root = self.root.resolve()

    # === Core paths ===

    @property
    def idlergear_dir(self) -> Path:
        """The .idlergear/ directory."""
        return self.root / ".idlergear"

    @property
    def config_file(self) -> Path:
        """Project configuration: .idlergear/config.toml"""
        return self.idlergear_dir / "config.toml"

    # === Knowledge directories ===

    @property
    def issues_dir(self) -> Path:
        """Local issue tracking: .idlergear/issues/"""
        return self.idlergear_dir / "issues"

    @property
    def wiki_dir(self) -> Path:
        """Local knowledge base: .idlergear/wiki/"""
        return self.idlergear_dir / "wiki"

    @property
    def notes_dir(self) -> Path:
        """Quick notes: .idlergear/notes/"""
        return self.idlergear_dir / "notes"

    @property
    def plans_dir(self) -> Path:
        """Implementation plans: .idlergear/plans/"""
        return self.idlergear_dir / "plans"

    @property
    def runs_dir(self) -> Path:
        """Script execution logs: .idlergear/runs/"""
        return self.idlergear_dir / "runs"

    @property
    def vision_dir(self) -> Path:
        """Project vision: .idlergear/vision/"""
        return self.idlergear_dir / "vision"

    @property
    def projects_dir(self) -> Path:
        """Kanban projects: .idlergear/projects/"""
        return self.idlergear_dir / "projects"

    @property
    def sync_dir(self) -> Path:
        """Sync state with external systems: .idlergear/sync/"""
        return self.idlergear_dir / "sync"

    # === Specific files ===

    @property
    def vision_file(self) -> Path:
        """Main vision document: .idlergear/vision/VISION.md"""
        return self.vision_dir / "VISION.md"

    @property
    def issues_index(self) -> Path:
        """Issues index for fast lookup: .idlergear/issues/index.json"""
        return self.issues_dir / "index.json"

    @property
    def wiki_index(self) -> Path:
        """Wiki index for fast lookup: .idlergear/wiki/index.json"""
        return self.wiki_dir / "index.json"

    @property
    def plans_index(self) -> Path:
        """Plans index for fast lookup: .idlergear/plans/index.json"""
        return self.plans_dir / "index.json"

    # === Legacy paths (for migration) ===

    @property
    def legacy_tasks_dir(self) -> Path:
        """Legacy tasks directory (v0.2): .idlergear/tasks/"""
        return self.idlergear_dir / "tasks"

    @property
    def legacy_reference_dir(self) -> Path:
        """Legacy reference directory (v0.2): .idlergear/reference/"""
        return self.idlergear_dir / "reference"

    @property
    def legacy_explorations_dir(self) -> Path:
        """Legacy explorations directory (v0.2): .idlergear/explorations/"""
        return self.idlergear_dir / "explorations"

    @property
    def legacy_vision_file(self) -> Path:
        """Legacy vision file (v0.2): .idlergear/vision.md"""
        return self.idlergear_dir / "vision.md"

    # === Directory lists ===

    def get_all_directories(self) -> list[Path]:
        """Get all directories that should exist in v0.3 schema."""
        return [
            self.idlergear_dir,
            self.issues_dir,
            self.wiki_dir,
            self.notes_dir,
            self.plans_dir,
            self.runs_dir,
            self.vision_dir,
            self.projects_dir,
            self.sync_dir,
        ]

    def get_legacy_directories(self) -> list[Path]:
        """Get legacy directories that may need migration."""
        return [
            self.legacy_tasks_dir,
            self.legacy_reference_dir,
            self.legacy_explorations_dir,
        ]

    # === Validation ===

    def exists(self) -> bool:
        """Check if .idlergear/ exists."""
        return self.idlergear_dir.exists()

    def validate(self) -> dict[str, Any]:
        """Validate the directory structure.

        Returns:
            Dict with validation results:
            - valid: bool, True if structure is valid
            - missing: list of missing directories
            - legacy: list of legacy directories found
            - errors: list of error messages
        """
        result = {
            "valid": True,
            "missing": [],
            "legacy": [],
            "errors": [],
        }

        if not self.exists():
            result["valid"] = False
            result["errors"].append("No .idlergear/ directory found")
            return result

        # Check required directories
        for dir_path in self.get_all_directories():
            if not dir_path.exists():
                result["missing"].append(str(dir_path.relative_to(self.root)))

        # Check for legacy directories
        for dir_path in self.get_legacy_directories():
            if dir_path.exists():
                result["legacy"].append(str(dir_path.relative_to(self.root)))

        # Check legacy vision file
        if self.legacy_vision_file.exists() and not self.vision_file.exists():
            result["legacy"].append(str(self.legacy_vision_file.relative_to(self.root)))

        if result["missing"] or result["legacy"]:
            result["valid"] = False

        return result

    def needs_migration(self) -> bool:
        """Check if the project needs migration from v0.2 to v0.3."""
        return (
            self.legacy_tasks_dir.exists() or
            self.legacy_reference_dir.exists() or
            self.legacy_explorations_dir.exists() or
            (self.legacy_vision_file.exists() and not self.vision_file.exists())
        )


# === Index file schemas ===

def create_empty_index() -> dict[str, Any]:
    """Create an empty index.json structure."""
    return {
        "version": SCHEMA_VERSION,
        "items": {},
        "last_updated": None,
    }


# === File type detection for organize command ===

MISPLACED_FILE_PATTERNS = {
    # Task-like files
    "TODO.md": {"type": "issue", "action": "Convert to issues"},
    "TODO.txt": {"type": "issue", "action": "Convert to issues"},
    "TODOS.md": {"type": "issue", "action": "Convert to issues"},
    "TASKS.md": {"type": "issue", "action": "Convert to issues"},
    "BACKLOG.md": {"type": "issue", "action": "Convert to issues"},
    "IDEAS.md": {"type": "issue", "action": "Convert to issues with 'idea' label"},
    "FEATURE_IDEAS.md": {"type": "issue", "action": "Convert to issues with 'enhancement' label"},

    # Note-like files
    "NOTES.md": {"type": "note", "action": "Convert to notes"},
    "SCRATCH.md": {"type": "note", "action": "Convert to notes"},
    "RESEARCH.md": {"type": "note", "action": "Convert to notes with 'research' tag"},

    # Documentation files
    "AGENTS.md": {"type": "forbidden", "action": "Use IdlerGear instead"},
}


def detect_misplaced_files(project_root: Path) -> list[dict[str, Any]]:
    """Find misplaced files that should be organized.

    Returns:
        List of dicts with 'path', 'type', 'action' for each misplaced file.
    """
    results = []

    for name, info in MISPLACED_FILE_PATTERNS.items():
        file_path = project_root / name
        if file_path.exists():
            results.append({
                "path": file_path,
                "name": name,
                "type": info["type"],
                "action": info["action"],
            })

    # Check for SESSION_*.md files
    for f in project_root.glob("SESSION_*.md"):
        results.append({
            "path": f,
            "name": f.name,
            "type": "note",
            "action": "Convert to notes",
        })

    # Check for *-notes.md files
    for f in project_root.glob("*-notes.md"):
        results.append({
            "path": f,
            "name": f.name,
            "type": "note",
            "action": "Convert to notes",
        })

    return results
