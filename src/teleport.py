"""
Teleport session tracking for IdlerGear.

This module provides functionality to track and manage Claude Code web teleport
sessions, allowing users to log session information, list past sessions, and
export session details.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class TeleportTracker:
    """
    Manages teleport session tracking for IdlerGear projects.

    Teleport sessions represent transfers from Claude Code web to local CLI.
    This class stores metadata about each teleport session including:
    - Session UUID
    - Timestamp
    - Branch name
    - Description
    - Files changed
    """

    def __init__(self, project_path: str = "."):
        """
        Initialize the teleport tracker.

        Args:
            project_path: Path to the project root (default: current directory)
        """
        self.project_root = Path(project_path).resolve()
        self.teleport_dir = self.project_root / ".idlergear" / "teleport-sessions"
        self.metadata_file = self.teleport_dir / "metadata.json"

        # Ensure teleport directory exists
        self.teleport_dir.mkdir(parents=True, exist_ok=True)

        # Initialize metadata file if it doesn't exist
        if not self.metadata_file.exists():
            self._write_metadata({"sessions": []})

    def _read_metadata(self) -> Dict:
        """Read teleport sessions metadata."""
        if not self.metadata_file.exists():
            return {"sessions": []}

        with open(self.metadata_file, "r") as f:
            return json.load(f)

    def _write_metadata(self, data: Dict):
        """Write teleport sessions metadata."""
        with open(self.metadata_file, "w") as f:
            json.dump(data, f, indent=2)

    def _get_current_branch(self) -> str:
        """Get the current git branch name."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"

    def _get_changed_files(self) -> List[str]:
        """Get list of currently changed files."""
        try:
            # Get staged files
            staged_result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            # Get unstaged files
            unstaged_result = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            # Get untracked files
            untracked_result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            # Combine all changed files
            all_files = set()
            for result in [staged_result, unstaged_result, untracked_result]:
                files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
                all_files.update(files)

            return sorted(list(all_files))

        except subprocess.CalledProcessError:
            return []

    def log_session(
        self,
        session_id: str,
        description: Optional[str] = None,
        files_changed: Optional[List[str]] = None,
        branch: Optional[str] = None,
    ) -> Dict:
        """
        Log a teleport session.

        Args:
            session_id: The UUID from the teleport command
            description: Optional description of the session
            files_changed: Optional list of files changed (auto-detected if not provided)
            branch: Optional branch name (auto-detected if not provided)

        Returns:
            Dictionary with session information
        """
        # Get current branch if not provided
        if branch is None:
            branch = self._get_current_branch()

        # Get changed files if not provided
        if files_changed is None:
            files_changed = self._get_changed_files()

        # Create session record
        session = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "branch": branch,
            "description": description or f"Teleport session {session_id[:8]}",
            "files_changed": files_changed,
            "files_count": len(files_changed),
        }

        # Read existing metadata
        metadata = self._read_metadata()

        # Check if session already exists
        existing_index = None
        for i, s in enumerate(metadata["sessions"]):
            if s["session_id"] == session_id:
                existing_index = i
                break

        # Update or append session
        if existing_index is not None:
            metadata["sessions"][existing_index] = session
            status = "updated"
        else:
            metadata["sessions"].append(session)
            status = "created"

        # Write metadata
        self._write_metadata(metadata)

        # Also write individual session file for easy reference
        session_file = self.teleport_dir / f"{session_id}.json"
        with open(session_file, "w") as f:
            json.dump(session, f, indent=2)

        return {
            "status": status,
            "session": session,
            "session_file": str(session_file),
        }

    def list_sessions(
        self,
        limit: Optional[int] = None,
        branch: Optional[str] = None,
    ) -> List[Dict]:
        """
        List teleport sessions.

        Args:
            limit: Optional limit on number of sessions to return
            branch: Optional branch filter

        Returns:
            List of session dictionaries
        """
        metadata = self._read_metadata()
        sessions = metadata.get("sessions", [])

        # Filter by branch if specified
        if branch:
            sessions = [s for s in sessions if s.get("branch") == branch]

        # Sort by timestamp (most recent first)
        sessions = sorted(
            sessions,
            key=lambda s: s.get("timestamp", ""),
            reverse=True,
        )

        # Apply limit if specified
        if limit:
            sessions = sessions[:limit]

        return sessions

    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get a specific teleport session by ID.

        Args:
            session_id: The session UUID (full or partial)

        Returns:
            Session dictionary if found, None otherwise
        """
        metadata = self._read_metadata()
        sessions = metadata.get("sessions", [])

        # Try exact match first
        for session in sessions:
            if session["session_id"] == session_id:
                return session

        # Try partial match (for convenience)
        matches = [s for s in sessions if s["session_id"].startswith(session_id)]

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            raise ValueError(
                f"Ambiguous session ID '{session_id}'. "
                f"Matches: {[s['session_id'][:8] for s in matches]}"
            )

        return None

    def export_session(
        self,
        session_id: str,
        output_format: str = "json",
    ) -> Dict:
        """
        Export a teleport session in the specified format.

        Args:
            session_id: The session UUID
            output_format: Format for export (json or markdown)

        Returns:
            Dictionary with export content and metadata
        """
        session = self.get_session(session_id)

        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if output_format == "json":
            content = json.dumps(session, indent=2)
        elif output_format == "markdown":
            content = self._format_session_markdown(session)
        else:
            raise ValueError(f"Unsupported format: {output_format}")

        return {
            "session": session,
            "format": output_format,
            "content": content,
        }

    def _format_session_markdown(self, session: Dict) -> str:
        """Format a session as markdown."""
        lines = [
            f"# Teleport Session: {session['session_id'][:8]}",
            "",
            f"**Session ID:** `{session['session_id']}`",
            f"**Timestamp:** {session['timestamp']}",
            f"**Branch:** `{session['branch']}`",
            f"**Description:** {session['description']}",
            "",
            "## Files Changed",
            "",
        ]

        files = session.get("files_changed", [])
        if files:
            for file_path in files:
                lines.append(f"- `{file_path}`")
        else:
            lines.append("_(No files changed)_")

        lines.extend(["", f"**Total Files:** {session['files_count']}", ""])

        return "\n".join(lines)

    def format_session_list(self, sessions: List[Dict]) -> str:
        """
        Format a list of sessions for display.

        Args:
            sessions: List of session dictionaries

        Returns:
            Formatted string for terminal display
        """
        if not sessions:
            return "No teleport sessions found."

        lines = [f"Found {len(sessions)} teleport session(s):", ""]

        for session in sessions:
            session_id_short = session["session_id"][:8]
            timestamp = session.get("timestamp", "unknown")
            branch = session.get("branch", "unknown")
            desc = session.get("description", "")
            files_count = session.get("files_count", 0)

            lines.extend(
                [
                    f"📍 Session: {session_id_short}",
                    f"   Time: {timestamp}",
                    f"   Branch: {branch}",
                    f"   Description: {desc}",
                    f"   Files changed: {files_count}",
                    "",
                ]
            )

        return "\n".join(lines)

    def format_session(self, session: Dict) -> str:
        """
        Format a single session for detailed display.

        Args:
            session: Session dictionary

        Returns:
            Formatted string for terminal display
        """
        lines = [
            f"Teleport Session: {session['session_id'][:8]}",
            "",
            f"Session ID:  {session['session_id']}",
            f"Timestamp:   {session.get('timestamp', 'unknown')}",
            f"Branch:      {session.get('branch', 'unknown')}",
            f"Description: {session.get('description', '')}",
            "",
            "Files Changed:",
        ]

        files = session.get("files_changed", [])
        if files:
            for file_path in files:
                lines.append(f"  - {file_path}")
        else:
            lines.append("  (none)")

        lines.extend(["", f"Total: {session.get('files_count', 0)} file(s)", ""])

        return "\n".join(lines)
