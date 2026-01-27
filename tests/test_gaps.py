"""Tests for knowledge gap detection."""

import pytest
from pathlib import Path

from idlergear.gaps import (
    detect_gaps,
    gap_report,
    auto_fix_gap,
    KnowledgeGap,
)
from idlergear.tasks import create_task
from idlergear.reference import add_reference
from idlergear.file_registry import FileRegistry


def test_detect_orphaned_files(temp_project):
    """Test detection of files without annotations."""
    # Create some source files
    src_dir = temp_project / "src"
    src_dir.mkdir()

    # Create unannotated Python file
    (src_dir / "main.py").write_text("print('hello')")
    (src_dir / "utils.py").write_text("def helper(): pass")

    # Annotate one file
    registry = FileRegistry()
    registry.annotate_file(
        path="src/main.py",
        description="Main entry point",
        tags=["entry"]
    )

    gaps = detect_gaps(temp_project)

    # Should detect utils.py as orphaned
    orphaned_gaps = [g for g in gaps if g.type == "orphaned_code"]
    assert len(orphaned_gaps) >= 1
    assert any("utils.py" in g.location for g in orphaned_gaps)

    # Should not flag annotated file
    assert not any("main.py" in g.location for g in orphaned_gaps)


def test_detect_undefined_acronyms(temp_project):
    """Test detection of undefined acronyms in tasks."""
    # Create task with acronym
    create_task("Implement REST API endpoint", body="Use HTTP protocol")

    # Create reference for one acronym but not the other
    add_reference(
        title="REST",
        body="Representational State Transfer"
    )

    gaps = detect_gaps(temp_project)

    acronym_gaps = [g for g in gaps if g.type == "undefined_acronym"]

    # API is a common acronym and should be skipped
    # HTTP is also common and should be skipped
    # So we shouldn't get gaps for these common ones
    assert all(
        gap.location not in ["Tasks/Notes containing 'API'", "Tasks/Notes containing 'HTTP'"]
        for gap in acronym_gaps
    )


def test_detect_broken_links(temp_project):
    """Test detection of broken links in references."""
    # Create reference with link to non-existent file
    add_reference(
        title="Documentation",
        body="See [design doc](docs/design.md) for details"
    )

    gaps = detect_gaps(temp_project)

    broken_link_gaps = [g for g in gaps if g.type == "broken_link"]
    assert len(broken_link_gaps) >= 1
    assert any("design.md" in g.description for g in broken_link_gaps)


def test_detect_broken_links_ignores_urls(temp_project):
    """Test that URL links are not flagged as broken."""
    add_reference(
        title="Documentation",
        body="See [GitHub](https://github.com/example/repo) for code"
    )

    gaps = detect_gaps(temp_project)

    broken_link_gaps = [g for g in gaps if g.type == "broken_link"]
    # Should not flag https:// links
    assert not any("github.com" in g.description for g in broken_link_gaps)


def test_gap_severity_levels(temp_project):
    """Test that gaps have appropriate severity levels."""
    # Create orphaned file
    src_dir = temp_project / "src"
    src_dir.mkdir()
    (src_dir / "code.py").write_text("pass")

    gaps = detect_gaps(temp_project)

    for gap in gaps:
        assert gap.severity in ["high", "medium", "low"]

    # Orphaned files should be medium severity
    orphaned = [g for g in gaps if g.type == "orphaned_code"]
    if orphaned:
        assert orphaned[0].severity == "medium"


def test_gap_suggestions(temp_project):
    """Test that gaps include actionable suggestions."""
    src_dir = temp_project / "src"
    src_dir.mkdir()
    (src_dir / "module.py").write_text("pass")

    gaps = detect_gaps(temp_project)

    for gap in gaps:
        assert gap.suggestion  # Should have a suggestion
        assert gap.suggestion.startswith("idlergear")  # Should be a command


def test_auto_fix_gap_returns_false(temp_project):
    """Test that auto-fix currently returns False (not implemented)."""
    gap = KnowledgeGap(
        type="orphaned_code",
        severity="medium",
        location="test.py",
        description="Test gap",
        suggestion="idlergear file annotate test.py",
        auto_fixable=False
    )

    result = auto_fix_gap(gap)
    assert result is False


def test_gap_report_empty(temp_project):
    """Test gap report with no gaps."""
    # Clean project with no gaps
    report = gap_report([])

    assert "No knowledge gaps detected" in report


def test_gap_report_with_gaps(temp_project):
    """Test gap report formatting with gaps."""
    gaps = [
        KnowledgeGap(
            type="orphaned_code",
            severity="high",
            location="src/main.py",
            description="File without annotation",
            suggestion="idlergear file annotate src/main.py",
            auto_fixable=False
        ),
        KnowledgeGap(
            type="broken_link",
            severity="medium",
            location="docs/README.md",
            description="Link to missing file",
            suggestion="Fix link in docs/README.md",
            auto_fixable=False
        )
    ]

    report = gap_report(gaps)

    assert "HIGH Priority" in report
    assert "MEDIUM Priority" in report
    assert "orphaned code" in report.lower()
    assert "src/main.py" in report
    assert "broken link" in report.lower()


def test_gaps_exclude_ignored_directories(temp_project):
    """Test that gaps detection ignores venv, node_modules, etc."""
    # Create files in ignored directories
    venv_dir = temp_project / "venv"
    venv_dir.mkdir()
    (venv_dir / "lib.py").write_text("pass")

    node_modules = temp_project / "node_modules"
    node_modules.mkdir()
    (node_modules / "module.js").write_text("console.log('hi')")

    gaps = detect_gaps(temp_project)

    orphaned = [g for g in gaps if g.type == "orphaned_code"]
    # Should not flag files in venv or node_modules
    assert not any("venv" in g.location for g in orphaned)
    assert not any("node_modules" in g.location for g in orphaned)


def test_empty_project_has_no_gaps(temp_project):
    """Test that an empty project has no gaps."""
    gaps = detect_gaps(temp_project)

    # Empty project should have no gaps
    assert len(gaps) == 0


def test_gap_context_data(temp_project):
    """Test that gaps include context data."""
    src_dir = temp_project / "src"
    src_dir.mkdir()
    (src_dir / "app.py").write_text("pass")

    gaps = detect_gaps(temp_project)

    orphaned = [g for g in gaps if g.type == "orphaned_code"]
    if orphaned:
        gap = orphaned[0]
        assert gap.context is not None
        assert "file_path" in gap.context
