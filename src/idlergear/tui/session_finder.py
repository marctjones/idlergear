"""Session finder - locate active Claude Code session files."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


def find_claude_session_file() -> Optional[Path]:
    """Find the active Claude Code session file.

    Looks for the session file using these strategies:
    1. CLAUDE_SESSION_FILE environment variable
    2. Standard Claude Code session location in ~/.claude/projects
    3. Most recently modified .jsonl file in ~/.claude/projects

    Returns:
        Path to session file or None if not found
    """
    # Strategy 1: Check environment variable
    env_path = os.getenv("CLAUDE_SESSION_FILE")
    if env_path:
        session_file = Path(env_path).expanduser()
        if session_file.exists() and session_file.suffix == ".jsonl":
            return session_file

    # Strategy 2: Look in standard Claude Code session directory
    claude_projects_dir = Path.home() / ".claude" / "projects"

    if not claude_projects_dir.exists():
        return None

    # Find project directory for current working directory
    cwd = Path.cwd()
    cwd_normalized = str(cwd).replace("/", "-").lstrip("-")

    # Look for matching project directory
    for project_dir in claude_projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        if cwd_normalized in project_dir.name:
            # Find most recent .jsonl file in this project
            jsonl_files = list(project_dir.glob("*.jsonl"))
            if jsonl_files:
                # Return most recently modified
                return max(jsonl_files, key=lambda p: p.stat().st_mtime)

    # Strategy 3: Fallback - find most recent .jsonl across all projects
    all_jsonl = list(claude_projects_dir.rglob("*.jsonl"))
    if all_jsonl:
        return max(all_jsonl, key=lambda p: p.stat().st_mtime)

    return None


def get_session_metadata(session_file: Path) -> dict:
    """Extract metadata from a session file.

    Args:
        session_file: Path to .jsonl session file

    Returns:
        Dictionary with session metadata (project, start_time, etc.)
    """
    if not session_file.exists():
        return {}

    # Read first line to get session metadata
    try:
        with open(session_file, "r") as f:
            first_line = f.readline()
            if first_line:
                data = json.loads(first_line)
                return {
                    "file": str(session_file),
                    "project": session_file.parent.name,
                    "size": session_file.stat().st_size,
                    "created": session_file.stat().st_ctime,
                    "modified": session_file.stat().st_mtime,
                }
    except (json.JSONDecodeError, OSError):
        pass

    return {
        "file": str(session_file),
        "size": session_file.stat().st_size if session_file.exists() else 0,
    }
