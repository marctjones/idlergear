"""Knowledge gap detection module.

Detects various types of knowledge gaps in the project:
- Missing references (terms used but not documented)
- Orphaned files (files without annotations)
- Stale documentation (docs older than code)
- Undefined acronyms
- Broken links
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from .config import find_idlergear_root
from .file_registry import FileRegistry
from .reference import list_references
from .tasks import list_tasks

GapType = Literal[
    "missing_reference",    # Term used but not documented
    "orphaned_code",        # File without annotations
    "stale_documentation",  # Docs older than code
    "undefined_acronym",    # Acronym not in references
    "broken_link",          # Link to missing file/doc
]


@dataclass
class KnowledgeGap:
    """Represents a detected knowledge gap."""
    type: GapType
    severity: Literal["high", "medium", "low"]
    location: str  # File path or reference ID
    description: str
    suggestion: str  # How to fix
    auto_fixable: bool
    context: dict | None = None


def detect_gaps(project_path: Path | None = None) -> list[KnowledgeGap]:
    """Detect knowledge gaps in project.

    Args:
        project_path: Project root path (auto-detected if not provided)

    Returns:
        List of detected gaps
    """
    if project_path is None:
        project_path = find_idlergear_root()
        if not project_path:
            return []

    gaps = []

    # 1. Find orphaned code (files without annotations)
    gaps.extend(_detect_orphaned_files(project_path))

    # 2. Find undefined acronyms
    gaps.extend(_detect_undefined_acronyms(project_path))

    # 3. Find broken links
    gaps.extend(_detect_broken_links(project_path))

    return gaps


def _detect_orphaned_files(project_path: Path) -> list[KnowledgeGap]:
    """Find code files without annotations."""
    gaps = []

    registry = FileRegistry()
    annotated_files = {entry.path for entry in registry.list_files()}

    # Find all source code files
    source_patterns = ["**/*.py", "**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx"]
    all_source_files = set()

    for pattern in source_patterns:
        for file_path in project_path.glob(pattern):
            # Skip virtual env, node_modules, .git, etc.
            parts = file_path.relative_to(project_path).parts
            if any(
                part.startswith(".")
                or part in ["venv", "env", "node_modules", "__pycache__", "build", "dist"]
                for part in parts
            ):
                continue
            all_source_files.add(str(file_path.relative_to(project_path)))

    # Find orphaned files (source files not in registry)
    for file_path in all_source_files:
        if file_path not in annotated_files:
            gaps.append(
                KnowledgeGap(
                    type="orphaned_code",
                    severity="medium",
                    location=file_path,
                    description=f"File '{file_path}' has no annotation",
                    suggestion=f"idlergear file annotate '{file_path}' --description '...'",
                    auto_fixable=False,  # Requires human description
                    context={"file_path": file_path},
                )
            )

    return gaps


def _detect_undefined_acronyms(project_path: Path) -> list[KnowledgeGap]:
    """Find acronyms used in code but not documented."""
    gaps = []

    # Load documented acronyms from references
    references = list_references()
    documented_acronyms = {
        ref.get("title", "").upper()
        for ref in references
        if ref.get("category") == "acronym"
    }

    # Find acronyms in task titles/descriptions
    tasks = list_tasks()
    acronym_pattern = re.compile(r'\b[A-Z]{2,}\b')  # 2+ uppercase letters

    found_acronyms = set()
    for task in tasks:
        title = task.get("title", "")
        body = task.get("body", "")
        for text in [title, body]:
            matches = acronym_pattern.findall(text)
            found_acronyms.update(matches)

    # Find undocumented acronyms
    for acronym in found_acronyms:
        # Skip common words that look like acronyms
        if acronym in ["OK", "ID", "US", "UK", "API", "URL", "HTTP", "JSON", "XML"]:
            continue

        if acronym not in documented_acronyms:
            gaps.append(
                KnowledgeGap(
                    type="undefined_acronym",
                    severity="low",
                    location=f"Tasks/Notes containing '{acronym}'",
                    description=f"Acronym '{acronym}' used but not documented",
                    suggestion=f"idlergear reference add '{acronym}' --category acronym --body 'Stands for ...'",
                    auto_fixable=False,
                    context={"acronym": acronym},
                )
            )

    return gaps


def _detect_broken_links(project_path: Path) -> list[KnowledgeGap]:
    """Find links to missing files in references."""
    gaps = []

    references = list_references()

    for ref in references:
        content = ref.get("content", "") or ref.get("body", "")
        if not content:
            continue

        # Find markdown links: [text](path)
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        matches = link_pattern.findall(content)

        for link_text, link_path in matches:
            # Skip URLs
            if link_path.startswith(("http://", "https://", "mailto:", "#")):
                continue

            # Check if file exists
            full_path = project_path / link_path
            if not full_path.exists():
                gaps.append(
                    KnowledgeGap(
                        type="broken_link",
                        severity="medium",
                        location=f"Reference: {ref.get('title', 'Unknown')}",
                        description=f"Link to missing file: {link_path}",
                        suggestion=f"Update link in reference '{ref.get('title')}' or create file",
                        auto_fixable=False,
                        context={
                            "reference_id": ref.get("id"),
                            "link_path": link_path,
                            "link_text": link_text,
                        },
                    )
                )

    return gaps


def auto_fix_gap(gap: KnowledgeGap) -> bool:
    """Attempt to automatically fix a knowledge gap.

    Args:
        gap: Gap to fix

    Returns:
        True if fixed, False if manual intervention needed
    """
    # Currently no gaps are auto-fixable as they all require human input
    # Future: Could auto-create basic file annotations with AI assistance
    return False


def gap_report(gaps: list[KnowledgeGap]) -> str:
    """Generate human-readable gap report.

    Args:
        gaps: List of detected gaps

    Returns:
        Formatted report string
    """
    if not gaps:
        return "No knowledge gaps detected ✅"

    # Group by severity
    by_severity = {"high": [], "medium": [], "low": []}
    for gap in gaps:
        by_severity[gap.severity].append(gap)

    lines = ["# Knowledge Gaps Report\n"]

    for severity in ["high", "medium", "low"]:
        gaps_in_severity = by_severity[severity]
        if not gaps_in_severity:
            continue

        emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[severity]
        lines.append(f"\n## {emoji} {severity.upper()} Priority ({len(gaps_in_severity)})\n")

        for i, gap in enumerate(gaps_in_severity, 1):
            lines.append(f"{i}. **{gap.type.replace('_', ' ').title()}**")
            lines.append(f"   - Location: {gap.location}")
            lines.append(f"   - Issue: {gap.description}")
            lines.append(f"   - Fix: `{gap.suggestion}`\n")

    return "\n".join(lines)
