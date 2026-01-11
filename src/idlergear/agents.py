"""AGENTS.md generation and management with language detection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Language(str, Enum):
    """Supported programming languages."""

    PYTHON = "python"
    RUST = "rust"
    JAVASCRIPT = "javascript"
    GO = "go"
    JAVA = "java"
    UNKNOWN = "unknown"


@dataclass
class LanguageTemplate:
    """Template for a specific language."""

    language: Language
    commands: dict[str, dict[str, str]]
    style: list[str]
    boundaries: dict[str, list[str]]
    project_structure: dict[str, str]
    detection_files: list[str] = field(default_factory=list)


# Language templates
PYTHON_TEMPLATE = LanguageTemplate(
    language=Language.PYTHON,
    detection_files=[
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
        "Pipfile",
        "poetry.lock",
    ],
    commands={
        "test": {"cmd": "pytest", "desc": "Run tests"},
        "lint": {"cmd": "ruff check .", "desc": "Lint code"},
        "format": {"cmd": "ruff format .", "desc": "Format code"},
        "typecheck": {"cmd": "mypy .", "desc": "Type check"},
    },
    style=[
        "Follow PEP 8 naming conventions",
        "Use type hints for function signatures",
        "Prefer f-strings over .format()",
        "Use pathlib.Path instead of os.path",
    ],
    boundaries={
        "always": [
            "Run tests before committing",
            "Update tests when changing behavior",
            "Use type hints for new functions",
        ],
        "ask_first": [
            "Adding new dependencies",
            "Changing public API signatures",
            "Modifying configuration files",
        ],
        "never": [
            "Modify .env or credentials files directly",
            "Remove existing tests without discussion",
            "Force push to main/master branch",
        ],
    },
    project_structure={
        "src/": "Source modules",
        "tests/": "Test suites (pytest)",
        "pyproject.toml": "Project configuration",
    },
)

RUST_TEMPLATE = LanguageTemplate(
    language=Language.RUST,
    detection_files=["Cargo.toml", "Cargo.lock"],
    commands={
        "build": {"cmd": "cargo build", "desc": "Build project"},
        "test": {"cmd": "cargo test", "desc": "Run tests"},
        "lint": {"cmd": "cargo clippy", "desc": "Lint code"},
        "format": {"cmd": "cargo fmt", "desc": "Format code"},
    },
    style=[
        "Follow Rust naming conventions (snake_case for functions)",
        "Use Result<T, E> for fallible operations",
        "Prefer &str over String for function parameters",
        "Use clippy suggestions",
    ],
    boundaries={
        "always": [
            "Run cargo test before committing",
            "Run cargo clippy and fix warnings",
            "Document public items with ///",
        ],
        "ask_first": [
            "Adding new crate dependencies",
            "Changing public API",
            "Using unsafe code",
        ],
        "never": [
            "Ignore clippy warnings without #[allow] explanation",
            "Use unwrap() in library code without comment",
            "Force push to main/master branch",
        ],
    },
    project_structure={
        "src/": "Source code",
        "tests/": "Integration tests",
        "Cargo.toml": "Package manifest",
    },
)

JAVASCRIPT_TEMPLATE = LanguageTemplate(
    language=Language.JAVASCRIPT,
    detection_files=["package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"],
    commands={
        "install": {"cmd": "npm install", "desc": "Install dependencies"},
        "test": {"cmd": "npm test", "desc": "Run tests"},
        "lint": {"cmd": "npm run lint", "desc": "Lint code"},
        "format": {"cmd": "npm run format", "desc": "Format code"},
        "build": {"cmd": "npm run build", "desc": "Build project"},
    },
    style=[
        "Use const/let, never var",
        "Prefer arrow functions for callbacks",
        "Use async/await over .then() chains",
        "Use template literals for string interpolation",
    ],
    boundaries={
        "always": [
            "Run tests before committing",
            "Update package-lock.json when changing dependencies",
            "Use TypeScript types if project uses TypeScript",
        ],
        "ask_first": [
            "Adding new npm dependencies",
            "Changing build configuration",
            "Modifying tsconfig.json or webpack config",
        ],
        "never": [
            "Commit node_modules/",
            "Store secrets in source code",
            "Force push to main/master branch",
        ],
    },
    project_structure={
        "src/": "Source code",
        "tests/": "Test suites",
        "package.json": "Package configuration",
    },
)

GO_TEMPLATE = LanguageTemplate(
    language=Language.GO,
    detection_files=["go.mod", "go.sum"],
    commands={
        "build": {"cmd": "go build ./...", "desc": "Build all packages"},
        "test": {"cmd": "go test ./...", "desc": "Run tests"},
        "lint": {"cmd": "golangci-lint run", "desc": "Lint code"},
        "format": {"cmd": "gofmt -w .", "desc": "Format code"},
        "vet": {"cmd": "go vet ./...", "desc": "Static analysis"},
    },
    style=[
        "Follow Effective Go guidelines",
        "Use gofmt for formatting (non-negotiable)",
        "Prefer explicit error handling over panic",
        "Use context.Context for cancellation",
    ],
    boundaries={
        "always": [
            "Run go vet before committing",
            "Handle all errors explicitly",
            "Run gofmt before committing",
        ],
        "ask_first": [
            "Adding new dependencies to go.mod",
            "Changing exported API (capitalized names)",
            "Modifying build tags",
        ],
        "never": [
            "Use panic for normal error handling",
            "Ignore linter warnings without comment",
            "Force push to main/master branch",
        ],
    },
    project_structure={
        "cmd/": "Main applications",
        "pkg/": "Library code (public)",
        "internal/": "Private packages",
        "go.mod": "Module definition",
    },
)

JAVA_TEMPLATE = LanguageTemplate(
    language=Language.JAVA,
    detection_files=["pom.xml", "build.gradle", "build.gradle.kts"],
    commands={
        "build": {"cmd": "mvn compile", "desc": "Compile project"},
        "test": {"cmd": "mvn test", "desc": "Run tests"},
        "package": {"cmd": "mvn package", "desc": "Package application"},
        "clean": {"cmd": "mvn clean", "desc": "Clean build artifacts"},
    },
    style=[
        "Follow Java naming conventions",
        "Use Optional<T> instead of null returns",
        "Prefer records for data classes (Java 14+)",
        "Use var for local variables when type is obvious",
    ],
    boundaries={
        "always": [
            "Run tests before committing",
            "Update tests when changing behavior",
            "Document public APIs with Javadoc",
        ],
        "ask_first": [
            "Adding new dependencies to pom.xml",
            "Changing public API signatures",
            "Modifying build configuration",
        ],
        "never": [
            "Commit IDE-specific files (.idea/, *.iml)",
            "Store secrets in source code",
            "Force push to main/master branch",
        ],
    },
    project_structure={
        "src/main/java/": "Source code",
        "src/test/java/": "Test code",
        "pom.xml": "Maven configuration",
    },
)

# Template registry
TEMPLATES: dict[Language, LanguageTemplate] = {
    Language.PYTHON: PYTHON_TEMPLATE,
    Language.RUST: RUST_TEMPLATE,
    Language.JAVASCRIPT: JAVASCRIPT_TEMPLATE,
    Language.GO: GO_TEMPLATE,
    Language.JAVA: JAVA_TEMPLATE,
}


def detect_language(project_path: Path) -> Language:
    """Detect the primary language of a project based on files present.

    Returns Language.UNKNOWN if no language can be detected.
    """
    # Check each language's detection files
    for language, template in TEMPLATES.items():
        for detection_file in template.detection_files:
            if (project_path / detection_file).exists():
                return language

    # Fallback: check for source file extensions
    py_files = list(project_path.glob("**/*.py"))
    rs_files = list(project_path.glob("**/*.rs"))
    js_files = list(project_path.glob("**/*.js")) + list(project_path.glob("**/*.ts"))
    go_files = list(project_path.glob("**/*.go"))
    java_files = list(project_path.glob("**/*.java"))

    # Ignore files in common non-source directories
    def filter_source(files: list[Path]) -> list[Path]:
        exclude_dirs = {"node_modules", "venv", ".venv", "target", "build", "dist"}
        return [f for f in files if not any(d in f.parts for d in exclude_dirs)]

    counts = {
        Language.PYTHON: len(filter_source(py_files)),
        Language.RUST: len(filter_source(rs_files)),
        Language.JAVASCRIPT: len(filter_source(js_files)),
        Language.GO: len(filter_source(go_files)),
        Language.JAVA: len(filter_source(java_files)),
    }

    if max(counts.values()) > 0:
        return max(counts, key=lambda k: counts[k])

    return Language.UNKNOWN


def generate_agents_md(
    template: LanguageTemplate,
    include_idlergear: bool = True,
) -> str:
    """Generate AGENTS.md content from a template."""
    lines = ["# AGENTS.md", ""]

    # Commands section
    lines.append("## Commands")
    lines.append("")
    lines.append("```bash")
    for cmd_name, cmd_info in template.commands.items():
        # Pad command for alignment
        cmd = cmd_info["cmd"]
        desc = cmd_info["desc"]
        lines.append(f"{cmd:<30} # {desc}")
    lines.append("```")
    lines.append("")

    # Project Structure
    lines.append("## Project Structure")
    lines.append("")
    for path, desc in template.project_structure.items():
        lines.append(f"- `{path}` - {desc}")
    lines.append("")

    # Code Style
    lines.append("## Code Style")
    lines.append("")
    for style_item in template.style:
        lines.append(f"- {style_item}")
    lines.append("")

    # Boundaries
    lines.append("## Boundaries")
    lines.append("")

    lines.append("### ✅ Always")
    for item in template.boundaries["always"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("### ⚠️ Ask First")
    for item in template.boundaries["ask_first"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("### 🚫 Never")
    for item in template.boundaries["never"]:
        lines.append(f"- {item}")
    lines.append("")

    # Add IdlerGear section if requested
    if include_idlergear:
        from idlergear.install import AGENTS_MD_SECTION

        lines.append(AGENTS_MD_SECTION)

    return "\n".join(lines)


def generate_claude_md(
    template: LanguageTemplate,
    include_idlergear: bool = True,
) -> str:
    """Generate CLAUDE.md content (shorter, Claude Code specific)."""
    lines = ["# CLAUDE.md", ""]

    # Quick commands reference
    lines.append("## Quick Commands")
    lines.append("")
    lines.append("```bash")
    for cmd_name, cmd_info in template.commands.items():
        lines.append(f"{cmd_info['cmd']}")
    lines.append("```")
    lines.append("")

    # Key style points (just top 2-3)
    lines.append("## Code Style")
    lines.append("")
    for style_item in template.style[:3]:
        lines.append(f"- {style_item}")
    lines.append("")

    # Add IdlerGear section if requested
    if include_idlergear:
        from idlergear.install import CLAUDE_MD_SECTION

        lines.append(CLAUDE_MD_SECTION)

    return "\n".join(lines)


def validate_agents_md(content: str) -> list[str]:
    """Validate AGENTS.md content and return list of issues.

    Returns empty list if valid.
    """
    issues = []

    # Check for required sections
    required_sections = ["## Commands", "## Code Style"]
    for section in required_sections:
        if section not in content:
            issues.append(f"Missing section: {section}")

    # Check for common problems
    if "TODO" in content:
        issues.append("Contains TODO - consider completing or removing")

    if "FIXME" in content:
        issues.append("Contains FIXME - consider fixing or removing")

    # Check for empty code blocks
    if "```\n```" in content or "```bash\n```" in content:
        issues.append("Contains empty code blocks")

    return issues


def update_agents_md(
    existing_content: str,
    template: LanguageTemplate,
    preserve_custom: bool = True,
) -> str:
    """Update existing AGENTS.md with new template while preserving customizations.

    If preserve_custom is True, keeps any sections not in the template.
    """
    # Parse existing content into sections
    sections = {}
    current_section = "preamble"
    current_lines = []

    for line in existing_content.split("\n"):
        if line.startswith("## "):
            if current_lines:
                sections[current_section] = "\n".join(current_lines)
            current_section = line
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_section] = "\n".join(current_lines)

    # Generate new content
    new_content = generate_agents_md(template, include_idlergear=True)

    if preserve_custom:
        # Parse new content sections
        new_sections = {}
        current_section = "preamble"
        current_lines = []

        for line in new_content.split("\n"):
            if line.startswith("## "):
                if current_lines:
                    new_sections[current_section] = "\n".join(current_lines)
                current_section = line
                current_lines = [line]
            else:
                current_lines.append(line)

        if current_lines:
            new_sections[current_section] = "\n".join(current_lines)

        # Merge: use new template sections but keep custom sections
        template_section_names = {
            "## Commands",
            "## Project Structure",
            "## Code Style",
            "## Boundaries",
            "## IdlerGear",
        }

        merged_sections = {}
        for section_name, content in sections.items():
            if section_name in template_section_names:
                # Use new template version
                if section_name in new_sections:
                    merged_sections[section_name] = new_sections[section_name]
            else:
                # Keep custom section
                merged_sections[section_name] = content

        # Add any new sections from template not in original
        for section_name, content in new_sections.items():
            if section_name not in merged_sections:
                merged_sections[section_name] = content

        # Reconstruct in order
        result_lines = []
        if "preamble" in merged_sections:
            result_lines.append(merged_sections["preamble"])
            del merged_sections["preamble"]

        # Add sections in preferred order
        preferred_order = [
            "## Commands",
            "## Project Structure",
            "## Code Style",
            "## Boundaries",
        ]
        for section_name in preferred_order:
            if section_name in merged_sections:
                result_lines.append(merged_sections[section_name])
                del merged_sections[section_name]

        # Add remaining sections (custom and IdlerGear)
        for section_name, content in sorted(merged_sections.items()):
            result_lines.append(content)

        return "\n".join(result_lines)

    return new_content
