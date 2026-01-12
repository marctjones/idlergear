"""Documentation generation for Python projects.

This module provides tools for generating structured API documentation
from Python source code using pdoc.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

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
