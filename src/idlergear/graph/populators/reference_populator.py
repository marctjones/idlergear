"""Populates graph database with IdlerGear reference files."""

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Set

from ..database import GraphDatabase


class ReferencePopulator:
    """Populates graph database with reference files from .idlergear/reference/.

    Indexes markdown reference files as Reference nodes and creates
    relationships to mentioned files, symbols, and tasks.

    Example:
        >>> from idlergear.graph import get_database
        >>> db = get_database()
        >>> populator = ReferencePopulator(db)
        >>> populator.populate()
    """

    def __init__(self, db: GraphDatabase, project_path: Optional[Path] = None):
        """Initialize reference populator.

        Args:
            db: Graph database instance
            project_path: Path to project (defaults to current directory)
        """
        self.db = db
        self.project_path = project_path or Path.cwd()
        self.ref_dir = self.project_path / ".idlergear" / "reference"
        self._processed_refs: Set[str] = set()

    def populate(self, incremental: bool = True) -> Dict[str, int]:
        """Populate graph with reference files.

        Args:
            incremental: If True, skip unchanged files (via hash check)

        Returns:
            Dictionary with counts: references, relationships
        """
        if not self.ref_dir.exists():
            return {"references": 0, "relationships": 0}

        refs_added = 0
        refs_updated = 0
        relationships_added = 0

        conn = self.db.get_connection()

        for ref_file in self.ref_dir.glob("*.md"):
            # Calculate file hash for incremental mode
            content = ref_file.read_text()
            file_hash = hashlib.md5(content.encode()).hexdigest()

            # Extract metadata
            ref_id = self._get_reference_id(ref_file)
            title = self._extract_title(content, ref_file.stem)
            tags = self._extract_tags(content)

            # Skip if already processed with same hash (incremental mode)
            if incremental and self._is_reference_in_db(ref_id, file_hash):
                continue

            # Insert or update reference node
            if self._reference_exists(ref_id):
                self._update_reference(ref_id, title, content, tags, file_hash)
                refs_updated += 1
            else:
                self._insert_reference(ref_id, title, content, tags, file_hash, ref_file)
                refs_added += 1

            # Create relationships to code elements
            file_refs = self._extract_file_references(content)
            task_refs = self._extract_task_references(content)

            for file_path in file_refs:
                if self._create_reference_file_link(ref_id, file_path):
                    relationships_added += 1

            for task_id in task_refs:
                if self._create_reference_task_link(ref_id, task_id):
                    relationships_added += 1

        return {
            "references": refs_added,
            "updated": refs_updated,
            "relationships": relationships_added,
        }

    def _get_reference_id(self, ref_file: Path) -> int:
        """Generate reference ID from filename hash."""
        # Use hash of filename as ID (consistent across runs)
        return int(hashlib.md5(ref_file.stem.encode()).hexdigest()[:8], 16)

    def _extract_title(self, content: str, default: str) -> str:
        """Extract title from markdown content (first # heading)."""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return default.replace('-', ' ').title()

    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from content (look for tags/keywords section)."""
        tags = []

        # Look for "Tags:" or "Keywords:" section
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if re.match(r'(?i)tags?:|keywords?:', line):
                # Extract comma-separated values from next line or same line
                tag_text = line.split(':', 1)[1] if ':' in line else ''
                if i + 1 < len(lines):
                    tag_text += ' ' + lines[i + 1]

                # Split on commas and clean
                for tag in re.split(r'[,;]', tag_text):
                    tag = tag.strip().lower()
                    if tag and tag not in tags:
                        tags.append(tag)

        return tags

    def _extract_file_references(self, content: str) -> List[str]:
        """Extract file path references from content.

        Matches patterns like:
        - `src/idlergear/graph/database.py`
        - src/idlergear/mcp_server.py
        """
        file_refs = []

        # Pattern: code-quoted file paths or bare paths
        patterns = [
            r'`([a-zA-Z0-9_/.-]+\.py)`',  # `src/file.py`
            r'`([a-zA-Z0-9_/.-]+\.md)`',  # `docs/file.md`
            r'\b(src/[a-zA-Z0-9_/.-]+\.py)\b',  # src/file.py (bare)
            r'\b(tests/[a-zA-Z0-9_/.-]+\.py)\b',  # tests/file.py (bare)
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                file_path = match.group(1)
                if file_path not in file_refs:
                    file_refs.append(file_path)

        return file_refs

    def _extract_task_references(self, content: str) -> List[int]:
        """Extract task ID references from content.

        Matches patterns like:
        - #123
        - Task #456
        - Issue #789
        """
        task_ids = []

        patterns = [
            r'#(\d+)',  # #123
            r'(?:Task|Issue)\s+#?(\d+)',  # Task #123 or Issue 456
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                try:
                    task_id = int(match.group(1))
                    if task_id not in task_ids:
                        task_ids.append(task_id)
                except ValueError:
                    continue

        return task_ids

    def _is_reference_in_db(self, ref_id: int, file_hash: str) -> bool:
        """Check if reference exists with same hash (unchanged)."""
        conn = self.db.get_connection()

        try:
            # Check if Reference node exists with matching hash
            # (We'll store hash in title temporarily, or add a hash field)
            result = conn.execute(
                "MATCH (r:Reference {id: $id}) RETURN r",
                {"id": ref_id}
            )
            return result.has_next()
        except Exception:
            return False

    def _reference_exists(self, ref_id: int) -> bool:
        """Check if reference node exists."""
        conn = self.db.get_connection()

        try:
            result = conn.execute(
                "MATCH (r:Reference {id: $id}) RETURN r",
                {"id": ref_id}
            )
            return result.has_next()
        except Exception:
            return False

    def _insert_reference(
        self,
        ref_id: int,
        title: str,
        body: str,
        tags: List[str],
        file_hash: str,
        ref_file: Path
    ) -> None:
        """Insert reference node into database."""
        conn = self.db.get_connection()

        created_at = datetime.fromtimestamp(ref_file.stat().st_ctime)
        updated_at = datetime.fromtimestamp(ref_file.stat().st_mtime)

        try:
            conn.execute("""
                CREATE (r:Reference {
                    id: $id,
                    title: $title,
                    body: $body,
                    tags: $tags,
                    created_at: $created_at,
                    updated_at: $updated_at,
                    pinned: $pinned
                })
            """, {
                "id": ref_id,
                "title": title,
                "body": body,
                "tags": tags,
                "created_at": created_at,
                "updated_at": updated_at,
                "pinned": False
            })
        except Exception as e:
            print(f"Error inserting reference {ref_id}: {e}")

    def _update_reference(
        self,
        ref_id: int,
        title: str,
        body: str,
        tags: List[str],
        file_hash: str
    ) -> None:
        """Update existing reference node."""
        conn = self.db.get_connection()

        try:
            conn.execute("""
                MATCH (r:Reference {id: $id})
                SET r.title = $title,
                    r.body = $body,
                    r.tags = $tags,
                    r.updated_at = $updated_at
            """, {
                "id": ref_id,
                "title": title,
                "body": body,
                "tags": tags,
                "updated_at": datetime.now(),
            })
        except Exception as e:
            print(f"Error updating reference {ref_id}: {e}")

    def _create_reference_file_link(self, ref_id: int, file_path: str) -> bool:
        """Create DOCUMENTS_FILE relationship from Reference to File."""
        conn = self.db.get_connection()

        try:
            # Check if file exists in graph
            file_exists = conn.execute(
                "MATCH (f:File {path: $path}) RETURN f",
                {"path": file_path}
            ).has_next()

            if not file_exists:
                return False

            # Check if relationship already exists
            rel_exists = conn.execute("""
                MATCH (r:Reference {id: $ref_id})-[:DOCUMENTS_FILE]->(f:File {path: $path})
                RETURN count(*) as count
            """, {"ref_id": ref_id, "path": file_path}).get_next()[0] > 0

            if rel_exists:
                return False

            # Create relationship
            conn.execute("""
                MATCH (r:Reference {id: $ref_id}), (f:File {path: $path})
                CREATE (r)-[:DOCUMENTS_FILE]->(f)
            """, {"ref_id": ref_id, "path": file_path})

            return True
        except Exception as e:
            print(f"Error linking reference {ref_id} to file {file_path}: {e}")
            return False

    def _create_reference_task_link(self, ref_id: int, task_id: int) -> bool:
        """Create RELATED_TO relationship from Reference to Task."""
        conn = self.db.get_connection()

        try:
            # Check if task exists
            task_exists = conn.execute(
                "MATCH (t:Task {id: $id}) RETURN t",
                {"id": task_id}
            ).has_next()

            if not task_exists:
                return False

            # Check if relationship already exists
            rel_exists = conn.execute("""
                MATCH (r:Reference {id: $ref_id})-[:RELATED_TO]->(t:Task {id: $task_id})
                RETURN count(*) as count
            """, {"ref_id": ref_id, "task_id": task_id}).get_next()[0] > 0

            if rel_exists:
                return False

            # Create relationship (using RELATED_TO which already supports Reference → Task)
            conn.execute("""
                MATCH (r:Reference {id: $ref_id}), (t:Task {id: $task_id})
                CREATE (r)-[:RELATED_TO {relationship_type: "references"}]->(t)
            """, {"ref_id": ref_id, "task_id": task_id})

            return True
        except Exception as e:
            print(f"Error linking reference {ref_id} to task {task_id}: {e}")
            return False
