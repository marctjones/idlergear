"""Tests for filesystem server."""

import tempfile
from pathlib import Path
import pytest

from idlergear.fs import FilesystemServer, FilesystemError, SecurityError


class TestFilesystemServer:
    """Tests for FilesystemServer."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def fs_server(self, temp_dir):
        """Create a filesystem server with temp directory as allowed dir."""
        return FilesystemServer(allowed_dirs=[str(temp_dir)])

    def test_read_file(self, fs_server, temp_dir):
        """Test reading a file."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello, World!")

        result = fs_server.read_file(str(test_file))

        assert result["content"] == "Hello, World!"
        assert result["size"] == 13
        assert "test.txt" in result["path"]

    def test_write_file(self, fs_server, temp_dir):
        """Test writing a file."""
        test_file = temp_dir / "new.txt"

        result = fs_server.write_file(str(test_file), "Test content")

        assert test_file.exists()
        assert test_file.read_text() == "Test content"
        assert result["size"] == 12

    def test_create_directory(self, fs_server, temp_dir):
        """Test creating a directory."""
        new_dir = temp_dir / "subdir" / "nested"

        result = fs_server.create_directory(str(new_dir))

        assert new_dir.exists()
        assert new_dir.is_dir()
        assert result["created"] is True

    def test_list_directory(self, fs_server, temp_dir):
        """Test listing directory contents."""
        # Create some files
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.py").write_text("content2")
        (temp_dir / "subdir").mkdir()

        result = fs_server.list_directory(str(temp_dir))

        assert len(result["entries"]) == 3
        names = {entry["name"] for entry in result["entries"]}
        assert names == {"file1.txt", "file2.py", "subdir"}

    def test_directory_tree(self, fs_server, temp_dir):
        """Test generating directory tree."""
        # Create nested structure
        (temp_dir / "dir1").mkdir()
        (temp_dir / "dir1" / "file1.txt").write_text("content1")
        (temp_dir / "dir2").mkdir()
        (temp_dir / "file2.txt").write_text("content2")

        result = fs_server.directory_tree(str(temp_dir))

        assert result["name"] == temp_dir.name
        assert result["type"] == "directory"
        assert "children" in result
        assert len(result["children"]) == 3

    def test_search_files(self, fs_server, temp_dir):
        """Test searching for files."""
        # Create test files
        (temp_dir / "test1.py").write_text("print('1')")
        (temp_dir / "test2.py").write_text("print('2')")
        (temp_dir / "test.txt").write_text("text")
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "test3.py").write_text("print('3')")

        result = fs_server.search_files(
            str(temp_dir), pattern="*.py", use_gitignore=False
        )

        assert result["count"] == 3
        assert all(path.endswith(".py") for path in result["matches"])

    def test_file_info(self, fs_server, temp_dir):
        """Test getting file info."""
        test_file = temp_dir / "info.txt"
        test_file.write_text("test content")

        result = fs_server.get_file_info(str(test_file))

        assert result["type"] == "file"
        assert result["size"] == 12
        assert "modified" in result
        assert "created" in result

    def test_file_checksum(self, fs_server, temp_dir):
        """Test calculating file checksum."""
        test_file = temp_dir / "checksum.txt"
        test_file.write_text("Hello, World!")

        result = fs_server.get_file_checksum(str(test_file), algorithm="sha256")

        assert result["algorithm"] == "sha256"
        assert len(result["checksum"]) == 64  # SHA256 produces 64 hex chars
        assert (
            result["checksum"]
            == "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        )

    def test_move_file(self, fs_server, temp_dir):
        """Test moving a file."""
        source = temp_dir / "source.txt"
        dest = temp_dir / "dest.txt"
        source.write_text("content")

        result = fs_server.move_file(str(source), str(dest))

        assert not source.exists()
        assert dest.exists()
        assert dest.read_text() == "content"

    def test_read_multiple_files(self, fs_server, temp_dir):
        """Test reading multiple files at once."""
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        result = fs_server.read_multiple_files([str(file1), str(file2)])

        assert len(result) == 2
        assert result[0]["content"] == "content1"
        assert result[1]["content"] == "content2"

    def test_security_outside_allowed_dir(self, fs_server, temp_dir):
        """Test that accessing files outside allowed dirs raises SecurityError."""
        outside_file = Path("/tmp") / "outside.txt"

        with pytest.raises(SecurityError):
            fs_server.read_file(str(outside_file))

    def test_security_parent_directory_traversal(self, fs_server, temp_dir):
        """Test that parent directory traversal is blocked."""
        malicious_path = str(temp_dir / ".." / ".." / "etc" / "passwd")

        with pytest.raises(SecurityError):
            fs_server.read_file(malicious_path)

    def test_file_not_found(self, fs_server, temp_dir):
        """Test that reading non-existent file raises error."""
        with pytest.raises(FilesystemError, match="File not found"):
            fs_server.read_file(str(temp_dir / "nonexistent.txt"))

    def test_exclude_patterns(self, fs_server, temp_dir):
        """Test that exclude patterns work."""
        # Create files
        (temp_dir / "keep.txt").write_text("keep")
        (temp_dir / "exclude.pyc").write_text("exclude")
        (temp_dir / "__pycache__").mkdir()

        result = fs_server.list_directory(str(temp_dir))

        # Should only see keep.txt, not .pyc or __pycache__
        assert len(result["entries"]) == 1
        assert result["entries"][0]["name"] == "keep.txt"

    def test_list_allowed_directories(self, fs_server, temp_dir):
        """Test listing allowed directories."""
        result = fs_server.list_allowed_directories()

        assert "allowed_directories" in result
        assert str(temp_dir) in result["allowed_directories"]
