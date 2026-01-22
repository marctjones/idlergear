"""Links commits to tasks by parsing commit messages."""

import re
from pathlib import Path
from typing import Optional, Dict, List, Set

from ..database import GraphDatabase


class CommitTaskLinker:
    """Links commits to tasks by parsing commit messages for task references.

    Parses commit messages for patterns like:
    - "Task: #123"
    - "Closes #456"
    - "Fix #789"
    - "#123" (standalone)

    Creates IMPLEMENTED_IN relationships between tasks and commits,
    and infers MODIFIES relationships from commit file changes.

    Example:
        >>> from idlergear.graph import get_database
        >>> db = get_database()
        >>> linker = CommitTaskLinker(db)
        >>> linker.link_all()
    """

    # Regex patterns for task references
    PATTERNS = [
        # "Task: #123" or "Task #123"
        r'[Tt]ask[:\s]+#?(\d+)',
        # "Closes #123", "Fixes #456", "Resolves #789"
        r'(?:[Cc]lose[sd]?|[Ff]ix(?:e[sd])?|[Rr]esolve[sd]?)\s+#(\d+)',
        # Standalone "#123" (but not in URLs or other contexts)
        r'(?:^|\s)#(\d+)(?:\s|,|$)',
    ]

    def __init__(self, db: GraphDatabase, project_path: Optional[Path] = None):
        """Initialize commit-task linker.

        Args:
            db: Graph database instance
            project_path: Path to project (defaults to current directory)
        """
        self.db = db
        self.project_path = project_path or Path.cwd()
        self._linked_pairs: Set[tuple[str, int]] = set()

    def link_all(self, incremental: bool = True) -> Dict[str, int]:
        """Link all commits to tasks by parsing commit messages.

        Args:
            incremental: If True, skip already-linked commit-task pairs

        Returns:
            Dictionary with counts: links_created, tasks_linked, commits_linked
        """
        conn = self.db.get_connection()

        # Get all commits from database
        try:
            commits_result = conn.execute("""
                MATCH (c:Commit)
                RETURN c.hash as hash, c.message as message
            """)
        except Exception as e:
            print(f"Error fetching commits: {e}")
            return {"links_created": 0, "tasks_linked": 0, "commits_linked": 0}

        links_created = 0
        commits_linked_set = set()
        tasks_linked_set = set()

        commits = commits_result.get_as_df()
        for _, row in commits.iterrows():
            commit_hash = row['hash']
            message = row['message']

            # Extract task IDs from commit message
            task_ids = self._extract_task_ids(message)

            for task_id in task_ids:
                # Skip if already linked (incremental mode)
                if incremental and self._is_linked(commit_hash, task_id):
                    continue

                # Create IMPLEMENTED_IN relationship
                if self._link_commit_to_task(commit_hash, task_id):
                    links_created += 1
                    commits_linked_set.add(commit_hash)
                    tasks_linked_set.add(task_id)

                # Infer MODIFIES relationships (Task → File via Commit)
                self._infer_task_file_relationships(task_id, commit_hash)

        return {
            "links_created": links_created,
            "tasks_linked": len(tasks_linked_set),
            "commits_linked": len(commits_linked_set),
        }

    def _extract_task_ids(self, message: str) -> List[int]:
        """Extract task IDs from commit message.

        Args:
            message: Commit message text

        Returns:
            List of task IDs found in message
        """
        if not message:
            return []

        task_ids = []
        for pattern in self.PATTERNS:
            matches = re.finditer(pattern, message)
            for match in matches:
                try:
                    task_id = int(match.group(1))
                    if task_id not in task_ids:
                        task_ids.append(task_id)
                except (ValueError, IndexError):
                    continue

        return task_ids

    def _is_linked(self, commit_hash: str, task_id: int) -> bool:
        """Check if commit is already linked to task."""
        conn = self.db.get_connection()

        try:
            result = conn.execute("""
                MATCH (t:Task {id: $task_id})-[:IMPLEMENTED_IN]->(c:Commit {hash: $hash})
                RETURN count(*) as count
            """, {"task_id": task_id, "hash": commit_hash})

            if result.has_next():
                count = result.get_next()[0]
                return count > 0
        except Exception:
            pass

        return False

    def _link_commit_to_task(self, commit_hash: str, task_id: int) -> bool:
        """Create IMPLEMENTED_IN relationship between task and commit.

        Args:
            commit_hash: Git commit hash
            task_id: Task ID

        Returns:
            True if link created successfully
        """
        conn = self.db.get_connection()

        try:
            # Check if both nodes exist
            task_exists = conn.execute(
                "MATCH (t:Task {id: $id}) RETURN t",
                {"id": task_id}
            ).has_next()

            commit_exists = conn.execute(
                "MATCH (c:Commit {hash: $hash}) RETURN c",
                {"hash": commit_hash}
            ).has_next()

            if not task_exists or not commit_exists:
                return False

            # Create relationship
            conn.execute("""
                MATCH (t:Task {id: $task_id}), (c:Commit {hash: $hash})
                CREATE (t)-[:IMPLEMENTED_IN]->(c)
            """, {"task_id": task_id, "hash": commit_hash})

            return True
        except Exception as e:
            print(f"Error linking task {task_id} to commit {commit_hash}: {e}")
            return False

    def _infer_task_file_relationships(self, task_id: int, commit_hash: str) -> None:
        """Infer MODIFIES relationships from Task to Files via Commit.

        If a task is implemented in a commit, and that commit changes files,
        create MODIFIES relationships from the task to those files.

        Args:
            task_id: Task ID
            commit_hash: Git commit hash
        """
        conn = self.db.get_connection()

        try:
            # Get files changed by this commit
            files_result = conn.execute("""
                MATCH (c:Commit {hash: $hash})-[r:CHANGES]->(f:File)
                RETURN f.path as path, r.status as status
            """, {"hash": commit_hash})

            files = files_result.get_as_df()
            for _, row in files.iterrows():
                file_path = row['path']
                change_type = row['status']

                # Check if MODIFIES relationship already exists
                exists = conn.execute("""
                    MATCH (t:Task {id: $task_id})-[:MODIFIES]->(f:File {path: $path})
                    RETURN count(*) as count
                """, {"task_id": task_id, "path": file_path}).get_next()[0] > 0

                if not exists:
                    # Create MODIFIES relationship
                    conn.execute("""
                        MATCH (t:Task {id: $task_id}), (f:File {path: $path})
                        CREATE (t)-[:MODIFIES {change_type: $change_type}]->(f)
                    """, {
                        "task_id": task_id,
                        "path": file_path,
                        "change_type": change_type or "modified"
                    })
        except Exception as e:
            print(f"Error inferring file relationships for task {task_id}: {e}")
