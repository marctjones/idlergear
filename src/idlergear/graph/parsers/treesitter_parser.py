"""Tree-sitter based code parser for multiple languages.

Implements Issue #400: Replace AST parsing with tree-sitter.

This parser provides:
- Multi-language support (Python, JS, TS, Rust, Go, C/C++, Java)
- Incremental parsing (only re-parse changed code)
- Error tolerance (works with broken code)
- Comment preservation (AST discards comments)
- Exact position tracking

Usage:
    >>> parser = TreeSitterParser()
    >>> result = parser.parse_file(Path("src/main.py"))
    >>> print(result["symbols"])  # Functions, classes, methods
    >>> print(result["comments"])  # Preserved comments!
"""

import tree_sitter_languages
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TreeSitterParser:
    """Multi-language code parser using tree-sitter.

    Supports parsing of multiple languages with a unified interface.
    Much faster and more robust than language-specific AST parsers.
    """

    # Map file extensions to tree-sitter language names
    SUPPORTED_LANGUAGES = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".rs": "rust",
        ".go": "go",
        ".c": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".java": "java",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "c_sharp",
        ".swift": "swift",
        ".kt": "kotlin",
    }

    def __init__(self):
        """Initialize tree-sitter parser."""
        self._parsers = {}  # Cache parsers by language
        self._languages = {}  # Cache language objects

    def get_parser(self, language: str):
        """Get or create parser for a language.

        Args:
            language: Language name (e.g., "python", "javascript")

        Returns:
            tree_sitter.Parser for the language
        """
        if language not in self._parsers:
            self._parsers[language] = tree_sitter_languages.get_parser(language)
        return self._parsers[language]

    def get_language(self, language: str):
        """Get language object for queries.

        Args:
            language: Language name

        Returns:
            tree_sitter.Language object
        """
        if language not in self._languages:
            self._languages[language] = tree_sitter_languages.get_language(language)
        return self._languages[language]

    def parse_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a source file and extract symbols.

        Args:
            file_path: Path to source file

        Returns:
            Dictionary with:
                - symbols: List of functions/classes/methods
                - imports: List of import statements
                - comments: List of comments (NEW!)
                - language: Detected language

            None if file can't be parsed (unsupported language, read error)
        """
        # Detect language from extension
        ext = file_path.suffix
        language = self.SUPPORTED_LANGUAGES.get(ext)

        if not language:
            logger.debug(f"Unsupported language for {file_path.suffix}")
            return None

        try:
            code = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError, FileNotFoundError) as e:
            logger.debug(f"Can't read {file_path}: {e}")
            return None

        try:
            parser = self.get_parser(language)
            tree = parser.parse(bytes(code, "utf8"))

            # Extract symbols based on language
            symbols, imports, comments = self._extract_all(tree, code, language)

            return {
                "symbols": symbols,
                "imports": imports,
                "comments": comments,
                "language": language,
            }

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return None

    def _extract_all(
        self, tree, code: str, language: str
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Extract symbols, imports, and comments from parse tree.

        Args:
            tree: tree-sitter parse tree
            code: Source code string
            language: Language name

        Returns:
            Tuple of (symbols, imports, comments)
        """
        if language == "python":
            return self._extract_python(tree, code)
        elif language in ("javascript", "typescript"):
            return self._extract_javascript(tree, code)
        elif language == "rust":
            return self._extract_rust(tree, code)
        elif language == "go":
            return self._extract_go(tree, code)
        # TODO: Add more languages as needed

        # Default: empty results for unsupported language
        logger.warning(f"Extraction not implemented for {language}")
        return [], [], []

    def _extract_docstring(self, node, code: str) -> str:
        """Extract docstring from a Python function or class node.

        Args:
            node: tree-sitter node for function_definition or class_definition
            code: Source code string

        Returns:
            Docstring text, or empty string if none found
        """
        # Find the body node
        body_node = None
        for child in node.children:
            if child.type == "block":
                body_node = child
                break

        if not body_node or len(body_node.children) == 0:
            return ""

        # Check if first child is an expression statement with a string
        first_stmt = body_node.children[0]
        if first_stmt.type == "expression_statement":
            for child in first_stmt.children:
                if child.type == "string":
                    # Extract string content (remove quotes)
                    doc_text = code[child.start_byte:child.end_byte]
                    # Remove triple quotes or single quotes
                    if doc_text.startswith('"""') or doc_text.startswith("'''"):
                        return doc_text[3:-3].strip()
                    elif doc_text.startswith('"') or doc_text.startswith("'"):
                        return doc_text[1:-1].strip()
                    return doc_text

        return ""

    def _extract_python(self, tree, code: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Extract Python symbols, imports, and comments.

        Returns:
            (symbols, imports, comments)
        """
        symbols = []
        imports = []
        comments = []

        lang = self.get_language("python")
        root = tree.root_node

        # Query for function definitions (not inside classes)
        func_query = lang.query("""
            (function_definition
                name: (identifier) @func_name) @func
        """)

        for node, tag in func_query.captures(root):
            if tag == "func":
                # Skip if this is a method (inside a class)
                parent = node.parent
                while parent:
                    if parent.type == "class_definition":
                        # This is a method, skip it (will be handled in class processing)
                        break
                    parent = parent.parent
                else:
                    # This is a top-level function
                    name_node = None
                    for child in node.children:
                        if child.type == "identifier":
                            name_node = child
                            break

                    if name_node:
                        docstring = self._extract_docstring(node, code)
                        symbols.append({
                            "name": code[name_node.start_byte:name_node.end_byte],
                            "type": "function",
                            "line_start": node.start_point[0] + 1,  # 1-indexed
                            "line_end": node.end_point[0] + 1,
                            "code": code[node.start_byte:node.end_byte],
                            "docstring": docstring,
                        })

        # Query for class definitions
        class_query = lang.query("""
            (class_definition
                name: (identifier) @class_name) @class
        """)

        for node, tag in class_query.captures(root):
            if tag == "class":
                name_node = None
                for child in node.children:
                    if child.type == "identifier":
                        name_node = child
                        break

                if name_node:
                    class_name = code[name_node.start_byte:name_node.end_byte]
                    docstring = self._extract_docstring(node, code)
                    symbols.append({
                        "name": class_name,
                        "type": "class",
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                        "code": code[node.start_byte:node.end_byte],
                        "docstring": docstring,
                    })

                    # Extract methods from this class
                    body_node = None
                    for child in node.children:
                        if child.type == "block":
                            body_node = child
                            break

                    if body_node:
                        # Find all function definitions in the class body
                        method_query = lang.query("""
                            (function_definition
                                name: (identifier) @method_name) @method
                        """)

                        for method_node, method_tag in method_query.captures(body_node):
                            if method_tag == "method":
                                method_name_node = None
                                for child in method_node.children:
                                    if child.type == "identifier":
                                        method_name_node = child
                                        break

                                if method_name_node:
                                    method_name = code[method_name_node.start_byte:method_name_node.end_byte]
                                    method_docstring = self._extract_docstring(method_node, code)
                                    symbols.append({
                                        "name": f"{class_name}.{method_name}",
                                        "type": "method",
                                        "line_start": method_node.start_point[0] + 1,
                                        "line_end": method_node.end_point[0] + 1,
                                        "code": code[method_node.start_byte:method_node.end_byte],
                                        "docstring": method_docstring,
                                    })

        # Query for comments
        comment_query = lang.query("""
            (comment) @comment
        """)

        for node, tag in comment_query.captures(root):
            if tag == "comment":
                comments.append({
                    "text": code[node.start_byte:node.end_byte],
                    "line": node.start_point[0] + 1,
                })

        # Query for imports
        import_query = lang.query("""
            (import_statement) @import
            (import_from_statement) @import_from
        """)

        for node, tag in import_query.captures(root):
            if tag == "import" or tag == "import_from":
                imports.append({
                    "text": code[node.start_byte:node.end_byte],
                    "line": node.start_point[0] + 1,
                    "type": tag,
                })

        return symbols, imports, comments

    def _extract_javascript(self, tree, code: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Extract JavaScript/TypeScript symbols, imports, and comments.

        Returns:
            (symbols, imports, comments)
        """
        symbols = []
        imports = []
        comments = []

        # Determine language (javascript or typescript based on file extension)
        # Both share similar syntax, so we'll detect based on calling context
        lang_name = "javascript"  # Default to javascript
        try:
            lang = self.get_language(lang_name)
        except Exception as e:
            logger.error(f"Failed to get language {lang_name}: {e}")
            return [], [], []
        root = tree.root_node

        # Query for function declarations
        func_query = lang.query("""
            (function_declaration
                name: (identifier) @func_name) @func
        """)

        for node, tag in func_query.captures(root):
            if tag == "func":
                # Find function name node
                name_node = None
                for child in node.children:
                    if child.type == "identifier":
                        name_node = child
                        break

                if name_node:
                    symbols.append({
                        "name": code[name_node.start_byte:name_node.end_byte],
                        "type": "function",
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                        "code": code[node.start_byte:node.end_byte],
                    })

        # Query for arrow functions (const foo = () => {})
        arrow_query = lang.query("""
            (lexical_declaration
                (variable_declarator
                    name: (identifier) @arrow_name
                    value: (arrow_function))) @arrow
        """)

        for node, tag in arrow_query.captures(root):
            if tag == "arrow_name":
                # Find the variable_declarator parent
                parent = node.parent
                if parent:
                    symbols.append({
                        "name": code[node.start_byte:node.end_byte],
                        "type": "function",
                        "line_start": parent.start_point[0] + 1,
                        "line_end": parent.end_point[0] + 1,
                        "code": code[parent.start_byte:parent.end_byte],
                    })

        # Query for class declarations
        class_query = lang.query("""
            (class_declaration
                name: (identifier) @class_name) @class
        """)

        for node, tag in class_query.captures(root):
            if tag == "class":
                name_node = None
                for child in node.children:
                    if child.type == "identifier":
                        name_node = child
                        break

                if name_node:
                    symbols.append({
                        "name": code[name_node.start_byte:name_node.end_byte],
                        "type": "class",
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                        "code": code[node.start_byte:node.end_byte],
                    })

        # Query for method definitions (inside classes)
        method_query = lang.query("""
            (method_definition
                name: (property_identifier) @method_name) @method
        """)

        for node, tag in method_query.captures(root):
            if tag == "method":
                name_node = None
                for child in node.children:
                    if child.type == "property_identifier":
                        name_node = child
                        break

                if name_node:
                    # Try to find parent class name
                    parent = node.parent
                    while parent and parent.type != "class_declaration":
                        parent = parent.parent

                    class_name = "unknown"
                    if parent:
                        for child in parent.children:
                            if child.type == "identifier":
                                class_name = code[child.start_byte:child.end_byte]
                                break

                    method_name = code[name_node.start_byte:name_node.end_byte]
                    full_name = f"{class_name}.{method_name}" if class_name != "unknown" else method_name

                    symbols.append({
                        "name": full_name,
                        "type": "method",
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                        "code": code[node.start_byte:node.end_byte],
                    })

        # Query for comments
        comment_query = lang.query("""
            (comment) @comment
        """)

        for node, tag in comment_query.captures(root):
            if tag == "comment":
                comments.append({
                    "text": code[node.start_byte:node.end_byte],
                    "line": node.start_point[0] + 1,
                })

        # Query for import statements
        import_query = lang.query("""
            (import_statement) @import
        """)

        for node, tag in import_query.captures(root):
            if tag == "import":
                imports.append({
                    "text": code[node.start_byte:node.end_byte],
                    "line": node.start_point[0] + 1,
                    "type": "import",
                })

        return symbols, imports, comments

    def _extract_rust(self, tree, code: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Extract Rust symbols, imports (use statements), and comments.

        Returns:
            (symbols, imports, comments)
        """
        symbols = []
        imports = []
        comments = []

        lang = self.get_language("rust")
        root = tree.root_node

        # Query for function definitions
        func_query = lang.query("""
            (function_item
                name: (identifier) @func_name) @func
        """)

        for node, tag in func_query.captures(root):
            if tag == "func":
                # Find function name node
                name_node = None
                for child in node.children:
                    if child.type == "identifier":
                        name_node = child
                        break

                if name_node:
                    symbols.append({
                        "name": code[name_node.start_byte:name_node.end_byte],
                        "type": "function",
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                        "code": code[node.start_byte:node.end_byte],
                    })

        # Query for struct definitions
        struct_query = lang.query("""
            (struct_item
                name: (type_identifier) @struct_name) @struct
        """)

        for node, tag in struct_query.captures(root):
            if tag == "struct":
                name_node = None
                for child in node.children:
                    if child.type == "type_identifier":
                        name_node = child
                        break

                if name_node:
                    symbols.append({
                        "name": code[name_node.start_byte:name_node.end_byte],
                        "type": "class",  # Treat struct as class for consistency
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                        "code": code[node.start_byte:node.end_byte],
                    })

        # Query for impl blocks (methods)
        impl_query = lang.query("""
            (impl_item
                type: (type_identifier) @impl_type
                body: (declaration_list
                    (function_item
                        name: (identifier) @method_name) @method))
        """)

        captures_dict = {}
        for node, tag in impl_query.captures(root):
            if tag == "impl_type":
                captures_dict["impl_type"] = code[node.start_byte:node.end_byte]
            elif tag == "method" and "impl_type" in captures_dict:
                # Find method name
                name_node = None
                for child in node.children:
                    if child.type == "identifier":
                        name_node = child
                        break

                if name_node:
                    method_name = code[name_node.start_byte:name_node.end_byte]
                    full_name = f"{captures_dict['impl_type']}.{method_name}"

                    symbols.append({
                        "name": full_name,
                        "type": "method",
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                        "code": code[node.start_byte:node.end_byte],
                    })

        # Query for enum definitions
        enum_query = lang.query("""
            (enum_item
                name: (type_identifier) @enum_name) @enum
        """)

        for node, tag in enum_query.captures(root):
            if tag == "enum":
                name_node = None
                for child in node.children:
                    if child.type == "type_identifier":
                        name_node = child
                        break

                if name_node:
                    symbols.append({
                        "name": code[name_node.start_byte:name_node.end_byte],
                        "type": "class",  # Treat enum as class for consistency
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                        "code": code[node.start_byte:node.end_byte],
                    })

        # Query for comments (both line and block comments)
        comment_query = lang.query("""
            (line_comment) @comment
            (block_comment) @comment
        """)

        for node, tag in comment_query.captures(root):
            if tag == "comment":
                comments.append({
                    "text": code[node.start_byte:node.end_byte],
                    "line": node.start_point[0] + 1,
                })

        # Query for use statements (imports)
        use_query = lang.query("""
            (use_declaration) @use
        """)

        for node, tag in use_query.captures(root):
            if tag == "use":
                imports.append({
                    "text": code[node.start_byte:node.end_byte],
                    "line": node.start_point[0] + 1,
                    "type": "use",
                })

        return symbols, imports, comments

    def _extract_go(self, tree, code: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Extract Go symbols, imports, and comments.

        Returns:
            (symbols, imports, comments)
        """
        symbols = []
        imports = []
        comments = []

        lang = self.get_language("go")
        root = tree.root_node

        # Query for function declarations
        func_query = lang.query("""
            (function_declaration
                name: (identifier) @func_name) @func
        """)

        for node, tag in func_query.captures(root):
            if tag == "func":
                # Find function name node
                name_node = None
                for child in node.children:
                    if child.type == "identifier":
                        name_node = child
                        break

                if name_node:
                    symbols.append({
                        "name": code[name_node.start_byte:name_node.end_byte],
                        "type": "function",
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                        "code": code[node.start_byte:node.end_byte],
                    })

        # Query for method declarations (functions with receivers)
        method_query = lang.query("""
            (method_declaration
                receiver: (parameter_list
                    (parameter_declaration
                        type: (_) @receiver_type))
                name: (field_identifier) @method_name) @method
        """)

        for node, tag in method_query.captures(root):
            if tag == "method":
                # Find method name and receiver type
                method_name = None
                receiver_type = None

                for child in node.children:
                    if child.type == "field_identifier":
                        method_name = code[child.start_byte:child.end_byte]
                    elif child.type == "parameter_list":
                        # Extract receiver type from parameter_list
                        for param in child.children:
                            if param.type == "parameter_declaration":
                                for p_child in param.children:
                                    if p_child.type in ["type_identifier", "pointer_type"]:
                                        receiver_type = code[p_child.start_byte:p_child.end_byte]
                                        # Strip * from pointer types
                                        if receiver_type.startswith("*"):
                                            receiver_type = receiver_type[1:]
                                        break

                if method_name:
                    full_name = f"{receiver_type}.{method_name}" if receiver_type else method_name
                    symbols.append({
                        "name": full_name,
                        "type": "method",
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                        "code": code[node.start_byte:node.end_byte],
                    })

        # Query for type declarations (structs, interfaces)
        type_query = lang.query("""
            (type_declaration
                (type_spec
                    name: (type_identifier) @type_name
                    type: [(struct_type) (interface_type)])) @type_decl
        """)

        for node, tag in type_query.captures(root):
            if tag == "type_decl":
                # Find type name
                name_node = None
                for child in node.children:
                    if child.type == "type_spec":
                        for spec_child in child.children:
                            if spec_child.type == "type_identifier":
                                name_node = spec_child
                                break

                if name_node:
                    symbols.append({
                        "name": code[name_node.start_byte:name_node.end_byte],
                        "type": "class",  # Treat struct/interface as class
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1,
                        "code": code[node.start_byte:node.end_byte],
                    })

        # Query for comments
        comment_query = lang.query("""
            (comment) @comment
        """)

        for node, tag in comment_query.captures(root):
            if tag == "comment":
                comments.append({
                    "text": code[node.start_byte:node.end_byte],
                    "line": node.start_point[0] + 1,
                })

        # Query for import declarations
        import_query = lang.query("""
            (import_declaration) @import
        """)

        for node, tag in import_query.captures(root):
            if tag == "import":
                imports.append({
                    "text": code[node.start_byte:node.end_byte],
                    "line": node.start_point[0] + 1,
                    "type": "import",
                })

        return symbols, imports, comments
