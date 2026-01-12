"""Rust documentation generation support.

This module provides tools for generating structured API documentation
from Rust source code. Designed for token-efficient API exploration
by AI assistants.

Uses source parsing (not rustdoc JSON) for maximum compatibility.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

SummaryMode = Literal["minimal", "standard", "detailed"]


@dataclass
class RustItem:
    """Base class for Rust documentation items."""

    name: str
    visibility: str = "pub"
    doc_comment: str | None = None
    line_number: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"name": self.name}
        if self.doc_comment:
            result["doc"] = self.doc_comment
        return result


@dataclass
class RustFunction(RustItem):
    """Documentation for a Rust function."""

    signature: str = ""
    is_async: bool = False
    is_unsafe: bool = False
    is_const: bool = False
    parameters: list[tuple[str, str]] = field(default_factory=list)
    return_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        if self.signature:
            result["signature"] = self.signature
        if self.is_async:
            result["async"] = True
        if self.is_unsafe:
            result["unsafe"] = True
        if self.parameters:
            result["parameters"] = [
                {"name": name, "type": typ} for name, typ in self.parameters
            ]
        if self.return_type:
            result["returns"] = self.return_type
        return result


@dataclass
class RustStruct(RustItem):
    """Documentation for a Rust struct."""

    fields: list[tuple[str, str, str | None]] = field(
        default_factory=list
    )  # (name, type, doc)
    is_tuple: bool = False
    derives: list[str] = field(default_factory=list)
    methods: list[RustFunction] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        if self.fields:
            result["fields"] = [
                {"name": name, "type": typ, "doc": doc}
                if doc
                else {"name": name, "type": typ}
                for name, typ, doc in self.fields
            ]
        if self.derives:
            result["derives"] = self.derives
        if self.methods:
            result["methods"] = [m.to_dict() for m in self.methods]
        return result


@dataclass
class RustEnum(RustItem):
    """Documentation for a Rust enum."""

    variants: list[tuple[str, str | None]] = field(default_factory=list)  # (name, doc)
    derives: list[str] = field(default_factory=list)
    methods: list[RustFunction] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        if self.variants:
            result["variants"] = [
                {"name": name, "doc": doc} if doc else {"name": name}
                for name, doc in self.variants
            ]
        if self.derives:
            result["derives"] = self.derives
        if self.methods:
            result["methods"] = [m.to_dict() for m in self.methods]
        return result


@dataclass
class RustTrait(RustItem):
    """Documentation for a Rust trait."""

    methods: list[RustFunction] = field(default_factory=list)
    supertraits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        if self.supertraits:
            result["supertraits"] = self.supertraits
        if self.methods:
            result["methods"] = [m.to_dict() for m in self.methods]
        return result


@dataclass
class RustModule:
    """Documentation for a Rust module."""

    name: str
    path: str
    doc_comment: str | None = None
    functions: list[RustFunction] = field(default_factory=list)
    structs: list[RustStruct] = field(default_factory=list)
    enums: list[RustEnum] = field(default_factory=list)
    traits: list[RustTrait] = field(default_factory=list)
    submodules: list[str] = field(default_factory=list)
    constants: list[tuple[str, str]] = field(default_factory=list)  # (name, type)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"name": self.name, "path": self.path}
        if self.doc_comment:
            result["doc"] = self.doc_comment
        if self.functions:
            result["functions"] = [f.to_dict() for f in self.functions]
        if self.structs:
            result["structs"] = [s.to_dict() for s in self.structs]
        if self.enums:
            result["enums"] = [e.to_dict() for e in self.enums]
        if self.traits:
            result["traits"] = [t.to_dict() for t in self.traits]
        if self.submodules:
            result["submodules"] = self.submodules
        if self.constants:
            result["constants"] = [{"name": n, "type": t} for n, t in self.constants]
        return result


@dataclass
class RustCrate:
    """Documentation for a Rust crate."""

    name: str
    version: str | None = None
    description: str | None = None
    modules: list[RustModule] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"name": self.name}
        if self.version:
            result["version"] = self.version
        if self.description:
            result["description"] = self.description
        if self.modules:
            result["modules"] = [m.to_dict() for m in self.modules]
        return result

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


def check_cargo_available() -> bool:
    """Check if cargo is available."""
    try:
        result = subprocess.run(
            ["cargo", "--version"], capture_output=True, text=True, check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def detect_rust_project(path: Path | str = ".") -> dict[str, Any]:
    """Detect Rust project configuration.

    Args:
        path: Project directory path

    Returns:
        Dictionary with project info (name, version, edition, etc.)
    """
    path = Path(path)
    result: dict[str, Any] = {
        "path": str(path.absolute()),
        "detected": False,
        "language": "rust",
    }

    cargo_toml = path / "Cargo.toml"
    if not cargo_toml.exists():
        return result

    result["detected"] = True
    result["config_file"] = "Cargo.toml"

    # Parse Cargo.toml
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    content = cargo_toml.read_text()
    data = tomllib.loads(content)

    if "package" in data:
        pkg = data["package"]
        result["name"] = pkg.get("name")
        result["version"] = pkg.get("version")
        result["edition"] = pkg.get("edition", "2021")
        result["description"] = pkg.get("description")

    # Check for workspace
    if "workspace" in data:
        result["is_workspace"] = True
        members = data["workspace"].get("members", [])
        result["workspace_members"] = members

    # Detect source files
    src_dir = path / "src"
    if src_dir.exists():
        result["source_dir"] = "src"
        if (src_dir / "lib.rs").exists():
            result["crate_type"] = "lib"
        elif (src_dir / "main.rs").exists():
            result["crate_type"] = "bin"

    return result


def _extract_doc_comment(lines: list[str], end_line: int) -> str | None:
    """Extract doc comment above a line."""
    doc_lines = []
    i = end_line - 1

    while i >= 0:
        line = lines[i].strip()
        if line.startswith("///"):
            doc_lines.insert(0, line[3:].strip())
            i -= 1
        elif line.startswith("//!"):
            doc_lines.insert(0, line[3:].strip())
            i -= 1
        elif line == "" or line.startswith("#["):
            i -= 1
        else:
            break

    return "\n".join(doc_lines) if doc_lines else None


def _parse_function_signature(sig: str) -> tuple[list[tuple[str, str]], str | None]:
    """Parse function parameters and return type from signature."""
    parameters = []
    return_type = None

    # Extract parameters
    param_match = re.search(r"\((.*?)\)", sig, re.DOTALL)
    if param_match:
        params_str = param_match.group(1)
        # Simple parsing - split by comma (doesn't handle nested generics perfectly)
        for param in params_str.split(","):
            param = param.strip()
            if not param or param == "self" or param == "&self" or param == "&mut self":
                continue
            if ":" in param:
                name, typ = param.split(":", 1)
                parameters.append((name.strip(), typ.strip()))

    # Extract return type
    ret_match = re.search(r"->\s*(.+?)(?:\s*where|\s*\{|$)", sig)
    if ret_match:
        return_type = ret_match.group(1).strip()

    return parameters, return_type


def parse_rust_file(file_path: Path) -> RustModule:
    """Parse a Rust source file and extract documentation.

    Args:
        file_path: Path to the .rs file

    Returns:
        RustModule with extracted documentation
    """
    content = file_path.read_text()
    lines = content.split("\n")

    module_name = file_path.stem
    if module_name == "lib" or module_name == "main":
        module_name = file_path.parent.name

    module = RustModule(name=module_name, path=str(file_path))

    # Extract module-level doc comment (//!)
    module_doc_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//!"):
            module_doc_lines.append(stripped[3:].strip())
        elif stripped and not stripped.startswith("//"):
            break
    if module_doc_lines:
        module.doc_comment = "\n".join(module_doc_lines)

    # Patterns for public items
    pub_fn_pattern = re.compile(
        r"^\s*pub(?:\s*\([^)]*\))?\s+(async\s+)?(unsafe\s+)?(const\s+)?fn\s+(\w+)"
    )
    pub_struct_pattern = re.compile(r"^\s*pub(?:\s*\([^)]*\))?\s+struct\s+(\w+)")
    pub_enum_pattern = re.compile(r"^\s*pub(?:\s*\([^)]*\))?\s+enum\s+(\w+)")
    pub_trait_pattern = re.compile(r"^\s*pub(?:\s*\([^)]*\))?\s+trait\s+(\w+)")
    pub_const_pattern = re.compile(
        r"^\s*pub(?:\s*\([^)]*\))?\s+const\s+(\w+)\s*:\s*([^=]+)"
    )
    mod_pattern = re.compile(r"^\s*pub(?:\s*\([^)]*\))?\s+mod\s+(\w+)")
    derive_pattern = re.compile(r"#\[derive\(([^)]+)\)\]")

    current_derives: list[str] = []

    for i, line in enumerate(lines):
        # Track derives
        derive_match = derive_pattern.search(line)
        if derive_match:
            derives = [d.strip() for d in derive_match.group(1).split(",")]
            current_derives.extend(derives)
            continue

        # Check for pub fn
        fn_match = pub_fn_pattern.match(line)
        if fn_match:
            is_async = fn_match.group(1) is not None
            is_unsafe = fn_match.group(2) is not None
            is_const = fn_match.group(3) is not None
            name = fn_match.group(4)

            # Get full signature (up to opening brace)
            sig_lines = [line]
            j = i + 1
            while j < len(lines) and "{" not in "".join(sig_lines):
                sig_lines.append(lines[j])
                j += 1
            signature = " ".join(line.strip() for line in sig_lines)
            signature = re.sub(r"\s*\{.*", "", signature)

            params, ret_type = _parse_function_signature(signature)
            doc = _extract_doc_comment(lines, i)

            func = RustFunction(
                name=name,
                signature=signature,
                is_async=is_async,
                is_unsafe=is_unsafe,
                is_const=is_const,
                parameters=params,
                return_type=ret_type,
                doc_comment=doc,
                line_number=i + 1,
            )
            module.functions.append(func)
            current_derives = []
            continue

        # Check for pub struct
        struct_match = pub_struct_pattern.match(line)
        if struct_match:
            name = struct_match.group(1)
            doc = _extract_doc_comment(lines, i)

            struct = RustStruct(
                name=name,
                doc_comment=doc,
                derives=current_derives.copy(),
                line_number=i + 1,
            )
            module.structs.append(struct)
            current_derives = []
            continue

        # Check for pub enum
        enum_match = pub_enum_pattern.match(line)
        if enum_match:
            name = enum_match.group(1)
            doc = _extract_doc_comment(lines, i)

            enum = RustEnum(
                name=name,
                doc_comment=doc,
                derives=current_derives.copy(),
                line_number=i + 1,
            )
            module.enums.append(enum)
            current_derives = []
            continue

        # Check for pub trait
        trait_match = pub_trait_pattern.match(line)
        if trait_match:
            name = trait_match.group(1)
            doc = _extract_doc_comment(lines, i)

            trait = RustTrait(
                name=name,
                doc_comment=doc,
                line_number=i + 1,
            )
            module.traits.append(trait)
            current_derives = []
            continue

        # Check for pub const
        const_match = pub_const_pattern.match(line)
        if const_match:
            name = const_match.group(1)
            typ = const_match.group(2).strip()
            module.constants.append((name, typ))
            current_derives = []
            continue

        # Check for pub mod
        mod_match = mod_pattern.match(line)
        if mod_match:
            name = mod_match.group(1)
            module.submodules.append(name)
            current_derives = []
            continue

        # Reset derives if we hit a non-attribute, non-empty line
        if line.strip() and not line.strip().startswith("#["):
            current_derives = []

    return module


def parse_rust_crate(path: Path | str = ".") -> RustCrate:
    """Parse a Rust crate and extract documentation.

    Args:
        path: Path to the crate root

    Returns:
        RustCrate with all module documentation
    """
    path = Path(path)
    project = detect_rust_project(path)

    if not project["detected"]:
        raise ValueError(f"No Rust project found at {path}")

    crate = RustCrate(
        name=project.get("name", path.name),
        version=project.get("version"),
        description=project.get("description"),
    )

    src_dir = path / "src"
    if not src_dir.exists():
        return crate

    # Parse all .rs files
    for rs_file in src_dir.rglob("*.rs"):
        try:
            module = parse_rust_file(rs_file)
            # Set relative path
            module.path = str(rs_file.relative_to(path))
            crate.modules.append(module)
        except Exception:
            # Skip files that can't be parsed
            pass

    return crate


def generate_rust_summary(
    path: Path | str = ".",
    mode: SummaryMode = "standard",
) -> dict[str, Any]:
    """Generate a token-efficient summary of a Rust crate.

    Args:
        path: Path to the crate root
        mode: Summary verbosity level:
            - "minimal": ~500 tokens - names only
            - "standard": ~2000 tokens - first-line docstrings
            - "detailed": ~5000 tokens - full docstrings

    Returns:
        Dictionary with token-efficient crate summary
    """
    crate = parse_rust_crate(path)

    if mode == "minimal":
        return _generate_minimal_rust_summary(crate)
    elif mode == "standard":
        return _generate_standard_rust_summary(crate)
    else:
        return _generate_detailed_rust_summary(crate)


def _generate_minimal_rust_summary(crate: RustCrate) -> dict[str, Any]:
    """Generate minimal summary - names only."""
    modules = {}
    for mod in crate.modules:
        mod_info: dict[str, Any] = {}
        if mod.functions:
            mod_info["functions"] = [f.name for f in mod.functions]
        if mod.structs:
            mod_info["structs"] = [s.name for s in mod.structs]
        if mod.enums:
            mod_info["enums"] = [e.name for e in mod.enums]
        if mod.traits:
            mod_info["traits"] = [t.name for t in mod.traits]
        if mod.submodules:
            mod_info["submodules"] = mod.submodules
        if mod_info:
            modules[mod.path] = mod_info

    result: dict[str, Any] = {
        "crate": crate.name,
        "language": "rust",
        "mode": "minimal",
        "modules": modules,
    }
    if crate.version:
        result["version"] = crate.version
    return result


def _generate_standard_rust_summary(crate: RustCrate) -> dict[str, Any]:
    """Generate standard summary - first-line docstrings."""
    modules = {}
    for mod in crate.modules:
        mod_info: dict[str, Any] = {}

        if mod.doc_comment:
            first_line = mod.doc_comment.split("\n")[0].strip()
            if first_line:
                mod_info["description"] = first_line

        if mod.functions:
            funcs = []
            for f in mod.functions:
                func_info: dict[str, Any] = {"name": f.name}
                if f.signature:
                    # Shortened signature
                    sig = f.signature
                    if len(sig) > 80:
                        sig = sig[:77] + "..."
                    func_info["sig"] = sig
                if f.doc_comment:
                    first_line = f.doc_comment.split("\n")[0].strip()
                    if first_line:
                        func_info["desc"] = first_line
                funcs.append(func_info)
            mod_info["functions"] = funcs

        if mod.structs:
            structs = []
            for s in mod.structs:
                struct_info: dict[str, Any] = {"name": s.name}
                if s.derives:
                    struct_info["derives"] = s.derives
                if s.doc_comment:
                    first_line = s.doc_comment.split("\n")[0].strip()
                    if first_line:
                        struct_info["desc"] = first_line
                structs.append(struct_info)
            mod_info["structs"] = structs

        if mod.enums:
            enums = []
            for e in mod.enums:
                enum_info: dict[str, Any] = {"name": e.name}
                if e.doc_comment:
                    first_line = e.doc_comment.split("\n")[0].strip()
                    if first_line:
                        enum_info["desc"] = first_line
                enums.append(enum_info)
            mod_info["enums"] = enums

        if mod.traits:
            traits = []
            for t in mod.traits:
                trait_info: dict[str, Any] = {"name": t.name}
                if t.doc_comment:
                    first_line = t.doc_comment.split("\n")[0].strip()
                    if first_line:
                        trait_info["desc"] = first_line
                traits.append(trait_info)
            mod_info["traits"] = traits

        if mod.submodules:
            mod_info["submodules"] = mod.submodules

        if mod_info:
            modules[mod.path] = mod_info

    result: dict[str, Any] = {
        "crate": crate.name,
        "language": "rust",
        "mode": "standard",
        "modules": modules,
    }
    if crate.version:
        result["version"] = crate.version
    if crate.description:
        result["description"] = crate.description
    return result


def _generate_detailed_rust_summary(crate: RustCrate) -> dict[str, Any]:
    """Generate detailed summary - full docstrings."""
    result: dict[str, Any] = {
        "crate": crate.name,
        "language": "rust",
        "mode": "detailed",
        "modules": {mod.path: mod.to_dict() for mod in crate.modules},
    }
    if crate.version:
        result["version"] = crate.version
    if crate.description:
        result["description"] = crate.description
    return result


def generate_rust_summary_json(
    path: Path | str = ".",
    mode: SummaryMode = "standard",
    indent: int = 2,
) -> str:
    """Generate token-efficient JSON summary of a Rust crate.

    Args:
        path: Path to the crate root
        mode: Summary verbosity level
        indent: JSON indentation

    Returns:
        JSON string containing crate summary
    """
    summary = generate_rust_summary(path, mode)
    return json.dumps(summary, indent=indent)


def build_rust_docs(
    path: Path | str = ".",
    open_browser: bool = False,
    document_private: bool = False,
) -> dict[str, Any]:
    """Build HTML documentation using cargo doc.

    Args:
        path: Path to the crate root
        open_browser: Whether to open docs in browser
        document_private: Whether to document private items

    Returns:
        Dictionary with build result
    """
    path = Path(path)

    if not check_cargo_available():
        return {"success": False, "error": "cargo not found"}

    if not (path / "Cargo.toml").exists():
        return {"success": False, "error": f"No Cargo.toml found at {path}"}

    cmd = ["cargo", "doc"]
    if open_browser:
        cmd.append("--open")
    if document_private:
        cmd.append("--document-private-items")

    try:
        result = subprocess.run(
            cmd, cwd=path, capture_output=True, text=True, check=True
        )

        # Find output directory
        target_doc = path / "target" / "doc"
        files = list(target_doc.rglob("*.html")) if target_doc.exists() else []

        return {
            "success": True,
            "output_dir": str(target_doc.absolute()),
            "count": len(files),
            "message": result.stdout or "Documentation built successfully",
        }

    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": e.stderr or str(e),
        }
