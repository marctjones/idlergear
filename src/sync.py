"""
Sync commands: Coordinate work between local and web LLM environments.
"""

import subprocess
from pathlib import Path
from typing import Tuple
from src.status import ProjectStatus


class ProjectSync:
    """Manage synchronization between local and web LLM environments."""

    SYNC_BRANCH_PREFIX = "idlergear-web-sync"

    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.status = ProjectStatus(project_path)

    def _run_git(self, *args, check=True) -> Tuple[int, str, str]:
        """Run a git command and return (returncode, stdout, stderr)."""
        result = subprocess.run(
            ["git", *args],
            cwd=self.project_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"Git command failed: {result.stderr}")
        return result.returncode, result.stdout, result.stderr

    def get_sync_branch_name(self) -> str:
        """Generate sync branch name from current branch."""
        current_branch = self.status.get_git_branch()
        if not current_branch:
            current_branch = "main"
        return f"{self.SYNC_BRANCH_PREFIX}-{current_branch}"

    def sync_push(self, include_untracked: bool = False) -> dict:
        """
        Push current state to sync branch for web environment.

        Returns dict with status info.
        """
        if not self.status.is_git_repo:
            raise RuntimeError("Not a git repository")

        current_branch = self.status.get_git_branch()
        sync_branch = self.get_sync_branch_name()

        result = {
            "current_branch": current_branch,
            "sync_branch": sync_branch,
            "created_branch": False,
            "committed_changes": False,
            "pushed": False,
        }

        # Check if sync branch already exists
        returncode, stdout, stderr = self._run_git(
            "rev-parse", "--verify", sync_branch, check=False
        )
        branch_exists = returncode == 0

        if branch_exists:
            # Switch to sync branch
            self._run_git("checkout", sync_branch)

            # Merge current branch into sync
            self._run_git("merge", current_branch, "--no-edit")
        else:
            # Create new sync branch from current branch
            self._run_git("checkout", "-b", sync_branch)
            result["created_branch"] = True

        # Add all tracked and optionally untracked files
        if include_untracked:
            self._run_git("add", "-A")
        else:
            self._run_git("add", "-u")  # Only tracked files

        # Check if there are changes to commit
        returncode, stdout, stderr = self._run_git("status", "--porcelain", check=False)
        has_changes = bool(stdout.strip())

        if has_changes:
            # Commit changes
            self._run_git("commit", "-m", "sync: Push state to web environment")
            result["committed_changes"] = True

        # Push to remote
        self._run_git("push", "-u", "origin", sync_branch)
        result["pushed"] = True

        # Switch back to original branch
        self._run_git("checkout", current_branch)

        return result

    def sync_pull(self, cleanup: bool = True) -> dict:
        """
        Pull changes from sync branch to current branch.

        Returns dict with status info.
        """
        if not self.status.is_git_repo:
            raise RuntimeError("Not a git repository")

        current_branch = self.status.get_git_branch()
        sync_branch = self.get_sync_branch_name()

        result = {
            "current_branch": current_branch,
            "sync_branch": sync_branch,
            "fetched": False,
            "merged": False,
            "cleaned_up": False,
        }

        # Fetch from remote
        self._run_git("fetch", "origin")
        result["fetched"] = True

        # Check if remote sync branch exists
        returncode, stdout, stderr = self._run_git(
            "ls-remote", "--heads", "origin", sync_branch, check=False
        )

        if not stdout.strip():
            raise RuntimeError(f"Sync branch '{sync_branch}' not found on remote")

        # Merge sync branch into current branch
        self._run_git("merge", f"origin/{sync_branch}", "--no-edit")
        result["merged"] = True

        # Cleanup if requested
        if cleanup:
            # Delete local sync branch if it exists
            returncode, _, _ = self._run_git(
                "rev-parse", "--verify", sync_branch, check=False
            )
            if returncode == 0:
                self._run_git("branch", "-D", sync_branch, check=False)

            # Delete remote sync branch
            self._run_git("push", "origin", "--delete", sync_branch, check=False)
            result["cleaned_up"] = True

        return result

    def sync_status(self) -> dict:
        """
        Check status of sync branches.

        Returns dict with sync status info.
        """
        if not self.status.is_git_repo:
            raise RuntimeError("Not a git repository")

        current_branch = self.status.get_git_branch()
        sync_branch = self.get_sync_branch_name()

        result = {
            "current_branch": current_branch,
            "sync_branch": sync_branch,
            "local_exists": False,
            "remote_exists": False,
            "uncommitted_changes": self.status.get_uncommitted_changes(),
            "ahead_behind": None,
        }

        # Check local sync branch
        returncode, _, _ = self._run_git(
            "rev-parse", "--verify", sync_branch, check=False
        )
        result["local_exists"] = returncode == 0

        # Check remote sync branch
        self._run_git("fetch", "origin", check=False)
        returncode, stdout, _ = self._run_git(
            "ls-remote", "--heads", "origin", sync_branch, check=False
        )
        result["remote_exists"] = bool(stdout.strip())

        # If remote exists, check ahead/behind status
        if result["remote_exists"]:
            returncode, stdout, _ = self._run_git(
                "rev-list",
                "--left-right",
                "--count",
                f"{current_branch}...origin/{sync_branch}",
                check=False,
            )
            if returncode == 0 and stdout.strip():
                ahead, behind = stdout.strip().split()
                result["ahead_behind"] = {"ahead": int(ahead), "behind": int(behind)}

        return result
