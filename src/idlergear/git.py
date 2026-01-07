"""
Git operations MCP server for IdlerGear.

Provides git integration with IdlerGear-specific task linking features.
Replaces Node.js git-mcp-server with pure Python implementation.
"""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class GitStatus:
    """Git repository status."""

    branch: str
    ahead: int
    behind: int
    staged: List[str]
    modified: List[str]
    untracked: List[str]
    conflicts: List[str]
    last_commit: Optional[Dict[str, str]]


@dataclass
class GitCommit:
    """Git commit information."""

    hash: str
    short_hash: str
    author: str
    email: str
    date: str
    message: str
    files: List[str]


class GitServer:
    """Git operations server for MCP."""

    def __init__(self, allowed_repos: Optional[List[str]] = None):
        """
        Initialize git server.

        Args:
            allowed_repos: List of allowed repository paths. If None, uses cwd.
        """
        self.allowed_repos = allowed_repos or [os.getcwd()]

    def _is_allowed_repo(self, path: str) -> bool:
        """Check if path is within allowed repositories."""
        abs_path = Path(path).resolve()
        for repo in self.allowed_repos:
            repo_path = Path(repo).resolve()
            try:
                abs_path.relative_to(repo_path)
                return True
            except ValueError:
                continue
        return False

    def _run_git(
        self, args: List[str], cwd: Optional[str] = None, check: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Run git command.

        Args:
            args: Git command arguments
            cwd: Working directory
            check: Raise exception on non-zero exit

        Returns:
            CompletedProcess result

        Raises:
            ValueError: If repository not allowed
            subprocess.CalledProcessError: If command fails and check=True
        """
        if cwd and not self._is_allowed_repo(cwd):
            raise ValueError(f"Repository not allowed: {cwd}")

        cwd = cwd or os.getcwd()
        return subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
        )

    def status(self, repo_path: Optional[str] = None) -> GitStatus:
        """
        Get git repository status.

        Args:
            repo_path: Repository path (defaults to cwd)

        Returns:
            GitStatus object with repository state
        """
        repo_path = repo_path or os.getcwd()

        # Get branch info
        branch_result = self._run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path
        )
        branch = branch_result.stdout.strip()

        # Get ahead/behind counts
        ahead = 0
        behind = 0
        try:
            count_result = self._run_git(
                ["rev-list", "--left-right", "--count", f"HEAD...@{{u}}"],
                cwd=repo_path,
                check=False,
            )
            if count_result.returncode == 0:
                counts = count_result.stdout.strip().split()
                ahead = int(counts[0]) if len(counts) > 0 else 0
                behind = int(counts[1]) if len(counts) > 1 else 0
        except (ValueError, IndexError):
            pass

        # Get status
        status_result = self._run_git(
            ["status", "--porcelain=v1", "-z"], cwd=repo_path
        )

        staged = []
        modified = []
        untracked = []
        conflicts = []

        # Parse null-terminated status output
        entries = status_result.stdout.split("\0")
        for entry in entries:
            if not entry:
                continue

            index_status = entry[0]
            worktree_status = entry[1]
            filepath = entry[3:]

            # Conflict markers
            if index_status in ("U", "D", "A") and worktree_status in ("U", "D", "A"):
                conflicts.append(filepath)
            # Staged changes
            elif index_status in ("M", "A", "D", "R", "C"):
                staged.append(filepath)
            # Modified (unstaged) changes
            elif worktree_status in ("M", "D"):
                modified.append(filepath)
            # Untracked files
            elif index_status == "?" and worktree_status == "?":
                untracked.append(filepath)

        # Get last commit
        last_commit = None
        try:
            log_result = self._run_git(
                ["log", "-1", "--format=%H|%h|%an|%ae|%ai|%s"], cwd=repo_path
            )
            if log_result.stdout.strip():
                parts = log_result.stdout.strip().split("|")
                last_commit = {
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "author": parts[2],
                    "email": parts[3],
                    "date": parts[4],
                    "message": parts[5],
                }
        except subprocess.CalledProcessError:
            pass

        return GitStatus(
            branch=branch,
            ahead=ahead,
            behind=behind,
            staged=staged,
            modified=modified,
            untracked=untracked,
            conflicts=conflicts,
            last_commit=last_commit,
        )

    def diff(
        self,
        repo_path: Optional[str] = None,
        staged: bool = False,
        files: Optional[List[str]] = None,
        context_lines: int = 3,
    ) -> str:
        """
        Get git diff.

        Args:
            repo_path: Repository path
            staged: Show staged changes (git diff --cached)
            files: Specific files to diff
            context_lines: Number of context lines

        Returns:
            Diff output
        """
        repo_path = repo_path or os.getcwd()

        args = ["diff", f"--unified={context_lines}"]
        if staged:
            args.append("--cached")

        if files:
            args.append("--")
            args.extend(files)

        result = self._run_git(args, cwd=repo_path)
        return result.stdout

    def log(
        self,
        repo_path: Optional[str] = None,
        max_count: int = 10,
        since: Optional[str] = None,
        until: Optional[str] = None,
        author: Optional[str] = None,
        grep: Optional[str] = None,
    ) -> List[GitCommit]:
        """
        Get git commit log.

        Args:
            repo_path: Repository path
            max_count: Maximum number of commits
            since: Show commits since date
            until: Show commits until date
            author: Filter by author
            grep: Filter by commit message

        Returns:
            List of GitCommit objects
        """
        repo_path = repo_path or os.getcwd()

        args = [
            "log",
            f"--max-count={max_count}",
            "--format=COMMIT_START%nHASH:%H%nSHORT:%h%nAUTHOR:%an%nEMAIL:%ae%nDATE:%ai%nMESSAGE_START%n%B%nMESSAGE_END%nFILES_START",
            "--name-only",
        ]

        if since:
            args.append(f"--since={since}")
        if until:
            args.append(f"--until={until}")
        if author:
            args.append(f"--author={author}")
        if grep:
            args.append(f"--grep={grep}")

        result = self._run_git(args, cwd=repo_path)

        commits = []
        entries = result.stdout.split("COMMIT_START\n")[1:]  # Skip first empty element

        for entry in entries:
            if not entry.strip():
                continue

            lines = entry.split("\n")

            # Parse structured output
            data = {}
            message_lines = []
            files_lines = []
            in_message = False
            in_files = False

            for line in lines:
                if line.startswith("HASH:"):
                    data["hash"] = line[5:]
                elif line.startswith("SHORT:"):
                    data["short_hash"] = line[6:]
                elif line.startswith("AUTHOR:"):
                    data["author"] = line[7:]
                elif line.startswith("EMAIL:"):
                    data["email"] = line[6:]
                elif line.startswith("DATE:"):
                    data["date"] = line[5:]
                elif line == "MESSAGE_START":
                    in_message = True
                elif line == "MESSAGE_END":
                    in_message = False
                elif line == "FILES_START":
                    in_files = True
                elif in_message:
                    message_lines.append(line)
                elif in_files and line.strip():
                    files_lines.append(line.strip())

            if data.get("hash"):
                commits.append(
                    GitCommit(
                        hash=data["hash"],
                        short_hash=data["short_hash"],
                        author=data["author"],
                        email=data["email"],
                        date=data["date"],
                        message="\n".join(message_lines).strip(),
                        files=files_lines,
                    )
                )

        return commits

    def add(
        self, files: List[str], repo_path: Optional[str] = None, all: bool = False
    ) -> str:
        """
        Stage files for commit.

        Args:
            files: Files to stage
            repo_path: Repository path
            all: Stage all changes (git add -A)

        Returns:
            Success message
        """
        repo_path = repo_path or os.getcwd()

        if all:
            result = self._run_git(["add", "-A"], cwd=repo_path)
        else:
            args = ["add", "--"] + files
            result = self._run_git(args, cwd=repo_path)

        return f"Staged {len(files) if not all else 'all'} files"

    def commit(
        self,
        message: str,
        repo_path: Optional[str] = None,
        task_id: Optional[int] = None,
    ) -> str:
        """
        Create a commit.

        Args:
            message: Commit message
            repo_path: Repository path
            task_id: Optional task ID to link

        Returns:
            Commit hash
        """
        repo_path = repo_path or os.getcwd()

        # Add task ID to message if provided
        if task_id is not None:
            message = f"{message}\n\nTask: #{task_id}"

        result = self._run_git(["commit", "-m", message], cwd=repo_path)

        # Extract commit hash from output
        hash_result = self._run_git(["rev-parse", "HEAD"], cwd=repo_path)
        return hash_result.stdout.strip()

    def reset(
        self,
        files: Optional[List[str]] = None,
        repo_path: Optional[str] = None,
        hard: bool = False,
    ) -> str:
        """
        Unstage files or reset repository.

        Args:
            files: Files to unstage (None = all)
            repo_path: Repository path
            hard: Hard reset (WARNING: discards changes)

        Returns:
            Success message
        """
        repo_path = repo_path or os.getcwd()

        if hard:
            self._run_git(["reset", "--hard"], cwd=repo_path)
            return "Hard reset complete (changes discarded)"
        elif files:
            args = ["reset", "HEAD", "--"] + files
            self._run_git(args, cwd=repo_path)
            return f"Unstaged {len(files)} files"
        else:
            self._run_git(["reset", "HEAD"], cwd=repo_path)
            return "Unstaged all files"

    def show(self, commit: str, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Show commit details.

        Args:
            commit: Commit hash or reference
            repo_path: Repository path

        Returns:
            Commit details with diff
        """
        repo_path = repo_path or os.getcwd()

        # Get commit info with files
        info_result = self._run_git(
            ["show", "--format=HASH:%H%nSHORT:%h%nAUTHOR:%an%nEMAIL:%ae%nDATE:%ai%nMESSAGE_START%n%B%nMESSAGE_END%nFILES_START", "--name-only", commit],
            cwd=repo_path,
        )

        lines = info_result.stdout.split("\n")

        # Parse structured output
        data = {}
        message_lines = []
        files_lines = []
        in_message = False
        in_files = False

        for line in lines:
            if line.startswith("HASH:"):
                data["hash"] = line[5:]
            elif line.startswith("SHORT:"):
                data["short_hash"] = line[6:]
            elif line.startswith("AUTHOR:"):
                data["author"] = line[7:]
            elif line.startswith("EMAIL:"):
                data["email"] = line[6:]
            elif line.startswith("DATE:"):
                data["date"] = line[5:]
            elif line == "MESSAGE_START":
                in_message = True
            elif line == "MESSAGE_END":
                in_message = False
            elif line == "FILES_START":
                in_files = True
            elif in_message:
                message_lines.append(line)
            elif in_files and line.strip():
                files_lines.append(line.strip())

        commit_info = {
            "hash": data["hash"],
            "short_hash": data["short_hash"],
            "author": data["author"],
            "email": data["email"],
            "date": data["date"],
            "message": "\n".join(message_lines).strip(),
            "files": files_lines,
        }

        # Get diff
        diff_result = self._run_git(["show", commit], cwd=repo_path)
        commit_info["diff"] = diff_result.stdout

        return commit_info

    def branch_list(self, repo_path: Optional[str] = None) -> List[Dict[str, str]]:
        """
        List branches.

        Args:
            repo_path: Repository path

        Returns:
            List of branches with current marker
        """
        repo_path = repo_path or os.getcwd()

        result = self._run_git(
            ["branch", "-v", "--format=%(HEAD)|%(refname:short)|%(upstream:short)"],
            cwd=repo_path,
        )

        branches = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|")
            branches.append(
                {
                    "current": parts[0] == "*",
                    "name": parts[1],
                    "upstream": parts[2] if len(parts) > 2 else "",
                }
            )

        return branches

    def branch_create(
        self, name: str, repo_path: Optional[str] = None, checkout: bool = True
    ) -> str:
        """
        Create a new branch.

        Args:
            name: Branch name
            repo_path: Repository path
            checkout: Checkout after creation

        Returns:
            Success message
        """
        repo_path = repo_path or os.getcwd()

        if checkout:
            self._run_git(["checkout", "-b", name], cwd=repo_path)
            return f"Created and checked out branch: {name}"
        else:
            self._run_git(["branch", name], cwd=repo_path)
            return f"Created branch: {name}"

    def branch_checkout(self, name: str, repo_path: Optional[str] = None) -> str:
        """
        Checkout a branch.

        Args:
            name: Branch name
            repo_path: Repository path

        Returns:
            Success message
        """
        repo_path = repo_path or os.getcwd()
        self._run_git(["checkout", name], cwd=repo_path)
        return f"Checked out branch: {name}"

    def branch_delete(
        self, name: str, repo_path: Optional[str] = None, force: bool = False
    ) -> str:
        """
        Delete a branch.

        Args:
            name: Branch name
            repo_path: Repository path
            force: Force delete (even if not merged)

        Returns:
            Success message
        """
        repo_path = repo_path or os.getcwd()

        flag = "-D" if force else "-d"
        self._run_git(["branch", flag, name], cwd=repo_path)
        return f"Deleted branch: {name}"

    def commit_task(
        self,
        task_id: int,
        message: str,
        repo_path: Optional[str] = None,
        auto_add: bool = True,
    ) -> str:
        """
        Commit with task linking (IdlerGear-specific).

        Args:
            task_id: Task ID to link
            message: Commit message
            repo_path: Repository path
            auto_add: Automatically stage all changes

        Returns:
            Commit hash
        """
        repo_path = repo_path or os.getcwd()

        if auto_add:
            self.add([], repo_path=repo_path, all=True)

        return self.commit(message, repo_path=repo_path, task_id=task_id)

    def status_for_task(
        self, task_id: int, repo_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get git status filtered by task files (IdlerGear-specific).

        Args:
            task_id: Task ID
            repo_path: Repository path

        Returns:
            Filtered status
        """
        # Get full status
        status = self.status(repo_path=repo_path)

        # TODO: Load task from IdlerGear and filter by task files
        # For now, return full status with task_id annotation
        return {
            "task_id": task_id,
            "branch": status.branch,
            "staged": status.staged,
            "modified": status.modified,
            "untracked": status.untracked,
            "note": "Full task file filtering requires task backend integration",
        }

    def task_commits(
        self, task_id: int, repo_path: Optional[str] = None, max_count: int = 50
    ) -> List[GitCommit]:
        """
        Find commits linked to a task (IdlerGear-specific).

        Args:
            task_id: Task ID
            repo_path: Repository path
            max_count: Maximum commits to search

        Returns:
            List of commits mentioning the task
        """
        return self.log(
            repo_path=repo_path, max_count=max_count, grep=f"Task: #{task_id}"
        )

    def sync_tasks_from_commits(
        self, repo_path: Optional[str] = None, since: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sync task status from commit messages (IdlerGear-specific).

        Args:
            repo_path: Repository path
            since: Only process commits since this date

        Returns:
            Sync summary
        """
        commits = self.log(repo_path=repo_path, max_count=100, since=since)

        task_commits = {}
        for commit in commits:
            # Look for "Task: #123" in commit message
            if "Task: #" in commit.message:
                try:
                    task_part = commit.message.split("Task: #")[1]
                    task_id = int(task_part.split()[0])
                    if task_id not in task_commits:
                        task_commits[task_id] = []
                    task_commits[task_id].append(commit)
                except (ValueError, IndexError):
                    continue

        return {
            "total_commits": len(commits),
            "task_commits": len([c for commits in task_commits.values() for c in commits]),
            "tasks_found": list(task_commits.keys()),
            "note": "Full task sync requires task backend integration",
        }
