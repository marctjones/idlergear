"""Session history and snapshot management for IdlerGear.

Provides git-like session history with branching, allowing users to:
- Save full session snapshots (not just current state)
- Branch sessions to explore different approaches
- Restore to previous session states
- Compare sessions
- Track session lineage
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from idlergear.config import find_idlergear_root


class SessionSnapshot:
    """Represents a full session snapshot."""

    def __init__(self, data: dict[str, Any]):
        """Initialize from snapshot data dict."""
        self.data = data

    @property
    def session_id(self) -> str:
        """Get session ID."""
        return self.data["session_id"]

    @property
    def branch(self) -> str:
        """Get branch name."""
        return self.data.get("branch", "main")

    @property
    def parent(self) -> Optional[str]:
        """Get parent session ID."""
        return self.data.get("parent")

    @property
    def timestamp(self) -> str:
        """Get ISO timestamp."""
        return self.data["timestamp"]

    @property
    def duration_seconds(self) -> int:
        """Get session duration in seconds."""
        return self.data.get("duration_seconds", 0)

    @property
    def state(self) -> dict[str, Any]:
        """Get session state (task, files, git, notes)."""
        return self.data.get("state", {})

    @property
    def outcome(self) -> dict[str, Any]:
        """Get session outcome."""
        return self.data.get("outcome", {})

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.data


class SessionIndex:
    """Manages session index (registry of all sessions and branches)."""

    def __init__(self, root: Path):
        """Initialize session index.

        Args:
            root: IdlerGear root directory
        """
        self.root = root
        self.sessions_dir = root / ".idlergear" / "sessions"
        self.index_file = self.sessions_dir / "index.json"

    def load(self) -> dict[str, Any]:
        """Load session index.

        Returns:
            Index data or default structure if doesn't exist
        """
        if not self.index_file.exists():
            return {
                "version": "2.0",
                "current_branch": "main",
                "current_session": None,
                "branches": {
                    "main": {
                        "created": datetime.now().isoformat(),
                        "sessions": [],
                        "latest": None,
                    }
                },
            }

        try:
            return json.loads(self.index_file.read_text())
        except (json.JSONDecodeError, OSError):
            # Corrupted index, return default
            return self.load()

    def save(self, index: dict[str, Any]) -> None:
        """Save session index.

        Args:
            index: Index data to save
        """
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.index_file.write_text(json.dumps(index, indent=2))

    def get_current_branch(self) -> str:
        """Get current branch name."""
        index = self.load()
        return index.get("current_branch", "main")

    def get_current_session(self) -> Optional[str]:
        """Get current session ID."""
        index = self.load()
        return index.get("current_session")

    def get_branch_sessions(self, branch: str) -> list[str]:
        """Get list of session IDs for a branch.

        Args:
            branch: Branch name

        Returns:
            List of session IDs in chronological order
        """
        index = self.load()
        branch_data = index.get("branches", {}).get(branch, {})
        return branch_data.get("sessions", [])

    def add_session(self, session_id: str, branch: str = "main") -> None:
        """Add session to index.

        Args:
            session_id: Session ID to add
            branch: Branch name (default: main)
        """
        index = self.load()

        # Ensure branch exists
        if branch not in index["branches"]:
            index["branches"][branch] = {
                "created": datetime.now().isoformat(),
                "sessions": [],
                "latest": None,
            }

        # Add session to branch
        branch_data = index["branches"][branch]
        if session_id not in branch_data["sessions"]:
            branch_data["sessions"].append(session_id)
            branch_data["latest"] = session_id

        # Update current session
        index["current_session"] = session_id
        index["current_branch"] = branch

        self.save(index)


class SessionHistory:
    """Manages session history with snapshots and branching."""

    def __init__(self, root: Optional[Path] = None, auto_migrate: bool = True):
        """Initialize session history manager.

        Args:
            root: IdlerGear root directory. If None, auto-detect.
            auto_migrate: If True, automatically migrate old session_state.json
        """
        self.root = root or find_idlergear_root()
        if not self.root:
            raise ValueError("Not in an IdlerGear project")

        self.sessions_dir = self.root / ".idlergear" / "sessions"
        self.checkpoints_dir = self.sessions_dir / "checkpoints"
        self.index = SessionIndex(self.root)

        # Auto-migrate from old session_state.json if exists
        if auto_migrate:
            migrate_from_old_session_state()

    def _get_session_file(self, session_id: str, branch: str = "main") -> Path:
        """Get path to session file.

        Args:
            session_id: Session ID
            branch: Branch name

        Returns:
            Path to session JSON file
        """
        return self.sessions_dir / branch / f"{session_id}.json"

    def _generate_session_id(self, branch: str = "main") -> str:
        """Generate new session ID for a branch.

        Args:
            branch: Branch name to generate ID for

        Returns:
            Session ID (e.g., s001, s002, ...)
        """
        sessions = self.index.get_branch_sessions(branch)

        # Extract numeric part and increment
        if not sessions:
            return "s001"

        # Get last session number
        last_num = 0
        for sid in sessions:
            if sid.startswith("s"):
                try:
                    num = int(sid[1:])
                    last_num = max(last_num, num)
                except ValueError:
                    continue

        return f"s{last_num + 1:03d}"

    def create_snapshot(
        self,
        state: dict[str, Any],
        conversation: Optional[dict[str, Any]] = None,
        code_changes: Optional[dict[str, Any]] = None,
        statistics: Optional[dict[str, Any]] = None,
        outcome: Optional[dict[str, Any]] = None,
        duration_seconds: int = 0,
        parent: Optional[str] = None,
        branch: str = "main",
    ) -> SessionSnapshot:
        """Create a new session snapshot.

        Args:
            state: Session state (task, files, git, notes)
            conversation: Conversation summary
            code_changes: Code changes made
            statistics: Session statistics
            outcome: Session outcome
            duration_seconds: Session duration
            parent: Parent session ID
            branch: Branch name

        Returns:
            Created snapshot
        """
        session_id = self._generate_session_id(branch)

        # If parent not specified, use latest session from current branch
        if parent is None:
            sessions = self.index.get_branch_sessions(branch)
            parent = sessions[-1] if sessions else None

        snapshot_data = {
            "session_id": session_id,
            "branch": branch,
            "parent": parent,
            "children": [],
            "forks": [],
            "forked_from": None,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration_seconds,
            "state": state,
            "conversation": conversation or {},
            "code_changes": code_changes or {},
            "statistics": statistics or {},
            "outcome": outcome or {},
        }

        snapshot = SessionSnapshot(snapshot_data)

        # Save snapshot to file
        session_file = self._get_session_file(session_id, branch)
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps(snapshot_data, indent=2))

        # Update parent's children list if parent exists
        if parent:
            parent_snapshot = self.load_snapshot(parent, branch)
            if parent_snapshot:
                parent_data = parent_snapshot.to_dict()
                if session_id not in parent_data.get("children", []):
                    parent_data.setdefault("children", []).append(session_id)
                    parent_file = self._get_session_file(parent, branch)
                    parent_file.write_text(json.dumps(parent_data, indent=2))

        # Add to index
        self.index.add_session(session_id, branch)

        return snapshot

    def load_snapshot(self, session_id: str, branch: str = "main") -> Optional[SessionSnapshot]:
        """Load a session snapshot.

        Args:
            session_id: Session ID to load
            branch: Branch name

        Returns:
            SessionSnapshot or None if not found
        """
        session_file = self._get_session_file(session_id, branch)

        if not session_file.exists():
            return None

        try:
            data = json.loads(session_file.read_text())
            return SessionSnapshot(data)
        except (json.JSONDecodeError, OSError):
            return None

    def list_sessions(self, branch: str = "main") -> list[SessionSnapshot]:
        """List all sessions in a branch.

        Args:
            branch: Branch name

        Returns:
            List of session snapshots in chronological order
        """
        session_ids = self.index.get_branch_sessions(branch)
        snapshots = []

        for session_id in session_ids:
            snapshot = self.load_snapshot(session_id, branch)
            if snapshot:
                snapshots.append(snapshot)

        return snapshots

    def get_latest_snapshot(self, branch: str = "main") -> Optional[SessionSnapshot]:
        """Get the latest session snapshot for a branch.

        Args:
            branch: Branch name

        Returns:
            Latest snapshot or None
        """
        sessions = self.list_sessions(branch)
        return sessions[-1] if sessions else None

    def get_session_history(self, session_id: str, branch: str = "main") -> list[SessionSnapshot]:
        """Get full history (ancestors) of a session.

        Args:
            session_id: Session ID
            branch: Branch name

        Returns:
            List of session snapshots from root to specified session
        """
        history = []
        current_id = session_id

        while current_id:
            snapshot = self.load_snapshot(current_id, branch)
            if not snapshot:
                break

            history.insert(0, snapshot)  # Prepend to maintain chronological order
            current_id = snapshot.parent

        return history

    def _get_last_checkpoint_time(self) -> Optional[datetime]:
        """Get timestamp of the last checkpoint.

        Returns:
            Datetime of last checkpoint or None if no checkpoints exist
        """
        checkpoints = self.list_checkpoints()
        if not checkpoints:
            return None

        # Get most recent checkpoint
        latest = checkpoints[-1]
        try:
            return datetime.fromisoformat(latest["timestamp"])
        except (ValueError, KeyError):
            return None

    def should_save_checkpoint(self, interval_minutes: int = 15) -> bool:
        """Check if a checkpoint should be saved based on time interval.

        Args:
            interval_minutes: Checkpoint interval in minutes (default: 15)

        Returns:
            True if interval has elapsed since last checkpoint
        """
        last_checkpoint = self._get_last_checkpoint_time()
        if last_checkpoint is None:
            return True

        elapsed = datetime.now() - last_checkpoint
        return elapsed.total_seconds() >= (interval_minutes * 60)

    def save_checkpoint(self, state: dict[str, Any]) -> Path:
        """Save a lightweight checkpoint.

        Args:
            state: Essential state only (task, files, git commit)

        Returns:
            Path to saved checkpoint file
        """
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

        # Generate checkpoint ID (c001, c002, etc.)
        existing = list(self.checkpoints_dir.glob("c*.json"))
        if not existing:
            checkpoint_id = "c001"
        else:
            # Extract numbers and find max
            nums = []
            for cp in existing:
                if cp.stem.startswith("c"):
                    try:
                        nums.append(int(cp.stem[1:]))
                    except ValueError:
                        continue
            next_num = max(nums) + 1 if nums else 1
            checkpoint_id = f"c{next_num:03d}"

        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "timestamp": datetime.now().isoformat(),
            "state": state,
        }

        checkpoint_file = self.checkpoints_dir / f"{checkpoint_id}.json"
        checkpoint_file.write_text(json.dumps(checkpoint_data, indent=2))

        return checkpoint_file

    def load_checkpoint(self, checkpoint_id: Optional[str] = None) -> Optional[dict[str, Any]]:
        """Load a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID to load (e.g., c001). If None, loads latest.

        Returns:
            Checkpoint data or None if not found
        """
        if checkpoint_id is None:
            # Load latest
            checkpoints = self.list_checkpoints()
            if not checkpoints:
                return None
            checkpoint_id = checkpoints[-1]["checkpoint_id"]

        checkpoint_file = self.checkpoints_dir / f"{checkpoint_id}.json"
        if not checkpoint_file.exists():
            return None

        try:
            return json.loads(checkpoint_file.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """List all checkpoints.

        Returns:
            List of checkpoint metadata dicts
        """
        if not self.checkpoints_dir.exists():
            return []

        checkpoints = []
        for checkpoint_file in sorted(self.checkpoints_dir.glob("c*.json")):
            try:
                data = json.loads(checkpoint_file.read_text())
                checkpoints.append(
                    {
                        "checkpoint_id": data["checkpoint_id"],
                        "timestamp": data["timestamp"],
                        "file": str(checkpoint_file),
                    }
                )
            except (json.JSONDecodeError, KeyError, OSError):
                continue

        return checkpoints

    def recover_from_checkpoint(self) -> Optional[dict[str, Any]]:
        """Recover state from the latest checkpoint.

        Returns:
            Recovered state or None if no checkpoint exists
        """
        checkpoint = self.load_checkpoint()
        if checkpoint:
            return checkpoint.get("state")
        return None

    def cleanup_old_checkpoints(self, keep_last_n: int = 10) -> int:
        """Clean up old checkpoints, keeping only the most recent N.

        Args:
            keep_last_n: Number of recent checkpoints to keep

        Returns:
            Number of checkpoints deleted
        """
        checkpoints = self.list_checkpoints()
        if len(checkpoints) <= keep_last_n:
            return 0

        # Delete oldest checkpoints
        to_delete = checkpoints[:-keep_last_n]
        deleted = 0

        for cp in to_delete:
            try:
                Path(cp["file"]).unlink()
                deleted += 1
            except OSError:
                continue

        return deleted


def migrate_from_old_session_state() -> bool:
    """Migrate from old session_state.json to new session history.

    This provides backwards compatibility.

    Returns:
        True if migration was performed, False if no old state existed
    """
    root = find_idlergear_root()
    if not root:
        return False

    old_state_file = root / ".idlergear" / "session_state.json"

    if not old_state_file.exists():
        return False

    try:
        # Load old state
        old_state = json.loads(old_state_file.read_text())

        # Create first session snapshot from old state (disable auto-migrate to avoid recursion)
        history = SessionHistory(root, auto_migrate=False)
        history.create_snapshot(
            state={
                "current_task_id": old_state.get("current_task_id"),
                "working_files": old_state.get("working_files", []),
                "notes": old_state.get("notes"),
                "metadata": old_state.get("metadata", {}),
            },
            outcome={
                "status": "migrated",
                "goals_achieved": ["Migrated from old session state"],
            },
        )

        # Rename old file for safety (don't delete)
        backup_file = root / ".idlergear" / "session_state.json.backup"
        old_state_file.rename(backup_file)

        return True

    except (json.JSONDecodeError, OSError):
        return False
