"""Populates graph database with code symbols (functions, classes, methods)."""

import ast
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Set

from ..database import GraphDatabase
from ..parsers import TreeSitterParser

try:
    from ..vector import VectorCodeIndex
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VectorCodeIndex = None
    VECTOR_SEARCH_AVAILABLE = False


class CodePopulator:
    """Populates graph database with code symbols from source files.

    Extracts functions, classes, and methods from source files using tree-sitter
    for multi-language support (Python, JavaScript, TypeScript, Rust, Go, C/C++, Java).
    Falls back to Python AST for unsupported files.

    Creates Symbol nodes with CONTAINS relationships to File nodes.

    Example:
        >>> from idlergear.graph import get_database
        >>> db = get_database()
        >>> populator = CodePopulator(db)
        >>> populator.populate_directory("src/")  # Indexes all supported languages
    """

    def __init__(
        self,
        db: GraphDatabase,
        repo_path: Optional[Path] = None,
        vector_index: Optional[Any] = None,
        enable_vector_search: bool = True,
    ):
        """Initialize code populator.

        Args:
            db: Graph database instance
            repo_path: Path to repository root (defaults to current directory)
            vector_index: Optional VectorCodeIndex for semantic search
            enable_vector_search: If True and VectorCodeIndex available, enable semantic indexing
        """
        self.db = db
        self.repo_path = repo_path or Path.cwd()
        self._processed_files: Set[str] = set()
        self._parser = TreeSitterParser()  # Multi-language parser

        # Initialize vector search if enabled and available
        self.vector_index = vector_index
        if self.vector_index is None and enable_vector_search and VECTOR_SEARCH_AVAILABLE:
            try:
                index_path = self.repo_path / ".idlergear" / "code_index"
                self.vector_index = VectorCodeIndex(index_path=index_path)
            except Exception as e:
                import logging
                logging.warning(f"Failed to initialize vector search: {e}")
                self.vector_index = None

    def populate_directory(
        self,
        directory: str = "src",
        extensions: Optional[List[str]] = None,
        incremental: bool = True,
    ) -> Dict[str, int]:
        """Populate graph with symbols from a directory.

        Args:
            directory: Directory to scan (relative to repo_path)
            extensions: File extensions to process (default: all supported languages)
            incremental: If True, skip files that haven't changed

        Returns:
            Dictionary with counts: files, symbols, relationships
        """
        if extensions is None:
            # Default: all supported languages from TreeSitterParser
            extensions = list(TreeSitterParser.SUPPORTED_LANGUAGES.keys())

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
        """Populate symbols and imports from a single file."""
        # Try tree-sitter parser first (multi-language support)
        parse_result = self._parser.parse_file(full_path)

        if parse_result:
            # Tree-sitter succeeded - extract symbols, imports, comments
            symbols = self._convert_treesitter_symbols(parse_result["symbols"], rel_path)
            imports = parse_result.get("imports", [])
            comments = parse_result.get("comments", [])
            language = parse_result.get("language", "unknown")
        else:
            # Fall back to AST for Python files or unsupported languages
            try:
                content = full_path.read_text()
            except (UnicodeDecodeError, PermissionError):
                return None  # Skip binary or unreadable files

            # Parse AST (Python only)
            try:
                tree = ast.parse(content, filename=str(full_path))
            except SyntaxError:
                return None  # Skip files with syntax errors

            # Extract symbols and imports using AST
            symbols, imports = self._extract_symbols_and_imports(tree, rel_path)
            comments = []
            language = "python"

        # Ensure file node exists with detected language
        self._ensure_file_node(rel_path, full_path, language)

        # Insert symbols and create relationships
        symbols_added = 0
        relationships_added = 0
        vector_indexed_symbols = []  # Collect for batch vector indexing

        for symbol in symbols:
            # Create symbol ID: file_path:line_number:name
            symbol_id = f"{rel_path}:{symbol['line_start']}:{symbol['name']}"

            # Insert symbol
            if self._insert_symbol(symbol_id, symbol):
                symbols_added += 1

                # Create CONTAINS relationship
                if self._create_contains_relationship(rel_path, symbol_id):
                    relationships_added += 1

                # Collect for vector indexing
                if self.vector_index and "code" in symbol:
                    vector_indexed_symbols.append({
                        "symbol_id": symbol_id,
                        "name": symbol["name"],
                        "type": symbol["type"],
                        "code": symbol.get("code", symbol.get("docstring", "")),
                        "file_path": rel_path,
                        "line_start": symbol["line_start"],
                        "line_end": symbol["line_end"],
                    })

        # Batch index symbols in vector database
        if self.vector_index and vector_indexed_symbols:
            try:
                self.vector_index.index_symbols_batch(
                    vector_indexed_symbols, incremental=True
                )
            except Exception as e:
                import logging
                logging.warning(f"Failed to vector index {rel_path}: {e}")

        # Process imports and create IMPORTS relationships
        for import_info in imports:
            # Handle both tree-sitter format (text-based) and AST format (module-based)
            if "module" in import_info:
                # AST format
                resolved_path = self._resolve_import_path(
                    import_info["module"], rel_path
                )
                if resolved_path and self._create_imports_relationship(
                    rel_path, resolved_path, import_info["line"]
                ):
                    relationships_added += 1
            # For tree-sitter format, we would need to parse the import text
            # For now, skip tree-sitter imports (can be enhanced later)

        return {"symbols": symbols_added, "relationships": relationships_added}

    def _extract_symbols_and_imports(
        self, tree: ast.AST, file_path: str
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract functions, classes, methods, and imports from AST.

        Returns:
            Tuple of (symbols, imports)
        """
        symbols = []
        imports = []

        # Only iterate through module body to avoid double-counting
        # ast.walk() would find methods both in class body and as standalone nodes
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                # Extract top-level function
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

            elif isinstance(node, ast.Import):
                # Extract import statements: import foo, bar
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "names": [],
                        "line": node.lineno,
                        "type": "import",
                    })

            elif isinstance(node, ast.ImportFrom):
                # Extract from imports: from foo import bar, baz
                module_name = node.module or ""
                names = [alias.name for alias in node.names]
                imports.append({
                    "module": module_name,
                    "names": names,
                    "line": node.lineno,
                    "type": "from_import",
                    "level": node.level,  # For relative imports
                })

        return symbols, imports

    def _convert_treesitter_symbols(
        self, treesitter_symbols: List[Dict[str, Any]], file_path: str
    ) -> List[Dict[str, Any]]:
        """Convert tree-sitter symbol format to internal format.

        Args:
            treesitter_symbols: Symbols from TreeSitterParser
            file_path: Relative file path

        Returns:
            List of symbols in internal format with docstring, code, and file_path
        """
        converted = []
        for symbol in treesitter_symbols:
            # Extract docstring from code if available (basic implementation)
            # For now, leave empty - full docstring extraction would require
            # parsing the code field or using tree-sitter queries for docstrings
            docstring = ""

            converted.append({
                "name": symbol["name"],
                "type": symbol["type"],
                "line_start": symbol["line_start"],
                "line_end": symbol["line_end"],
                "docstring": docstring,
                "file_path": file_path,
                "code": symbol.get("code", ""),  # Include code for vector indexing
            })

        return converted

    def _ensure_file_node(self, rel_path: str, full_path: Path, language: str = "python") -> None:
        """Ensure file node exists in database.

        Args:
            rel_path: Relative path to file
            full_path: Full path to file
            language: Detected language (from tree-sitter or fallback)
        """
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

    def _escape_cypher_string(self, value: str) -> str:
        """Escape string value for Cypher query.

        Args:
            value: String to escape

        Returns:
            Escaped string safe for Cypher queries
        """
        return value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")

    def _insert_symbol(self, symbol_id: str, symbol: Dict[str, Any]) -> bool:
        """Insert symbol node into database.

        Returns:
            True if symbol was inserted, False if it already existed
        """
        conn = self.db.get_connection()

        # Escape all string values for Cypher
        safe_id = self._escape_cypher_string(symbol_id)
        safe_name = self._escape_cypher_string(symbol["name"])
        safe_type = self._escape_cypher_string(symbol["type"])
        safe_file_path = self._escape_cypher_string(symbol["file_path"])
        safe_docstring = self._escape_cypher_string(symbol["docstring"])

        # Check if exists
        result = conn.execute(f"""
            MATCH (s:Symbol {{id: '{safe_id}'}})
            RETURN COUNT(s) AS count
        """)

        exists = result.get_next()[0] > 0 if result.has_next() else False

        if exists:
            return False  # Already exists

        # Insert symbol
        conn.execute(f"""
            CREATE (s:Symbol {{
                id: '{safe_id}',
                name: '{safe_name}',
                type: '{safe_type}',
                file_path: '{safe_file_path}',
                line_start: {symbol["line_start"]},
                line_end: {symbol["line_end"]},
                docstring: '{safe_docstring}'
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

    def _resolve_import_path(
        self, module_name: str, from_file: str
    ) -> Optional[str]:
        """Resolve import module name to file path.

        Args:
            module_name: Module name (e.g., 'api_old', 'utils.helper')
            from_file: Path of file containing the import

        Returns:
            Resolved file path or None if can't resolve
        """
        if not module_name:
            return None

        # Get directory of importing file
        from_path = Path(from_file).parent

        # Handle relative imports (e.g., from . import foo, from ..utils import bar)
        # For now, we'll focus on simple module-based imports
        # Relative imports would need level information from ast.ImportFrom

        # Try to find matching .py file
        # Strategy: Look for module_name.py in common locations

        # 1. Try as direct path relative to repo root
        candidates = [
            # Direct module name as file
            f"{module_name}.py",
            f"{module_name}/__init__.py",
            # In same directory as importing file
            str(from_path / f"{module_name}.py"),
            str(from_path / module_name / "__init__.py"),
            # In src/ directory
            f"src/{module_name}.py",
            f"src/{module_name}/__init__.py",
        ]

        # Handle dotted imports (e.g., utils.helper -> utils/helper.py)
        if "." in module_name:
            module_path = module_name.replace(".", "/")
            candidates.extend([
                f"{module_path}.py",
                f"{module_path}/__init__.py",
                f"src/{module_path}.py",
                f"src/{module_path}/__init__.py",
            ])

        # Check which candidate exists
        for candidate in candidates:
            full_path = self.repo_path / candidate
            if full_path.exists() and full_path.is_file():
                # Return relative path
                try:
                    return str(Path(candidate))
                except ValueError:
                    continue

        return None

    def _create_imports_relationship(
        self, from_file: str, to_file: str, line: int
    ) -> bool:
        """Create IMPORTS relationship between two files.

        Args:
            from_file: Path of file doing the import
            to_file: Path of file being imported
            line: Line number of import statement

        Returns:
            True if relationship was created, False if it already existed
        """
        conn = self.db.get_connection()

        # Ensure both file nodes exist
        for file_path in [from_file, to_file]:
            result = conn.execute(f"""
                MATCH (f:File {{path: '{file_path}'}})
                RETURN COUNT(f) AS count
            """)
            exists = result.get_next()[0] > 0 if result.has_next() else False

            if not exists:
                # Create minimal file node if it doesn't exist
                conn.execute(f"""
                    CREATE (f:File {{
                        path: '{file_path}',
                        file_exists: false
                    }})
                """)

        # Check if relationship already exists
        result = conn.execute(f"""
            MATCH (f1:File {{path: '{from_file}'}})-[r:IMPORTS]->(f2:File {{path: '{to_file}'}})
            RETURN COUNT(r) AS count
        """)

        exists = result.get_next()[0] > 0 if result.has_next() else False

        if exists:
            return False

        # Create IMPORTS relationship
        conn.execute(f"""
            MATCH (f1:File {{path: '{from_file}'}})
            MATCH (f2:File {{path: '{to_file}'}})
            CREATE (f1)-[:IMPORTS {{line: {line}, import_type: 'python'}}]->(f2)
        """)

        return True
