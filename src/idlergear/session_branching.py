"""Session branching and merging for IdlerGear.

Enables git-like branching for sessions to try different approaches without
losing main work.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root
from idlergear.session_history import SessionHistory, SessionIndex, SessionSnapshot


class SessionBranching:
    """Manages session branching operations."""

    def __init__(self, root: Path | None = None):
        """Initialize session branching manager.

        Args:
            root: IdlerGear root directory (auto-detect if None)
        """
        self.root = root or find_idlergear_root()
        if not self.root:
            raise ValueError("Not in an IdlerGear project")

        self.history = SessionHistory(self.root)
        self.index = SessionIndex(self.root)
        self.sessions_dir = self.root / ".idlergear" / "sessions"

    def create_branch(
        self,
        branch_name: str,
        from_session: str | None = None,
        from_branch: str = "main",
        purpose: str | None = None,
    ) -> dict[str, Any]:
        """Create a new session branch.

        Args:
            branch_name: Name for the new branch
            from_session: Session ID to branch from (None = latest in from_branch)
            from_branch: Branch to fork from (default: main)
            purpose: Optional description of why this branch was created

        Returns:
            Branch info dict with name, created time, forked_from

        Raises:
            ValueError: If branch already exists
        """
        # Check if branch already exists
        index_data = self.index.load()
        if branch_name in index_data.get("branches", {}):
            raise ValueError(f"Branch '{branch_name}' already exists")

        # Create branch directory
        branch_dir = self.sessions_dir / branch_name
        branch_dir.mkdir(parents=True, exist_ok=True)

        # Determine source session
        if from_session is None:
            # Use latest session from source branch
            source_snapshot = self.history.get_latest_snapshot(from_branch)
            if not source_snapshot:
                raise ValueError(f"No sessions found in branch '{from_branch}'")
            from_session = source_snapshot.session_id
        else:
            # Validate source session exists
            source_snapshot = self.history.load_snapshot(from_session, from_branch)
            if not source_snapshot:
                raise ValueError(
                    f"Session '{from_session}' not found in branch '{from_branch}'"
                )

        # Copy source session as first session in new branch
        source_file = self.sessions_dir / from_branch / f"{from_session}.json"
        dest_file = branch_dir / "s001.json"

        if source_file.exists():
            # Copy session data but update branch and session_id
            source_data = json.loads(source_file.read_text())
            source_data["session_id"] = "s001"
            source_data["branch"] = branch_name
            source_data["parent"] = f"{from_branch}/{from_session}"

            dest_file.write_text(json.dumps(source_data, indent=2))

        # Create branch metadata
        branch_metadata = {
            "name": branch_name,
            "created": datetime.now().isoformat(),
            "forked_from": f"{from_branch}/{from_session}",
            "status": "active",  # active, merged, abandoned
            "purpose": purpose,
            "outcome": None,
        }

        metadata_file = branch_dir / "branch.json"
        metadata_file.write_text(json.dumps(branch_metadata, indent=2))

        # Update index
        index_data["branches"][branch_name] = {
            "created": branch_metadata["created"],
            "sessions": ["s001"],
            "latest": "s001",
            "forked_from": branch_metadata["forked_from"],
            "status": "active",
        }
        self.index.save(index_data)

        return branch_metadata

    def checkout_branch(self, branch_name: str) -> dict[str, Any]:
        """Switch to a different branch.

        Args:
            branch_name: Branch name to switch to

        Returns:
            Dict with branch info and latest session

        Raises:
            ValueError: If branch doesn't exist
        """
        index_data = self.index.load()

        if branch_name not in index_data.get("branches", {}):
            raise ValueError(f"Branch '{branch_name}' not found")

        # Update current branch
        index_data["current_branch"] = branch_name

        # Get latest session in branch
        branch_data = index_data["branches"][branch_name]
        latest_session = branch_data.get("latest")

        if latest_session:
            index_data["current_session"] = latest_session

        self.index.save(index_data)

        return {
            "branch": branch_name,
            "latest_session": latest_session,
            "session_count": len(branch_data.get("sessions", [])),
        }

    def list_branches(self) -> list[dict[str, Any]]:
        """List all branches.

        Returns:
            List of branch info dicts
        """
        index_data = self.index.load()
        current_branch = index_data.get("current_branch", "main")

        branches = []
        for branch_name, branch_data in index_data.get("branches", {}).items():
            # Load branch metadata if exists
            metadata_file = self.sessions_dir / branch_name / "branch.json"
            metadata = {}
            if metadata_file.exists():
                try:
                    metadata = json.loads(metadata_file.read_text())
                except json.JSONDecodeError:
                    pass

            branches.append(
                {
                    "name": branch_name,
                    "current": branch_name == current_branch,
                    "sessions": len(branch_data.get("sessions", [])),
                    "latest": branch_data.get("latest"),
                    "created": branch_data.get("created"),
                    "forked_from": metadata.get("forked_from"),
                    "status": metadata.get("status", "active"),
                    "purpose": metadata.get("purpose"),
                }
            )

        return sorted(branches, key=lambda b: b["created"] or "")

    def diff_branches(
        self, branch_a: str, branch_b: str
    ) -> dict[str, Any]:
        """Compare two branches.

        Args:
            branch_a: First branch name
            branch_b: Second branch name

        Returns:
            Diff dict with comparison results

        Raises:
            ValueError: If either branch doesn't exist
        """
        # Get sessions from both branches
        sessions_a = self.history.list_sessions(branch=branch_a)
        sessions_b = self.history.list_sessions(branch=branch_b)

        if not sessions_a:
            raise ValueError(f"Branch '{branch_a}' has no sessions")
        if not sessions_b:
            raise ValueError(f"Branch '{branch_b}' has no sessions")

        # Get latest snapshot from each
        latest_a = sessions_a[-1]
        latest_b = sessions_b[-1]

        # Compare working files
        files_a = set(latest_a.state.get("working_files", []))
        files_b = set(latest_b.state.get("working_files", []))

        # Compare tasks
        tasks_a_created = latest_a.outcome.get("tasks_created", [])
        tasks_b_created = latest_b.outcome.get("tasks_created", [])

        return {
            "branch_a": {
                "name": branch_a,
                "sessions": len(sessions_a),
                "latest": latest_a.session_id,
                "duration": sum(s.duration_seconds for s in sessions_a),
            },
            "branch_b": {
                "name": branch_b,
                "sessions": len(sessions_b),
                "latest": latest_b.session_id,
                "duration": sum(s.duration_seconds for s in sessions_b),
            },
            "files": {
                "common": list(files_a & files_b),
                "only_in_a": list(files_a - files_b),
                "only_in_b": list(files_b - files_a),
            },
            "tasks": {
                "a_created": len(tasks_a_created),
                "b_created": len(tasks_b_created),
            },
        }

    def merge_branch(
        self, source_branch: str, target_branch: str = "main"
    ) -> dict[str, Any]:
        """Merge a branch into target branch.

        This creates a new session in the target branch with the state
        from the source branch's latest session.

        Args:
            source_branch: Branch to merge from
            target_branch: Branch to merge into (default: main)

        Returns:
            Merge result dict with new session info

        Raises:
            ValueError: If branches don't exist
        """
        # Get latest session from source branch
        source_sessions = self.history.list_sessions(branch=source_branch)
        if not source_sessions:
            raise ValueError(f"Branch '{source_branch}' has no sessions")

        source_latest = source_sessions[-1]

        # Create new session in target branch with source state
        new_session = self.history.create_snapshot(
            state=source_latest.state,
            outcome=source_latest.outcome,
            duration_seconds=source_latest.duration_seconds,
            branch=target_branch,
            parent=source_latest.session_id,
        )

        # Mark source branch as merged
        metadata_file = self.sessions_dir / source_branch / "branch.json"
        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text())
            metadata["status"] = "merged"
            metadata["merged_at"] = datetime.now().isoformat()
            metadata["merged_to"] = target_branch
            metadata["outcome"] = "success"
            metadata_file.write_text(json.dumps(metadata, indent=2))

        # Update index
        index_data = self.index.load()
        if source_branch in index_data.get("branches", {}):
            index_data["branches"][source_branch]["status"] = "merged"
        self.index.save(index_data)

        return {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "new_session": new_session,
            "status": "merged",
        }

    def abandon_branch(self, branch_name: str, reason: str | None = None) -> bool:
        """Mark a branch as abandoned.

        Args:
            branch_name: Branch to abandon
            reason: Optional reason for abandoning

        Returns:
            True if abandoned successfully

        Raises:
            ValueError: If branch is main or doesn't exist
        """
        if branch_name == "main":
            raise ValueError("Cannot abandon main branch")

        index_data = self.index.load()
        if branch_name not in index_data.get("branches", {}):
            raise ValueError(f"Branch '{branch_name}' not found")

        # Update branch metadata
        metadata_file = self.sessions_dir / branch_name / "branch.json"
        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text())
            metadata["status"] = "abandoned"
            metadata["abandoned_at"] = datetime.now().isoformat()
            metadata["outcome"] = "failed"
            if reason:
                metadata["abandon_reason"] = reason
            metadata_file.write_text(json.dumps(metadata, indent=2))

        # Update index
        index_data["branches"][branch_name]["status"] = "abandoned"
        self.index.save(index_data)

        # If currently on this branch, switch to main
        if index_data.get("current_branch") == branch_name:
            self.checkout_branch("main")

        return True

    def delete_branch(self, branch_name: str, force: bool = False) -> bool:
        """Delete a branch and its sessions.

        Args:
            branch_name: Branch to delete
            force: If True, delete even if not merged/abandoned

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If branch is main, doesn't exist, or not merged/abandoned
        """
        if branch_name == "main":
            raise ValueError("Cannot delete main branch")

        index_data = self.index.load()
        if branch_name not in index_data.get("branches", {}):
            raise ValueError(f"Branch '{branch_name}' not found")

        # Check if branch is merged or abandoned
        branch_dir = self.sessions_dir / branch_name
        metadata_file = branch_dir / "branch.json"

        if not force and metadata_file.exists():
            metadata = json.loads(metadata_file.read_text())
            status = metadata.get("status", "active")
            if status == "active":
                raise ValueError(
                    f"Branch '{branch_name}' is still active. "
                    "Merge or abandon it first, or use force=True"
                )

        # Delete branch directory
        if branch_dir.exists():
            shutil.rmtree(branch_dir)

        # Remove from index
        if branch_name in index_data["branches"]:
            del index_data["branches"][branch_name]
        self.index.save(index_data)

        # If currently on this branch, switch to main
        if index_data.get("current_branch") == branch_name:
            self.checkout_branch("main")

        return True
