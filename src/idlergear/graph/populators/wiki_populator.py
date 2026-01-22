"""Populates graph database with GitHub wiki documentation."""

import hashlib
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Set

from ..database import GraphDatabase


class WikiPopulator:
    """Populates graph database with GitHub wiki as Documentation nodes.

    Clones or updates the GitHub wiki repository and indexes markdown files
    as Documentation nodes, creating relationships to code elements mentioned.

    Example:
        >>> from idlergear.graph import get_database
        >>> db = get_database()
        >>> populator = WikiPopulator(db)
        >>> populator.populate()
    """

    def __init__(
        self,
        db: GraphDatabase,
        wiki_url: Optional[str] = None,
        wiki_path: Optional[Path] = None,
    ):
        """Initialize wiki populator.

        Args:
            db: Graph database instance
            wiki_url: GitHub wiki repository URL (e.g., https://github.com/user/repo.wiki.git)
            wiki_path: Local path for wiki clone (defaults to /tmp/repo.wiki)
        """
        self.db = db
        self.wiki_url = wiki_url or "https://github.com/marctjones/idlergear.wiki.git"
        self.wiki_path = wiki_path or Path("/tmp/idlergear.wiki")
        self._processed_docs: Set[str] = set()

    def populate(self, incremental: bool = True) -> Dict[str, int]:
        """Populate graph with wiki documentation.

        Args:
            incremental: If True, skip unchanged files (via hash check)

        Returns:
            Dictionary with counts: documents, relationships
        """
        # Clone or update wiki repository
        if not self._sync_wiki():
            print("Failed to sync wiki repository")
            return {"documents": 0, "relationships": 0}

        docs_added = 0
        docs_updated = 0
        relationships_added = 0

        conn = self.db.get_connection()

        for md_file in self.wiki_path.glob("*.md"):
            # Skip hidden files and special pages
            if md_file.name.startswith(('.', '_')):
                continue

            content = md_file.read_text()
            file_hash = hashlib.md5(content.encode()).hexdigest()

            # Extract metadata
            doc_path = f"wiki/{md_file.name}"
            title = self._extract_title(content, md_file.stem)

            # Skip if already processed with same hash (incremental mode)
            if incremental and self._is_doc_in_db(doc_path, file_hash):
                continue

            # Insert or update documentation node
            if self._doc_exists(doc_path):
                self._update_doc(doc_path, title, content, file_hash, md_file)
                docs_updated += 1
            else:
                self._insert_doc(doc_path, title, content, file_hash, md_file)
                docs_added += 1

            # Create relationships to code elements
            file_refs = self._extract_file_references(content)
            symbol_refs = self._extract_symbol_references(content)
            task_refs = self._extract_task_references(content)

            for file_path in file_refs:
                if self._create_doc_file_link(doc_path, file_path):
                    relationships_added += 1

            for symbol_name in symbol_refs:
                if self._create_doc_symbol_links(doc_path, symbol_name):
                    relationships_added += 1

            for task_id in task_refs:
                if self._create_doc_task_link(doc_path, task_id):
                    relationships_added += 1

        return {
            "documents": docs_added,
            "updated": docs_updated,
            "relationships": relationships_added,
        }

    def _sync_wiki(self) -> bool:
        """Clone or pull wiki repository.

        Returns:
            True if successful
        """
        try:
            if self.wiki_path.exists() and (self.wiki_path / ".git").exists():
                # Update existing clone
                result = subprocess.run(
                    ["git", "-C", str(self.wiki_path), "pull"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return result.returncode == 0
            else:
                # Clone repository
                self.wiki_path.parent.mkdir(parents=True, exist_ok=True)
                result = subprocess.run(
                    ["git", "clone", self.wiki_url, str(self.wiki_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError) as e:
            print(f"Error syncing wiki: {e}")
            return False

    def _extract_title(self, content: str, default: str) -> str:
        """Extract title from markdown (first # heading)."""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return default.replace('-', ' ')

    def _extract_file_references(self, content: str) -> List[str]:
        """Extract file path references from wiki content.

        Matches patterns like:
        - `src/idlergear/graph/database.py`
        - [database.py](../src/idlergear/graph/database.py)
        """
        file_refs = []

        # Pattern 1: Code-quoted paths
        code_pattern = r'`([a-zA-Z0-9_/.-]+\.py)`'
        for match in re.finditer(code_pattern, content):
            file_path = match.group(1)
            if file_path not in file_refs:
                file_refs.append(file_path)

        # Pattern 2: Markdown links to code files
        link_pattern = r'\[([^\]]+)\]\(([^)]+\.py)\)'
        for match in re.finditer(link_pattern, content):
            file_path = match.group(2)
            # Remove ../ or ./ prefixes
            file_path = re.sub(r'^\.\./', '', file_path)
            file_path = re.sub(r'^\./','', file_path)
            if file_path not in file_refs:
                file_refs.append(file_path)

        # Pattern 3: Bare paths in text
        bare_pattern = r'\b((?:src|tests)/[a-zA-Z0-9_/.-]+\.py)\b'
        for match in re.finditer(bare_pattern, content):
            file_path = match.group(1)
            if file_path not in file_refs:
                file_refs.append(file_path)

        return file_refs

    def _extract_symbol_references(self, content: str) -> List[str]:
        """Extract symbol (class/function) references from wiki content.

        Matches patterns like:
        - `ProcessManager` (code-quoted identifiers)
        - GraphDatabase.get_connection()
        """
        symbol_refs = []

        # Pattern 1: Code-quoted identifiers (CamelCase or snake_case)
        code_pattern = r'`([A-Z][a-zA-Z0-9_]+|[a-z_][a-z0-9_]+)`'
        for match in re.finditer(code_pattern, content):
            symbol = match.group(1)
            # Filter out common words and short identifiers
            if len(symbol) > 3 and symbol not in ['True', 'False', 'None', 'self']:
                if symbol not in symbol_refs:
                    symbol_refs.append(symbol)

        return symbol_refs

    def _extract_task_references(self, content: str) -> List[int]:
        """Extract task ID references from wiki content."""
        task_ids = []

        patterns = [
            r'#(\d+)',  # #123
            r'(?:Task|Issue)\s+#?(\d+)',  # Task #123
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                try:
                    task_id = int(match.group(1))
                    if task_id not in task_ids:
                        task_ids.append(task_id)
                except ValueError:
                    continue

        return task_ids

    def _is_doc_in_db(self, doc_path: str, file_hash: str) -> bool:
        """Check if documentation exists with same hash (unchanged)."""
        conn = self.db.get_connection()

        try:
            result = conn.execute(
                "MATCH (d:Documentation {path: $path}) RETURN d",
                {"path": doc_path}
            )
            return result.has_next()
        except Exception:
            return False

    def _doc_exists(self, doc_path: str) -> bool:
        """Check if documentation node exists."""
        conn = self.db.get_connection()

        try:
            result = conn.execute(
                "MATCH (d:Documentation {path: $path}) RETURN d",
                {"path": doc_path}
            )
            return result.has_next()
        except Exception:
            return False

    def _insert_doc(
        self,
        doc_path: str,
        title: str,
        body: str,
        file_hash: str,
        md_file: Path
    ) -> None:
        """Insert documentation node into database."""
        conn = self.db.get_connection()

        created_at = datetime.fromtimestamp(md_file.stat().st_ctime)
        updated_at = datetime.fromtimestamp(md_file.stat().st_mtime)

        try:
            conn.execute("""
                CREATE (d:Documentation {
                    path: $path,
                    title: $title,
                    body: $body,
                    source: $source,
                    created_at: $created_at,
                    updated_at: $updated_at
                })
            """, {
                "path": doc_path,
                "title": title,
                "body": body,
                "source": "wiki",
                "created_at": created_at,
                "updated_at": updated_at,
            })
        except Exception as e:
            print(f"Error inserting documentation {doc_path}: {e}")

    def _update_doc(
        self,
        doc_path: str,
        title: str,
        body: str,
        file_hash: str,
        md_file: Path
    ) -> None:
        """Update existing documentation node."""
        conn = self.db.get_connection()

        updated_at = datetime.fromtimestamp(md_file.stat().st_mtime)

        try:
            conn.execute("""
                MATCH (d:Documentation {path: $path})
                SET d.title = $title,
                    d.body = $body,
                    d.updated_at = $updated_at
            """, {
                "path": doc_path,
                "title": title,
                "body": body,
                "updated_at": updated_at,
            })
        except Exception as e:
            print(f"Error updating documentation {doc_path}: {e}")

    def _create_doc_file_link(self, doc_path: str, file_path: str) -> bool:
        """Create DOC_DOCUMENTS_FILE relationship."""
        conn = self.db.get_connection()

        try:
            # Check if file exists
            file_exists = conn.execute(
                "MATCH (f:File {path: $path}) RETURN f",
                {"path": file_path}
            ).has_next()

            if not file_exists:
                return False

            # Check if relationship exists
            rel_exists = conn.execute("""
                MATCH (d:Documentation {path: $doc_path})-[:DOC_DOCUMENTS_FILE]->(f:File {path: $file_path})
                RETURN count(*) as count
            """, {"doc_path": doc_path, "file_path": file_path}).get_next()[0] > 0

            if rel_exists:
                return False

            # Create relationship
            conn.execute("""
                MATCH (d:Documentation {path: $doc_path}), (f:File {path: $file_path})
                CREATE (d)-[:DOC_DOCUMENTS_FILE]->(f)
            """, {"doc_path": doc_path, "file_path": file_path})

            return True
        except Exception as e:
            print(f"Error linking doc {doc_path} to file {file_path}: {e}")
            return False

    def _create_doc_symbol_links(self, doc_path: str, symbol_name: str) -> int:
        """Create DOC_DOCUMENTS_SYMBOL relationships for all symbols matching name.

        Returns:
            Number of relationships created
        """
        conn = self.db.get_connection()
        links_created = 0

        try:
            # Find all symbols matching this name
            symbols_result = conn.execute("""
                MATCH (s:Symbol)
                WHERE s.name = $name OR s.name CONTAINS $name
                RETURN s.id as id
            """, {"name": symbol_name})

            symbols = symbols_result.get_as_df()
            for _, row in symbols.iterrows():
                symbol_id = row['id']

                # Check if relationship exists
                rel_exists = conn.execute("""
                    MATCH (d:Documentation {path: $doc_path})-[:DOC_DOCUMENTS_SYMBOL]->(s:Symbol {id: $symbol_id})
                    RETURN count(*) as count
                """, {"doc_path": doc_path, "symbol_id": symbol_id}).get_next()[0] > 0

                if not rel_exists:
                    # Create relationship
                    conn.execute("""
                        MATCH (d:Documentation {path: $doc_path}), (s:Symbol {id: $symbol_id})
                        CREATE (d)-[:DOC_DOCUMENTS_SYMBOL]->(s)
                    """, {"doc_path": doc_path, "symbol_id": symbol_id})
                    links_created += 1

        except Exception as e:
            print(f"Error linking doc {doc_path} to symbol {symbol_name}: {e}")

        return links_created

    def _create_doc_task_link(self, doc_path: str, task_id: int) -> bool:
        """Create DOC_REFERENCES_TASK relationship."""
        conn = self.db.get_connection()

        try:
            # Check if task exists
            task_exists = conn.execute(
                "MATCH (t:Task {id: $id}) RETURN t",
                {"id": task_id}
            ).has_next()

            if not task_exists:
                return False

            # Check if relationship exists
            rel_exists = conn.execute("""
                MATCH (d:Documentation {path: $doc_path})-[:DOC_REFERENCES_TASK]->(t:Task {id: $task_id})
                RETURN count(*) as count
            """, {"doc_path": doc_path, "task_id": task_id}).get_next()[0] > 0

            if rel_exists:
                return False

            # Create relationship
            conn.execute("""
                MATCH (d:Documentation {path: $doc_path}), (t:Task {id: $task_id})
                CREATE (d)-[:DOC_REFERENCES_TASK]->(t)
            """, {"doc_path": doc_path, "task_id": task_id})

            return True
        except Exception as e:
            print(f"Error linking doc {doc_path} to task {task_id}: {e}")
            return False
