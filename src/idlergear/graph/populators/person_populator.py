"""Populates graph database with Person nodes from git commit authors."""

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Set
import subprocess
import re

from ..database import GraphDatabase


class PersonPopulator:
    """Populates graph database with Person nodes and relationships.

    Extracts contributor information from git history and creates:
    - Person nodes with commit statistics
    - AUTHORED relationships to commits
    - OWNS relationships to files (based on contribution %)

    Example:
        >>> from idlergear.graph import get_database
        >>> db = get_database()
        >>> populator = PersonPopulator(db)
        >>> populator.populate()
    """

    def __init__(self, db: GraphDatabase, repo_path: Optional[Path] = None):
        """Initialize person populator.

        Args:
            db: Graph database instance
            repo_path: Path to git repository (defaults to current directory)
        """
        self.db = db
        self.repo_path = repo_path or Path.cwd()
        self._processed_persons: Set[str] = set()

    def populate(
        self,
        incremental: bool = True,
        calculate_ownership: bool = True,
    ) -> Dict[str, int]:
        """Populate graph with person nodes and relationships.

        Args:
            incremental: If True, skip persons already in database
            calculate_ownership: If True, calculate file ownership percentages

        Returns:
            Dictionary with counts: persons, authored_rels, owns_rels
        """
        persons_added = 0
        authored_added = 0
        owns_added = 0

        conn = self.db.get_connection()

        # Get all commit authors from git log
        persons_data = self._get_persons_from_git()

        for email, person_info in persons_data.items():
            # Skip if already processed (incremental mode)
            if incremental and self._is_person_in_db(email):
                continue

            # Insert person node
            self._insert_person(person_info)
            persons_added += 1

            # Create AUTHORED relationships to commits
            authored_count = self._link_commits_to_person(email, person_info["commit_hashes"])
            authored_added += authored_count

        # Calculate file ownership if requested
        if calculate_ownership:
            owns_added = self._calculate_file_ownership()

        return {
            "persons": persons_added,
            "authored": authored_added,
            "owns": owns_added,
        }

    def _get_persons_from_git(self) -> Dict[str, Dict[str, Any]]:
        """Extract person information from git history."""
        persons = {}

        try:
            # Get all commits with author info
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.repo_path),
                    "log",
                    "--all",
                    "--format=%H|%ae|%an|%at",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|")
                if len(parts) != 4:
                    continue

                commit_hash, email, name, timestamp = parts

                # Parse timestamp
                try:
                    commit_time = datetime.fromtimestamp(int(timestamp))
                except (ValueError, OSError):
                    commit_time = datetime.now()

                # Initialize or update person info
                if email not in persons:
                    persons[email] = {
                        "email": email,
                        "name": name,
                        "username": self._extract_username(email),
                        "commit_count": 0,
                        "first_commit": commit_time,
                        "last_commit": commit_time,
                        "commit_hashes": [],
                    }

                # Update statistics
                person = persons[email]
                person["commit_count"] += 1
                person["commit_hashes"].append(commit_hash)

                # Update first/last commit times
                if commit_time < person["first_commit"]:
                    person["first_commit"] = commit_time
                if commit_time > person["last_commit"]:
                    person["last_commit"] = commit_time

        except subprocess.CalledProcessError:
            pass  # Not a git repository

        return persons

    def _extract_username(self, email: str) -> Optional[str]:
        """Extract username from email address."""
        if "@" in email:
            return email.split("@")[0]
        return None

    def _is_person_in_db(self, email: str) -> bool:
        """Check if person already exists in database."""
        conn = self.db.get_connection()
        try:
            result = conn.execute(
                "MATCH (p:Person {email: $email}) RETURN p",
                {"email": email}
            )
            return result.has_next()
        except Exception:
            return False

    def _insert_person(self, person_info: Dict[str, Any]) -> None:
        """Insert person node into database."""
        conn = self.db.get_connection()

        try:
            conn.execute("""
                CREATE (p:Person {
                    email: $email,
                    name: $name,
                    username: $username,
                    commit_count: $commit_count,
                    first_commit: $first_commit,
                    last_commit: $last_commit
                })
            """, {
                "email": person_info["email"],
                "name": person_info["name"],
                "username": person_info["username"],
                "commit_count": person_info["commit_count"],
                "first_commit": person_info["first_commit"],
                "last_commit": person_info["last_commit"],
            })
        except Exception as e:
            print(f"Error inserting person {person_info['email']}: {e}")

    def _link_commits_to_person(self, email: str, commit_hashes: list) -> int:
        """Create AUTHORED relationships between person and commits."""
        conn = self.db.get_connection()
        count = 0

        for commit_hash in commit_hashes:
            try:
                # Check if commit exists in database
                check_result = conn.execute(
                    "MATCH (c:Commit {hash: $hash}) RETURN c",
                    {"hash": commit_hash}
                )

                if not check_result.has_next():
                    continue

                # Create AUTHORED relationship
                conn.execute("""
                    MATCH (p:Person {email: $email})
                    MATCH (c:Commit {hash: $hash})
                    CREATE (p)-[:AUTHORED {commit_timestamp: c.timestamp}]->(c)
                """, {
                    "email": email,
                    "hash": commit_hash,
                })
                count += 1
            except Exception as e:
                print(f"Error linking commit {commit_hash} to {email}: {e}")

        return count

    def _calculate_file_ownership(self) -> int:
        """Calculate file ownership based on git blame data."""
        conn = self.db.get_connection()
        count = 0

        try:
            # Get all files from database
            result = conn.execute("MATCH (f:File) WHERE f.file_exists = true RETURN f.path")
            files = []
            while result.has_next():
                files.append(result.get_next()[0])

            for file_path in files:
                # Get blame data for file
                ownership = self._get_file_ownership(file_path)

                # Create OWNS relationships
                for email, data in ownership.items():
                    try:
                        conn.execute("""
                            MATCH (p:Person {email: $email})
                            MATCH (f:File {path: $path})
                            CREATE (p)-[:OWNS {
                                ownership_percent: $percent,
                                lines_contributed: $lines
                            }]->(f)
                        """, {
                            "email": email,
                            "path": file_path,
                            "percent": data["percent"],
                            "lines": data["lines"],
                        })
                        count += 1
                    except Exception as e:
                        print(f"Error creating OWNS relationship for {file_path}: {e}")

        except Exception as e:
            print(f"Error calculating file ownership: {e}")

        return count

    def _get_file_ownership(self, file_path: str) -> Dict[str, Dict[str, Any]]:
        """Get ownership data for a file using git blame."""
        ownership = {}

        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.repo_path),
                    "blame",
                    "--line-porcelain",
                    file_path,
                ],
                capture_output=True,
                text=True,
                check=False,  # File might not exist or be tracked
            )

            if result.returncode != 0:
                return ownership

            # Parse blame output
            current_email = None
            total_lines = 0

            for line in result.stdout.split("\n"):
                if line.startswith("author-mail"):
                    # Extract email from <email>
                    match = re.search(r"<(.+?)>", line)
                    if match:
                        current_email = match.group(1)
                        total_lines += 1

                        if current_email not in ownership:
                            ownership[current_email] = {"lines": 0, "percent": 0.0}

                        ownership[current_email]["lines"] += 1

            # Calculate percentages
            if total_lines > 0:
                for email in ownership:
                    ownership[email]["percent"] = (ownership[email]["lines"] / total_lines) * 100.0

        except Exception:
            pass

        return ownership
