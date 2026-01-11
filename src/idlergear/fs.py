#!/usr/bin/env python3
"""
IdlerGear Filesystem MCP Server

Replaces @modelcontextprotocol/server-filesystem with Python-native implementation.

Features:
- File operations (read, write, edit, move)
- Directory operations (list, tree, create)
- Search with gitignore-aware filtering
- File metadata and checksums
- Task-aware file searching
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import fnmatch

# Try to import gitignore parser, fall back to basic pattern matching
try:
    from gitignore_parser import parse_gitignore

    HAS_GITIGNORE_PARSER = True
except ImportError:
    HAS_GITIGNORE_PARSER = False


class FilesystemError(Exception):
    """Base exception for filesystem operations."""

    pass


class SecurityError(FilesystemError):
    """Raised when attempting to access forbidden paths."""

    pass


class FilesystemServer:
    """IdlerGear filesystem operations server."""

    DEFAULT_ALLOWED_DIRS = [os.getcwd()]
    DEFAULT_EXCLUDE_PATTERNS = [
        ".git",
        "__pycache__",
        "*.pyc",
        "node_modules",
        ".venv",
        "venv",
        "*.egg-info",
        "dist",
        "build",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        ".coverage",
        "htmlcov",
    ]

    def __init__(self, allowed_dirs: Optional[List[str]] = None):
        """
        Initialize filesystem server.

        Args:
            allowed_dirs: List of directories that can be accessed.
                         Defaults to current working directory.
        """
        self.allowed_dirs = [
            Path(d).resolve() for d in (allowed_dirs or self.DEFAULT_ALLOWED_DIRS)
        ]

    def _check_access(self, path: Union[str, Path]) -> Path:
        """
        Check if path is allowed to be accessed.

        Args:
            path: Path to check

        Returns:
            Resolved absolute path

        Raises:
            SecurityError: If path is outside allowed directories
        """
        resolved = Path(path).resolve()

        for allowed_dir in self.allowed_dirs:
            try:
                resolved.relative_to(allowed_dir)
                return resolved
            except ValueError:
                continue

        raise SecurityError(
            f"Access denied: {path} is outside allowed directories: "
            f"{[str(d) for d in self.allowed_dirs]}"
        )

    def read_file(self, path: str) -> Dict[str, Any]:
        """
        Read file contents.

        Args:
            path: Path to file

        Returns:
            {"content": str, "path": str, "size": int}
        """
        file_path = self._check_access(path)

        if not file_path.exists():
            raise FilesystemError(f"File not found: {path}")

        if not file_path.is_file():
            raise FilesystemError(f"Not a file: {path}")

        content = file_path.read_text()

        return {
            "content": content,
            "path": str(file_path),
            "size": file_path.stat().st_size,
        }

    def read_multiple_files(self, paths: List[str]) -> List[Dict[str, Any]]:
        """
        Read multiple files at once.

        Args:
            paths: List of file paths

        Returns:
            List of file contents (same format as read_file)
        """
        results = []
        for path in paths:
            try:
                results.append(self.read_file(path))
            except Exception as e:
                results.append({"path": path, "error": str(e)})
        return results

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """
        Write file contents.

        Args:
            path: Path to file
            content: Content to write

        Returns:
            {"path": str, "size": int}
        """
        file_path = self._check_access(path)

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(content)

        return {
            "path": str(file_path),
            "size": file_path.stat().st_size,
        }

    def create_directory(self, path: str) -> Dict[str, Any]:
        """
        Create directory (and parents if needed).

        Args:
            path: Path to directory

        Returns:
            {"path": str, "created": bool}
        """
        dir_path = self._check_access(path)

        existed = dir_path.exists()
        dir_path.mkdir(parents=True, exist_ok=True)

        return {
            "path": str(dir_path),
            "created": not existed,
        }

    def list_directory(
        self, path: str = ".", exclude_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        List directory contents.

        Args:
            path: Directory path
            exclude_patterns: Patterns to exclude (gitignore-style)

        Returns:
            {
                "path": str,
                "entries": [{
                    "name": str,
                    "type": "file"|"directory",
                    "size": int,
                    "modified": float
                }]
            }
        """
        dir_path = self._check_access(path)

        if not dir_path.exists():
            raise FilesystemError(f"Directory not found: {path}")

        if not dir_path.is_dir():
            raise FilesystemError(f"Not a directory: {path}")

        exclude = exclude_patterns or self.DEFAULT_EXCLUDE_PATTERNS

        entries = []
        for item in sorted(dir_path.iterdir()):
            # Check exclude patterns
            if any(fnmatch.fnmatch(item.name, pattern) for pattern in exclude):
                continue

            stat = item.stat()
            entries.append(
                {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )

        return {
            "path": str(dir_path),
            "entries": entries,
        }

    def directory_tree(
        self,
        path: str = ".",
        max_depth: int = 3,
        exclude_patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate directory tree structure.

        Args:
            path: Root directory
            max_depth: Maximum recursion depth
            exclude_patterns: Patterns to exclude

        Returns:
            Tree structure with nested entries
        """
        dir_path = self._check_access(path)

        if not dir_path.exists():
            raise FilesystemError(f"Directory not found: {path}")

        if not dir_path.is_dir():
            raise FilesystemError(f"Not a directory: {path}")

        exclude = exclude_patterns or self.DEFAULT_EXCLUDE_PATTERNS

        def build_tree(current_path: Path, depth: int) -> Dict[str, Any]:
            if depth > max_depth:
                return None

            stat = current_path.stat()
            node = {
                "name": current_path.name,
                "type": "directory" if current_path.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
            }

            if current_path.is_dir():
                children = []
                for item in sorted(current_path.iterdir()):
                    # Check exclude patterns
                    if any(fnmatch.fnmatch(item.name, p) for p in exclude):
                        continue

                    child = build_tree(item, depth + 1)
                    if child:
                        children.append(child)

                if children:
                    node["children"] = children

            return node

        return build_tree(dir_path, 0)

    def move_file(self, source: str, destination: str) -> Dict[str, Any]:
        """
        Move or rename file/directory.

        Args:
            source: Source path
            destination: Destination path

        Returns:
            {"source": str, "destination": str}
        """
        src_path = self._check_access(source)
        dst_path = self._check_access(destination)

        if not src_path.exists():
            raise FilesystemError(f"Source not found: {source}")

        shutil.move(str(src_path), str(dst_path))

        return {
            "source": str(src_path),
            "destination": str(dst_path),
        }

    def search_files(
        self,
        path: str = ".",
        pattern: str = "*",
        exclude_patterns: Optional[List[str]] = None,
        use_gitignore: bool = True,
    ) -> Dict[str, Any]:
        """
        Search for files matching pattern.

        Args:
            path: Root directory to search
            pattern: Glob pattern (e.g., "*.py", "test_*.py")
            exclude_patterns: Additional patterns to exclude
            use_gitignore: Whether to respect .gitignore files

        Returns:
            {
                "matches": [str],
                "count": int
            }
        """
        dir_path = self._check_access(path)

        if not dir_path.exists():
            raise FilesystemError(f"Directory not found: {path}")

        exclude = exclude_patterns or self.DEFAULT_EXCLUDE_PATTERNS

        # Load gitignore if available
        gitignore_matcher = None
        if use_gitignore and HAS_GITIGNORE_PARSER:
            gitignore_path = dir_path / ".gitignore"
            if gitignore_path.exists():
                gitignore_matcher = parse_gitignore(gitignore_path)

        matches = []
        for item in dir_path.rglob(pattern):
            # Check access (must be within allowed dirs)
            try:
                self._check_access(item)
            except SecurityError:
                continue

            # Check exclude patterns
            if any(fnmatch.fnmatch(item.name, p) for p in exclude):
                continue

            # Check gitignore
            if gitignore_matcher and gitignore_matcher(str(item)):
                continue

            matches.append(str(item))

        return {
            "matches": sorted(matches),
            "count": len(matches),
        }

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """
        Get file metadata.

        Args:
            path: File path

        Returns:
            File metadata including size, timestamps, permissions
        """
        file_path = self._check_access(path)

        if not file_path.exists():
            raise FilesystemError(f"Path not found: {path}")

        stat = file_path.stat()

        return {
            "path": str(file_path),
            "type": "directory" if file_path.is_dir() else "file",
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime,
            "permissions": oct(stat.st_mode)[-3:],
        }

    def get_file_checksum(self, path: str, algorithm: str = "sha256") -> Dict[str, Any]:
        """
        Calculate file checksum.

        Args:
            path: File path
            algorithm: Hash algorithm (md5, sha1, sha256)

        Returns:
            {"path": str, "algorithm": str, "checksum": str}
        """
        file_path = self._check_access(path)

        if not file_path.exists():
            raise FilesystemError(f"File not found: {path}")

        if not file_path.is_file():
            raise FilesystemError(f"Not a file: {path}")

        if algorithm == "md5":
            hasher = hashlib.md5()
        elif algorithm == "sha1":
            hasher = hashlib.sha1()
        elif algorithm == "sha256":
            hasher = hashlib.sha256()
        else:
            raise FilesystemError(f"Unsupported algorithm: {algorithm}")

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)

        return {
            "path": str(file_path),
            "algorithm": algorithm,
            "checksum": hasher.hexdigest(),
        }

    def list_allowed_directories(self) -> Dict[str, Any]:
        """
        List all allowed directories.

        Returns:
            {"allowed_directories": [str]}
        """
        return {"allowed_directories": [str(d) for d in self.allowed_dirs]}
