"""Populates graph database with git history data."""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Set

from ..database import GraphDatabase
from idlergear.git import GitServer, GitCommit


class GitPopulator:
    """Populates graph database with git commit and file change data.

    Example:
        >>> from idlergear.graph import get_database
        >>> db = get_database()
        >>> populator = GitPopulator(db)
        >>> populator.populate(max_commits=100)
    """

    def __init__(self, db: GraphDatabase, repo_path: Optional[Path] = None):
        """Initialize git populator.

        Args:
            db: Graph database instance
            repo_path: Path to git repository (defaults to current directory)
        """
        self.db = db
        self.repo_path = repo_path or Path.cwd()
        self.git = GitServer(allowed_repos=[str(self.repo_path)])
        self._processed_commits: Set[str] = set()
        self._processed_files: Set[str] = set()

    def populate(
        self,
        max_commits: int = 100,
        since: Optional[str] = None,
        incremental: bool = True,
    ) -> Dict[str, int]:
        """Populate graph with git history.

        Args:
            max_commits: Maximum number of commits to process
            since: Only process commits since this date (e.g., "2025-01-01")
            incremental: If True, skip commits already in database

        Returns:
            Dictionary with counts: commits, files, relationships
        """
        commits = self.git.log(
            repo_path=str(self.repo_path),
            max_count=max_commits,
            since=since,
        )

        commits_added = 0
        files_added = 0
        relationships_added = 0

        for commit in commits:
            # Skip if already processed (incremental mode)
            if incremental and self._is_commit_in_db(commit.hash):
                continue

            # Insert commit node
            self._insert_commit(commit)
            commits_added += 1

            # Get file stats for this commit
            file_stats = self._get_file_stats(commit.hash)

            # Insert file nodes and CHANGES relationships
            for file_path in commit.files:
                if file_path not in self._processed_files:
                    file_info = self._get_file_info(file_path)
                    if file_info:
                        self._insert_file(file_path, file_info)
                        files_added += 1
                        self._processed_files.add(file_path)

                # Create CHANGES relationship with stats
                stats = file_stats.get(file_path, {})
                self._create_changes_relationship(
                    commit.hash,
                    file_path,
                    stats.get("insertions", 0),
                    stats.get("deletions", 0),
                    stats.get("status", "modified"),
                )
                relationships_added += 1

            self._processed_commits.add(commit.hash)

        return {
            "commits": commits_added,
            "files": files_added,
            "relationships": relationships_added,
        }

    def _is_commit_in_db(self, commit_hash: str) -> bool:
        """Check if commit is already in database."""
        conn = self.db.get_connection()
        result = conn.execute(f"""
            MATCH (c:Commit {{hash: '{commit_hash}'}})
            RETURN COUNT(c) AS count
        """)
        return result.get_next()[0] > 0 if result.has_next() else False

    def _insert_commit(self, commit: GitCommit) -> None:
        """Insert commit node into database."""
        conn = self.db.get_connection()

        # Parse timestamp
        # Git format: "2026-01-18 10:42:33 -0500"
        # Kuzu format: "2026-01-18T10:42:33" (no timezone)
        timestamp_str = commit.date.strip()

        # Remove timezone offset (everything after last space)
        if " " in timestamp_str:
            parts = timestamp_str.rsplit(" ", 1)
            if len(parts) == 2 and (parts[1].startswith("+") or parts[1].startswith("-")):
                timestamp_str = parts[0]

        # Replace first space with T for ISO format
        timestamp_str = timestamp_str.replace(" ", "T", 1)

        # Escape quotes and newlines in message for Cypher
        message = commit.message.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")

        # Get branch name (simplified - just current branch)
        try:
            branch_result = subprocess.run(
                ["git", "branch", "--contains", commit.hash],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=True,
            )
            branches = [
                b.strip().lstrip("* ")
                for b in branch_result.stdout.split("\n")
                if b.strip()
            ]
            branch = branches[0] if branches else "unknown"
        except subprocess.CalledProcessError:
            branch = "unknown"

        conn.execute(f"""
            CREATE (c:Commit {{
                hash: '{commit.hash}',
                short_hash: '{commit.short_hash}',
                message: '{message}',
                author: '{commit.author}',
                timestamp: timestamp('{timestamp_str}'),
                branch: '{branch}'
            }})
        """)

    def _insert_file(self, file_path: str, file_info: Dict[str, Any]) -> None:
        """Insert or update file node."""
        conn = self.db.get_connection()

        # Check if file exists
        result = conn.execute(f"""
            MATCH (f:File {{path: '{file_path}'}})
            RETURN COUNT(f) AS count
        """)
        exists = result.get_next()[0] > 0 if result.has_next() else False

        if not exists:
            # Create new file node
            timestamp_str = file_info.get("last_modified", datetime.now().isoformat())
            conn.execute(f"""
                CREATE (f:File {{
                    path: '{file_path}',
                    language: '{file_info.get("language", "unknown")}',
                    size: {file_info.get("size", 0)},
                    lines: {file_info.get("lines", 0)},
                    last_modified: timestamp('{timestamp_str}'),
                    file_exists: {str(file_info.get("exists", True)).lower()},
                    hash: '{file_info.get("hash", "")}'
                }})
            """)

    def _create_changes_relationship(
        self,
        commit_hash: str,
        file_path: str,
        insertions: int,
        deletions: int,
        status: str,
    ) -> None:
        """Create CHANGES relationship between commit and file."""
        conn = self.db.get_connection()

        conn.execute(f"""
            MATCH (c:Commit {{hash: '{commit_hash}'}})
            MATCH (f:File {{path: '{file_path}'}})
            CREATE (c)-[:CHANGES {{
                insertions: {insertions},
                deletions: {deletions},
                status: '{status}'
            }}]->(f)
        """)

    def _get_file_stats(self, commit_hash: str) -> Dict[str, Dict[str, Any]]:
        """Get file change statistics for a commit.

        Returns:
            Dictionary mapping file path to stats (insertions, deletions, status)
        """
        try:
            result = subprocess.run(
                ["git", "show", "--numstat", "--format=", commit_hash],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=True,
            )

            stats = {}
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split("\t")
                if len(parts) >= 3:
                    insertions = parts[0]
                    deletions = parts[1]
                    file_path = parts[2]

                    # Handle binary files (shows as "-")
                    if insertions == "-":
                        insertions = 0
                    if deletions == "-":
                        deletions = 0

                    stats[file_path] = {
                        "insertions": int(insertions) if insertions else 0,
                        "deletions": int(deletions) if deletions else 0,
                        "status": "modified",  # Could enhance this
                    }

            return stats
        except subprocess.CalledProcessError:
            return {}

    def _get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file metadata.

        Args:
            file_path: Relative file path

        Returns:
            Dictionary with file info or None if file doesn't exist
        """
        full_path = self.repo_path / file_path

        if not full_path.exists():
            return {
                "exists": False,
                "size": 0,
                "lines": 0,
                "language": "unknown",
                "hash": "",
                "last_modified": datetime.now().isoformat(),
            }

        try:
            stat = full_path.stat()
            size = stat.st_size
            last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

            # Count lines (only for text files)
            lines = 0
            try:
                if full_path.is_file():
                    lines = len(full_path.read_text().splitlines())
            except (UnicodeDecodeError, PermissionError):
                pass  # Binary file or no permission

            # Detect language from extension
            language = self._detect_language(file_path)

            # Get git hash for file
            try:
                hash_result = subprocess.run(
                    ["git", "hash-object", file_path],
                    cwd=str(self.repo_path),
                    capture_output=True,
                    text=True,
                    check=True,
                )
                file_hash = hash_result.stdout.strip()
            except subprocess.CalledProcessError:
                file_hash = ""

            return {
                "exists": True,
                "size": size,
                "lines": lines,
                "language": language,
                "hash": file_hash,
                "last_modified": last_modified,
            }
        except OSError:
            return None

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".sh": "shell",
            ".bash": "shell",
            ".md": "markdown",
            ".toml": "toml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
        }

        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "unknown")
