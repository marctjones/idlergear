"""Documentation generation for Python projects.

This module provides tools for generating structured API documentation
from Python source code using pdoc. Designed for token-efficient API
exploration by AI assistants.

Features:
- Token-efficient summary modes (minimal ~500 tokens, standard ~2k, detailed ~5k)
- Structured JSON output for AI consumption
- Local HTML documentation build and serve
- Automatic project detection
"""

from __future__ import annotations

import http.server
import json
import socketserver
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

SummaryMode = Literal["minimal", "standard", "detailed"]

# Check if pdoc is available
try:
    import pdoc.doc

    PDOC_AVAILABLE = True
except ImportError:
    PDOC_AVAILABLE = False


@dataclass
class ParameterDoc:
    """Documentation for a function/method parameter."""

    name: str
    annotation: str | None = None
    default: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"name": self.name}
        if self.annotation:
            result["type"] = self.annotation
        if self.default:
            result["default"] = self.default
        if self.description:
            result["description"] = self.description
        return result


@dataclass
class FunctionDoc:
    """Documentation for a function or method."""

    name: str
    signature: str
    docstring: str | None = None
    parameters: list[ParameterDoc] = field(default_factory=list)
    return_type: str | None = None
    return_description: str | None = None
    is_async: bool = False
    decorators: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "name": self.name,
            "signature": self.signature,
        }
        if self.docstring:
            result["docstring"] = self.docstring
        if self.parameters:
            result["parameters"] = [p.to_dict() for p in self.parameters]
        if self.return_type:
            result["returns"] = {"type": self.return_type}
            if self.return_description:
                result["returns"]["description"] = self.return_description
        if self.is_async:
            result["async"] = True
        if self.decorators:
            result["decorators"] = self.decorators
        return result


@dataclass
class ClassDoc:
    """Documentation for a class."""

    name: str
    docstring: str | None = None
    bases: list[str] = field(default_factory=list)
    methods: list[FunctionDoc] = field(default_factory=list)
    class_variables: list[tuple[str, str | None]] = field(default_factory=list)
    instance_variables: list[tuple[str, str | None]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"name": self.name}
        if self.docstring:
            result["docstring"] = self.docstring
        if self.bases:
            result["bases"] = self.bases
        if self.methods:
            result["methods"] = [m.to_dict() for m in self.methods]
        if self.class_variables:
            result["class_variables"] = [
                {"name": name, "type": type_} if type_ else {"name": name}
                for name, type_ in self.class_variables
            ]
        if self.instance_variables:
            result["instance_variables"] = [
                {"name": name, "type": type_} if type_ else {"name": name}
                for name, type_ in self.instance_variables
            ]
        return result


@dataclass
class ModuleDoc:
    """Documentation for a module."""

    name: str
    docstring: str | None = None
    functions: list[FunctionDoc] = field(default_factory=list)
    classes: list[ClassDoc] = field(default_factory=list)
    submodules: list[str] = field(default_factory=list)
    variables: list[tuple[str, str | None]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"name": self.name}
        if self.docstring:
            result["docstring"] = self.docstring
        if self.functions:
            result["functions"] = [f.to_dict() for f in self.functions]
        if self.classes:
            result["classes"] = [c.to_dict() for c in self.classes]
        if self.submodules:
            result["submodules"] = self.submodules
        if self.variables:
            result["variables"] = [
                {"name": name, "type": type_} if type_ else {"name": name}
                for name, type_ in self.variables
            ]
        return result

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


def check_pdoc_available() -> bool:
    """Check if pdoc is available."""
    return PDOC_AVAILABLE


def _extract_parameter(param: Any) -> ParameterDoc:
    """Extract parameter documentation from pdoc parameter."""
    name = param.name
    annotation = None
    default = None

    # Get annotation if present
    if param.annotation is not param.empty:
        annotation = str(param.annotation)

    # Get default if present
    if param.default is not param.empty:
        default = repr(param.default)

    return ParameterDoc(name=name, annotation=annotation, default=default)


def _extract_function(func: Any) -> FunctionDoc:
    """Extract function documentation from pdoc function."""
    name = func.name
    docstring = func.docstring if func.docstring else None

    # Get signature
    sig = str(func.signature) if func.signature else "()"

    # Extract parameters
    parameters = []
    if func.signature and hasattr(func.signature, "parameters"):
        for param_name, param in func.signature.parameters.items():
            if param_name not in ("self", "cls"):
                parameters.append(_extract_parameter(param))

    # Get return type
    return_type = None
    if func.signature and func.signature.return_annotation is not func.signature.empty:
        return_type = str(func.signature.return_annotation)

    # Check if async
    is_async = getattr(func, "is_async", False) or (
        hasattr(func, "obj")
        and hasattr(func.obj, "__code__")
        and getattr(func.obj.__code__, "co_flags", 0) & 0x80  # CO_COROUTINE
    )

    return FunctionDoc(
        name=name,
        signature=sig,
        docstring=docstring,
        parameters=parameters,
        return_type=return_type,
        is_async=is_async,
    )


def _extract_class(cls: Any) -> ClassDoc:
    """Extract class documentation from pdoc class."""
    name = cls.name
    docstring = cls.docstring if cls.docstring else None

    # Get base classes
    bases = []
    if hasattr(cls, "bases"):
        bases = [str(b) for b in cls.bases if str(b) != "object"]

    # Extract methods
    methods = []
    for member_name, member in cls.members.items():
        if isinstance(member, pdoc.doc.Function):
            if not member_name.startswith("_") or member_name in (
                "__init__",
                "__call__",
                "__enter__",
                "__exit__",
                "__iter__",
                "__next__",
            ):
                methods.append(_extract_function(member))

    return ClassDoc(
        name=name,
        docstring=docstring,
        bases=bases,
        methods=methods,
    )


def generate_module_docs(module_name: str) -> ModuleDoc:
    """Generate documentation for a Python module.

    Args:
        module_name: The fully qualified module name (e.g., 'idlergear.tasks')

    Returns:
        ModuleDoc containing structured documentation

    Raises:
        ImportError: If pdoc is not installed
        ModuleNotFoundError: If the module cannot be found
    """
    if not PDOC_AVAILABLE:
        raise ImportError(
            "pdoc is not installed. Install with: pip install 'idlergear[docs]'"
        )

    # Load the module
    mod = pdoc.doc.Module.from_name(module_name)

    # Extract documentation
    docstring = mod.docstring if mod.docstring else None

    # Extract functions
    functions = []
    for name, member in mod.members.items():
        if isinstance(member, pdoc.doc.Function):
            if not name.startswith("_"):
                functions.append(_extract_function(member))

    # Extract classes
    classes = []
    for name, member in mod.members.items():
        if isinstance(member, pdoc.doc.Class):
            if not name.startswith("_"):
                classes.append(_extract_class(member))

    # Extract submodules
    submodules = []
    for name, member in mod.members.items():
        if isinstance(member, pdoc.doc.Module):
            submodules.append(name)

    # Extract module-level variables
    variables = []
    for name, member in mod.members.items():
        if isinstance(member, pdoc.doc.Variable):
            if not name.startswith("_"):
                annotation = str(member.annotation) if member.annotation else None
                variables.append((name, annotation))

    return ModuleDoc(
        name=module_name,
        docstring=docstring,
        functions=functions,
        classes=classes,
        submodules=submodules,
        variables=variables,
    )


def generate_package_docs(
    package_name: str,
    include_private: bool = False,
    max_depth: int | None = None,
) -> dict[str, ModuleDoc]:
    """Generate documentation for a Python package and all its submodules.

    Args:
        package_name: The package name (e.g., 'idlergear')
        include_private: Whether to include private modules (starting with _)
        max_depth: Maximum depth of submodules to document (None for unlimited)

    Returns:
        Dictionary mapping module names to their documentation
    """
    if not PDOC_AVAILABLE:
        raise ImportError(
            "pdoc is not installed. Install with: pip install 'idlergear[docs]'"
        )

    result: dict[str, ModuleDoc] = {}

    def _process_module(mod_name: str, depth: int = 0) -> None:
        """Process a module and its submodules recursively."""
        if max_depth is not None and depth > max_depth:
            return

        # Skip private modules unless requested
        parts = mod_name.split(".")
        if not include_private and any(p.startswith("_") for p in parts[1:]):
            return

        try:
            mod_doc = generate_module_docs(mod_name)
            result[mod_name] = mod_doc

            # Process submodules
            for submod in mod_doc.submodules:
                sub_name = f"{mod_name}.{submod}"
                _process_module(sub_name, depth + 1)
        except Exception:
            # Skip modules that can't be loaded
            pass

    _process_module(package_name)
    return result


def generate_docs_json(
    package_name: str,
    include_private: bool = False,
    max_depth: int | None = None,
    indent: int = 2,
) -> str:
    """Generate JSON documentation for a Python package.

    Args:
        package_name: The package name
        include_private: Whether to include private modules
        max_depth: Maximum depth of submodules
        indent: JSON indentation

    Returns:
        JSON string containing all module documentation
    """
    docs = generate_package_docs(package_name, include_private, max_depth)
    return json.dumps(
        {"package": package_name, "modules": {k: v.to_dict() for k, v in docs.items()}},
        indent=indent,
    )


def generate_docs_markdown(
    package_name: str,
    include_private: bool = False,
    max_depth: int | None = None,
) -> str:
    """Generate Markdown documentation for a Python package.

    Args:
        package_name: The package name
        include_private: Whether to include private modules
        max_depth: Maximum depth of submodules

    Returns:
        Markdown string containing all module documentation
    """
    docs = generate_package_docs(package_name, include_private, max_depth)

    lines = [f"# {package_name} API Reference", ""]

    for mod_name, mod_doc in sorted(docs.items()):
        # Module header
        depth = mod_name.count(".") + 1
        lines.append(f"{'#' * min(depth + 1, 6)} {mod_name}")
        lines.append("")

        if mod_doc.docstring:
            lines.append(mod_doc.docstring)
            lines.append("")

        # Functions
        if mod_doc.functions:
            lines.append("**Functions:**")
            lines.append("")
            for func in mod_doc.functions:
                lines.append(f"- `{func.name}{func.signature}`")
                if func.docstring:
                    # First line of docstring
                    first_line = func.docstring.split("\n")[0].strip()
                    if first_line:
                        lines.append(f"  - {first_line}")
            lines.append("")

        # Classes
        if mod_doc.classes:
            lines.append("**Classes:**")
            lines.append("")
            for cls in mod_doc.classes:
                bases_str = f"({', '.join(cls.bases)})" if cls.bases else ""
                lines.append(f"- `{cls.name}{bases_str}`")
                if cls.docstring:
                    first_line = cls.docstring.split("\n")[0].strip()
                    if first_line:
                        lines.append(f"  - {first_line}")
            lines.append("")

    return "\n".join(lines)


# Token-efficient summary generation


def generate_summary(
    package_name: str,
    mode: SummaryMode = "standard",
    include_private: bool = False,
    max_depth: int | None = None,
) -> dict[str, Any]:
    """Generate a token-efficient summary of a Python package.

    Args:
        package_name: The package name (e.g., 'idlergear')
        mode: Summary verbosity level:
            - "minimal": ~500 tokens - names only, no descriptions
            - "standard": ~2000 tokens - first-line docstrings
            - "detailed": ~5000 tokens - full docstrings, parameters
        include_private: Whether to include private modules
        max_depth: Maximum depth of submodules

    Returns:
        Dictionary with token-efficient package summary
    """
    docs = generate_package_docs(package_name, include_private, max_depth)

    if mode == "minimal":
        return _generate_minimal_summary(package_name, docs)
    elif mode == "standard":
        return _generate_standard_summary(package_name, docs)
    else:  # detailed
        return _generate_detailed_summary(package_name, docs)


def _generate_minimal_summary(
    package_name: str, docs: dict[str, ModuleDoc]
) -> dict[str, Any]:
    """Generate minimal summary (~500 tokens) - names only."""
    modules = {}
    for mod_name, mod_doc in sorted(docs.items()):
        mod_info: dict[str, Any] = {}
        if mod_doc.functions:
            mod_info["functions"] = [f.name for f in mod_doc.functions]
        if mod_doc.classes:
            mod_info["classes"] = [c.name for c in mod_doc.classes]
        if mod_doc.submodules:
            mod_info["submodules"] = mod_doc.submodules
        if mod_info:
            modules[mod_name] = mod_info

    return {"package": package_name, "mode": "minimal", "modules": modules}


def _generate_standard_summary(
    package_name: str, docs: dict[str, ModuleDoc]
) -> dict[str, Any]:
    """Generate standard summary (~2000 tokens) - first-line docstrings."""
    modules = {}
    for mod_name, mod_doc in sorted(docs.items()):
        mod_info: dict[str, Any] = {}

        # First line of module docstring
        if mod_doc.docstring:
            first_line = mod_doc.docstring.split("\n")[0].strip()
            if first_line:
                mod_info["description"] = first_line

        if mod_doc.functions:
            funcs = []
            for f in mod_doc.functions:
                func_info: dict[str, Any] = {"name": f.name, "sig": f.signature}
                if f.docstring:
                    first_line = f.docstring.split("\n")[0].strip()
                    if first_line:
                        func_info["desc"] = first_line
                funcs.append(func_info)
            mod_info["functions"] = funcs

        if mod_doc.classes:
            classes = []
            for c in mod_doc.classes:
                cls_info: dict[str, Any] = {"name": c.name}
                if c.bases:
                    cls_info["bases"] = c.bases
                if c.docstring:
                    first_line = c.docstring.split("\n")[0].strip()
                    if first_line:
                        cls_info["desc"] = first_line
                # Method names only
                if c.methods:
                    cls_info["methods"] = [m.name for m in c.methods]
                classes.append(cls_info)
            mod_info["classes"] = classes

        if mod_doc.submodules:
            mod_info["submodules"] = mod_doc.submodules

        if mod_info:
            modules[mod_name] = mod_info

    return {"package": package_name, "mode": "standard", "modules": modules}


def _generate_detailed_summary(
    package_name: str, docs: dict[str, ModuleDoc]
) -> dict[str, Any]:
    """Generate detailed summary (~5000 tokens) - full docstrings, parameters."""
    modules = {}
    for mod_name, mod_doc in sorted(docs.items()):
        mod_info: dict[str, Any] = {}

        if mod_doc.docstring:
            mod_info["docstring"] = mod_doc.docstring

        if mod_doc.functions:
            mod_info["functions"] = [f.to_dict() for f in mod_doc.functions]

        if mod_doc.classes:
            mod_info["classes"] = [c.to_dict() for c in mod_doc.classes]

        if mod_doc.submodules:
            mod_info["submodules"] = mod_doc.submodules

        if mod_doc.variables:
            mod_info["variables"] = [
                {"name": name, "type": type_} if type_ else {"name": name}
                for name, type_ in mod_doc.variables
            ]

        if mod_info:
            modules[mod_name] = mod_info

    return {"package": package_name, "mode": "detailed", "modules": modules}


def generate_summary_json(
    package_name: str,
    mode: SummaryMode = "standard",
    include_private: bool = False,
    max_depth: int | None = None,
    indent: int = 2,
) -> str:
    """Generate token-efficient JSON summary of a Python package.

    Args:
        package_name: The package name
        mode: Summary verbosity level (minimal, standard, detailed)
        include_private: Whether to include private modules
        max_depth: Maximum depth of submodules
        indent: JSON indentation

    Returns:
        JSON string containing package summary
    """
    summary = generate_summary(package_name, mode, include_private, max_depth)
    return json.dumps(summary, indent=indent)


# HTML documentation build and serve


def detect_python_project(path: Path | str = ".") -> dict[str, Any]:
    """Detect Python project configuration.

    Args:
        path: Project directory path

    Returns:
        Dictionary with project info (name, version, source_dir, etc.)
    """
    path = Path(path)
    result: dict[str, Any] = {"path": str(path.absolute()), "detected": False}

    # Check pyproject.toml
    pyproject = path / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        content = pyproject.read_text()
        data = tomllib.loads(content)

        if "project" in data:
            result["detected"] = True
            result["name"] = data["project"].get("name")
            result["version"] = data["project"].get("version")
            result["config_file"] = "pyproject.toml"

    # Check setup.py
    setup_py = path / "setup.py"
    if setup_py.exists() and not result["detected"]:
        result["detected"] = True
        result["config_file"] = "setup.py"

    # Find source directory
    for src_dir in ["src", "lib", "."]:
        src_path = path / src_dir
        if src_path.is_dir():
            # Look for packages (directories with __init__.py)
            packages = [
                d.name
                for d in src_path.iterdir()
                if d.is_dir() and (d / "__init__.py").exists()
            ]
            if packages:
                result["source_dir"] = src_dir
                result["packages"] = packages
                break

    return result


def build_html_docs(
    package_name: str,
    output_dir: Path | str = "docs/api",
    logo: str | None = None,
    favicon: str | None = None,
) -> dict[str, Any]:
    """Build HTML documentation using pdoc.

    Args:
        package_name: The package name to document
        output_dir: Output directory for HTML files
        logo: Optional path to logo image
        favicon: Optional path to favicon

    Returns:
        Dictionary with build result (success, output_dir, files)

    Raises:
        RuntimeError: If pdoc fails to build documentation
    """
    if not PDOC_AVAILABLE:
        raise ImportError(
            "pdoc is not installed. Install with: pip install 'idlergear[docs]'"
        )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Build pdoc command
    cmd = ["pdoc", package_name, "--output-directory", str(output_path)]
    if logo:
        cmd.extend(["--logo", logo])
    if favicon:
        cmd.extend(["--favicon", favicon])

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Create index redirect
        index_html = output_path / "index.html"
        if not index_html.exists():
            index_html.write_text(
                f"<!DOCTYPE html><html><head>"
                f'<meta http-equiv="refresh" content="0; url={package_name}.html">'
                f"</head></html>"
            )

        # List generated files
        files = [str(f.relative_to(output_path)) for f in output_path.rglob("*.html")]

        return {
            "success": True,
            "output_dir": str(output_path.absolute()),
            "files": files,
            "count": len(files),
        }

    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": e.stderr or str(e),
            "output_dir": str(output_path.absolute()),
        }


def serve_docs(
    docs_dir: Path | str = "docs/api",
    port: int = 8080,
    host: str = "127.0.0.1",
    open_browser: bool = True,
) -> dict[str, Any]:
    """Serve HTML documentation locally.

    Args:
        docs_dir: Directory containing HTML documentation
        port: Port to serve on
        host: Host to bind to
        open_browser: Whether to open browser automatically

    Returns:
        Dictionary with server info (url, pid)
    """
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        return {"success": False, "error": f"Directory not found: {docs_path}"}

    # Check if docs exist
    html_files = list(docs_path.glob("*.html"))
    if not html_files:
        return {"success": False, "error": f"No HTML files found in {docs_path}"}

    url = f"http://{host}:{port}"

    # Simple HTTP server
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(docs_path), **kwargs)

        def log_message(self, format: str, *args: Any) -> None:
            pass  # Suppress logging

    try:
        with socketserver.TCPServer((host, port), Handler):
            if open_browser:
                import webbrowser

                threading.Timer(0.5, lambda: webbrowser.open(url)).start()

            return {
                "success": True,
                "url": url,
                "docs_dir": str(docs_path.absolute()),
                "message": f"Serving docs at {url} - Press Ctrl+C to stop",
                "blocking": True,
            }
    except OSError as e:
        return {"success": False, "error": str(e)}
