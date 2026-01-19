"""Populates graph database with code symbols (functions, classes, methods)."""

import ast
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Set

from ..database import GraphDatabase


class CodePopulator:
    """Populates graph database with code symbols from Python files.

    Extracts functions, classes, and methods from Python source files
    and creates Symbol nodes with CONTAINS relationships to File nodes.

    Example:
        >>> from idlergear.graph import get_database
        >>> db = get_database()
        >>> populator = CodePopulator(db)
        >>> populator.populate_directory("src/")
    """

    def __init__(self, db: GraphDatabase, repo_path: Optional[Path] = None):
        """Initialize code populator.

        Args:
            db: Graph database instance
            repo_path: Path to repository root (defaults to current directory)
        """
        self.db = db
        self.repo_path = repo_path or Path.cwd()
        self._processed_files: Set[str] = set()

    def populate_directory(
        self,
        directory: str = "src",
        extensions: Optional[List[str]] = None,
        incremental: bool = True,
    ) -> Dict[str, int]:
        """Populate graph with symbols from a directory.

        Args:
            directory: Directory to scan (relative to repo_path)
            extensions: File extensions to process (default: [".py"])
            incremental: If True, skip files that haven't changed

        Returns:
            Dictionary with counts: files, symbols, relationships
        """
        if extensions is None:
            extensions = [".py"]

        scan_path = self.repo_path / directory
        if not scan_path.exists():
            return {"files": 0, "symbols": 0, "relationships": 0}

        files_processed = 0
        symbols_added = 0
        relationships_added = 0

        # Find all Python files
        for ext in extensions:
            for file_path in scan_path.rglob(f"*{ext}"):
                rel_path = str(file_path.relative_to(self.repo_path))

                # Skip if already processed and incremental mode
                if incremental and self._should_skip_file(rel_path, file_path):
                    continue

                # Parse and insert symbols
                result = self._populate_file(rel_path, file_path)
                if result:
                    files_processed += 1
                    symbols_added += result["symbols"]
                    relationships_added += result["relationships"]
                    self._processed_files.add(rel_path)

        return {
            "files": files_processed,
            "symbols": symbols_added,
            "relationships": relationships_added,
        }

    def populate_file(self, file_path: str) -> Dict[str, int]:
        """Populate graph with symbols from a single file.

        Args:
            file_path: Relative path to Python file

        Returns:
            Dictionary with counts: symbols, relationships
        """
        full_path = self.repo_path / file_path
        if not full_path.exists():
            return {"symbols": 0, "relationships": 0}

        return self._populate_file(file_path, full_path) or {
            "symbols": 0,
            "relationships": 0,
        }

    def _should_skip_file(self, rel_path: str, full_path: Path) -> bool:
        """Check if file should be skipped in incremental mode."""
        # Get file hash from database
        conn = self.db.get_connection()
        result = conn.execute(f"""
            MATCH (f:File {{path: '{rel_path}'}})
            RETURN f.hash AS hash
        """)

        if not result.has_next():
            return False  # File not in DB, don't skip

        db_hash = result.get_next()[0]

        # Calculate current file hash
        try:
            content = full_path.read_bytes()
            current_hash = hashlib.sha1(content).hexdigest()[:8]
            return db_hash == current_hash  # Skip if hashes match
        except (OSError, UnicodeDecodeError):
            return False  # Can't read file, don't skip

    def _populate_file(
        self, rel_path: str, full_path: Path
    ) -> Optional[Dict[str, int]]:
        """Populate symbols from a single file."""
        try:
            content = full_path.read_text()
        except (UnicodeDecodeError, PermissionError):
            return None  # Skip binary or unreadable files

        # Parse AST
        try:
            tree = ast.parse(content, filename=str(full_path))
        except SyntaxError:
            return None  # Skip files with syntax errors

        # Extract symbols
        symbols = self._extract_symbols(tree, rel_path)

        # Ensure file node exists
        self._ensure_file_node(rel_path, full_path)

        # Insert symbols and create relationships
        symbols_added = 0
        relationships_added = 0

        for symbol in symbols:
            # Create symbol ID: file_path:line_number:name
            symbol_id = f"{rel_path}:{symbol['line_start']}:{symbol['name']}"

            # Insert symbol
            if self._insert_symbol(symbol_id, symbol):
                symbols_added += 1

                # Create CONTAINS relationship
                if self._create_contains_relationship(rel_path, symbol_id):
                    relationships_added += 1

        return {"symbols": symbols_added, "relationships": relationships_added}

    def _extract_symbols(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        """Extract functions, classes, and methods from AST."""
        symbols = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Extract function/method
                symbols.append({
                    "name": node.name,
                    "type": "function",
                    "line_start": node.lineno,
                    "line_end": node.end_lineno or node.lineno,
                    "docstring": ast.get_docstring(node) or "",
                    "file_path": file_path,
                })

            elif isinstance(node, ast.ClassDef):
                # Extract class
                symbols.append({
                    "name": node.name,
                    "type": "class",
                    "line_start": node.lineno,
                    "line_end": node.end_lineno or node.lineno,
                    "docstring": ast.get_docstring(node) or "",
                    "file_path": file_path,
                })

                # Extract methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        symbols.append({
                            "name": f"{node.name}.{item.name}",
                            "type": "method",
                            "line_start": item.lineno,
                            "line_end": item.end_lineno or item.lineno,
                            "docstring": ast.get_docstring(item) or "",
                            "file_path": file_path,
                        })

        return symbols

    def _ensure_file_node(self, rel_path: str, full_path: Path) -> None:
        """Ensure file node exists in database."""
        conn = self.db.get_connection()

        # Check if exists
        result = conn.execute(f"""
            MATCH (f:File {{path: '{rel_path}'}})
            RETURN COUNT(f) AS count
        """)

        exists = result.get_next()[0] > 0 if result.has_next() else False

        if not exists:
            # Create file node
            stat = full_path.stat()
            size = stat.st_size
            lines = len(full_path.read_text().splitlines())
            language = "python"  # We're only processing Python for now

            # Calculate file hash
            content = full_path.read_bytes()
            file_hash = hashlib.sha1(content).hexdigest()[:8]

            conn.execute(f"""
                CREATE (f:File {{
                    path: '{rel_path}',
                    language: '{language}',
                    size: {size},
                    lines: {lines},
                    last_modified: timestamp('1970-01-01T00:00:00'),
                    file_exists: true,
                    hash: '{file_hash}'
                }})
            """)

    def _insert_symbol(self, symbol_id: str, symbol: Dict[str, Any]) -> bool:
        """Insert symbol node into database.

        Returns:
            True if symbol was inserted, False if it already existed
        """
        conn = self.db.get_connection()

        # Check if exists
        result = conn.execute(f"""
            MATCH (s:Symbol {{id: '{symbol_id}'}})
            RETURN COUNT(s) AS count
        """)

        exists = result.get_next()[0] > 0 if result.has_next() else False

        if exists:
            return False  # Already exists

        # Escape quotes and special chars in docstring for Cypher
        docstring = symbol["docstring"].replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")

        # Insert symbol
        conn.execute(f"""
            CREATE (s:Symbol {{
                id: '{symbol_id}',
                name: '{symbol["name"]}',
                type: '{symbol["type"]}',
                file_path: '{symbol["file_path"]}',
                line_start: {symbol["line_start"]},
                line_end: {symbol["line_end"]},
                docstring: '{docstring}'
            }})
        """)

        return True

    def _create_contains_relationship(
        self, file_path: str, symbol_id: str
    ) -> bool:
        """Create CONTAINS relationship from File to Symbol.

        Returns:
            True if relationship was created, False if it already existed
        """
        conn = self.db.get_connection()

        # Check if relationship exists
        result = conn.execute(f"""
            MATCH (f:File {{path: '{file_path}'}})-[r:CONTAINS]->(s:Symbol {{id: '{symbol_id}'}})
            RETURN COUNT(r) AS count
        """)

        exists = result.get_next()[0] > 0 if result.has_next() else False

        if exists:
            return False

        # Create relationship
        conn.execute(f"""
            MATCH (f:File {{path: '{file_path}'}})
            MATCH (s:Symbol {{id: '{symbol_id}'}})
            CREATE (f)-[:CONTAINS]->(s)
        """)

        return True
