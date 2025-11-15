import pytest
import tempfile
import os
from pathlib import Path
from src.main import replace_placeholders


class TestPlaceholderReplacement:
    """Tests for placeholder replacement functionality."""

    def test_replace_single_placeholder(self):
        """Test replacing a single placeholder in a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Project: {{PROJECT_NAME}}")
            
            replace_placeholders(tmpdir, {"PROJECT_NAME": "my-project"})
            
            assert test_file.read_text() == "Project: my-project"

    def test_replace_multiple_placeholders(self):
        """Test replacing multiple placeholders in a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("# {{PROJECT_NAME}}\n\nAuthor: {{AUTHOR}}")
            
            replace_placeholders(tmpdir, {
                "PROJECT_NAME": "awesome-app",
                "AUTHOR": "testuser"
            })
            
            content = test_file.read_text()
            assert "awesome-app" in content
            assert "testuser" in content
            assert "{{PROJECT_NAME}}" not in content
            assert "{{AUTHOR}}" not in content

    def test_replace_placeholders_multiple_files(self):
        """Test replacing placeholders across multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"
            
            file1.write_text("Name: {{PROJECT_NAME}}")
            file2.write_text("Also: {{PROJECT_NAME}}")
            
            replace_placeholders(tmpdir, {"PROJECT_NAME": "test-project"})
            
            assert file1.read_text() == "Name: test-project"
            assert file2.read_text() == "Also: test-project"

    def test_ignore_binary_files(self):
        """Test that binary files are ignored without errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            binary_file = Path(tmpdir) / "binary.bin"
            binary_file.write_bytes(b"\x00\x01\x02\xff\xfe")
            
            # Should not raise an error
            replace_placeholders(tmpdir, {"PROJECT_NAME": "test"})
            
            # Binary content should be unchanged
            assert binary_file.read_bytes() == b"\x00\x01\x02\xff\xfe"

    def test_nested_directory_replacement(self):
        """Test placeholder replacement in nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            
            nested_file = subdir / "nested.txt"
            nested_file.write_text("{{PROJECT_NAME}}")
            
            replace_placeholders(tmpdir, {"PROJECT_NAME": "nested-test"})
            
            assert nested_file.read_text() == "nested-test"
