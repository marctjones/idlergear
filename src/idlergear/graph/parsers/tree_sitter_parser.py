"""Multi-language code parser using tree-sitter.

Supports Python, JavaScript, TypeScript, Rust, Go, C/C++, Java, and more.
Provides unified API for extracting code symbols (functions, classes, methods)
with exact source positions and preserves comments.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List

from tree_sitter_languages import get_parser, get_language


class TreeSitterParser:
    """Multi-language parser using tree-sitter.

    Example:
        >>> parser = TreeSitterParser()
        >>> result = parser.parse_file(Path("src/main.py"))
        >>> print(f"Found {len(result['symbols'])} symbols")
        >>> for symbol in result['symbols']:
        ...     print(f"{symbol['type']} {symbol['name']} at line {symbol['line_start']}")
    """

    # Map file extensions to tree-sitter language names
    SUPPORTED_LANGUAGES = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".rs": "rust",
        ".go": "go",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
        ".java": "java",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "c_sharp",
    }

    # Tree-sitter queries for each language to extract symbols
    # Format: (node_type, name_field, symbol_type)
    SYMBOL_QUERIES = {
        "python": """
            (function_definition
                name: (identifier) @function.name) @function.def
            (class_definition
                name: (identifier) @class.name) @class.def
        """,
        "javascript": """
            (function_declaration
                name: (identifier) @function.name) @function.def
            (class_declaration
                name: (identifier) @class.name) @class.def
            (method_definition
                name: (property_identifier) @method.name) @method.def
        """,
        "typescript": """
            (function_declaration
                name: (identifier) @function.name) @function.def
            (class_declaration
                name: (type_identifier) @class.name) @class.def
            (method_definition
                name: (property_identifier) @method.name) @method.def
        """,
        "rust": """
            (function_item
                name: (identifier) @function.name) @function.def
            (struct_item
                name: (type_identifier) @class.name) @class.def
            (impl_item
                type: (type_identifier) @class.name) @impl.def
        """,
        "go": """
            (function_declaration
                name: (identifier) @function.name) @function.def
            (type_declaration
                (type_spec
                    name: (type_identifier) @class.name)) @class.def
        """,
    }

    def __init__(self):
        """Initialize parser with language caches."""
        self._parsers: Dict[str, Any] = {}  # Cached parsers by language
        self._languages: Dict[str, Any] = {}  # Cached language objects
        self._queries: Dict[str, Any] = {}  # Cached queries by language

    def parse_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a source file and extract symbols.

        Args:
            file_path: Path to source file

        Returns:
            Dictionary with:
                - language: Detected language (e.g., "python", "javascript")
                - symbols: List of extracted symbols (functions, classes, methods)
                - imports: List of import statements (if detected)
                - comments: List of comments with positions (if detected)
            Returns None if file is unsupported or parsing fails.
        """
        # Detect language from file extension
        extension = file_path.suffix.lower()
        language = self.SUPPORTED_LANGUAGES.get(extension)

        if not language:
            return None  # Unsupported file type

        # Read file content
        try:
            content = file_path.read_bytes()
        except (OSError, PermissionError):
            return None

        # Get or create parser for this language
        parser = self._get_parser(language)
        if not parser:
            return None

        # Parse the code
        try:
            tree = parser.parse(content)
        except Exception:
            return None  # Parsing failed

        # Extract symbols using language-specific queries
        symbols = self._extract_symbols(tree.root_node, language, content)

        # Extract imports (basic implementation)
        imports = self._extract_imports(tree.root_node, language, content)

        # Extract comments (basic implementation)
        comments = self._extract_comments(tree.root_node, content)

        return {
            "language": language,
            "symbols": symbols,
            "imports": imports,
            "comments": comments,
        }

    def _get_parser(self, language: str) -> Optional[Any]:
        """Get or create cached parser for language."""
        if language in self._parsers:
            return self._parsers[language]

        try:
            parser = get_parser(language)
            self._parsers[language] = parser
            return parser
        except Exception:
            return None

    def _get_language(self, language: str) -> Optional[Any]:
        """Get or create cached language object."""
        if language in self._languages:
            return self._languages[language]

        try:
            lang = get_language(language)
            self._languages[language] = lang
            return lang
        except Exception:
            return None

    def _get_query(self, language: str) -> Optional[Any]:
        """Get or create cached query for language."""
        if language in self._queries:
            return self._queries[language]

        query_string = self.SYMBOL_QUERIES.get(language)
        if not query_string:
            return None

        lang = self._get_language(language)
        if not lang:
            return None

        try:
            query = lang.query(query_string)
            self._queries[language] = query
            return query
        except Exception:
            return None

    def _extract_symbols(
        self, root_node: Any, language: str, content: bytes
    ) -> List[Dict[str, Any]]:
        """Extract functions, classes, and methods from AST.

        Args:
            root_node: Tree-sitter root node
            language: Language name
            content: Original file content (for extracting text)

        Returns:
            List of symbol dictionaries with name, type, line positions
        """
        query = self._get_query(language)
        if not query:
            return []

        symbols = []
        captures = query.captures(root_node)

        # Group captures by definition node
        # Captures come in pairs: (def_node, "X.def") and (name_node, "X.name")
        defs = {}  # def_node -> (def_type, name_text)

        for node, capture_name in captures:
            if capture_name.endswith(".def"):
                # This is a definition node
                def_type = capture_name.split(".")[0]  # function, class, method, impl
                defs[id(node)] = (def_type, node)
            elif capture_name.endswith(".name"):
                # This is a name node - find its parent definition
                parent = node.parent
                while parent:
                    if id(parent) in defs:
                        def_type, def_node = defs[id(parent)]
                        name_text = content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

                        # For Rust impl blocks, skip (we want the functions inside)
                        if def_type == "impl":
                            break

                        symbols.append({
                            "name": name_text,
                            "type": def_type,  # function, class, method
                            "line_start": def_node.start_point[0] + 1,  # 0-indexed to 1-indexed
                            "line_end": def_node.end_point[0] + 1,
                            "code": content[def_node.start_byte:def_node.end_byte].decode("utf-8", errors="replace"),
                        })
                        break
                    parent = parent.parent

        return symbols

    def _extract_imports(
        self, root_node: Any, language: str, content: bytes
    ) -> List[Dict[str, Any]]:
        """Extract import statements from AST.

        Args:
            root_node: Tree-sitter root node
            language: Language name
            content: Original file content

        Returns:
            List of import dictionaries with module, line, and text
        """
        imports = []

        # Simple implementation: Find import-related nodes by type
        # This can be enhanced with language-specific queries
        import_types = {
            "python": ["import_statement", "import_from_statement"],
            "javascript": ["import_statement"],
            "typescript": ["import_statement"],
            "go": ["import_declaration"],
            "rust": ["use_declaration"],
        }

        types_to_find = import_types.get(language, [])

        def visit_node(node):
            if node.type in types_to_find:
                imports.append({
                    "text": content[node.start_byte:node.end_byte].decode("utf-8", errors="replace"),
                    "line": node.start_point[0] + 1,
                })
            for child in node.children:
                visit_node(child)

        visit_node(root_node)
        return imports

    def _extract_comments(
        self, root_node: Any, content: bytes
    ) -> List[Dict[str, Any]]:
        """Extract comments from AST.

        Args:
            root_node: Tree-sitter root node
            content: Original file content

        Returns:
            List of comment dictionaries with text and line position
        """
        comments = []

        def visit_node(node):
            if "comment" in node.type:
                comments.append({
                    "text": content[node.start_byte:node.end_byte].decode("utf-8", errors="replace"),
                    "line": node.start_point[0] + 1,
                })
            for child in node.children:
                visit_node(child)

        visit_node(root_node)
        return comments
